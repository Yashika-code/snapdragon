import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime

# Streamlit Cloud Entrypoint for SettleIQ

# Load environment variables or Streamlit Secrets
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
if "RAZORPAY_KEY_ID" in st.secrets:
    os.environ["RAZORPAY_KEY_ID"] = st.secrets["RAZORPAY_KEY_ID"]
if "RAZORPAY_KEY_SECRET" in st.secrets:
    os.environ["RAZORPAY_KEY_SECRET"] = st.secrets["RAZORPAY_KEY_SECRET"]

# Import app logic from app.py
from app import main

if __name__ == "__main__":
    main()
