import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. SETTINGS & CLOUD CONNECTION ---
st.set_page_config(page_title="TripSplit Pro", layout="centered")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 ensures we always get the freshest data from the group
    try:
        friends = conn.read(worksheet="friends", ttl=0)
        expenses = conn.read(worksheet="expenses", ttl=0)
        return friends, expenses
    except:
        # Returns empty dataframes if sheets are not yet initialized
        return pd.DataFrame(columns=["trip_id", "name", "upi_id"]), pd.DataFrame(columns=["trip_id", "description", "amount", "payer", "involved"])

f_all, e_all = load_data()

# --- 2. MULTI-TRIP SELECTOR ---
st.title("✈️ TripSplit: Group Expense Manager")

# Get list of unique trips already in the sheet
existing_trips = f_all['trip_id'].unique().tolist() if not f_all.empty else []

with st.sidebar:
    st.header("📍 Trip Selection")
    if existing_trips:
        active_trip = st.selectbox("Current Trip", existing_trips)
    else:
        active_trip = st.text_input("First Trip Name (e.g. Goa2025)")
    
    st.divider()
    new_trip_name = st.text_input("Create New Trip Name")
    if st.button("➕ Start New Trip"):
        if new_trip_name:
            active_trip = new_trip_name
            st.success(f"Trip '{active_trip}' selected!")

    st.header("👤 Join this Trip")
    u_name = st.text_input("Your Name")
    u_upi = st.text_input("UPI ID (e.g. name@okaxis)")
    if st.button("Join Group"):
        if u_name and u_upi:
            new_f = pd.concat([f_all, pd.DataFrame([{"trip_id": active_trip, "name": u_name, "upi_id": u_upi}])], ignore_index=True)
            conn.update(worksheet="friends", data=new_f)
            st.success(f"{u_name} joined {active_trip}!")
            st.rerun()

# --- 3. FILTER DATA FOR ACTIVE TRIP ---
friends_df = f_all[f_all['trip_id'] == active_trip] if not f_all.empty else pd.DataFrame()
expenses_df = e_all[e_all['trip_id'] == active_trip] if not e_all.empty else pd.DataFrame()

# --- 4. ADD EXPENSE SECTION ---
if not friends_df.empty:
    st.subheader(f"Current Trip: {active_trip}")
    with st.expander("💸 Add a New Expense"):
        with st.form("exp_form"):
            item = st.text_input("Description (e.g. Dinner)")
            amt = st.number_input("Amount", min_value=1.0)
            payer = st.selectbox("Who paid?", friends_df["name"])
            involved = st.multiselect("Who shared this?", friends_df["name"], default=friends_df["name"].tolist())
            
            if st.form_submit_button("Save to Cloud"):
                if item and involved:
                    new_e = pd.concat([e_all, pd.DataFrame([{
                        "trip_id": active_trip, "description": item, 
                        "amount": amt, "payer": payer, "involved": ";".join(involved)
                    }])], ignore_index=True)
                    conn.update(worksheet="expenses", data=new_e)
                    st.rerun()

    # --- 5. SETTLEMENT LOGIC & UPI ---
    st.divider()
    st.subheader("🤝 Who owes Whom")
    
    balances = {n: 0.0 for n in friends_df["name"]}
    for _, row in expenses_df.iterrows():
        inv_list = str(row['involved']).split(";")
        share = float(row['amount']) / len(inv_list)
        balances[row['payer']] += float(row['amount'])
        for p in inv_list:
            if p in balances: balances[p] -= share

    debtors = sorted([[p, a] for p, a in balances.items() if a < -1], key=lambda x: x[1])
    creditors = sorted([[p, a] for p, a in balances.items() if a > 1], key=lambda x: x[1], reverse=True)

    settlement_list_text = [] 
    
    for d in debtors:
        for c in creditors:
            if c[1] <= 0: continue
            pay_amt = min(abs(d[1]), c[1])
            c_upi = friends_df[friends_df['name'] == c[0]]['upi_id'].iloc[0]
            
            col1, col2 = st.columns([3, 1])
            col1.write(f"🔴 **{d[0]}** owes **{c[0]}**: ₹{pay_amt:.2f}")
            
            pay_url = f"upi://pay?pa={c_upi}&pn={c[0]}&am={pay_amt:.2f}&cu=INR"
            col2.markdown(f'[<button style="background-color:#28a745;color:white;border:none;border-radius:5px;padding:5px 10px;cursor:pointer;">Pay</button>]({pay_url})', unsafe_allow_html=True)
            
            settlement_list_text.append(f"{d[0]} owes {c[0]}: Rs. {pay_amt:.2f}")
            d[1] += pay_amt
            c[1] -= pay_amt

    # --- 6. PDF EXPORT ---
    if not expenses_df.empty:
        st.divider()
        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=f"Trip Report: {active_trip}", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="Settlements:", ln=True)
            pdf.set_font("Arial", size=11)
            for line in settlement_list_text:
                pdf.cell(200, 8, txt=line, ln=True)
            return pdf.output(dest='S').encode('latin-1')

        st.download_button("Download PDF Report", data=generate_pdf(), file_name=f"{active_trip}.pdf", mime="application/pdf")
else:
    st.info("No members joined this trip yet. Use the sidebar to join!")
