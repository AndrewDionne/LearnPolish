"""Production Gunicorn module; fails closed before accepting requests."""
from render_app import create_render_app

app = create_render_app()
