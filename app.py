import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Cloud-Native SIOP Tool", layout="wide")
st.title("📊 Digital SIOP Workbench")
st.markdown("### Strategic Alignment: Demand, Supply, and Inventory")

# --- SIDEBAR: INPUT PARAMETERS ---
st.sidebar.header("1. Planning Assumptions")
start_inv = st.sidebar.number_input("Beginning Inventory (Units)", value=1000)
safety_stock_target = st.sidebar.number_input("Safety Stock Target", value=200)

st.sidebar.header("2. Monthly Demand Forecast")
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
demand_input = {}
for m in months:
    demand_input[m] = st.sidebar.slider(f"Demand - {m}", 0, 2000, 500)

st.sidebar.header("3. Production Capacity")
prod_cap = st.sidebar.slider("Max Monthly Production Capacity", 0, 2000, 600)

# --- LOGIC: SIOP ENGINE ---
def run_siop_engine(start_inv, demand_dict, capacity):
    data = []
    current_inv = start_inv
    
    for m in months:
        demand = demand_dict[m]
        # Logic: Produce to demand but cap at capacity
        production = min(demand, capacity) 
        # Logic: If inventory is low, try to produce more to reach safety stock
        if current_inv < safety_stock_target:
            production = min(capacity, demand + (safety_stock_target - current_inv))
            
        ending_inv = current_inv + production - demand
        shortage = abs(ending_inv) if ending_inv < 0 else 0
        if ending_inv < 0: ending_inv = 0 # Cannot have negative physical stock
        
        data.append({
            "Month": m,
            "Demand": demand,
            "Supply": production,
            "Inventory": ending_inv,
            "Shortage": shortage
        })
        current_inv = ending_inv
        
    return pd.DataFrame(data)

df = run_siop_engine(start_inv, demand_input, prod_cap)

# --- VISUALIZATION: THE S&OP DASHBOARD ---
col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Month'], y=df['Demand'], name='Demand', marker_color='#EF553B'))
    fig.add_trace(go.Bar(x=df['Month'], y=df['Supply'], name='Supply (Prod)', marker_color='#00CC96'))
    fig.add_trace(go.Scatter(x=df['Month'], y=df['Inventory'], name='Inventory Level', line=dict(color='#636EFA', width=4)))
    
    fig.update_layout(title="Demand vs. Supply vs. Inventory", barmode='group', template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Plan Health Metrics")
    total_shortage = df['Shortage'].sum()
    avg_inv = df['Inventory'].mean()
    
    st.metric("Total Projected Shortage", f"{total_shortage} Units", delta=-total_shortage, delta_color="inverse")
    st.metric("Average Monthly Inventory", f"{int(avg_inv)} Units")
    
    if total_shortage > 0:
        st.error("⚠️ Gap Detected: Supply cannot meet demand.")
    else:
        st.success("✅ Plan Feasible: Supply meets demand.")

# --- DATA TABLE ---
st.subheader("Detailed Planning Grid")
st.table(df.set_index("Month"))