from dash import Dash, html, dcc

from bodyloop_dashboards.pages import sync_excel, scan_compare

app = Dash(__name__)

app.layout = html.Div(
    [
        html.H2("BodyLoop Dashboards"),
        dcc.Tabs(
            id="main-tabs",
            value="sync-excel",
            children=[
                sync_excel.layout,
                scan_compare.layout,
            ],
        ),
        *sync_excel.stores,
    ],
    style={"padding": "2rem"},
)


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
