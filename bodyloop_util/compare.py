from dash import Dash, html, dcc, Input, Output, State, callback, no_update
from bodyloop_sdk.client.client import Client, AuthenticatedClient
from bodyloop_sdk.client.api.authentification import login_api_v2_authentification_token_post
from bodyloop_sdk.client.models.body_login_api_v2_authentification_token_post import BodyLoginApiV2AuthentificationTokenPost
from bodyloop_sdk.client.api.probands import (
    get_probands_api_v2_probands_get,
    get_proband_api_v2_probands_proband_id_get,
)
from bodyloop_sdk.client.api.viatars import (
    get_viatar_api_v2_viatars_viatar_id_get,
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


def format_viatar_label(viatar_id: int, viatar) -> str:
    created_at = getattr(getattr(viatar, "meta", None), "crtime", None)
    return f"{created_at.strftime('%Y-%m-%d %H:%M:%S')} ({viatar_id}) {viatar.note or ''}".strip()

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
        html.Div(
            [
                html.Label("Compare Viatars of Proband", style=FIELD_LABEL_STYLE),
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
        html.Div(
            [
                html.Label("Viatar", style=FIELD_LABEL_STYLE),
                dcc.Dropdown(
                    id="viatar-dropdown",
                    options=[],
                    value=None,
                    placeholder="Select a proband to fetch viatars",
                    style={"width": "28rem"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "0.75rem", "marginTop": "1rem"},
        ),
        dcc.Store(id="auth-store"),
        html.Div(id="load-info", style={"marginTop": "1rem"}),
    ],
    style={"padding": "2rem"},
)

@callback(
    Output("load-info", "children"),
    Output("proband-dropdown", "options"),
    Output("proband-dropdown", "value"),
    Output("viatar-dropdown", "options"),
    Output("viatar-dropdown", "value"),
    Output("auth-store", "data"),
    Input("load-button", "n_clicks"),
    State("base-url-input", "value"),
    State("username-input", "value"),
    State("password-input", "value"),
    prevent_initial_call=True,
)
def compare(n_clicks, base_url, username, password):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update
    
    if not base_url or not username or not password:
        return "Please fill in all fields.", [], None, [], None, None
    
   
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
        return f"Could not connect to {base_url}. Please check the URL and that BodyLoop is running. {e}", [], None, [], None, None

    if response.status_code == 200:
        api_token = response.parsed.access_token
    else:
        return "Login failed. Please check your credentials and try again.", [], None, [], None, None

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
        return "No probands found.", [], None, [], None, {
            "base_url": base_url,
            "api_token": api_token,
        }
    
    return f"Loaded {len(options)} probands.", options, options[0]["value"], [], None, {
        "base_url": base_url,
        "api_token": api_token,
    }


@callback(
    Output("viatar-dropdown", "options", allow_duplicate=True),
    Output("viatar-dropdown", "value", allow_duplicate=True),
    Input("proband-dropdown", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def load_viatars_for_proband(selected_proband_id, auth_data):
    if not selected_proband_id or not auth_data:
        return [], None

    base_url = auth_data.get("base_url")
    api_token = auth_data.get("api_token")
    if not base_url or not api_token:
        return [], None

    try:
        proband_id = int(selected_proband_id)
    except (TypeError, ValueError):
        return [], None

    client = AuthenticatedClient(
        base_url=base_url,
        verify_ssl=False,
        token=api_token,
        timeout=10.0,
    )

    details_of_selected_proband = get_proband_api_v2_probands_proband_id_get.sync(
        client=client,
        proband_id=proband_id,
    )
    if not details_of_selected_proband or not details_of_selected_proband.viatars:
        return [], None

    options = []
    for viatar_ref in details_of_selected_proband.viatars:
        viatar_id = viatar_ref.viatar_id
        viatar = get_viatar_api_v2_viatars_viatar_id_get.sync(
            client=client,
            viatar_id=viatar_id,
        )
        if viatar is None:
            continue
        options.append(
            {
                "label": format_viatar_label(viatar_id, viatar),
                "value": str(viatar_id),
            }
        )

    if not options:
        return [], None

    options.reverse()

    return options, options[0]["value"]
