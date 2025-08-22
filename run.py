from dotenv import load_dotenv
from app import create_app
import os

# Load environment variables from .env locally
if os.environ.get("RENDER") != "true":  # Only load .env when NOT on Render
    load_dotenv()  # This reads .env in the project root
    
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if os.environ.get("RENDER") != "true":
        from app.utils import open_browser
        open_browser()
    print(f"🚀 Starting Flask app on port {port}...")
    app.run(host="0.0.0.0", port=port)
