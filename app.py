import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF

# --- 1. APP CONFIG ---
st.set_page_config(page_title="TripSplit Validator", layout="centered")

# --- 2. DEFINE THE REQUIRED STRUCTURE ---
REQUIRED_STRUCTURE = {
    "friends": ["trip_id", "name", "upi_id"],
    "expenses": ["trip_id", "description", "amount", "payer", "involved"]
}

# --- 3. THE VALIDATOR ENGINE ---
def validate_and_load():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Load the data
        f = conn.read(worksheet="friends", ttl=0)
        e = conn.read(worksheet="expenses", ttl=0)
        
        # Check Columns
        missing_f = [col for col in REQUIRED_STRUCTURE["friends"] if col not in f.columns]
        missing_e = [col for col in REQUIRED_STRUCTURE["expenses"] if col not in e.columns]
        
        if missing_f or missing_e:
            error_details = ""
            if missing_f: error_details += f"**'friends' tab** is missing: {', '.join(missing_f)}\n\n"
            if missing_e: error_details += f"**'expenses' tab** is missing: {', '.join(missing_e)}"
            return None, None, f"Column Header Mismatch:\n\n{error_details}"
            
        return f, e, None
        
    except Exception as err:
        return None, None, f"Connection Failed: {str(err)}"

# --- 4. RUN THE CHECK ---
st.title("✈️ TripSplit Pro")

with st.status("🔍 Performing System Check...", expanded=False) as status:
    f_all, e_all, error_msg = validate_and_load()
    if error_msg:
        status.update(label="❌ System Check Failed", state="error")
        st.error(error_msg)
        st.info("💡 Pro-Tip: Column headers are case-sensitive. Use all lowercase (e.g., 'trip_id' NOT 'Trip_ID').")
        st.stop()
    else:
        status.update(label="✅ System Ready", state="complete")

# --- 5. APP LOGIC (Only runs if valid) ---
# Your existing code for Trip Selection, Add Expense, and Settlement...
st.success("Successfully connected to your Google Sheet.")

# (Rest of the app continues here)
