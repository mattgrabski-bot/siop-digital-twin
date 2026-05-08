 as px
import numpy as np

# 1. Domain Configuration for OPmobility
BUSINESS_GROUPS = ["Exterior & Lighting", "Modules", "C-Power", "H2-Power"]
REGIONS = ["EMEA", "Americas", "Asia-Pacific"]
COUNTRIES = [f"Country {i+1}" for i in range(28)]
MONTHS = ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]

# Mock Data Generator (152 Plants across 4 BGs)
np.random.seed(42)
data_list = []
for i in range(152):
    plant_id = f"PL-{1000 + i}"
    bg = np.random.choice(BUSINESS_GROUPS)
    region = np.random.choice(REGIONS)
    country = np.random.choice(COUNTRIES)
    for month in MONTHS:
        stat = np.random.randint(100, 500)
        data_list.append({
            "BG": bg, "Region": region, "Country": country, "Plant": plant_id,
            "Month": month, "Stat_Forecast": stat, "Manual_Adj": 0, "Final_Plan": stat
        })

df_init = pd.DataFrame(data_list)

app = dash.Dash(__name__, external_stylesheets=["https://codepen.io"])

# 2. Modern "Anaplan-Style" Layout
app.layout = html.Div([
    # Top Header & Global Navigation
    html.Header([
        html.H2("OPmobility | Integrated Business Planning (IBP)", style={'margin': '0', 'color': 'white'}),
        html.P("Scenario: 2024 Master Production Schedule", style={'margin': '0', 'color': '#ccc'})
    ], style={'backgroundColor': '#002D62', 'padding': '20px', 'display': 'flex', 'flexDirection': 'column'}),

    # Filter/Selector Panel (Context Bar)
    html.Div([
        html.Div([
            html.Label("Business Group View", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='bg-selector', options=BUSINESS_GROUPS, value=BUSINESS_GROUPS[0], clearable=False)
        ], style={'width': '250px', 'marginRight': '20px'}),
        
        html.Div([
            html.Label("Region Filter", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='region-selector', options=REGIONS, multi=True, placeholder="All Regions")
        ], style={'width': '250px'})
    ], style={'padding': '15px', 'display': 'flex', 'borderBottom': '1px solid #ddd'}),

    # Workspace Area
    html.Div([
        # Data Grid (Input Layer)
        html.Div([
            html.H4("Plant Production overrides (Volume in K-Units)"),
            dag.AgGrid(
                id="planning-grid",
                columnDefs=[
                    {"field": "Region", "rowGroup": True, "hide": True},
                    {"field": "Country", "rowGroup": True, "hide": True},
                    {"field": "Plant", "pinned": "left", "width": 120},
                    {"field": "Month", "width": 110},
                    {"field": "Stat_Forecast", "headerName": "Stat. Forecast", "type": "numericColumn"},
                    {"field": "Manual_Adj", "headerName": "Adjustment (+/-)", "editable": True, 
                     "cellStyle": {"backgroundColor": "#fff7e6", "border": "1px solid #ffd591"}},
                    {"field": "Final_Plan", "headerName": "Final Plan", "type": "numericColumn", 
                     "cellStyle": {"fontWeight": "bold", "backgroundColor": "#f0f2f5"}}
                ],
                defaultColDef={"flex": 1, "sortable": True, "resizable": True, "filter": True},
                dashGridOptions={"rowGroupPanelShow": "always", "groupDefaultExpanded": 1},
                style={"height": "500px"}
            )
        ], className="eight columns"),

        # Insights Sidebar (Visualization Layer)
        html.Div([
            html.H4("Regional Concentration"),
            dcc.Graph(id="side-chart", style={"height": "450px"})
        ], className="four columns")
    ], className="row", style={'padding': '20px'})

], style={'fontFamily': 'Helvetica, Arial, sans-serif'})

# 3. Dynamic Write-back & Recalculation
@callback(
    Output("planning-grid", "rowData"),
    Output("side-chart", "figure"),
    Input("bg-selector", "value"),
    Input("region-selector", "value"),
    Input("planning-grid", "cellValueChanged"),
    State("planning-grid", "rowData")
)
def sync_dashboard(selected_bg, selected_regions, cell_change, current_data):
    # Filter base data for the selected BG
    dff = df_init[df_init['BG'] == selected_bg].copy()
    
    if selected_regions:
        dff = dff[dff['Region'].isin(selected_regions)]

    # Real-time Calculation (Final Plan = Stat + Manual)
    if cell_change:
        # If user edited a cell, update the calculation logic
        temp_df = pd.DataFrame(current_data)
        temp_df["Final_Plan"] = temp_df["Stat_Forecast"].astype(float) + temp_df["Manual_Adj"].astype(float)
        dff = temp_df

    # Sidebar Viz: Consolidated Plan by Region
    fig = px.pie(dff, values='Final_Plan', names='Region', hole=.4,
                 title=f"Production Share: {selected_bg}",
                 color_discrete_sequence=px.colors.qualitative.Prism)
    
    return dff.to_dict("records"), fig

if __name__ == "__main__":
    app.run_server(debug=True)
