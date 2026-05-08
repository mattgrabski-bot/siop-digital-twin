import dash
from dash import dcc, html, Input, Output, State, callback
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
import numpy as np

# --- CONFIGURATION ---
BUSINESS_GROUPS = ["E&L", "Mod", "C-P", "H2-P"]
REGIONS = ["EMEA", "Americas", "Asia-Pacific"]
MONTHS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]

# Generate synthetic Enterprise Data (200 Plants, 28 Countries)
np.random.seed(42)
data_list = []
for i in range(200):
    bg = np.random.choice(BUSINESS_GROUPS)
    region = np.random.choice(REGIONS)
    country = f"Country {np.random.randint(1, 29)}"
    plant_id = f"PL-{1000 + i}"
    for m in MONTHS:
        stat = np.random.randint(500, 2500)
        data_list.append({
            "BG": bg, "Region": region, "Country": country, "Plant": plant_id,
            "Month": m, "Stat_Forecast": stat, "Manual_Adj": 0, 
            "Final_Plan": stat, "Status": "Draft"
        })

initial_df = pd.DataFrame(data_list)

# --- DASH APP ---
app = dash.Dash(__name__)

app.layout = html.Div([
    # Modern Enterprise Header
    html.Header([
        html.Div([
            html.H2("OPmobility | IBP Command Centre", style={'margin': '0', 'color': '#FFFFFF'}),
            html.P("Global Production & Demand Alignment", style={'margin': '0', 'color': '#AABBCB'})
        ]),
        html.Div(id="workflow-status-badge", style={'padding': '10px 20px', 'borderRadius': '20px', 'fontWeight': 'bold'})
    ], style={'backgroundColor': '#002D62', 'padding': '20px 40px', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),

    # Context & Control Bar
    html.Div([
        html.Div([
            html.Label("Business Group Context", style={'fontWeight': 'bold', 'color': '#4A5568'}),
            dcc.Dropdown(id='bg-selector', options=BUSINESS_GROUPS, value="Exterior & Lighting", clearable=False)
        ], style={'width': '280px', 'marginRight': '30px'}),
        
        html.Div([
            html.Label("Actions", style={'fontWeight': 'bold', 'color': '#4A5568'}),
            html.Div([
                html.Button("Submit for Approval", id="submit-btn", n_clicks=0, 
                            style={'backgroundColor': '#2F855A', 'color': 'white', 'border': 'none', 'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer'}),
                html.Button("Reset to Draft", id="reset-btn", n_clicks=0, 
                            style={'marginLeft': '10px', 'backgroundColor': '#E2E8F0', 'border': '1px solid #CBD5E0', 'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer'})
            ])
        ])
    ], style={'padding': '20px 40px', 'display': 'flex', 'backgroundColor': '#F7FAFC', 'borderBottom': '1px solid #E2E8F0'}),

    # Main Workspace
    html.Div([
        # Data Input Grid (Anaplan Style)
        html.Div([
            html.H4("Demand Override Grid", style={'color': '#2D3748'}),
            dag.AgGrid(
                id="planning-grid",
                columnDefs=[
                    {"field": "Region", "rowGroup": True, "hide": True},
                    {"field": "Country", "rowGroup": True, "hide": True},
                    {"field": "Plant", "pinned": "left", "width": 120},
                    {"field": "Month", "width": 110},
                    {"field": "Stat_Forecast", "headerName": "Stat. Forecast", "type": "numericColumn"},
                    {"field": "Manual_Adj", "headerName": "Manual Adjustment", "editable": True, 
                     "cellStyle": {"styleConditions": [
                         {"condition": "params.data.Status === 'Draft'", "style": {"backgroundColor": "#FFFBE6", "border": "1px solid #FFE58F"}},
                         {"condition": "params.data.Status !== 'Draft'", "style": {"backgroundColor": "#F5F5F5", "color": "#8C8C8C"}}
                     ]}},
                    {"field": "Final_Plan", "headerName": "Final Plan", "type": "numericColumn", "cellStyle": {"fontWeight": "bold", "backgroundColor": "#EDF2F7"}},
                    {"field": "Status", "width": 150}
                ],
                defaultColDef={"flex": 1, "sortable": True, "resizable": True, "filter": True},
                dashGridOptions={"rowGroupPanelShow": "always", "groupDefaultExpanded": 1},
                style={"height": "600px", "width": "100%"}
            )
        ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingRight': '20px'}),

        # Analytics Sidebar
        html.Div([
            html.H4("Production Impact", style={'color': '#2D3748'}),
            dcc.Graph(id="impact-chart", style={'height': '550px'})
        ], style={'width': '33%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'padding': '20px 40px'}),

    # Hidden Storage for App State
    dcc.Store(id='app-db', data=initial_df.to_dict('records'))
], style={'fontFamily': 'Inter, sans-serif', 'margin': '-8px', 'backgroundColor': '#FFFFFF'})

# --- CALLBACKS ---
@callback(
    Output("planning-grid", "rowData"),
    Output("impact-chart", "figure"),
    Output("workflow-status-badge", "children"),
    Output("workflow-status-badge", "style"),
    Output("app-db", "data"),
    Input("bg-selector", "value"),
    Input("submit-btn", "n_clicks"),
    Input("reset-btn", "n_clicks"),
    Input("planning-grid", "cellValueChanged"),
    State("app-db", "data")
)
def manage_portal(selected_bg, submit_clicks, reset_clicks, cell_change, current_db):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else None
    df = pd.DataFrame(current_db)

    # 1. Handle Workflow Actions
    if trigger == "submit-btn.n_clicks":
        df.loc[df['BG'] == selected_bg, 'Status'] = 'Pending Approval'
    elif trigger == "reset-btn.n_clicks":
        df.loc[df['BG'] == selected_bg, 'Status'] = 'Draft'
    
    # 2. Handle Data Edits (Only if Status is Draft)
    if trigger == "planning-grid.cellValueChanged":
        # Note: In production, you'd match by unique ID
        edited_row = cell_change['data']
        if edited_row['Status'] == 'Draft':
            # Update the main DB with the new values
            idx = (df['Plant'] == edited_row['Plant']) & (df['Month'] == edited_row['Month'])
            df.loc[idx, 'Manual_Adj'] = edited_row['Manual_Adj']
            df.loc[idx, 'Final_Plan'] = float(edited_row['Stat_Forecast']) + float(edited_row['Manual_Adj'])

    # 3. Slice Data for View
    filtered_df = df[df['BG'] == selected_bg]
    current_status = filtered_df['Status'].iloc[0] if not filtered_df.empty else "N/A"
    
    # 4. Update Visuals
    fig = px.bar(filtered_df, x="Month", y="Final_Plan", color="Region", 
                 title=f"Forecast Trend: {selected_bg}", barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Bold)
    
    # 5. Badge Styling
    badge_style = {
        'backgroundColor': '#C6F6D5' if current_status == 'Pending Approval' else '#FEEBC8',
        'color': '#22543D' if current_status == 'Pending Approval' else '#744210',
        'padding': '10px 20px', 'borderRadius': '20px', 'fontWeight': 'bold'
    }

    return filtered_df.to_dict("records"), fig, f"CYCLE: {current_status.upper()}", badge_style, df.to_dict("records")

if __name__ == "__main__":
    app.run_server(debug=True)
