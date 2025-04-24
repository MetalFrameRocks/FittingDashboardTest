import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import pytz

# Load credentials
cred = service_account.Credentials.from_service_account_file("firebase_key.json")
db = firestore.Client(credentials=cred, project="metal-frame-fitting-fbef7")

st.set_page_config(page_title="Fitting Dashboard", layout="wide")

# Center the title using HTML
st.markdown("<h1 style='text-align: center;'>📦 Fitting Dashboard</h1>", unsafe_allow_html=True)

# Load data from Firestore
docs = db.collection("submissions").stream()
data = []
for doc in docs:
    d = doc.to_dict()
    if "timestamp" in d and d["timestamp"] is not None:
        d["timestamp"] = pd.to_datetime(d["timestamp"].isoformat())
    data.append(d)

if data:
    df = pd.DataFrame(data)

    # Drop rows without timestamp
    df = df.dropna(subset=["timestamp"])

    # Convert UTC to IST
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
    df["date"] = df["timestamp"].dt.date  # Date-only for filters

    # --- 📅 Top KPI and Date Range Selector ---
    st.markdown("### 🧾 Summary")

    # Date range limits
    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    # Two equal-width columns with aligned headings
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Summary")
        total_qty = df["quantity"].sum()
        st.markdown(f"""
        <div style='
            border: 1px solid #e1e1e1;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
            background-color: rgba(14,17,23,0.7);
            text-align: center;
            margin-top: 10px;
        '>
            <h1 style='font-weight: bold; margin-bottom: 5px;'>{int(total_qty)}</h1>
            <p style='font-size: 18px;'>📦 Total Quantity</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Slicers")
        selected_date_range = st.date_input(
            label="",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="top_date_range"
        )

        selected_model = st.multiselect(
            label="",
            options=["All Models"] + df['model'].unique().tolist(),
            default=["All Models"],
            key="model_filter"
        )   

    # Filter the dataframe based on the selected date range
    filtered_df = df[
        (df["date"] >= selected_date_range[0]) & 
        (df["date"] <= selected_date_range[1])
    ]

    # Filter by model
    filtered_df = filtered_df.copy()
    if "All Models" not in selected_model:
        filtered_df = filtered_df[filtered_df['model'].isin(selected_model)]

    st.divider()

    # --- 📊 Unique Models Count per Day ---
    st.subheader("📊 Count of Unique Models Per Day")
    unique_models_df = filtered_df.groupby(filtered_df["timestamp"].dt.date)["model"].nunique().reset_index()
    unique_models_df.columns = ["Date", "Unique Models"]

    unique_models_chart = px.bar(
        unique_models_df,
        x="Date",
        y="Unique Models",
        title="Unique Models Count Per Day",
        text="Unique Models"
    )
    unique_models_chart.update_layout(xaxis_title="Date", yaxis_title="Model Count")
    st.plotly_chart(unique_models_chart, use_container_width=True)

    st.divider()

    st.markdown("""
    <style>
    .footer {
        position: fixed;
        right: 20px;
        bottom: 20px;
        background-color: rgba(0,0,0,0.7);
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        font-size: 14px;
        font-family: 'Arial', sans-serif;
        text-align: center;        
        font-weight: bold;                              
        z-index: 100;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    </style>
    <div class="footer">Made with ❤️ by Govind & Deepanshu</div>
    """, unsafe_allow_html=True)

    # --- 📊 Quantity Over Time (Hourly Bar Chart) ---
    st.subheader("📊 Quantity Over Time (Hourly)")
    hourly_df = filtered_df.copy()
    hourly_df['hour'] = hourly_df['timestamp'].dt.floor("H")
    hourly_summary = hourly_df.groupby('hour', as_index=False)['quantity'].sum().sort_values('hour')

    hourly_bar = px.bar(
        hourly_summary,
        x='hour',
        y='quantity',
        title="Quantity Over Time (Hourly)"
    )
    hourly_bar.update_layout(xaxis_title="Hour", yaxis_title="Quantity")
    hourly_bar.update_xaxes(tickformat='%d-%b\n%H:%M', tickangle=0)
    st.plotly_chart(hourly_bar, use_container_width=True)

    st.divider()

    # --- 📦 Total Quantity per Model (Time Filtered) ---
    st.subheader("📦 Total Quantity per Model")
    model_sum = filtered_df.groupby('model')['quantity'].sum().reset_index().sort_values("quantity", ascending=False)

    model_bar = px.bar(
        model_sum,
        x='model',
        y='quantity',
        color='model',
        title="Model-wise Total Quantity",
        text='quantity'
    )
    model_bar.update_layout(xaxis_title="Model", yaxis_title="Quantity")
    st.plotly_chart(model_bar, use_container_width=True)

    st.divider()

    # --- 📋 Full Data Table ---
    st.subheader("📋 Full Data (All Time)")
    full_data = df.sort_values("timestamp", ascending=False)
    if 'serial_number' in full_data.columns:
        full_data = full_data.drop(columns=['serial_number'])
    st.dataframe(full_data.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
else:
    st.warning("No data found yet.")
