# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime as dt
import plotly.express as px


st.set_page_config(layout="wide", page_title="UPI Transactions Dashboard")

@st.cache_data
def load_data(path = r'C:\Users\Welcome\Desktop\PROJRCT\upi_transactions_2024.csv'):
    df = pd.read_csv(path, low_memory=False)
    # basic parsing - adjust column names to your file
    # Try to infer a datetime column
    for c in df.columns:
        if 'date' in c.lower() or 'time' in c.lower():
            try:
                df['txn_datetime'] = pd.to_datetime(df[c], errors='coerce')
                break
            except:
                pass
    if 'txn_datetime' not in df.columns:
        # fallback: try common column names
        for name in ['transaction_date', 'timestamp', 'datetime']:
            if name in df.columns:
                df['txn_datetime'] = pd.to_datetime(df[name], errors='coerce')
                break

    # Example standard columns - replace with your dataset columns
    # Ensure these exist or edit names accordingly
    if 'amount (INR)' in df.columns:
        df['amount (INR)'] = pd.to_numeric(df['amount (INR)'], errors='coerce')
    elif 'txn_amount' in df.columns:
        df['amount (INR)'] = pd.to_numeric(df['txn_amount'], errors='coerce')

    # Feature engineering
    df['date'] = pd.to_datetime(df['txn_datetime']).dt.date
    df['month'] = pd.to_datetime(df['txn_datetime']).dt.to_period('M')
    df['hour'] = pd.to_datetime(df['txn_datetime']).dt.hour
    df['dayofweek'] = pd.to_datetime(df['txn_datetime']).dt.day_name()
    return df

df = load_data()

# --- Sidebar filters ---
st.sidebar.header("Filters")
min_date = pd.to_datetime(df['date']).min()
max_date = pd.to_datetime(df['date']).max()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# Adjust these filter names to your df's actual columns
state_col = [c for c in df.columns if 'state' in c.lower()]
bank_col = [c for c in df.columns if 'bank' in c.lower()]
merchant_col = [c for c in df.columns if 'merchant' in c.lower()]

state_options = ['All'] + sorted(df[state_col[0]].dropna().unique().tolist()) if state_col else ['All']
bank_options = ['All'] + sorted(df[bank_col[0]].dropna().unique().tolist()) if bank_col else ['All']
merchant_options = ['All'] + sorted(df[merchant_col[0]].dropna().unique().tolist()) if merchant_col else ['All']

state = st.sidebar.selectbox("State", state_options)
bank = st.sidebar.selectbox("Bank", bank_options)
merchant = st.sidebar.selectbox("Merchant", merchant_options)

# filters
mask = pd.Series(True, index=df.index)
start_d, end_d = date_range
mask &= pd.to_datetime(df['date']) >= pd.to_datetime(start_d)
mask &= pd.to_datetime(df['date']) <= pd.to_datetime(end_d)

if state != 'All' and state_col:
    mask &= df[state_col[0]] == state
if bank != 'All' and bank_col:
    mask &= df[bank_col[0]] == bank
if merchant != 'All' and merchant_col:
    mask &= df[merchant_col[0]] == merchant

filtered = df[mask].copy()

# --- KPI row ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions", f"{len(filtered):,}")
col2.metric("Total Volume", f"{filtered['amount (INR)'].sum():,.2f}")
col3.metric("Avg Amount", f"{filtered['amount (INR)'].mean():,.2f}")
col4.metric("Median Amount", f"{filtered['amount (INR)'].median():,.2f}")

# --- Time series ---
st.markdown("### Transactions Over Time")
time_agg = filtered.groupby('date').agg(txn_count=('amount (INR)','count'), txn_value=('amount (INR)','sum')).reset_index()
fig_ts = px.line(time_agg, x='date', y=['txn_count','txn_value'], labels={'value':'Metric','date':'Date'})
st.plotly_chart(fig_ts, use_container_width=True)




# --- Box Plot: Amount Distribution by Category ---

st.markdown(
    """
    <h3 style='margin-bottom:0; color:#0B5345;'>💰 Transaction Amount Distribution</h3>
    <p style='color:#555; font-size:14px; margin-top:2px;'>
        Compare transaction amount patterns across different categories such as merchants, banks, states, or weekdays.
    </p>
    """,
    unsafe_allow_html=True
)

# Dropdown to select grouping
category_for_box = st.selectbox(
    "📂 Group by",
    ['merchant', 'bank', 'state', 'dayofweek'],
    index=0,
    help="Select the variable by which to group transaction amounts."
)

# Fallback check
if category_for_box not in filtered.columns:
    for c in ['merchant', 'bank', 'state', 'dayofweek']:
        if c in filtered.columns:
            category_for_box = c
            break

# box plot
fig_box = px.box(
    filtered,
    x=category_for_box,
    y='amount (INR)',
    color=category_for_box,
    points='all',
    labels={'amount (INR)': 'Transaction Amount (INR)', category_for_box: category_for_box.title()},
    title=f"💹 Distribution of Transaction Amounts by {category_for_box.title()}",
    color_discrete_sequence=px.colors.qualitative.Vivid  # Brighter palette
)

# styling
fig_box.update_layout(
    title=dict(x=0.5, xanchor='center', font=dict(size=22, color='#154360', family='Arial Black')),
    xaxis_title=f"{category_for_box.title()}",
    yaxis_title="Transaction Amount (INR)",
    font=dict(family="Segoe UI, sans-serif", size=13, color="#212F3C"),
    plot_bgcolor="#F8F9F9",
    paper_bgcolor="rgba(0,0,0,0)",
    hovermode="x unified",
    margin=dict(l=60, r=40, t=90, b=60),
    boxmode="group",
    boxgap=0.5,
    boxgroupgap=0.3,
)

# Add a clean grid and soft box outline
fig_box.update_xaxes(showgrid=False)
fig_box.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor="rgba(0,0,0,0.1)")

# Display chart
st.plotly_chart(fig_box, use_container_width=True)




# --- Heatmap: hour vs dayofweek ---
st.markdown("### Heatmap: Hour vs Day of Week")
heat = filtered.groupby(['dayofweek','hour']).size().reset_index(name='count')
# pivot
pivot = heat.pivot(index='dayofweek', columns='hour', values='count').reindex(
    ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
).fillna(0)
fig_heat = px.imshow(pivot, aspect='auto', labels=dict(x="Hour", y="Day of Week", color="Txn Count"))
st.plotly_chart(fig_heat, use_container_width=True)

# --- Top merchants / fraud candidates ---
st.markdown("### Top Merchants (by volume)")
top_merch = filtered.groupby(merchant_col[0] if merchant_col else 'merchant').agg(
    txn_count=('amount (INR)','count'),
    txn_value=('amount (INR)','sum'),
    avg_amount=('amount (INR)','mean')
).reset_index().sort_values('txn_value', ascending=False).head(10)
st.dataframe(top_merch)

# --- Simple fraud scoring (heuristics) ---
st.markdown("### Simple Fraud Scoring (Rule-based)")
f = filtered.copy()
# Example rules (tune thresholds)
f['is_large_amount'] = f['amount (INR)'] > (f['amount (INR)'].quantile(0.99))
f['is_out_of_hours'] = (~f['hour'].between(6, 22))  # transactions between 10pm-6am flagged
f['rapid_freq_flag'] = False
# rapid frequency per user (example column: 'user_id')
if 'user_id' in f.columns:
    f['txn_1h_user'] = f.groupby('user_id')['txn_datetime'].transform(lambda x: x.rolling('1h', on=x).count().fillna(0))
    f['rapid_freq_flag'] = f['txn_1h_user'] > 10

# score
f['fraud_score'] = f[['is_large_amount','is_out_of_hours','rapid_freq_flag']].sum(axis=1)
suspects = f[f['fraud_score']>0].sort_values('fraud_score', ascending=False).head(20)
st.dataframe(suspects[['txn_datetime','amount (INR)','fraud_score'] + ([ 'user_id'] if 'user_id' in f.columns else [])].fillna(''))




# --- Transaction Status Module ---
st.markdown("### Transaction Status Overview")

if 'transaction_status' in filtered.columns:
    status_counts = filtered['transaction_status'].value_counts().reset_index()
    status_counts.columns = ['transaction_status', 'Count']

    fig_status = px.pie(
        status_counts,
        names='transaction_status',
        values='Count',
        title='Transaction Status Distribution',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig_status, use_container_width=True)



# ===== Success Rate =====
total_txns = len(filtered)
completed_txns = status_counts.loc[
    status_counts['transaction_status'].str.lower() == 'completed', 'Count'
].sum()

status_col = None
for col in filtered.columns:
    if "status" in col.lower():
        status_col = col
        break

if status_col:
    filtered[status_col] = filtered[status_col].astype(str).str.strip().str.lower()

    total_txns = len(filtered)
    completed_txns = filtered[filtered[status_col].str.contains("success|completed", na=False)].shape[0]
    success_rate = (completed_txns / total_txns) * 100 if total_txns > 0 else 0
    st.metric("✅ Success Rate", f"{success_rate:.2f} %")





# ===== Merchant Type Insights (by Amount) =====
# Ensure required columns exist before processing
if {'merchant_category', 'amount (INR)'}.issubset(filtered.columns):
    # Group by merchant category and sum total amount
    merchant_df = (
        filtered.groupby('merchant_category', as_index=False)['amount (INR)']
        .sum()
        .rename(columns={'amount (INR)': 'total_amount_inr'})
        .sort_values(by='total_amount_inr', ascending=False)
    )

    # Calculate percentage share
    total_amount = merchant_df['total_amount_inr'].sum()
    merchant_df['percentage'] = (merchant_df['total_amount_inr'] / total_amount) * 100

    # ===== Styled Table =====
    st.dataframe(
        merchant_df.style.format({
            'total_amount_inr': '₹{:,}',
            'percentage': '{:.2f}%'
        }).hide(axis='index'),
        use_container_width=True
    )

    # ===== Add Caption =====
    st.caption("💡 Table showing total transaction amount (INR) and percentage share for each merchant type.")

    # ===== Donut Chart =====
    fig = px.pie(
        merchant_df,
        names='merchant_category',
        values='total_amount_inr',
        title="💰 Merchant Type Transaction Amount Distribution",
        hole=0.4
    )

    # Enhance appearance
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=True, height=500)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Columns 'merchant_category' or 'amount (INR)' not found in dataset.")




# chart for Sender age groups

if 'sender_age_group' in filtered.columns and 'amount (INR)' in filtered.columns:
    # Group data
    sender_df = (
        filtered.groupby('sender_age_group')['amount (INR)']
        .sum()
        .reset_index()
        .sort_values(by='amount (INR)', ascending=False)
    )

    # Format total for subtitle
    total_amt = sender_df['amount (INR)'].sum()
    subtitle = f"💰 Total Amount: ₹{total_amt:,.0f}"

    # ===== Plotly Professional Bar Chart =====
    fig = px.bar(
        sender_df,
        x='sender_age_group',
        y='amount (INR)',
        text='amount (INR)',
        color='sender_age_group',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="👤 Sender Age Group vs Transaction Amount (INR)"
    )

    # ===== Styling =====
    fig.update_traces(
        texttemplate='₹%{y:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Amount: ₹%{y:,.0f}<extra></extra>'
    )
    fig.update_layout(
        title=dict(x=0.5, font=dict(size=18, color="#333", family="Segoe UI")),
        xaxis_title="Sender Age Group",
        yaxis_title="Transaction Amount (INR)",
        plot_bgcolor="#F8F9FA",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Segoe UI", size=12, color="#333"),
        showlegend=False,
        margin=dict(t=80, b=50, l=50, r=50)
    )

    # ===== Display in Metric-Style Card =====
    with st.container(border=True):
        st.markdown("### 👤 Sender Age Group Insights")
        st.markdown(subtitle)
        st.plotly_chart(fig, use_container_width=True)

    
    


if 'receiver_age_group' in filtered.columns and 'amount (INR)' in filtered.columns:
    # Group data
    receiver_df = (
        filtered.groupby('receiver_age_group')['amount (INR)']
        .sum()
        .reset_index()
        .sort_values(by='amount (INR)', ascending=False)
    )

    # Format total for subtitle
    total_amt = receiver_df['amount (INR)'].sum()
    subtitle = f"💰 Total Amount: ₹{total_amt:,.0f}"

    # ===== Plotly Professional Bar Chart =====
    fig = px.bar(
        receiver_df,
        x='receiver_age_group',
        y='amount (INR)',
        text='amount (INR)',
        color='receiver_age_group',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="🎯 Receiver Age Group vs Transaction Amount (INR)"
    )

    # ===== Styling =====
    fig.update_traces(
        texttemplate='₹%{y:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Amount: ₹%{y:,.0f}<extra></extra>'
    )
    fig.update_layout(
        title=dict(x=0.5, font=dict(size=18, color="#333", family="Segoe UI")),
        xaxis_title="Receiver Age Group",
        yaxis_title="Transaction Amount (INR)",
        plot_bgcolor="#F8F9FA",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Segoe UI", size=12, color="#333"),
        showlegend=False,
        margin=dict(t=80, b=50, l=50, r=50)
    )

    # ===== Display in Metric-Style Card =====
    with st.container(border=True):
        st.markdown("### 🎯 Receiver Age Group Insights")
        st.markdown(subtitle)
        st.plotly_chart(fig, use_container_width=True)

    


