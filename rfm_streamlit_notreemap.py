import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="RFM Analysis App", layout="wide")
st.title("📊 RFM Customer Segmentation")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if {'customer_id', 'sales', 'date'}.issubset(df.columns):
        df['date'] = pd.to_datetime(df['date'])

        # Date filter UI
        min_date, max_date = df['date'].min(), df['date'].max()
        start_date, end_date = st.slider("Select date range", min_value=min_date.date(), max_value=max_date.date(),
                                         value=(min_date.date(), max_date.date()))
        df = df[df['date'].dt.date.between(start_date, end_date)]

        ref_date = df['date'].max() + pd.Timedelta(days=1)

        rfm = df.groupby('customer_id').agg({
            'date': lambda x: (ref_date - x.max()).days,
            'item_id': 'count',
            'sales': 'sum'
        }).reset_index()
        rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']

        rfm['recency_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1]).astype(int)
        rfm['frequency_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm['monetary_score'] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5]).astype(int)

        rfm['RFM_Segment'] = (
            rfm['recency_score'].astype(str) +
            rfm['frequency_score'].astype(str) +
            rfm['monetary_score'].astype(str)
        )
        rfm['RFM_Score'] = rfm[['recency_score', 'frequency_score', 'monetary_score']].sum(axis=1)

        def segment_customer(row):
            if row['RFM_Score'] >= 13:
                return 'Champions'
            elif row['recency_score'] >= 4 and row['frequency_score'] >= 4:
                return 'Loyal'
            elif row['recency_score'] >= 4:
                return 'Recent'
            elif row['frequency_score'] >= 4:
                return 'Frequent'
            elif row['RFM_Score'] <= 5:
                return 'At Risk'
            else:
                return 'Others'

        rfm['Segment'] = rfm.apply(segment_customer, axis=1)

        # Filter segments
        rfm_full = rfm.copy()
        segments = st.multiselect("Filter by Segment", options=rfm_full['Segment'].unique(),
                                  default=rfm_full['Segment'].unique())
        rfm = rfm_full[rfm_full['Segment'].isin(segments)]

        st.subheader("📋 RFM Table with Customer Segments")
        st.dataframe(rfm)

        st.markdown("""
        ### 📘 How to Read This
        - **Recency**: Days since last purchase. Lower is better.
        - **Frequency**: Number of purchases. Higher is better.
        - **Monetary**: Total spent. Higher is better.
        - **RFM Score**: Combined score (max 15). Champions score highest.
        - **Segment**: Quick classification:
            - 🏆 Champions: High RFM – recent, loyal, valuable.
            - 🔁 Loyal: Frequent buyers.
            - 🆕 Recent: New or recently active.
            - 💰 Frequent: Repeat buyers but not always recent.
            - ⚠️ At Risk: Haven't bought in a long time.
        """)

        st.subheader("📊 RFM Score Distribution")
        fig_hist = px.histogram(rfm, x='RFM_Score', nbins=10, title="RFM Score Histogram")
        st.plotly_chart(fig_hist, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            rfm.to_excel(writer, sheet_name="RFM_Results", index=False)
            workbook = writer.book
            worksheet = writer.sheets["RFM_Results"]
            for col_num, value in enumerate(rfm.columns.values):
                worksheet.write(0, col_num, value)
        st.download_button("📥 Download Excel", data=buffer.getvalue(),
                           file_name="rfm_segmented.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    else:
        st.error("❌ Required columns: customer_id, sales, date")
else:
    st.info("📁 Please upload an Excel file.")
