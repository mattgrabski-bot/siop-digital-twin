import dash
from dash import dcc, html, Input, Output, State, callback
import dash_ag_grid as dag
import pandas as pd
import numpy as np

# 1. Configuration for OPm BGs
BUSINESS_GROUPS = ["E&L", "Mod", "C-P", "H2-P"]

# Mock Data for 152 Plants
np.random.seed(42)
plants_data = []
for i in range(152):
    bg = np.random.choice(BUSINESS_GROUPS)
    stat = np.random.randint(200, 800)
    plants_data.append({
        "BG": bg, "Plant": f"PL-{1000+i}", "Stat_Forecast": stat, 
        "Manual_Adj": 0, "Final_Plan": stat, "Status": "Draft"
    })

app = dash.Dash(__name__)

# 2. UI Layout with Workflow Controls
app.layout = html.Div([
    # Enterprise Header
    html.Div([
        html.H2("OPmobility IBP | Approval Portal", style={'color': 'white', 'margin': '0'}),
        html.Div(id="cycle-status", style={'color': '#f0ad4e', 'fontWeight': 'bold', 'fontSize': '18px'})
    ], style={'backgroundColor': '#002D62', 'padding': '20px', 'display': 'flex', 'justifyContent:': 'space-between'}),

    # Approval Toolbar
    html.Div([
        html.Div([
            html.Label("Business Group Context", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='bg-selector', options=BUSINESS_GROUPS, value=BUSINESS_GROUPS[0], clearable=False)
        ], style={'width': '300px', 'marginRight': '20px'}),
        
        html.Div([
            html.Button("Submit for Approval", id="submit-btn", n_clicks=0, 
                        style={'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'padding': '10px 25px', 'borderRadius': '5px'}),
            html.Button("Recall / Reset", id="reset-btn", n_clicks=0, 
                        style={'marginLeft': '10px', 'padding': '10px 25px', 'borderRadius': '5px'})
        ], style={'display': 'flex', 'alignItems': 'flex-end'})
    ], style={'padding': '20px', 'borderBottom': '1px solid #ddd', 'display': 'flex', 'backgroundColor': '#f8f9fa'}),

    # Planning Grid
    html.Div([
        dag.AgGrid(
            id="workflow-grid",
            columnDefs=[
                {"field": "Plant", "pinned": "left"},
                {"field": "Stat_Forecast", "headerName": "Stat. Forecast"},
                {"field": "Manual_Adj", "headerName": "Adj (+/-)", "editable": True, 
                 "cellStyle": {"styleConditions": [{"condition": "params.data.Status === 'Draft'", "style": {"backgroundColor": "#fff7e6"}}]}},
                {"field": "Final_Plan", "headerName": "Final Plan", "cellStyle": {"fontWeight": "bold"}},
                {"field": "Status", "cellClassRules": {
                    "bg-warning": "params.value === 'Pending Approval'",
                    "bg-success": "params.value === 'Approved'"
                }}
            ],
            defaultColDef={"flex": 1, "sortable": True},
            style={"height": "550px"}
        )
    ], style={'padding': '20px'}),

    # Hidden Store to act as a "Database"
    dcc.Store(id='planning-db', data=pd.DataFrame(plants_data).to_dict('records'))
], style={'fontFamily': 'Segoe UI, Arial'})

# 3. Logic: Data Freeze and Approval Workflow
@callback(
    Output("workflow-grid", "rowData"),
    Output("cycle-status", "children"),
    Output("planning-db", "data"),
    Input("bg-selector", "value"),
    Input("submit-btn", "n_clicks"),
    Input("reset-btn", "n_clicks"),
    Input("workflow-grid", "cellValueChanged"),
    State("planning-db", "data")
)
def handle_workflow(selected_bg, submit_pts, reset_pts, cell_change, current_db):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    db_df = pd.DataFrame(current_db)

    # ACTION 1: Submit BG for Approval (Freeze)
    if trigger == "submit-btn":
        db_df.loc[db_df['BG'] == selected_bg, 'Status'] = 'Pending Approval'

    # ACTION 2: Reset to Draft (Unlock)
    elif trigger == "reset-btn":
        db_df.loc[db_df['BG'] == selected_bg, 'Status'] = 'Draft'

    # ACTION 3: Calculation (Only allowed if status is 'Draft')
    elif trigger == "workflow-grid":
        for i, row in db_df.iterrows():
            if row['Status'] == 'Draft':
                db_df.at[i, 'Final_Plan'] = float(row['Stat_Forecast']) + float(row['Manual_Adj'])

    # Filter UI view
    display_df = db_df[db_df['BG'] == selected_bg]
    status_text = f"Status: {display_df['Status'].iloc[0]}" if not display_df.empty else "N/A"
    
    return display_df.to_dict("records"), status_text, db_df.to_dict("records")

if __name__ == "__main__":
    app.run_server(debug=True)
