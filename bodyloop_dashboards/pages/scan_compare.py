from dash import html, dcc


layout = dcc.Tab(
    label="Scan Compare",
    value="scan-compare",
    children=[
        html.Div(
            [
                html.H3("Scan Compare"),
                html.P("This page is ready for scan comparison features."),
            ],
            style={"padding": "1rem 0"},
        )
    ],
)
