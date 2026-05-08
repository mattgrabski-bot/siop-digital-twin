import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Global SIOP Enterprise", layout="wide", initial_sidebar_state="expanded")

# --- DATA GENERATION (Simulating an Enterprise Database) ---
@st.cache_data
def load_global_data():
    np.random.seed(42)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    countries = ["USA", "Germany", "China", "India", "Brazil", "Mexico", "Japan", "UK"]
    business_groups = ["Automotive", "Industrial", "Consumer Tech", "Healthcare"]
    product_families = ["Motors", "Sensors", "Microcontrollers", "Displays"]
    
    data = []
    # Generate 100 Plants
    for plant_id in range(1, 101):
        country = np.random.choice(countries)
        bg = np.random.choice(business_groups)
        plant_name = f"Plant_{country[:3]}_{plant_id:03d}"
        
        # Each plant has 1-3 product families and multiple SKUs/Projects
        for _ in range(np.random.randint(1, 4)):
            family = np.random.choice(product_families)
            project = f"Proj_{family[:3]}_{np.random.randint(10,99)}"
            sku = f"SKU-{np.random.randint(1000, 9999)}"
            
            # Base metrics for this SKU/Plant combo
            base_demand = np.random.randint(500, 5000)
            base_capacity = int(base_demand * np.random.uniform(0.8, 1.2))
            start_inv = int(base_demand * np.random.uniform(0.1, 0.5))
            safety_stock = int(base_demand * 0.2)
            
            for m in months:
                # Add some seasonality and randomness
                m_demand = int(base_demand * np.random.uniform(0.9, 1.1))
                m_capacity = int(base_capacity * np.random.uniform(0.95, 1.05))
                
                data.append({
                    "Month": m,
                    "Country": country,
                    "Business Group": bg,
                    "Plant": plant_name,
                    "Product Family": family,
                    "Project": project,
                    "SKU": sku,
                    "Demand": m_demand,
                    "Capacity": m_capacity,
                    "Start_Inv": start_inv,
                    "Safety_Stock": safety_stock
                })
    
    df = pd.DataFrame(data)
    # Ensure chronological sorting
    df['Month'] = pd.Categorical(df['Month'], categories=months, ordered=True)
    return df

raw_data = load_global_data()

# --- SIDEBAR: GLOBAL FILTERS ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2272/2272535.png", width=50) # Generic globe icon
st.sidebar.title("Global Filters")

selected_bgs = st.sidebar.multiselect("Business Group", raw_data["Business Group"].unique(), default=raw_data["Business Group"].unique())
selected_countries = st.sidebar.multiselect("Country", raw_data["Country"].unique(), default=raw_data["Country"].unique())

# Filter data based on initial selections to update subsequent filters
filtered_initial = raw_data[(raw_data["Business Group"].isin(selected_bgs)) & (raw_data["Country"].isin(selected_countries))]

selected_plants = st.sidebar.multiselect("Plant", filtered_initial["Plant"].unique(), default=filtered_initial["Plant"].unique()[:5]) # Default to first 5 to avoid clutter

# Final Filtered Dataset
df_filtered = filtered_initial[filtered_initial["Plant"].isin(selected_plants)]

if df_filtered.empty:
    st.warning("No data available for the selected filters. Please adjust your selections.")
    st.stop()

# --- SIOP ENGINE (Vectorized for Scale) ---
def calculate_siop(df, demand_multiplier=1.0, capacity_multiplier=1.0):
    # Aggregate data by Month based on the filtered dataset
    agg_df = df.groupby('Month', observed=False).agg({
        'Demand': 'sum',
        'Capacity': 'sum',
        'Start_Inv': 'sum', # Note: In reality, start inv is only month 1, but we use an aggregate approximation here
        'Safety_Stock': 'sum'
    }).reset_index()
    
    agg_df['Demand'] = (agg_df['Demand'] * demand_multiplier).astype(int)
    agg_df['Capacity'] = (agg_df['Capacity'] * capacity_multiplier).astype(int)
    
    # Calculate SIOP Flow
    results = []
    # Use the first month's aggregated starting inventory
    current_inv = agg_df['Start_Inv'].iloc[0] if not agg_df.empty else 0 
    
    for index, row in agg_df.iterrows():
        demand = row['Demand']
        capacity = row['Capacity']
        ss_target = row['Safety_Stock']
        
        # Production tries to meet demand + refill safety stock, capped by capacity
        target_production = demand + max(0, ss_target - current_inv)
        production = min(target_production, capacity)
        
        ending_inv = current_inv + production - demand
        shortage = abs(ending_inv) if ending_inv < 0 else 0
        if ending_inv < 0: ending_inv = 0
        
        results.append({
            "Month": row['Month'],
            "Demand": demand,
            "Supply": production,
            "Capacity Limit": capacity,
            "Inventory": ending_inv,
            "Shortage": shortage
        })
        current_inv = ending_inv
        
    return pd.DataFrame(results)

# --- MAIN UI: TABS ---
st.title("🌐 Global SIOP Control Tower")
tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "🎛️ Scenario Builder", "📋 Operational Details"])

# === TAB 1: EXECUTIVE SUMMARY ===
with tab1:
    st.markdown("### Global Network Health")
    base_siop = calculate_siop(df_filtered)
    
    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    total_demand = base_siop['Demand'].sum()
    total_supply = base_siop['Supply'].sum()
    total_shortage = base_siop['Shortage'].sum()
    service_level = (total_supply / total_demand * 100) if total_demand > 0 else 100
    
    kpi1.metric("Total Annual Demand", f"{total_demand:,.0f} U")
    kpi2.metric("Total Constrained Supply", f"{total_supply:,.0f} U")
    kpi3.metric("Projected Shortage", f"{total_shortage:,.0f} U", delta=f"{-total_shortage:,.0f}" if total_shortage>0 else "0", delta_color="inverse")
    kpi4.metric("Est. Service Level", f"{service_level:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        # Demand by Country & Business Group (Sunburst)
        fig_sun = px.sunburst(df_filtered, path=['Country', 'Business Group', 'Product Family'], values='Demand',
                              title="Demand Distribution Hierarchy",
                              color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col2:
        # Shortage Risk by Country
        # Approximating risk by Demand vs Capacity gap per country
        country_gap = df_filtered.groupby('Country', observed=False).agg({'Demand': 'sum', 'Capacity': 'sum'}).reset_index()
        country_gap['Gap'] = country_gap['Capacity'] - country_gap['Demand']
        country_gap['Status'] = np.where(country_gap['Gap'] < 0, 'Risk (Deficit)', 'Healthy (Surplus)')
        
        fig_gap = px.bar(country_gap, x='Country', y='Gap', color='Status',
                         color_discrete_map={'Risk (Deficit)': '#EF553B', 'Healthy (Surplus)': '#00CC96'},
                         title="Capacity vs Demand Gap by Country")
        st.plotly_chart(fig_gap, use_container_width=True)

# === TAB 2: SCENARIO BUILDER ===
with tab2:
    st.markdown("### Macro-Economic Stress Testing")
    st.write("Adjust global demand and capacity parameters to test network resilience.")
    
    scol1, scol2 = st.columns(2)
    with scol1:
        d_mult = st.slider("Global Demand Adjustment (%)", -50, 100, 0, step=5) / 100.0 + 1.0
    with scol2:
        c_mult = st.slider("Global Capacity Adjustment (%)", -50, 50, 0, step=5) / 100.0 + 1.0
        
    scenario_df = calculate_siop(df_filtered, demand_multiplier=d_mult, capacity_multiplier=c_mult)
    
    # Scenario Visualization
    fig_scen = go.Figure()
    fig_scen.add_trace(go.Bar(x=scenario_df['Month'], y=scenario_df['Demand'], name='Stressed Demand', marker_color='#FFA15A'))
    fig_scen.add_trace(go.Bar(x=scenario_df['Month'], y=scenario_df['Supply'], name='Constrained Supply', marker_color='#19D3F3'))
    fig_scen.add_trace(go.Scatter(x=scenario_df['Month'], y=scenario_df['Inventory'], name='Proj. Inventory', line=dict(color='#AB63FA', width=4)))
    
    fig_scen.update_layout(title=f"Scenario Results: Demand x{d_mult:.2f} | Capacity x{c_mult:.2f}", barmode='group', template="plotly_dark")
    st.plotly_chart(fig_scen, use_container_width=True)
    
    if scenario_df['Shortage'].sum() > 0:
        st.error(f"🚨 This scenario results in a total network shortage of {scenario_df['Shortage'].sum():,.0f} units.")
    else:
        st.success("✅ The network can fully absorb this scenario without shortages.")

# === TAB 3: OPERATIONAL DETAILS ===
with tab3:
    st.markdown("### Granular S&OP Balancing")
    
    # The classic SIOP Chart for the current filtered view
    fig_op = go.Figure()
    fig_op.add_trace(go.Bar(x=base_siop['Month'], y=base_siop['Demand'], name='Demand', marker_color='#EF553B'))
    fig_op.add_trace(go.Bar(x=base_siop['Month'], y=base_siop['Supply'], name='Supply', marker_color='#00CC96'))
    fig_op.add_trace(go.Scatter(x=base_siop['Month'], y=base_siop['Capacity Limit'], name='Capacity Limit', line=dict(color='gray', width=2, dash='dash')))
    fig_op.add_trace(go.Scatter(x=base_siop['Month'], y=base_siop['Inventory'], name='Inventory', line=dict(color='#636EFA', width=4)))
    
    fig_op.update_layout(title="Aggregate SIOP Plan for Selected Network", barmode='group', template="plotly_white")
    st.plotly_chart(fig_op, use_container_width=True)
    
    st.markdown("#### SIOP Grid (Aggregated)")
    # Format the table for executive reading
    display_df = base_siop.set_index('Month').T
    display_df = display_df.applymap(lambda x: f"{int(x):,}")
    st.dataframe(display_df, use_container_width=True)
    
    st.markdown("#### Granular SKU/Project Data")
    st.dataframe(df_filtered.drop(columns=['Start_Inv', 'Safety_Stock']), use_container_width=True)
