import dash
from dash import dcc, html, Input, Output, State, callback
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Generate Scaled Mock Data (Simulating 28 Countries, 4 BGs, 200 Plants)
countries = [f"Country {i+1}" for i in range(28)]
business_groups = ["Electronics", "Automotive", "Healthcare", "Industrial"]
plants = [f"Plant {i+1}" for i in range(200)]

# Create a mapping for plants to countries/BGs to keep data logical
data_list = []
for p in plants:
    country = np.random.choice(countries)
    bg = np.random.choice(business_groups)
    for month in ["Jan", "Feb", "Mar"]:
        stat = np.random.randint(500, 2000)
        data_list.append({
            "Country": country,
            "Business_Group": bg,
            "Plant": p,
            "Month": month,
            "Stat_Forecast": stat,
            "Manual_Override": 0,
            "Final_Plan": stat
        })

df = pd.DataFrame(data_list)

app = dash.Dash(__name__)

# 2. UI Layout with Enterprise Filters
app.layout = html.Div([
    html.H1("Enterprise IBP Dashboard", style={'textAlign': 'center', 'color': '#2c3e50'}),
    
    # Filter Bar
    html.Div([
        html.Div([
            html.Label("Country"),
            dcc.Dropdown(id='country-filter', options=countries, multi=True, placeholder="All Countries")
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Business Group"),
            dcc.Dropdown(id='bg-filter', options=business_groups, multi=True, placeholder="All Groups")
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Search Plant"),
            dcc.Input(id='plant-search', type='text', placeholder='Filter by plant name...', style={'width': '100%', 'height': '35px'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
    ], style={'backgroundColor': '#f8f9fa', 'padding': '10px', 'borderRadius': '5px', 'marginBottom': '20px'}),

    # Planning Grid
    dag.AgGrid(
        id="enterprise-grid",
        columnDefs=[
            {"field": "Country", "rowGroup": True, "hide": True},
            {"field": "Business_Group", "rowGroup": True, "hide": True},
            {"field": "Plant", "filter": True},
            {"field": "Month"},
            {"field": "Stat_Forecast", "headerName": "Stat Forecast", "type": "numericColumn"},
            {"field": "Manual_Override", "headerName": "Override", "editable": True, "cellStyle": {"color": "blue"}, "type": "numericColumn"},
            {"field": "Final_Plan", "headerName": "Final Plan", "type": "numericColumn", "cellStyle": {"backgroundColor": "#e9ecef"}}
        ],
        defaultColDef={"flex": 1, "sortable": True, "resizable": True},
        dashGridOptions={
            "enableRangeSelection": True,
            "rowGroupPanelShow": 'always', # Allows users to custom-group by BG or Country
            "suppressAggFuncInHeader": True
        },
        enableEnterpriseModules=False, # Set to True if you have an AG Grid license for grouping
        style={"height": "400px"}
    ),

    dcc.Graph(id="agg-chart", style={'marginTop': '20px'})
], style={'padding': '30px', 'fontFamily': 'Segoe UI'})

# 3. Server-side Filtering & Calculation Logic
@callback(
    Output("enterprise-grid", "rowData"),
    Output("agg-chart", "figure"),
    Input("country-filter", "value"),
    Input("bg-filter", "value"),
    Input("plant-search", "value"),
    Input("enterprise-grid", "cellValueChanged"),
    State("enterprise-grid", "rowData")
)
def update_dashboard(selected_countries, selected_bgs, plant_query, cell_changed, current_rows):
    dff = df.copy()

    # Apply Filters
    if selected_countries:
        dff = dff[dff['Country'].isin(selected_countries)]
    if selected_bgs:
        dff = dff[dff['Business_Group'].isin(selected_bgs)]
    if plant_query:
        dff = dff[dff['Plant'].str.contains(plant_query, case=False)]

    # Handle calculations if data was edited
    if cell_changed:
        # In a real app, you'd update a DB here; for now, we update the filtered view
        temp_df = pd.DataFrame(current_rows)
        temp_df["Final_Plan"] = temp_df["Stat_Forecast"].astype(float) + temp_df["Manual_Override"].astype(float)
        dff = temp_df

    # Aggregate for Chart
    fig = px.area(dff, x="Month", y="Final_Plan", color="Business_Group", 
                  title="Aggregated Plan by Business Group",
                  template="plotly_white")
    
    return dff.to_dict("records"), fig

if __name__ == "__main__":
    app.run_server(debug=True)
