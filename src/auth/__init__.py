from flask import Flask
from flask_login import LoginManager
from .models import db, User

login_manager = LoginManager()

def init_auth(app: Flask):
    """
    Initialize authentication module.
    """
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None