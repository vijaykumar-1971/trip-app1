import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# 1. SETUP & ERROR CATCHING
st.set_page_config(page_title="TripSplit", layout="centered")

def get_connection():
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Secret Connection Failed: {e}")
        return None

conn = get_connection()

# 2. DATA VALIDATION
if conn is not None:
    try:
        f_all = conn.read(worksheet="friends", ttl=0).dropna(how="all")
        e_all = conn.read(worksheet="expenses", ttl=0).dropna(how="all")
        st.sidebar.success("✅ Connected to Google Sheets")
    except Exception as e:
        st.error(f"Could not read Sheets. Check tab names 'friends' and 'expenses'. Error: {e}")
        st.stop()
else:
    st.stop()

# 3. APP LOGIC
st.title("✈️ TripSplit Pro")

# Trip Selector
existing_trips = f_all['trip_id'].unique().tolist() if not f_all.empty else []
active_trip = st.sidebar.selectbox("Select Trip", existing_trips) if existing_trips else st.sidebar.text_input("Trip Name")

# Filter
friends_df = f_all[f_all['trip_id'] == active_trip] if not f_all.empty else pd.DataFrame()
expenses_df = e_all[e_all['trip_id'] == active_trip] if not e_all.empty else pd.DataFrame()

# Tabs for UX
tab1, tab2 = st.tabs(["💸 Expenses", "📜 History & PDF"])

with tab1:
    if not friends_df.empty:
        with st.form("new_exp"):
            item = st.text_input("What for?")
            amt = st.number_input("Amount", min_value=1.0)
            pay = st.selectbox("Who paid?", friends_df['name'])
            if st.form_submit_button("Save"):
                # Simplified saving logic
                st.success("Expense added! (Refreshing...)")
                # Add logic here...
                st.rerun()
    else:
        st.info("No members found. Join in the sidebar!")

with tab2:
    st.dataframe(expenses_df)
    if st.button("Generate Summary"):
        st.write("Generating...")
