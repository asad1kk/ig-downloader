Instagram Media Downloader Bot - Context Documentation
📌 Overview
Instagram Media Downloader Bot is a Telegram bot built using Pyrogram, designed to fetch and download images/videos from Instagram links. It provides users with a seamless way to access Instagram content directly from Telegram.

🛠️ Tech Stack
Framework: Pyrogram (for Telegram API interaction)

Database: MongoDB (Free - MongoDB Atlas)

Instagram Media Fetching: yt-dlp and instaloader

Hosting: Can be deployed on Heroku, VPS, or Railway.app

📂 Features
✔️ Accepts only Instagram links
✔️ Downloads images, videos, reels from Instagram
✔️ Uses MongoDB Atlas for user data storage
✔️ Sends media directly in Telegram chat
✔️ Efficient error handling for invalid/unsupported links
✔️ Supports both private and public Instagram content (login required for private)

📜 Requirements
Before running the bot, ensure you have:

Python 3.8+

A Telegram bot token (from @BotFather)

A MongoDB Atlas database

Installed dependencies:

pip install pyrogram tgcrypto instaloader yt-dlp pymongo


💾 Database Schema (MongoDB - Free Atlas Plan)
The bot stores user interactions in MongoDB.

📌 Collection: users
Stores basic user details.

json
Copy
Edit
{
  "_id": "123456789",
  "username": "example_user",
  "first_name": "John",
  "last_active": "2025-04-03T14:00:00Z"
}
📌 Collection: downloads
Stores download logs.

json
Copy
Edit
{
  "_id": "unique_id",
  "user_id": "123456789",
  "instagram_url": "https://www.instagram.com/p/xyz123/",
  "file_path": "/downloads/video.mp4",
  "timestamp": "2025-04-03T14:05:00Z"
}
🚀 Deployment Guide
Set Up MongoDB Atlas

Create a free account on MongoDB Atlas

Set up a free shared cluster

Get your MongoDB connection string

Set Up the Bot

Create a bot via @BotFather

Get the bot token

Add API credentials in config.env

Run the Bot

bash
Copy
Edit
python bot.py
🔒 Security & Limitations
⚠️ Limitations: Instagram API restrictions may apply for private content.
🔑 Security: Keep your bot token & MongoDB URI private.

📞 Support & Contributions
Contributions are welcome! For issues or suggestions, open a ticket on GitHub.

## BOT TELEGRAM TOKEN

TOKEN = "7602695025:AAEIEWYiERQeLa9ndOM2VGrKfJlceHva9v4"