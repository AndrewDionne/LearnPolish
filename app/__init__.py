import os
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    CORS(app, resources={r"/*": {"origins": "*"}})

    from .routes import init_routes
    init_routes(app)

    return app

