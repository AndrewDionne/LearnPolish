import os
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Debugging: check environment variables
    print("🔑 AZURE_SPEECH_KEY:", os.getenv("AZURE_SPEECH_KEY"))
    print("🌎 AZURE_REGION:", os.getenv("AZURE_REGION"))
    
    from .routes import init_routes
    init_routes(app)

    return app

