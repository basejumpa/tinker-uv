from dash import Dash, html, dcc, Input, Output, State, callback, no_update
from bodyloop_sdk.client.client import Client, AuthenticatedClient
from bodyloop_sdk.client.api.authentification import login_api_v2_authentification_token_post
from bodyloop_sdk.client.models.body_login_api_v2_authentification_token_post import BodyLoginApiV2AuthentificationTokenPost
from bodyloop_sdk.client.api.probands import (
    get_probands_api_v2_probands_get,
)

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


def format_proband_label(proband) -> str:
    given = (proband.name_given or "").strip()
    family = (proband.name_family or "").strip()
    birthdate = getattr(proband, "date_of_birth", None)

    full_name = f"{given} {family}".strip() or "Unnamed proband"
    if birthdate:
        birthdate_text = birthdate.isoformat() if hasattr(birthdate, "isoformat") else str(birthdate)
        return f"{full_name} ({birthdate_text})"
    return full_name

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
        html.Div(
            [
                html.Label("Proband", style=FIELD_LABEL_STYLE),
                dcc.Dropdown(
                    id="proband-dropdown",
                    options=[],
                    value=None,
                    placeholder="Click Load to fetch probands",
                    style={"width": "28rem"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "0.75rem", "marginTop": "1rem"},
        ),
        html.Div(id="load-info", style={"marginTop": "1rem"}),
    ],
    style={"padding": "2rem"},
)

@callback(
    Output("load-info", "children"),
    Output("proband-dropdown", "options"),
    Output("proband-dropdown", "value"),
    Input("load-button", "n_clicks"),
    State("base-url-input", "value"),
    State("username-input", "value"),
    State("password-input", "value"),
    prevent_initial_call=True,
)
def compare(n_clicks, base_url, username, password):
    if not n_clicks:
        return no_update, no_update, no_update
    
    if not base_url or not username or not password:
        return "Please fill in all fields.", [], None
    
   
    try:
        client = Client(
            base_url=base_url,
            verify_ssl=False,
            timeout=3.0
        )

        response = login_api_v2_authentification_token_post.sync_detailed(
            client=client,
            body=BodyLoginApiV2AuthentificationTokenPost(
                grant_type="password",
                username=username,
                password=password
            )
        )
    except Exception as e:
        return f"Could not connect to {base_url}. Please check the URL and that BodyLoop is running. {e}", [], None

    if response.status_code == 200:
        api_token = response.parsed.access_token
    else:
        return "Login failed. Please check your credentials and try again.", [], None

    client = AuthenticatedClient(
        base_url=base_url,
        verify_ssl=False,
        token=api_token, 
        timeout=10.0
    )
    
    probands = get_probands_api_v2_probands_get.sync(client=client) or []
    options = [
        {
            "label": format_proband_label(proband),
            "value": str(proband.proband_id),
        }
        for proband in probands
    ]
    options.sort(key=lambda option: option["label"].lower())

    if not options:
        return "No probands found.", [], None
    
    return f"Loaded {len(options)} probands.", options, options[0]["value"]
