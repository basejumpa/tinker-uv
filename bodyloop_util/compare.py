from dash import Dash, html, dcc, Input, Output, State, callback

web_app = Dash(__name__)

FIELD_ROW_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "1.5rem",
    "flexWrap": "nowrap",
    "overflowX": "auto",
    "paddingBottom": "0.25rem",
    "marginTop": "1rem",
}

FIELD_GROUP_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "0.75rem",
}

FIELD_LABEL_STYLE = {"marginBottom": "0", "whiteSpace": "nowrap"}

FIELD_INPUT_STYLE = {"width": "16rem"}

web_app.layout = html.Div(
    [

        html.Div(
            [
                html.Button(
                    "Load",
                    id="load-button",
                    n_clicks=0,
                    disabled=False,
                    style={"display": "block", "flexShrink": "0"},
                ),
                html.Div(
                    [
                        html.Label("Base URL", style=FIELD_LABEL_STYLE),
                        dcc.Input(
                            id="base-url-input",
                            type="text",
                            placeholder="https://bodyloop-control-pc ",
                            persistence=True,
                            persistence_type="local",
                            style={"width": "20rem"},
                        ),
                    ],
                    style=FIELD_GROUP_STYLE,
                ),
                html.Div(
                    [
                        html.Label("Username", style=FIELD_LABEL_STYLE),
                        dcc.Input(
                            id="username-input",
                            type="text",
                            placeholder="your-username",
                            persistence=True,
                            persistence_type="local",
                            style=FIELD_INPUT_STYLE,
                        ),
                    ],
                    style=FIELD_GROUP_STYLE,
                ),
                html.Div(
                    [
                        html.Label("Password", style=FIELD_LABEL_STYLE),
                        dcc.Input(
                            id="password-input",
                            type="password",
                            placeholder="Your password",
                            persistence=True,
                            persistence_type="local",
                            style=FIELD_INPUT_STYLE,
                        ),
                    ],
                    style=FIELD_GROUP_STYLE,
                ),
            ],
            style=FIELD_ROW_STYLE,
        ),
        html.H2("Compare Viatars"),
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
