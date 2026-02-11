import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF  # <--- This must look like this!
import datetime

# ... other code ...

# Inside your PDF function, use 'helvetica' (not Arial) to be safe:
def create_pdf_bytes():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16) # Helvetica is safer than Arial
    pdf.cell(0, 10, f"Trip Summary: {active_trip}", align='C', new_x="LMARGIN", new_y="NEXT")
    # ... rest of the code ...
    return pdf.output()
