# =============================================
# app.py — Streamlit RFM Customer Segmentation
# =============================================

import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="RFM Customer Segmentation", layout="wide")
st.title("RFM Customer Segmentation Tool")
st.write("Upload your transaction CSV to compute RFM metrics and visualize customer segments.")

# --- REQUIRED COLUMNS ---
REQUIRED_COLUMNS = ['customer_id', 'order_id', 'order_date', 'order_value']

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload your dataset (CSV)", type="csv")

if uploaded_file is not None:
    # Load CSV
    df = pd.read_csv(uploaded_file)

    # Validate required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}. Please check your file.")
        st.stop()

    # Preview data
    st.subheader("Data Preview (first 10 rows)")
    st.dataframe(df.head(10))

    # --- DATA PREP ---
    df['order_date'] = pd.to_datetime(df['order_date'])
    snapshot_date = df['order_date'].max()

    # --- INTERACTIVE FILTER ---
    st.subheader("Filter by Customer Segment")
    segment_options = ['All', 'High Value', 'Loyal', 'Occasional', 'At Risk']
    selected_segment = st.selectbox("Select segment to display:", segment_options)

    # --- RFM CALCULATION ---
    rfm = df.groupby('customer_id').agg(
        recency=('order_date', lambda x: (snapshot_date - x.max()).days),
        frequency=('order_id', 'count'),
        monetary=('order_value', 'sum')
    ).reset_index()

    # Normalize scores
    def min_max_normalize(series):
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:
            return pd.Series([50.0]*len(series), index=series.index)
        return ((series - min_val) / (max_val - min_val) * 100).round(2)

    rfm['recency_score'] = min_max_normalize(rfm['recency'])
    rfm['frequency_score'] = min_max_normalize(rfm['frequency'])
    rfm['monetary_score'] = min_max_normalize(rfm['monetary'])

    # Weighted RFM score
    W_RECENCY, W_FREQUENCY, W_MONETARY = 0.33, 0.33, 0.34
    rfm['rfm_score'] = (
        W_RECENCY * rfm['recency_score'] +
        W_FREQUENCY * rfm['frequency_score'] +
        W_MONETARY * rfm['monetary_score']
    ).round(2)

    # Segmentation
    p20, p50, p80 = rfm['rfm_score'].quantile([0.2, 0.5, 0.8])

    def assign_segment(score):
        if score >= p80:
            return 'High Value'
        elif score >= p50:
            return 'Loyal'
        elif score >= p20:
            return 'Occasional'
        else:
            return 'At Risk'

    rfm['segment'] = rfm['rfm_score'].apply(assign_segment)

    # Apply filter
    if selected_segment != 'All':
        rfm = rfm[rfm['segment'] == selected_segment]

    # --- METRICS ---
    st.subheader("Key Metrics")
    st.metric("Average Monetary Value", round(rfm['monetary'].mean(), 2))
    st.metric("Average Recency (days)", round(rfm['recency'].mean(), 1))
    st.metric("Average Frequency", round(rfm['frequency'].mean(), 1))

    # --- CHARTS ---
    st.subheader("Customer Segmentation Scatter Plot")
    fig = px.scatter(
        rfm,
        x='frequency',
        y='monetary',
        color='segment',
        size='rfm_score',
        title='Customer Value Segmentation',
        hover_data=['customer_id', 'recency']
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- INTERPRETATION ---
    st.subheader("Interpretation")
    st.info("""
    - **Recency:** Lower days indicate recent purchases (more engaged customers).
    - **Frequency:** Number of purchases; higher = more loyal.
    - **Monetary:** Total spending; higher = more valuable.
    - **Segments:** High Value = top customers, Loyal = frequent, Occasional = moderate, At Risk = inactive.
    """)