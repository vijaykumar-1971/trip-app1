import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="TripSplit Pro", layout="centered")

REQUIRED_STRUCTURE = {
    "friends": ["trip_id", "name", "upi_id"],
    "expenses": ["trip_id", "description", "amount", "payer", "involved"]
}

# --- 2. VALIDATOR & LOADER ---
def validate_and_load():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        f = conn.read(worksheet="friends", ttl=0).dropna(how="all")
        e = conn.read(worksheet="expenses", ttl=0).dropna(how="all")
        
        missing_f = [col for col in REQUIRED_STRUCTURE["friends"] if col not in f.columns]
        missing_e = [col for col in REQUIRED_STRUCTURE["expenses"] if col not in e.columns]
        
        if missing_f or missing_e:
            return f, e, f"Mismatch! Check Row 1 in Sheets."
        return f, e, None
    except Exception as err:
        return None, None, str(err)

# --- 3. SYSTEM CHECK ---
st.title("✈️ TripSplit Pro")
f_all, e_all, error_msg = validate_and_load()

if error_msg:
    st.error(f"🚨 Connection Error: {error_msg}")
    st.stop()

# --- 4. SIDEBAR: TRIP & USER MANAGEMENT ---
existing_trips = f_all['trip_id'].unique().tolist() if not f_all.empty else []

with st.sidebar:
    st.header("📍 Trip Selection")
    active_trip = st.selectbox("Current Trip", existing_trips) if existing_trips else st.text_input("New Trip Name")
    
    if st.button("➕ Create New Trip"):
        st.info("Enter a name above and Join to start!")
        
    st.divider()
    st.subheader("👤 Join Group")
    u_name = st.text_input("Your Name")
    u_upi = st.text_input("UPI ID")
    if st.button("Join"):
        if u_name and u_upi:
            new_f = pd.concat([f_all, pd.DataFrame([{"trip_id": active_trip, "name": u_name, "upi_id": u_upi}])], ignore_index=True)
            st.connection("gsheets", type=GSheetsConnection).update(worksheet="friends", data=new_f)
            st.rerun()

# Filter data
friends_df = f_all[f_all['trip_id'] == active_trip] if not f_all.empty else pd.DataFrame()
expenses_df = e_all[e_all['trip_id'] == active_trip] if not e_all.empty else pd.DataFrame()

if friends_df.empty:
    st.info("No members in this trip yet. Use the sidebar to join!")
    st.stop()

# --- 5. TABS: EXPENSES, SETTLEMENTS, HISTORY ---
tab1, tab2, tab3 = st.tabs(["💸 Add Expense", "🤝 Settlements", "📜 History"])

with tab1:
    with st.form("add_ex"):
        item = st.text_input("Description")
        amt = st.number_input("Amount", min_value=1.0)
        payer = st.selectbox("Who paid?", friends_df['name'])
        involved = st.multiselect("Split with?", friends_df['name'], default=friends_df['name'].tolist())
        if st.form_submit_button("Save Expense"):
            new_row = pd.DataFrame([{"trip_id": active_trip, "description": item, "amount": amt, "payer": payer, "involved": ";".join(involved)}])
            updated_e = pd.concat([e_all, new_row], ignore_index=True)
            st.connection("gsheets", type=GSheetsConnection).update(worksheet="expenses", data=updated_e)
            st.rerun()

with tab2:
    st.subheader("Who owes Whom")
    balances = {n: 0.0 for n in friends_df["name"]}
    for _, row in expenses_df.iterrows():
        inv_list = str(row['involved']).split(";")
        share = float(row['amount']) / len(inv_list)
        balances[row['payer']] += float(row['amount'])
        for p in inv_list:
            if p in balances: balances[p] -= share

    debtors = sorted([[p, a] for p, a in balances.items() if a < -1], key=lambda x: x[1])
    creditors = sorted([[p, a] for p, a in balances.items() if a > 1], key=lambda x: x[1], reverse=True)

    summary_text = []
    for d in debtors:
        for c in creditors:
            if c[1] <= 0: continue
            pay_amt = min(abs(d[1]), c[1])
            c_upi = friends_df[friends_df['name'] == c[0]]['upi_id'].iloc[0]
            st.write(f"🔴 **{d[0]}** owes **{c[0]}**: ₹{pay_amt:.2f}")
            
            pay_url = f"upi://pay?pa={c_upi}&pn={c[0]}&am={pay_amt:.2f}&cu=INR"
            st.markdown(f'[<button style="background-color:#28a745;color:white;border:none;border-radius:5px;padding:5px 10px;cursor:pointer;">Pay Now</button>]({pay_url})', unsafe_allow_html=True)
            
            summary_text.append(f"{d[0]} owes {c[0]}: Rs. {pay_amt:.2f}")
            d[1] += pay_amt
            c[1] -= pay_amt

    if summary_text:
        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", 'B', 16)
            pdf.cell(0, 10, f"Trip: {active_trip}", align='C', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", size=12); pdf.ln(10)
            for line in summary_text: pdf.cell(0, 10, line, new_x="LMARGIN", new_y="NEXT")
            return pdf.output()
        st.download_button("📥 Download PDF Report", data=generate_pdf(), file_name=f"{active_trip}.pdf")

with tab3:
    st.subheader("Expense History")
    if not expenses_df.empty:
        for i, row in expenses_df.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['description']}**")
            c2.write(f"₹{row['amount']}")
            if c3.button("🗑️", key=f"del_{i}"):
                # To delete, we drop this index from the ALL expenses dataframe
                updated_e = e_all.drop(i)
                st.connection("gsheets", type=GSheetsConnection).update(worksheet="expenses", data=updated_e)
                st.rerun()
    else:
        st.write("No expenses logged yet.")
