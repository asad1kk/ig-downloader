import os
import re
import logging
import asyncio
import time
from telethon import TelegramClient, events, Button
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

# Initialize the Telegram client (bot)
bot = TelegramClient(
    'instagram_downloader_bot_telethon',
    config.API_ID,
    config.API_HASH
)

# Command handlers
@bot.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    """Handle /start command"""
    try:
        user = await event.get_sender()
        user_id = user.id
        username = user.username or ""
        first_name = user.first_name or ""
        
        logger.info(f"Received /start command from user: {user_id}")
        
        # Add user to database
        db.add_user(user_id, username, first_name)
        
        # Simple welcome message
        welcome_text = f"👋 Hello {first_name}!\n\nI'm an Instagram Media Downloader Bot. Send me an Instagram link, and I'll download the media for you."
        
        # Create keyboard with buttons
        keyboard = [
            [Button.inline("My Stats", b'stats')],
            [Button.inline("Help", b'help')]
        ]
        
        await event.respond(welcome_text, buttons=keyboard)
        logger.info(f"Sent welcome message to user: {user_id}")
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")

@bot.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    """Handle /help command"""
    try:
        user = await event.get_sender()
        user_id = user.id
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
        
        keyboard = [
            [Button.url("Developer", "https://t.me/your_username")]
        ]
        
        await event.respond(help_text, buttons=keyboard)
        logger.info(f"Sent help message to user: {user_id}")
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")

@bot.on(events.NewMessage(pattern='/stats'))
async def stats_command(event):
    """Handle /stats command"""
    try:
        user = await event.get_sender()
        user_id = user.id
        logger.info(f"Received /stats command from user: {user_id}")
        
        stats = db.get_user_stats(user_id)
        
        stats_text = f"Your Statistics\n\n- Total Downloads: {stats['downloads_count']}"
        
        await event.respond(stats_text)
        logger.info(f"Sent stats to user: {user_id}")
    except Exception as e:
        logger.error(f"Error in stats_command: {str(e)}")

# Callback query handler
@bot.on(events.CallbackQuery())
async def handle_callback_query(event):
    """Handle callback queries from inline keyboard buttons"""
    try:
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        logger.info(f"Received callback query with data '{data}' from user: {user_id}")
        
        if data == 'stats':
            stats = db.get_user_stats(user_id)
            stats_text = f"Your Statistics\n\n- Total Downloads: {stats['downloads_count']}"
            await event.respond(stats_text)
        
        elif data == 'help':
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
            
            keyboard = [
                [Button.url("Developer", "https://t.me/your_username")]
            ]
            
            await event.respond(help_text, buttons=keyboard)
        
        await event.answer()  # Answer the callback query
        logger.info(f"Processed callback query with data '{data}' from user: {user_id}")
    except Exception as e:
        logger.error(f"Error in handle_callback_query: {str(e)}")

# Media downloader handler - using regex to match Instagram URLs
@bot.on(events.NewMessage(pattern=r'https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+'))
async def download_media(event):
    """Handle Instagram URLs"""
    try:
        user = await event.get_sender()
        user_id = user.id
        username = user.username or ""
        first_name = user.first_name or ""
        
        logger.info(f"Received Instagram URL from user: {user_id}")
        
        # Add/update user in database
        db.add_user(user_id, username, first_name)
        
        # Extract Instagram URL from message
        url_match = re.search(r'(https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+)', event.text)
        if not url_match:
            await event.respond("Invalid Instagram URL. Please send a valid Instagram post, reel, or IGTV link.")
            logger.warning(f"Invalid Instagram URL received from user: {user_id}")
            return
        
        url = url_match.group(1)
        logger.info(f"Extracted URL: {url}")
        
        # Send processing message
        processing_msg = await event.respond("Processing your Instagram link... Please wait.")
        
        # Download the media
        try:
            start_time = time.time()
            files = downloader.download(url)
            download_time = time.time() - start_time
            
            if not files:
                await bot.edit_message(processing_msg, "⚠️ Could not download this Instagram post. Instagram may be blocking our requests (HTTP 401). Please try another link.")
                logger.warning(f"Failed to download media from URL: {url}")
                return
            
            logger.info(f"Successfully downloaded {len(files)} files from {url}")
            
            # Send success message
            await bot.edit_message(processing_msg, f"Download successful! ({len(files)} files)\nTime taken: {download_time:.2f} seconds\n\nUploading to Telegram...")
            
            # Send media files to user
            for file_path in files:
                try:
                    file_size = os.path.getsize(file_path)
                    file_name = os.path.basename(file_path)
                    logger.info(f"Sending file: {file_name} ({file_size} bytes)")
                    
                    # Check if the file is a text file with error messages
                    if file_path.endswith('.txt'):
                        with open(file_path, 'r') as f:
                            error_content = f.read()
                        
                        # If it contains an error message, send a more user-friendly explanation
                        if "401" in error_content or "Unauthorized" in error_content:
                            await event.respond("⚠️ **Instagram Authentication Error**\n\nInstagram is requiring authentication to access this post. This may happen if:\n\n• The post is from a private account\n• Instagram is enforcing regional restrictions\n• Instagram has temporarily limited access to their API\n\nPlease try a different post or try again later.")
                            continue
                        elif "download_failed" in file_path or "post_unavailable" in file_path:
                            await event.respond("⚠️ **Download Failed**\n\nThis Instagram post could not be downloaded. Instagram may have restricted access to this content.")
                            continue
                    
                    # Check file extension
                    if file_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        await bot.send_file(
                            user_id,
                            file_path,
                            caption=f"Instagram Photo\n{url}"
                        )
                    elif file_path.endswith(('.mp4', '.mov', '.avi')):
                        if file_size > 50 * 1024 * 1024:  # If file size > 50MB
                            await event.respond(f"Video file is too large ({file_size / (1024 * 1024):.2f} MB). Telegram has a 50MB limit for bots.")
                        else:
                            await bot.send_file(
                                user_id,
                                file_path,
                                caption=f"Instagram Video\n{url}"
                            )
                    else:
                        await bot.send_file(
                            user_id,
                            file_path,
                            caption=f"Instagram Media\n{url}"
                        )
                    
                    logger.info(f"Successfully sent file: {file_name}")
                    
                    # Log successful download
                    db.log_download(user_id, url, file_path)
                
                except Exception as e:
                    logger.error(f"Error sending file to user: {e}")
                    await event.respond(f"Error sending file: {file_name}")
            
            # Final success message
            await bot.edit_message(processing_msg, f"All files sent successfully!\nTime taken: {time.time() - start_time:.2f} seconds")
            
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
            
            # Provide a better error message for authentication issues
            if "401" in str(e) or "Unauthorized" in str(e):
                await bot.edit_message(processing_msg, "⚠️ **Instagram Authentication Error**\n\nInstagram is requiring authentication to access this post. The post may be from a private account or Instagram has limited API access.")
            else:
                await bot.edit_message(processing_msg, f"Error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling Instagram URL: {str(e)}")

# Handle all other text messages
@bot.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/') and not re.match(r'https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+', e.text)))
async def handle_text(event):
    """Handle text messages that are not commands or Instagram URLs"""
    try:
        user = await event.get_sender()
        logger.info(f"Received text message from user: {user.id}")
        
        await event.respond(
            "Please send an Instagram link (post, reel, or IGTV) to download media.\n\n"
            "Example: https://www.instagram.com/p/XXXXXXXXXX/\n\n"
            "Type /help for more information."
        )
        
        logger.info(f"Sent help message for invalid text to user: {user.id}")
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}")

# Debug handler to log all messages
@bot.on(events.NewMessage())
async def debug_all_messages(event):
    """Log all incoming messages for debugging"""
    try:
        if event.sender_id:
            logger.info(f"DEBUG: Received message: {event.text or '[No text]'} from user: {event.sender_id}")
    except Exception as e:
        logger.error(f"Error in debug handler: {str(e)}")

async def main():
    """Main function to start the bot"""
    # Initialize the bot with the bot token
    await bot.start(bot_token=config.BOT_TOKEN)
    
    logging.info("Starting Instagram Downloader Bot (Telethon)...")
    
    # Print configuration status
    logging.info(f"Bot Token configured: {bool(config.BOT_TOKEN)}")
    logging.info(f"API ID configured: {bool(config.API_ID)}")
    logging.info(f"API Hash configured: {bool(config.API_HASH)}")
    logging.info(f"MongoDB configured: {bool(config.MONGO_URI)}")
    
    try:
        logging.info("Bot started successfully!")
        
        # Run the bot until disconnected
        await bot.run_until_disconnected()
        
        # Cleanup on exit
        db.close()
        logging.info("Bot has been stopped")
    except Exception as e:
        logging.error(f"Error running bot: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}") 