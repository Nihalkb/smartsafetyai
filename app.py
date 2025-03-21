import os
import logging
from flask import Flask
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"  # Change this to a strong secret key

# Enable CORS for frontend requests
CORS(app)

# Ensure logs directory exists
LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)
logger.info("Flask app initialized.")

# Import routes (after app initialization to avoid circular imports)
import routes
