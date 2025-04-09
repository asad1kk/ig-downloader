# Instagram Media Downloader Bot

A Telegram bot that allows users to download photos and videos from Instagram posts, reels, and IGTV.

## 👨‍💻 Author
**Asadbek Abdukhalilov** - [AsaDev]

## 📋 Features

- 📥 Download images, videos, and reels from Instagram
- 🚀 Fast download using yt-dlp and instaloader
- 📊 Track user statistics and downloads
- 🔐 Support for private Instagram content (with login)
- 📱 Clean and simple user interface
- 📦 MongoDB integration for storing user data

## 🛠️ Requirements

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API ID and API Hash (from [my.telegram.org](https://my.telegram.org))
- MongoDB Atlas account (free tier is sufficient)
- Instagram account (optional, for accessing private content)

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/asad1kk/ig-downloader.git
   cd ig-downloader
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file by copying the template:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your credentials:
   ```
   # Telegram API credentials
   API_ID=your_telegram_api_id
   API_HASH=your_telegram_api_hash
   BOT_TOKEN=your_bot_token
   
   # MongoDB connection string
   MONGO_URI=your_mongodb_connection_string
   
   # Instagram credentials (optional, for private content)
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   ```

## 🚀 Usage

1. Run the bot:
   ```bash
   python bot.py
   ```

2. Start a chat with your bot on Telegram.

3. Send an Instagram link (post, reel, or IGTV) to the bot.

4. The bot will download and send the media to you in Telegram.

## 💡 Available Commands

- `/start` - Start the bot and get introduction
- `/help` - Show help information
- `/stats` - View your download statistics

## 🔧 Configuration Options

### MongoDB Setup

This bot uses MongoDB Atlas (free tier) for storing user data. 

1. Create a [MongoDB Atlas account](https://www.mongodb.com/cloud/atlas/register)
2. Set up a free shared cluster
3. Create a database named `instagram_downloader`
4. Create collections: `users` and `downloads`
5. Get your MongoDB connection string and add it to the `.env` file

### Instagram Login (Optional)

For downloading content from private accounts:

1. Add your Instagram username and password to the `.env` file
2. The bot will automatically log in to Instagram using these credentials

## 🤔 Troubleshooting

- **Failed to download media**: The post might be from a private account or deleted.
- **Large files not sending**: Telegram has a 50MB file size limit for bots.
- **Rate limiting**: Instagram might temporarily block requests if too many are made in a short time.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Pyrogram](https://github.com/pyrogram/pyrogram) for Telegram API interactions

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details. 