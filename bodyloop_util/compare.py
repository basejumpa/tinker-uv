from dash import Dash, html, dcc, Input, Output, State, callback, no_update, dash_table, ctx
import io
import json
import pandas as pd
import plotly.graph_objects as go
import trimesh
from bodyloop_sdk.client.client import Client, AuthenticatedClient
from bodyloop_sdk.client.api.authentification import login_api_v2_authentification_token_post
from bodyloop_sdk.client.api.models import get_model_api_v2_viatars_viatar_id_models_model_name_get
from bodyloop_sdk.client.models.body_login_api_v2_authentification_token_post import BodyLoginApiV2AuthentificationTokenPost
from bodyloop_sdk.client.api.probands import (
    get_probands_api_v2_probands_get,
    get_proband_api_v2_probands_proband_id_get,
)
from bodyloop_sdk.client.api.viatars import (
    get_viatar_api_v2_viatars_viatar_id_get,
)
from bodyloop_sdk.client.api.markers_and_measures import (
    get_axes_api_v2_viatars_viatar_id_axes_get
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

BODY_TWO_COLUMN_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "1fr 1fr 1fr",
    "columnGap": "1.5rem",
    "alignItems": "start",
    "marginTop": "1rem",
}


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


def get_axes_payload(client: AuthenticatedClient, selected_viatar_id):
    if not selected_viatar_id:
        return None, "Select a viatar to load axes."

    try:
        viatar_id = int(selected_viatar_id)
    except (TypeError, ValueError):
        return None, "Invalid viatar selection."

    axes = get_axes_api_v2_viatars_viatar_id_axes_get.sync(
        client=client,
        viatar_id=viatar_id,
    )

    if not axes:
        return None, "No axes found for this viatar."

    axes_rows: list[dict] = []
    xy_by_axis_path: dict[str, float] = {}
    for axis in axes:
        axis_dict = axis.to_dict() if hasattr(axis, "to_dict") else {}
        rotation = axis_dict.get("rotation", None)
        axis_path = axis_dict.get("axis_path", "")

        axes_rows.append(
            {
                "Axis Path": axis_path,
                "Rotation": json.dumps(rotation, ensure_ascii=False),
            }
        )

        if isinstance(rotation, dict) and "xy" in rotation:
            try:
                xy_by_axis_path[axis_path] = float(rotation["xy"])
            except (TypeError, ValueError):
                pass

    return {
        "viatar_id": str(viatar_id),
        "rows": axes_rows,
        "xy_by_axis_path": xy_by_axis_path,
    }, None


def build_axes_component_from_payload(payload: dict):
    axes_rows = payload.get("rows", [])
    axes_df = pd.DataFrame(axes_rows, columns=["Axis Path", "Rotation"])
    if axes_df.empty:
        return html.Div("No axes found for this viatar.", style={"marginTop": "0.75rem", "color": "#666"})

    axes_table = dash_table.DataTable(
        data=axes_df.to_dict("records"),
        columns=[{"name": col, "id": col} for col in axes_df.columns],
        page_size=12,
        style_table={"marginTop": "0.75rem", "overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "0.35rem"},
    )

    return html.Div([axes_table], style={"width": "100%"})


def load_mesh_from_memory(glb_bytes: bytes):
    mesh = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")
    if isinstance(mesh, trimesh.Scene):
        meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if meshes:
            mesh = trimesh.util.concatenate(meshes)
    return mesh


def build_model_component(client: AuthenticatedClient, selected_viatar_id):
    if not selected_viatar_id:
        return html.Div("Select a viatar to load 3D model.", style={"marginTop": "0.75rem", "color": "#666"})

    try:
        viatar_id = int(selected_viatar_id)
    except (TypeError, ValueError):
        return html.Div("Invalid viatar selection for model.", style={"marginTop": "0.75rem", "color": "#b00020"})

    try:
        model = get_model_api_v2_viatars_viatar_id_models_model_name_get.sync_detailed(
            client=client,
            viatar_id=viatar_id,
            model_name="avatar_3d.glb",
        ).content
    except Exception as exc:
        return html.Div(f"Could not load 3D model: {exc}", style={"marginTop": "0.75rem", "color": "#b00020"})

    if not model:
        return html.Div("3D model is empty or unavailable.", style={"marginTop": "0.75rem", "color": "#666"})

    try:
        mesh = load_mesh_from_memory(model)
        if not isinstance(mesh, trimesh.Trimesh):
            return html.Div("3D model format could not be interpreted.", style={"marginTop": "0.75rem", "color": "#b00020"})

        vertices = mesh.vertices
        faces = mesh.faces
        if len(vertices) == 0 or len(faces) == 0:
            return html.Div("3D model has no visible geometry.", style={"marginTop": "0.75rem", "color": "#666"})

        z_norm = (vertices[:, 2] - vertices[:, 2].min()) / (vertices[:, 2].max() - vertices[:, 2].min() + 1e-8)

        figure = go.Figure(
            data=[
                go.Mesh3d(
                    x=vertices[:, 0],
                    y=vertices[:, 1],
                    z=vertices[:, 2],
                    i=faces[:, 0],
                    j=faces[:, 1],
                    k=faces[:, 2],
                    intensity=z_norm,
                    colorscale="Viridis",
                    showscale=False,
                    lighting={"ambient": 0.4, "diffuse": 0.8, "specular": 0.3},
                    lightposition={"x": 100, "y": 200, "z": 300},
                )
            ]
        )
        figure.update_layout(
            title="3D Viewer",
            scene={"aspectmode": "data", "camera": {"eye": {"x": 1.5, "y": 1.5, "z": 1.5}}},
            height=480,
            margin={"l": 10, "r": 10, "t": 40, "b": 10},
        )
    except Exception as exc:
        return html.Div(f"Failed to render 3D model: {exc}", style={"marginTop": "0.75rem", "color": "#b00020"})

    return dcc.Graph(
        figure=figure,
        config={"displayModeBar": True},
        style={"marginTop": "0.75rem", "width": "100%"},
    )


def build_viatar_content_component(client: AuthenticatedClient, payload: dict, selected_viatar_id):
    axes_component = build_axes_component_from_payload(payload)
    model_component = build_model_component(client, selected_viatar_id)
    return html.Div([axes_component, model_component], style={"width": "100%"})


def build_delta_component(payload_a: dict | None, payload_b: dict | None):
    if not payload_a or not payload_b:
        return html.Div("Fetch both A and B to show delta (B - A).", style={"marginTop": "0.75rem", "color": "#666"})

    xy_a = payload_a.get("xy_by_axis_path", {})
    xy_b = payload_b.get("xy_by_axis_path", {})
    common_axis_paths = sorted(set(xy_a.keys()) & set(xy_b.keys()))
    if not common_axis_paths:
        return html.Div("No shared XY axis rotations between A and B.", style={"marginTop": "0.75rem", "color": "#666"})

    delta_rows = []
    for axis_path in common_axis_paths:
        diff = float(xy_b[axis_path]) - float(xy_a[axis_path])
        delta_rows.append(
            {
                "Axis Path": axis_path,
                "XY A": round(float(xy_a[axis_path]), 6),
                "XY B": round(float(xy_b[axis_path]), 6),
                "XY Diff (B-A)": round(diff, 6),
            }
        )

    delta_table = dash_table.DataTable(
        data=delta_rows,
        columns=[
            {"name": "Axis Path", "id": "Axis Path"},
            {"name": "XY A", "id": "XY A"},
            {"name": "XY B", "id": "XY B"},
            {"name": "XY Diff (B-A)", "id": "XY Diff (B-A)"},
        ],
        page_size=12,
        style_table={"marginTop": "0.75rem", "overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "0.35rem"},
    )

    return html.Div([delta_table], style={"width": "100%"})

web_app.layout = html.Div(
    [
        html.Div(
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
            ],
            id="header",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Viatar A", style=FIELD_LABEL_STYLE),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="viatar-dropdown-a",
                                    options=[],
                                    value=None,
                                    placeholder="Select a proband to fetch viatars",
                                    style={"width": "28rem"},
                                ),
                                html.Button(
                                    "Fetch A",
                                    id="fetch-a-button",
                                    n_clicks=0,
                                    style={"minWidth": "7rem"},
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "0.75rem"},
                        ),
                        html.Div(id="sync-indicator-a"),
                        html.Div(id="axes-a-container"),
                    ],
                    style={"display": "flex", "flexDirection": "column", "alignItems": "flex-start", "gap": "0.75rem"},
                ),
                html.Div(
                    [
                        html.Label("Delta (B - A)", style=FIELD_LABEL_STYLE),
                        html.Div(id="axes-delta-container"),
                    ],
                    style={"display": "flex", "flexDirection": "column", "alignItems": "flex-start", "gap": "0.75rem"},
                ),
                html.Div(
                    [
                        html.Label("Viatar B", style=FIELD_LABEL_STYLE),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="viatar-dropdown-b",
                                    options=[],
                                    value=None,
                                    placeholder="Select a proband to fetch viatars",
                                    style={"width": "28rem"},
                                ),
                                html.Button(
                                    "Fetch B",
                                    id="fetch-b-button",
                                    n_clicks=0,
                                    style={"minWidth": "7rem"},
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "0.75rem"},
                        ),
                        html.Div(id="sync-indicator-b"),
                        html.Div(id="axes-b-container"),
                    ],
                    style={"display": "flex", "flexDirection": "column", "alignItems": "flex-start", "gap": "0.75rem"},
                ),
            ],
            id="body",
            style=BODY_TWO_COLUMN_STYLE,
        ),
        html.Div(
            [
                html.Div(id="load-info", style={"marginTop": "1rem"}),
            ],
            id="footer",
        ),
        dcc.Store(id="auth-store"),
        dcc.Store(id="axes-a-store"),
        dcc.Store(id="axes-b-store"),
    ],
    style={"padding": "2rem"},
)

@callback(
    Output("load-info", "children"),
    Output("proband-dropdown", "options"),
    Output("proband-dropdown", "value"),
    Output("viatar-dropdown-a", "options"),
    Output("viatar-dropdown-a", "value"),
    Output("viatar-dropdown-b", "options"),
    Output("viatar-dropdown-b", "value"),
    Output("auth-store", "data"),
    Input("load-button", "n_clicks"),
    State("base-url-input", "value"),
    State("username-input", "value"),
    State("password-input", "value"),
    prevent_initial_call=True,
)
def compare(n_clicks, base_url, username, password):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    if not base_url or not username or not password:
        return "Please fill in all fields.", [], None, [], None, [], None, None
    
   
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
        return f"Could not connect to {base_url}. Please check the URL and that BodyLoop is running. {e}", [], None, [], None, [], None, None

    if response.status_code == 200:
        api_token = response.parsed.access_token
    else:
        return "Login failed. Please check your credentials and try again.", [], None, [], None, [], None, None

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
        return "No probands found.", [], None, [], None, [], None, {
            "base_url": base_url,
            "api_token": api_token,
        }
    
    return f"Loaded {len(options)} probands.", options, options[0]["value"], [], None, [], None, {
        "base_url": base_url,
        "api_token": api_token,
    }


@callback(
    Output("viatar-dropdown-a", "options", allow_duplicate=True),
    Output("viatar-dropdown-a", "value", allow_duplicate=True),
    Output("viatar-dropdown-b", "options", allow_duplicate=True),
    Output("viatar-dropdown-b", "value", allow_duplicate=True),
    Input("proband-dropdown", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def load_viatars_for_proband(selected_proband_id, auth_data):
    if not selected_proband_id or not auth_data:
        return [], None, [], None

    base_url = auth_data.get("base_url")
    api_token = auth_data.get("api_token")
    if not base_url or not api_token:
        return [], None, [], None

    try:
        proband_id = int(selected_proband_id)
    except (TypeError, ValueError):
        return [], None, [], None

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
        return [], None, [], None

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
        return [], None, [], None

    options.reverse()

    selected_a = options[0]["value"]
    selected_b = options[1]["value"] if len(options) > 1 else options[0]["value"]
    return options, selected_a, options, selected_b


@callback(
    Output("axes-a-container", "children"),
    Output("axes-b-container", "children"),
    Output("axes-a-store", "data"),
    Output("axes-b-store", "data"),
    Input("fetch-a-button", "n_clicks"),
    Input("fetch-b-button", "n_clicks"),
    State("viatar-dropdown-a", "value"),
    State("viatar-dropdown-b", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def load_axes_for_selected_viatars(fetch_a_clicks, fetch_b_clicks, viatar_a_id, viatar_b_id, auth_data):
    if not fetch_a_clicks and not fetch_b_clicks:
        return no_update, no_update, no_update, no_update

    triggered_id = ctx.triggered_id

    if triggered_id == "fetch-a-button":
        if not auth_data:
            return html.Div("Load credentials first."), no_update, None, no_update

        base_url = auth_data.get("base_url")
        api_token = auth_data.get("api_token")
        if not base_url or not api_token:
            return html.Div("Load credentials first."), no_update, None, no_update

        client = AuthenticatedClient(
            base_url=base_url,
            verify_ssl=False,
            token=api_token,
            timeout=10.0,
        )
        payload_a, error_a = get_axes_payload(client, viatar_a_id)
        if error_a:
            return html.Div(error_a, style={"marginTop": "0.75rem", "color": "#b00020"}), no_update, None, no_update

        return build_viatar_content_component(client, payload_a, viatar_a_id), no_update, payload_a, no_update

    if triggered_id == "fetch-b-button":
        if not auth_data:
            return no_update, html.Div("Load credentials first."), no_update, None

        base_url = auth_data.get("base_url")
        api_token = auth_data.get("api_token")
        if not base_url or not api_token:
            return no_update, html.Div("Load credentials first."), no_update, None

        client = AuthenticatedClient(
            base_url=base_url,
            verify_ssl=False,
            token=api_token,
            timeout=10.0,
        )
        payload_b, error_b = get_axes_payload(client, viatar_b_id)
        if error_b:
            return no_update, html.Div(error_b, style={"marginTop": "0.75rem", "color": "#b00020"}), no_update, None

        return no_update, build_viatar_content_component(client, payload_b, viatar_b_id), no_update, payload_b

    return no_update, no_update, no_update, no_update


@callback(
    Output("axes-delta-container", "children"),
    Input("axes-a-store", "data"),
    Input("axes-b-store", "data"),
)
def load_delta_view(axes_a_payload, axes_b_payload):
    return build_delta_component(axes_a_payload, axes_b_payload)


@callback(
    Output("sync-indicator-a", "children"),
    Output("sync-indicator-b", "children"),
    Input("viatar-dropdown-a", "value"),
    Input("viatar-dropdown-b", "value"),
    Input("axes-a-store", "data"),
    Input("axes-b-store", "data"),
)
def show_not_in_sync_indicator(selected_a, selected_b, axes_a_payload, axes_b_payload):
    def build_indicator(selected_value, payload):
        if not payload or not payload.get("viatar_id"):
            return html.Div("No fetched data yet.", style={"color": "#666", "fontSize": "0.9rem"})

        fetched_viatar_id = str(payload.get("viatar_id"))
        selected_viatar_id = str(selected_value) if selected_value is not None else ""

        if selected_viatar_id != fetched_viatar_id:
            return html.Div(
                f"⚠ not-in-sync: selected {selected_viatar_id or '-'} vs fetched {fetched_viatar_id}",
                style={"color": "#b00020", "fontWeight": "600", "fontSize": "0.9rem"},
            )

        return html.Div("✓ in sync", style={"color": "#2e7d32", "fontWeight": "600", "fontSize": "0.9rem"})

    return build_indicator(selected_a, axes_a_payload), build_indicator(selected_b, axes_b_payload)
