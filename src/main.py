import logging

import orjson
from asgiref.wsgi import WsgiToAsgi
from dash import dcc, html
from flask import Response, redirect, request
from werkzeug.datastructures import FileStorage
from werkzeug.wrappers import Response as WerkzeugResponse

import my_dash_component

from .config import App
from .init_dash import app, server, setup

Dashboard: App = None  # type: ignore


def create_grid() -> list[my_dash_component.Container | dcc.Graph]:
    """Create the html grid for the dashboard. This grid contains all visualizations"""

    grid = []
    for grid_item in Dashboard.plots:
        if grid_item.selector:
            grid.append(
                my_dash_component.Container(
                    [
                        grid_item.selector[0],
                        grid_item.selector[1],
                        dcc.Graph(
                            className="w-full h-1/2 flex-1", id=grid_item.plot_id
                        ),
                    ]
                )
            )
        else:
            grid.append(
                dcc.Graph(
                    className="w-full h-full",
                    figure=grid_item.plot,
                    responsive=True,
                )
            )

    for grid_item in Dashboard.tables:
        grid.append(html.Div(className="w-full h-full pb-1.5", children=grid_item))

    return grid


def create_layout() -> list[my_dash_component.Container | dcc.Graph]:
    """Create the layout for the dashboard"""

    return html.Div(
        [
            dcc.Location(id="sag_url", refresh=False),
            my_dash_component.Navbar(
                id="sag_navbar",
                dashboard_name=Dashboard.service.name,
                dashboard_picture="https://www.fh-krems.ac.at/fileadmin/imc/images/logos/imc-logo-web-preview.png",
                dashboard_version=str(Dashboard.service.version),
            ),
            my_dash_component.Grid(create_grid(), hash=Dashboard.hash, id="sag_grid"),
        ]
    )


def init_dash() -> None:
    """Initialize the dash app"""

    global Dashboard
    Dashboard = App()
    app.layout = create_layout


@server.route("/")
def index() -> WerkzeugResponse:
    return redirect("/dash/")


@server.route("/config", methods=["POST"])
def change_config() -> Response:
    """Handle to update the dashboard configuration"""

    global Dashboard

    file: FileStorage = list(request.files.values())[0]
    new_config = orjson.loads(file.stream.read().decode("utf-8"))
    file.stream.seek(0)
    file.save("config.json")
    Dashboard = App(new_config)
    return Response(status=200)


def create_server() -> WsgiToAsgi:
    """Entry point aka main function to create the server"""

    logger = logging.getLogger("dash_app")

    setup()
    init_dash()

    logger.info("Starting server on http://localhost:8000 ...")

    return WsgiToAsgi(server)  # this tries to make stuff async
