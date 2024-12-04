import logging
import os

import dash
from flask import Flask
from flask_login import login_required

from .env import SECRET_KEY
from .user_auth import auth, login_manager
from .utils import create_logger

server = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)


app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname="/dash/",
    external_stylesheets=[
        "/static/tailwind.css",
        "/static/react-resizable-css.css",
        "/static/react-grid-layout-css.css",
    ],
)


def _secure_dash() -> None:
    """Adds login_required to all Dash routes"""

    for view_func in server.view_functions:
        if view_func.startswith("/dash/"):
            server.view_functions[view_func] = login_required(
                server.view_functions[view_func]
            )


def _setup_server() -> None:
    """Registers blueprints and sets up login_manager"""

    server.config["SECRET_KEY"] = SECRET_KEY
    server.register_blueprint(auth)
    login_manager.init_app(server)
    login_manager.login_view = "auth.login_get"


def setup() -> None:
    """Sets up everything for the Dash app"""

    logger = create_logger("dash_app")
    logger.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
    _secure_dash()
    _setup_server()
