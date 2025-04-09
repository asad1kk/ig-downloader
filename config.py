import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Bot credentials
API_ID = os.getenv("API_ID", "14344238")
API_HASH = os.getenv("API_HASH", "f8d62ea73d4ad0adf7a3ebd49b110a01")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7602695025:AAEIEWYiERQeLa9ndOM2VGrKfJlceHva9v4")

# MongoDB settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://abduhalilov245:fm2F8Gc51xPxmATN@cluster0.ahjat.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Instagram credentials (optional, for private content)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# Download settings
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")

# Create download directory if it doesn't exist
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH) 