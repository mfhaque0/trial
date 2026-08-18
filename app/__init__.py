from pathlib import Path

from flask import Flask
from config import Config


def create_app(config_object=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    from app.models.database import initialise
    initialise(app.config["DATABASE"])
    from app.routes.main import main
    from app.routes.calculators import calculators
    from app.routes.auth import auth
    from app.routes.workspace import workspace
    from app.routes.api import api
    app.register_blueprint(main)
    app.register_blueprint(calculators, url_prefix="/api/calculators")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(workspace)
    app.register_blueprint(api, url_prefix="/api")
    from app.routes.common import current_user, csrf_token
    @app.context_processor
    def inject_identity():
        return {"current_user": current_user(), "csrf_token": csrf_token()}
    return app
