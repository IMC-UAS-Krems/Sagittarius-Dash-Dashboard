import logging
import os

import dash
from flask import Flask
from flask_login import login_required

from .env import SECRET_KEY
from .utils import create_logger
from .auth import init_auth
from .auth.utils import setup_auth_db
from .auth.routes import auth_blueprint

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
    
    server.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/users.db"
    server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    server.config["LOGIN_DISABLED"] = False
    server.config["APPLICATION_ROOT"] = "/"
    server.config["PREFERRED_URL_SCHEME"] = "http"
    
    # define route bp's here
    server.register_blueprint(auth_blueprint)
    
    init_auth(server)
    setup_auth_db(server)
    app.logger.info(f"Db is in {os.path.abspath('users.db')}")


def setup() -> None:
    """Sets up everything for the Dash app"""

    logger = create_logger("dash_app")
    logger.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
    _setup_server()
    _secure_dash()
    
