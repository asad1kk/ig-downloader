import os
import re
import logging
import asyncio
import time
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import Database
from downloader import InstagramDownloader
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the database
db = Database()

# Initialize the downloader
downloader = InstagramDownloader()

# Initialize the Telegram bot - SIMPLIFIED
bot = Client(
    "instagram_downloader_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workers=8,  # Use more workers for better handling
    parse_mode=None  # Don't use any parse mode by default
)

# Debug handler to log all incoming messages - must be registered first but will execute last
@bot.on_message(group=-999)  # Very low priority group
async def debug_all_messages(client, message):
    """Log all incoming messages for debugging"""
    try:
        if message.from_user:
            logger.info(f"DEBUG: Received message from user: {message.from_user.id}, text: {message.text or '[No text]'}")
    except Exception as e:
        logger.error(f"Error in debug handler: {str(e)}")

# Command handlers
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        logger.info(f"Received /start command from user: {user_id}")
        
        # Add user to database
        db.add_user(user_id, username, first_name)
        
        # First, try sending a simple message
        try:
            await client.send_message(
                chat_id=user_id,
                text="Hello! I'm your Instagram downloader bot."
            )
            logger.info(f"Sent simple message to user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to send simple message: {str(e)}")

        # Then try with the welcome message and buttons
        try:
            # Full welcome message
            welcome_text = f"👋 Hello {first_name}!\n\nI'm an Instagram Media Downloader Bot. Send me an Instagram link, and I'll download the media for you."
            
            # Create keyboard with buttons
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("My Stats", callback_data="stats")],
                [InlineKeyboardButton("Help", callback_data="help")]
            ])
            
            await client.send_message(
                chat_id=user_id,
                text=welcome_text,
                reply_markup=keyboard
            )
            logger.info(f"Sent welcome message to user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to send welcome message: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")

@bot.on_message(filters.command("help"))
async def help_command(client, message):
    """Handle /help command"""
    try:
        user_id = message.from_user.id
        logger.info(f"Received /help command from user: {user_id}")
        
        help_text = (
            "How to use this bot:\n\n"
            "1. Find a post/reel/IGTV on Instagram that you want to download\n"
            "2. Copy the link (share button → copy link)\n"
            "3. Paste the link and send it to me\n"
            "4. Wait for me to download and send the media\n\n"
            "Supported links:\n"
            "- Instagram Posts: https://www.instagram.com/p/...\n"
            "- Instagram Reels: https://www.instagram.com/reel/...\n"
            "- IGTV: https://www.instagram.com/tv/..."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Developer", url="https://t.me/your_username")]
        ])
        
        await client.send_message(
            chat_id=user_id,
            text=help_text,
            reply_markup=keyboard
        )
        logger.info(f"Sent help message to user: {user_id}")
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")

@bot.on_message(filters.command("stats"))
async def stats_command(client, message):
    """Handle /stats command"""
    try:
        user_id = message.from_user.id
        logger.info(f"Received /stats command from user: {user_id}")
        
        stats = db.get_user_stats(user_id)
        
        stats_text = f"Your Statistics\n\n- Total Downloads: {stats['downloads_count']}"
        
        await client.send_message(
            chat_id=user_id,
            text=stats_text
        )
        logger.info(f"Sent stats to user: {user_id}")
    except Exception as e:
        logger.error(f"Error in stats_command: {str(e)}")

# Callback query handler
@bot.on_callback_query()
async def handle_callback_query(client, callback_query):
    """Handle callback queries from inline keyboard buttons"""
    try:
        data = callback_query.data
        user_id = callback_query.from_user.id
        logger.info(f"Received callback query with data '{data}' from user: {user_id}")
        
        if data == "stats":
            stats = db.get_user_stats(user_id)
            stats_text = f"Your Statistics\n\n- Total Downloads: {stats['downloads_count']}"
            await callback_query.answer()
            await callback_query.message.reply(stats_text)
        
        elif data == "help":
            help_text = (
                "How to use this bot:\n\n"
                "1. Find a post/reel/IGTV on Instagram that you want to download\n"
                "2. Copy the link (share button → copy link)\n"
                "3. Paste the link and send it to me\n"
                "4. Wait for me to download and send the media\n\n"
                "Supported links:\n"
                "- Instagram Posts: https://www.instagram.com/p/...\n"
                "- Instagram Reels: https://www.instagram.com/reel/...\n"
                "- IGTV: https://www.instagram.com/tv/..."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Developer", url="https://t.me/your_username")]
            ])
            
            await callback_query.answer()
            await callback_query.message.reply(help_text, reply_markup=keyboard)
        
        logger.info(f"Processed callback query with data '{data}' from user: {user_id}")
    except Exception as e:
        logger.error(f"Error in handle_callback_query: {str(e)}")

# Media downloader handler
@bot.on_message(filters.regex(r'https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+') & filters.text)
async def download_media(client, message):
    """Handle Instagram URLs"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        
        logger.info(f"Received Instagram URL from user: {user_id}")
        
        # Add/update user in database
        db.add_user(user_id, username, first_name)
        
        # Extract Instagram URL from message
        url_match = re.search(r'(https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+)', message.text)
        if not url_match:
            await message.reply("Invalid Instagram URL. Please send a valid Instagram post, reel, or IGTV link.")
            logger.warning(f"Invalid Instagram URL received from user: {user_id}")
            return
        
        url = url_match.group(1)
        logger.info(f"Extracted URL: {url}")
        
        # Send processing message
        processing_msg = await message.reply("Processing your Instagram link... Please wait.")
        
        # Download the media
        try:
            start_time = time.time()
            files = downloader.download(url)
            download_time = time.time() - start_time
            
            if not files:
                await processing_msg.edit("Failed to download media. Possible reasons:\n- Private content\n- Invalid or expired link\n- Content no longer available")
                logger.warning(f"Failed to download media from URL: {url}")
                return
            
            logger.info(f"Successfully downloaded {len(files)} files from {url}")
            
            # Send success message
            await processing_msg.edit(f"Download successful! ({len(files)} files)\nTime taken: {download_time:.2f} seconds\n\nUploading to Telegram...")
            
            # Send media files to user
            for file_path in files:
                try:
                    file_size = os.path.getsize(file_path)
                    file_name = os.path.basename(file_path)
                    logger.info(f"Sending file: {file_name} ({file_size} bytes)")
                    
                    # Check file extension
                    if file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        await message.reply_photo(
                            file_path,
                            caption=f"Instagram Photo\n{url}"
                        )
                    elif file_path.endswith(('.mp4', '.mov', '.avi')):
                        if file_size > 50 * 1024 * 1024:  # If file size > 50MB
                            await message.reply(f"Video file is too large ({file_size / (1024 * 1024):.2f} MB). Telegram has a 50MB limit for bots.")
                        else:
                            await message.reply_video(
                                file_path,
                                caption=f"Instagram Video\n{url}"
                            )
                    else:
                        await message.reply_document(
                            file_path,
                            caption=f"Instagram Media\n{url}"
                        )
                    
                    logger.info(f"Successfully sent file: {file_name}")
                    
                    # Log successful download
                    db.log_download(user_id, url, file_path)
                
                except Exception as e:
                    logger.error(f"Error sending file to user: {e}")
                    await message.reply(f"Error sending file: {file_name}")
            
            # Final success message
            await processing_msg.edit(f"All files sent successfully!\nTime taken: {time.time() - start_time:.2f} seconds")
            
            # Clean up downloaded files
            for file_path in files:
                try:
                    if os.path.exists(file_path):
                        # Delete the parent directory containing the downloaded files
                        parent_dir = os.path.dirname(file_path)
                        shutil.rmtree(parent_dir, ignore_errors=True)
                        logger.info(f"Cleaned up download directory: {parent_dir}")
                        break  # We only need to delete the parent directory once
                except Exception as e:
                    logger.error(f"Error cleaning up files: {e}")
        
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            await processing_msg.edit(f"Error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling Instagram URL: {str(e)}")

@bot.on_message(~filters.regex(r'https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+') & filters.text & ~filters.command(["start", "help", "stats"]))
async def handle_text(client, message):
    """Handle text messages that are not commands or Instagram URLs"""
    try:
        logger.info(f"Received text message from user: {message.from_user.id}")
        
        await message.reply(
            "Please send an Instagram link (post, reel, or IGTV) to download media.\n\n"
            "Example: https://www.instagram.com/p/XXXXXXXXXX/\n\n"
            "Type /help for more information."
        )
        
        logger.info(f"Sent help message for invalid text to user: {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}")

# Main function to start the bot
async def main():
    """Main function to start the bot"""
    logging.info("Starting Instagram Downloader Bot...")
    
    # Print configuration status
    logging.info(f"Bot Token configured: {bool(config.BOT_TOKEN)}")
    logging.info(f"API ID configured: {bool(config.API_ID)}")
    logging.info(f"API Hash configured: {bool(config.API_HASH)}")
    logging.info(f"MongoDB configured: {bool(config.MONGO_URI)}")
    
    try:
        # Start the bot
        await bot.start()
        logging.info("Bot started successfully!")
        
        # Keep the bot running
        await idle()
        
        # Cleanup on exit
        await bot.stop()
        db.close()
        logging.info("Bot has been stopped")
    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}") 