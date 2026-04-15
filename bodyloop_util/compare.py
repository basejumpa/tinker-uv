from dash import Dash, html, dcc, Input, Output, State, dash_table, callback, no_update

web_app = Dash(__name__)

web_app.layout = html.Div(
    [
        html.H2("Compare Viatars"),
                html.Div(
            [
                html.Label("Base URL", style={"width": "8rem", "marginRight": "0.75rem"}),
                dcc.Input(
                    id="base-url-input",
                    type="text",
                    placeholder="https://bodyloop-control-pc ",
                    persistence=True,
                    persistence_type="local",
                    style={"width": "24rem"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "marginTop": "1rem"},
        ),
        html.Div(
            [
                html.Label("Username", style={"width": "8rem", "marginRight": "0.75rem"}),
                dcc.Input(
                    id="username-input",
                    type="text",
                    placeholder="your-username",
                    persistence=True,
                    persistence_type="local",
                    style={"width": "24rem"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "marginTop": "1rem"},
        ),
        html.Div(
            [
                html.Label("Password", style={"width": "8rem", "marginRight": "0.75rem"}),
                dcc.Input(
                    id="password-input",
                    type="password",
                    placeholder="Your password",
                    persistence=True,
                    persistence_type="local",
                    style={"width": "24rem"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "marginTop": "1rem"},
        ),
        html.Button(
            "Load",
            id="load-button",
            n_clicks=0,
            disabled=False,
            style={"marginTop": "1rem", "display": "block"},
        ),
        html.Div(id="load-info", style={"marginTop": "1rem"}),
    ],
    style={"padding": "2rem"},
)

@callback(
    Output("load-info", "children"),
    Input("load-button", "n_clicks"),
    State("base-url-input", "value"),
    State("username-input", "value"),
    State("password-input", "value"),
    prevent_initial_call=True,
)
def compare(n_clicks, base_url, username, password):
    if not base_url or not username or not password:
        return "Please fill in all fields."
    
    # Here you would add the logic to compare the viatars using the provided credentials and base URL.
    # For now, we will just return a placeholder message.
    
    return "Comparison functionality is not yet implemented."
