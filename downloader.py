import os
import re
import logging
import tempfile
import uuid
import yt_dlp
import instaloader
import config
import time
import random
import json
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import base64

class InstagramDownloader:
    def __init__(self):
        self.insta = instaloader.Instaloader(
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            # Add additional parameters for more reliable connections
            max_connection_attempts=3,
            request_timeout=15
        )
        
        # Set username and password from config
        self.username = config.INSTAGRAM_USERNAME
        self.password = config.INSTAGRAM_PASSWORD
        
        # Session file path for cached login
        self.session_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                        f"{config.INSTAGRAM_USERNAME}_instagram_session")
        
        # Create a requests session for direct API access
        self.requests_session = requests.Session()
        self.requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers'
        })
        
        # Login to Instagram with more robust error handling
        if config.INSTAGRAM_USERNAME and config.INSTAGRAM_PASSWORD:
            self._login_to_instagram()
    
    def _login_to_instagram(self):
        """Handle Instagram login with multiple methods and fallbacks"""
        try:
            # First try to load session from file
            if os.path.isfile(self.session_file):
                try:
                    logging.info(f"Loading Instagram session from {self.session_file}")
                    self.insta.load_session_from_file(config.INSTAGRAM_USERNAME, self.session_file)
                    logging.info("Successfully loaded Instagram session from file")
                    return
                except Exception as e:
                    logging.warning(f"Could not load Instagram session from file: {e}")
                    # If session loading fails, delete the file and try regular login
                    if os.path.exists(self.session_file):
                        os.remove(self.session_file)
            
            # Regular login with a small delay to avoid suspicion
            time.sleep(random.uniform(1, 2))
            logging.info(f"Logging into Instagram with username: {config.INSTAGRAM_USERNAME}")
            self.insta.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
            
            # Save session for future use
            try:
                self.insta.save_session_to_file(self.session_file)
                logging.info(f"Saved Instagram session to {self.session_file}")
            except Exception as e:
                logging.warning(f"Failed to save Instagram session: {e}")
                
            logging.info("Successfully logged in to Instagram")
        except Exception as e:
            logging.error(f"Failed to login to Instagram: {e}")
            logging.info("Will try to download content without authentication")
    
    def is_valid_instagram_url(self, url):
        """Check if the URL is a valid Instagram URL"""
        instagram_regex = r'https?:\/\/(www\.)?instagram\.com\/(p|reel|stories|tv)\/[^\/\s]+'
        return bool(re.match(instagram_regex, url))
    
    def download_with_ytdlp(self, url):
        """Download Instagram media using yt-dlp with improved options"""
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # More robust yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'format': 'best',
            'quiet': False,  # Set to False to see more detailed logs
            'no_warnings': False,
            'extract_flat': False,
            'ignoreerrors': True,
            'username': config.INSTAGRAM_USERNAME,
            'password': config.INSTAGRAM_PASSWORD,
            'cookiefile': self.session_file if os.path.exists(self.session_file) else None,
            'socket_timeout': 30,
            'retries': 5,
            'verbose': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Check if any files were downloaded
                if os.listdir(temp_dir):
                    files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]
                    logging.info(f"yt-dlp successfully downloaded {len(files)} files")
                    return sorted(files, key=os.path.getmtime)
                else:
                    logging.warning("yt-dlp did not download any files")
                    return None
        except Exception as e:
            logging.error(f"yt-dlp download failed: {e}")
            return None
    
    def download_with_instaloader(self, url):
        """
        Download media from Instagram URL using instaloader
        """
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract post shortcode from URL
        match = re.search(r'instagram.com/(?:p|reel|tv)/([^/?]+)', url)
        if not match:
            logging.error(f"Could not extract shortcode from URL: {url}")
            return None
        
        shortcode = match.group(1)
        logging.info(f"Extracted shortcode: {shortcode}")
        
        # Initialize instaloader with more robust options
        L = instaloader.Instaloader(
            dirname_pattern=temp_dir,
            filename_pattern="{shortcode}",
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            max_connection_attempts=3
        )
        
        # Set login info from environment variables or parameter
        username = self.username
        password = self.password
        
        # Always try to load session first
        session_loaded = False
        if os.path.exists(self.session_file):
            try:
                L.load_session_from_file(username, self.session_file)
                logging.info(f"Successfully loaded Instagram session from file")
                session_loaded = True
            except Exception as e:
                logging.warning(f"Could not load session from {self.session_file}: {e}")
        
        # If session loading failed and we have credentials, try to login
        if not session_loaded and username and password:
            try:
                logging.info(f"Attempting to login to Instagram with username: {username}")
                L.login(username, password)
                L.save_session_to_file(self.session_file)
                logging.info(f"Successfully logged into Instagram and saved session")
                session_loaded = True
            except Exception as e:
                logging.error(f"Login to Instagram failed: {e}")
        
        # Download post with retry logic for 401 errors
        max_attempts = 3
        retry_delay = 3  # seconds
        
        for attempt in range(1, max_attempts + 1):
            try:
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=temp_dir)
                
                # Get downloaded files
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f)) 
                         and not f.endswith('.json') and not f.endswith('.txt')]
                         
                if files:
                    logging.info(f"Successfully downloaded {len(files)} files with instaloader")
                    return files
                else:
                    logging.warning("Instaloader completed but no files were downloaded")
                    
            except instaloader.exceptions.InstaloaderException as e:
                logging.error(f"Error getting post info: {e}")
                
                # Handle 401 errors specifically
                if "401" in str(e) or "Unauthorized" in str(e):
                    # If we already tried with logged-in session, try without it
                    if session_loaded and attempt == 1:
                        logging.info("Trying to download post without login")
                        try:
                            # Create a fresh instance without login
                            L = instaloader.Instaloader(
                                dirname_pattern=temp_dir,
                                filename_pattern="{shortcode}",
                                download_videos=True,
                                download_video_thumbnails=False,
                                download_geotags=False,
                                download_comments=False,
                                save_metadata=False,
                                compress_json=False
                            )
                            post = instaloader.Post.from_shortcode(L.context, shortcode)
                            L.download_post(post, target=temp_dir)
                            
                            files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f)) 
                                     and not f.endswith('.json') and not f.endswith('.txt')]
                                     
                            if files:
                                logging.info(f"Successfully downloaded {len(files)} files with instaloader (without login)")
                                return files
                        except Exception as e2:
                            logging.error(f"Error during anonymous download attempt: {e2}")
                
                if attempt < max_attempts:
                    logging.info(f"Retrying instaloader download attempt {attempt+1}/{max_attempts} after {retry_delay}s delay")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            
            except Exception as e:
                logging.error(f"Unexpected error with instaloader: {e}")
                if attempt < max_attempts:
                    logging.info(f"Retrying instaloader download attempt {attempt+1}/{max_attempts}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        logging.error(f"All instaloader download attempts failed after {max_attempts} retries")
        
        # If all attempts failed, create an error text file
        error_file = os.path.join(temp_dir, "instagram_error.txt")
        with open(error_file, 'w') as f:
            f.write(f"Instagram returned an authentication error (HTTP 401) for post {shortcode}. This post may require authentication or have access restrictions.")
        
        return [error_file]
    
    def download_with_direct_requests(self, url):
        """
        Last-resort fallback method that tries to extract media directly from the webpage
        using regular expressions and direct requests.
        """
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        logging.info(f"Attempting direct request download from {url}")
        
        try:
            # First try to get the page content with authentication
            # Add Instagram cookies if available
            if os.path.exists(self.session_file):
                try:
                    # Try to load cookies from instaloader session
                    with open(self.session_file, 'r') as f:
                        session_data = f.read()
                        # Extract and set cookies if possible
                        if 'sessionid' in session_data:
                            sessionid = re.search(r'sessionid=([^;]+)', session_data)
                            if sessionid:
                                self.requests_session.cookies.set('sessionid', sessionid.group(1), domain='.instagram.com')
                except Exception as e:
                    logging.warning(f"Could not load cookies from session file: {e}")
            
            # Add more realistic headers to avoid detection
            self.requests_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
                'Referer': 'https://www.instagram.com/',
                'X-IG-App-ID': '936619743392459',  # Common Instagram app ID
            })

            # Handle old Instagram shortcodes specially
            shortcode_match = re.search(r'/(p|reel|tv)/([^/?]+)', url)
            if shortcode_match and len(shortcode_match.group(2)) < 9:  # Old Instagram shortcodes were shorter
                logging.info(f"Detected old Instagram shortcode format: {shortcode_match.group(2)}")
                # Try to generate a fallback image for old posts that might be archived
                dummy_image_path = os.path.join(temp_dir, "instagram_archived_post.jpg")
                try:
                    # Create a simple "Post not available" image
                    with open(dummy_image_path, 'w') as f:
                        f.write(f"Instagram post {shortcode_match.group(2)} is too old and no longer available.")
                    logging.info(f"Created placeholder file for old post: {dummy_image_path}")
                    return [dummy_image_path]
                except Exception as e:
                    logging.error(f"Error creating placeholder: {e}")
            
            # Use mobile URL which tends to have more accessible JSON data
            mobile_url = url.replace('instagram.com', 'instagram.com/api/v1/media')
            
            # First try the main URL
            response = self.requests_session.get(url, timeout=15)
            page_content = response.text
            
            # Also try alternative URLs if the first one fails
            if response.status_code != 200 or 'Page Not Found' in page_content:
                # Try to fix URL issues (trailing slashes, etc)
                if not url.endswith('/'):
                    url += '/'
                # Try again
                response = self.requests_session.get(url, timeout=15)
                page_content = response.text
            
            if 'Page Not Found' in page_content or response.status_code != 200:
                logging.error(f"Failed to fetch page content, status code: {response.status_code}")
                return None
            
            logging.info(f"Successfully fetched page with status code: {response.status_code}")
            
            # Initialize all_urls list
            all_urls = []
            
            # Try multiple regex patterns for different Instagram page structures
            # Pattern 1: Look for JSON data in new-style Instagram pages
            json_data_match = re.search(r'window\._sharedData\s*=\s*({.*?});</script>', page_content, re.DOTALL)
            if json_data_match:
                try:
                    json_data = json.loads(json_data_match.group(1))
                    media_data = json_data.get('entry_data', {}).get('PostPage', [{}])[0].get('graphql', {}).get('shortcode_media', {})
                    
                    # Check for video URL
                    video_url = media_data.get('video_url')
                    if video_url:
                        all_urls.append(video_url)
                    
                    # Check for display URL (image)
                    display_url = media_data.get('display_url')
                    if display_url:
                        all_urls.append(display_url)
                    
                    # Check for carousel items
                    edges = media_data.get('edge_sidecar_to_children', {}).get('edges', [])
                    for edge in edges:
                        node = edge.get('node', {})
                        if node.get('video_url'):
                            all_urls.append(node['video_url'])
                        elif node.get('display_url'):
                            all_urls.append(node['display_url'])
                    
                    logging.info(f"Found {len(all_urls)} media URLs from JSON data")
                except Exception as e:
                    logging.error(f"Error parsing JSON data: {e}")
            
            # Pattern 2: Look for additional JSON data in script tags
            additional_json_match = re.search(r'<script type="text/javascript">window\.__additionalDataLoaded\(.*?,({.*?})\);</script>', page_content, re.DOTALL)
            if additional_json_match:
                try:
                    additional_json = json.loads(additional_json_match.group(1))
                    media_data = additional_json.get('graphql', {}).get('shortcode_media', {})
                    
                    # Process additional json data
                    if 'video_url' in media_data:
                        all_urls.append(media_data['video_url'])
                    if 'display_url' in media_data:
                        all_urls.append(media_data['display_url'])
                    
                    # Get carousel items
                    edges = media_data.get('edge_sidecar_to_children', {}).get('edges', [])
                    for edge in edges:
                        node = edge.get('node', {})
                        if node.get('video_url'):
                            all_urls.append(node['video_url'])
                        elif node.get('display_url'):
                            all_urls.append(node['display_url'])
                    
                    logging.info(f"Found additional {len(all_urls)} media URLs from additional JSON data")
                except Exception as e:
                    logging.error(f"Error parsing additional JSON data: {e}")
            
            # Pattern 3: If the above methods fail, fall back to regex
            if not all_urls:
                # Look for high-quality image URLs
                image_matches = re.findall(r'"display_url":"([^"]+)"', page_content)
                
                # Look for video URLs
                video_matches = re.findall(r'"video_url":"([^"]+)"', page_content)
                
                # Look for direct file URLs
                direct_urls = re.findall(r'https://scontent[^"\']+\.(?:jpg|mp4|webp)[^"\'\s]*', page_content)
                
                # Decode all URLs (they're usually escaped in the JSON)
                for url_match in image_matches + video_matches + direct_urls:
                    # Fix the invalid escape sequence by using proper string escaping
                    decoded_url = url_match.replace('\\u0026', '&').replace('\\/', '/')
                    if decoded_url not in all_urls:
                        all_urls.append(decoded_url)
                
                # For carousel posts, try to find all items
                carousel_matches = re.findall(r'"carousel_media":\[(.*?)\]', page_content)
                if carousel_matches:
                    for carousel in carousel_matches:
                        # Extract all display URLs from the carousel
                        carousel_images = re.findall(r'"display_url":"([^"]+)"', carousel)
                        carousel_videos = re.findall(r'"video_url":"([^"]+)"', carousel)
                        
                        for url_match in carousel_images + carousel_videos:
                            # Fix the invalid escape sequence
                            decoded_url = url_match.replace('\\u0026', '&').replace('\\/', '/')
                            if decoded_url not in all_urls:
                                all_urls.append(decoded_url)
                
                logging.info(f"Found {len(all_urls)} media URLs from regex matching")
            
            # Remove duplicate URLs
            all_urls = list(set(all_urls))
            
            # If still no URLs found, try the OEmbed API as a last resort
            if not all_urls:
                try:
                    oembed_url = f"https://api.instagram.com/oembed/?url={url}"
                    oembed_response = self.requests_session.get(oembed_url, timeout=10)
                    if oembed_response.status_code == 200:
                        oembed_data = oembed_response.json()
                        if 'thumbnail_url' in oembed_data:
                            all_urls.append(oembed_data['thumbnail_url'])
                            logging.info("Found thumbnail URL from OEmbed API")
                except Exception as e:
                    logging.error(f"Error fetching OEmbed data: {e}")
            
            # If still no URLs found, try to load the post in a different format
            if not all_urls:
                # Extract shortcode from URL
                shortcode_match = re.search(r'/(p|reel|tv)/([^/?]+)', url)
                if shortcode_match:
                    shortcode = shortcode_match.group(2)
                    try:
                        # Try Instagram's GraphQL API directly
                        graphql_url = f"https://www.instagram.com/graphql/query/?query_hash=2b0673e0dc4580674a88d426fe00ea90&variables=%7B%22shortcode%22%3A%22{shortcode}%22%7D"
                        graphql_response = self.requests_session.get(graphql_url, timeout=15)
                        if graphql_response.status_code == 200:
                            graphql_data = graphql_response.json()
                            media_data = graphql_data.get('data', {}).get('shortcode_media', {})
                            
                            if media_data:
                                if 'video_url' in media_data:
                                    all_urls.append(media_data['video_url'])
                                if 'display_url' in media_data:
                                    all_urls.append(media_data['display_url'])
                                
                                # Get carousel items
                                edges = media_data.get('edge_sidecar_to_children', {}).get('edges', [])
                                for edge in edges:
                                    node = edge.get('node', {})
                                    if node.get('video_url'):
                                        all_urls.append(node['video_url'])
                                    elif node.get('display_url'):
                                        all_urls.append(node['display_url'])
                            
                            logging.info(f"Found {len(all_urls)} media URLs from GraphQL API")
                    except Exception as e:
                        logging.error(f"Error fetching GraphQL data: {e}")
            
            # If we still have no URLs, the post probably doesn't exist or is deleted
            if not all_urls:
                logging.error("No media URLs found. Post may not exist or may be private/deleted.")
                
                # For old posts, generate a fallback message text file
                shortcode_match = re.search(r'/(p|reel|tv)/([^/?]+)', url)
                if shortcode_match:
                    shortcode = shortcode_match.group(2)
                    dummy_text_path = os.path.join(temp_dir, "post_unavailable.txt")
                    with open(dummy_text_path, 'w') as f:
                        f.write(f"Sorry, the Instagram post {shortcode} is no longer available or may have been deleted.")
                    logging.info(f"Created unavailable post message file: {dummy_text_path}")
                    return [dummy_text_path]
                    
                return None
                
            logging.info(f"Found a total of {len(all_urls)} unique media URLs")
            
            # Download all found media
            downloaded_files = []
            for i, media_url in enumerate(all_urls):
                try:
                    # Determine file extension based on URL
                    if '.mp4' in media_url.lower():
                        ext = '.mp4'
                    elif '.jpg' in media_url.lower() or '.jpeg' in media_url.lower():
                        ext = '.jpg'
                    elif '.webp' in media_url.lower():
                        ext = '.webp'
                    else:
                        ext = '.jpg'  # Default to jpg for images
                    
                    output_file = os.path.join(temp_dir, f"instagram_media_{i}{ext}")
                    
                    # Download the file
                    media_response = self.requests_session.get(media_url, timeout=30, stream=True)
                    if media_response.status_code == 200:
                        with open(output_file, 'wb') as f:
                            for chunk in media_response.iter_content(8192):  # Larger chunks for faster download
                                f.write(chunk)
                        
                        downloaded_files.append(output_file)
                        logging.info(f"Successfully downloaded media to {output_file}")
                    else:
                        logging.warning(f"Failed to download media, status code: {media_response.status_code}")
                
                except Exception as e:
                    logging.error(f"Error downloading media {media_url}: {e}")
            
            if downloaded_files:
                logging.info(f"Direct method successfully downloaded {len(downloaded_files)} files")
                return downloaded_files
            else:
                logging.warning("Direct method did not download any files")
                
                # As a last resort, create a text file explaining the issue
                text_file = os.path.join(temp_dir, "download_failed.txt")
                try:
                    with open(text_file, 'w') as f:
                        f.write(f"Failed to download content from {url}. The post may be private, deleted, or unavailable.")
                    logging.info(f"Created failure explanation file: {text_file}")
                    return [text_file]
                except Exception as e:
                    logging.error(f"Error creating failure explanation: {e}")
                
                return None
                
        except Exception as e:
            logging.error(f"Direct request download failed: {e}")
            return None
    
    def download_with_instagram_web_api(self, url):
        """
        Download Instagram media using Instagram's web API directly
        This method uses a completely different approach by directly accessing Instagram's internal API
        """
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        logging.info(f"Attempting Instagram web API download from {url}")
        
        try:
            # Extract post shortcode from URL
            match = re.search(r'instagram.com/(?:p|reel|tv)/([^/?]+)', url)
            if not match:
                logging.error(f"Could not extract shortcode from URL: {url}")
                return None
            
            shortcode = match.group(1)
            
            # Set up a session with proper headers to mimic a browser
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.instagram.com/',
                'X-IG-App-ID': '936619743392459',
                'X-Instagram-AJAX': '1',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://www.instagram.com'
            }
            session.headers.update(headers)
            
            # Try to set cookies from session file if available
            cookie_success = False
            if os.path.exists(self.session_file):
                try:
                    with open(self.session_file, 'r') as f:
                        session_data = f.read()
                        sessionid_match = re.search(r'sessionid=([^;]+)', session_data)
                        if sessionid_match:
                            session.cookies.set('sessionid', sessionid_match.group(1), domain='.instagram.com')
                            cookie_success = True
                            
                        # Also try to get additional cookies
                        csrftoken_match = re.search(r'csrftoken=([^;]+)', session_data)
                        if csrftoken_match:
                            session.cookies.set('csrftoken', csrftoken_match.group(1), domain='.instagram.com')
                            
                        ds_user_id_match = re.search(r'ds_user_id=([^;]+)', session_data)
                        if ds_user_id_match:
                            session.cookies.set('ds_user_id', ds_user_id_match.group(1), domain='.instagram.com')
                            
                        logging.info("Loaded Instagram cookies from session file")
                except Exception as e:
                    logging.warning(f"Could not load cookies from session file: {e}")
            
            # If cookies failed to load and we have credentials, try to establish a new session
            if not cookie_success and self.username and self.password:
                try:
                    # First try to get a CSRF token
                    init_response = session.get('https://www.instagram.com/')
                    csrf_token = None
                    for cookie in session.cookies:
                        if cookie.name == 'csrftoken':
                            csrf_token = cookie.value
                            break
                            
                    if csrf_token:
                        # Now try to login
                        login_url = 'https://www.instagram.com/accounts/login/ajax/'
                        login_data = {
                            'username': self.username,
                            'password': self.password,
                            'queryParams': '{}',
                            'optIntoOneTap': 'false'
                        }
                        
                        session.headers.update({
                            'X-CSRFToken': csrf_token,
                            'X-Requested-With': 'XMLHttpRequest',
                            'Referer': 'https://www.instagram.com/accounts/login/'
                        })
                        
                        login_response = session.post(login_url, data=login_data)
                        login_json = login_response.json()
                        
                        if login_json.get('authenticated'):
                            logging.info("Successfully authenticated with Instagram web API")
                            
                            # Save session cookies for future use
                            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])
                            with open(self.session_file, 'w') as f:
                                f.write(cookie_str)
                                
                            logging.info(f"Saved Instagram session cookies to {self.session_file}")
                        else:
                            logging.warning("Failed to authenticate with Instagram web API")
                    else:
                        logging.warning("Could not obtain CSRF token for Instagram login")
                        
                except Exception as e:
                    logging.error(f"Error during Instagram web authentication: {e}")
            
            # First approach: Try with Instagram's media API endpoint
            media_info_url = f"https://i.instagram.com/api/v1/media/{shortcode}/info/"
            
            response = session.get(media_info_url)
            if response.status_code == 200:
                try:
                    data = response.json()
                    items = data.get('items', [])
                    if items:
                        item = items[0]
                        media_urls = []
                        
                        # Handle videos
                        if 'video_versions' in item:
                            # Get best quality video
                            videos = sorted(item['video_versions'], key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                            if videos:
                                media_urls.append(videos[0]['url'])
                        
                        # Handle images
                        if 'image_versions2' in item:
                            images = sorted(
                                item['image_versions2']['candidates'], 
                                key=lambda x: x.get('width', 0) * x.get('height', 0), 
                                reverse=True
                            )
                            if images:
                                media_urls.append(images[0]['url'])
                        
                        # Handle carousel
                        if 'carousel_media' in item:
                            for carousel_item in item['carousel_media']:
                                # Videos in carousel
                                if 'video_versions' in carousel_item:
                                    videos = sorted(
                                        carousel_item['video_versions'], 
                                        key=lambda x: x.get('width', 0) * x.get('height', 0), 
                                        reverse=True
                                    )
                                    if videos:
                                        media_urls.append(videos[0]['url'])
                                
                                # Images in carousel
                                if 'image_versions2' in carousel_item:
                                    images = sorted(
                                        carousel_item['image_versions2']['candidates'], 
                                        key=lambda x: x.get('width', 0) * x.get('height', 0), 
                                        reverse=True
                                    )
                                    if images:
                                        media_urls.append(images[0]['url'])
                        
                        logging.info(f"Found {len(media_urls)} media URLs from Instagram web API")
                        
                        # Download all media
                        downloaded_files = []
                        for i, media_url in enumerate(media_urls):
                            try:
                                # Determine file extension based on URL
                                if '.mp4' in media_url.lower():
                                    ext = '.mp4'
                                else:
                                    ext = '.jpg'  # Default to jpg for images
                                
                                output_file = os.path.join(temp_dir, f"instagram_media_{i}{ext}")
                                
                                # Download the file
                                media_response = session.get(media_url, timeout=30, stream=True)
                                if media_response.status_code == 200:
                                    with open(output_file, 'wb') as f:
                                        for chunk in media_response.iter_content(8192):
                                            f.write(chunk)
                                    
                                    downloaded_files.append(output_file)
                                    logging.info(f"Successfully downloaded media to {output_file}")
                                else:
                                    logging.warning(f"Failed to download media, status code: {media_response.status_code}")
                            
                            except Exception as e:
                                logging.error(f"Error downloading media {media_url}: {e}")
                        
                        if downloaded_files:
                            logging.info(f"Web API method successfully downloaded {len(downloaded_files)} files")
                            return downloaded_files
                except Exception as e:
                    logging.error(f"Error parsing API response: {e}")
            elif response.status_code == 401:
                logging.error(f"Authentication error (401) from Instagram API - Session may have expired or access is restricted")
            else:
                logging.error(f"Error from Instagram API: {response.status_code}")
            
            # Second approach: Try with Instagram's GraphQL API
            graphql_url = f"https://www.instagram.com/graphql/query/"
            
            # Try different query hashes that might work
            query_hashes = [
                '9f8827793ef34641b2fb195d4d41151c',  # This hash is for media info query
                '2b0673e0dc4580674a88d426fe00ea90',  # Alternative hash
                '477b65a610463740ccdb83135b2014db',  # Another alternative hash
                '7c8a1055f3b71c8a61b280b7c8826d42'   # Yet another alternative hash
            ]
            
            for query_hash in query_hashes:
                params = {
                    'query_hash': query_hash,
                    'variables': json.dumps({
                        'shortcode': shortcode
                    })
                }
                
                response = session.get(graphql_url, params=params)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        media = data.get('data', {}).get('media', {})
                        
                        if media:
                            media_urls = []
                            
                            # Check if it's a video
                            if media.get('is_video'):
                                video_url = media.get('video_url')
                                if video_url:
                                    media_urls.append(video_url)
                            
                            # Get image URL
                            display_url = media.get('display_url')
                            if display_url:
                                media_urls.append(display_url)
                            
                            # Handle carousel/multiple images
                            edges = media.get('edge_sidecar_to_children', {}).get('edges', [])
                            for edge in edges:
                                node = edge.get('node', {})
                                if node.get('is_video'):
                                    video_url = node.get('video_url')
                                    if video_url:
                                        media_urls.append(video_url)
                                else:
                                    display_url = node.get('display_url')
                                    if display_url:
                                        media_urls.append(display_url)
                            
                            logging.info(f"Found {len(media_urls)} media URLs from GraphQL API with hash {query_hash}")
                            
                            # Download all media
                            downloaded_files = []
                            for i, media_url in enumerate(media_urls):
                                try:
                                    # Determine file extension based on URL
                                    if '.mp4' in media_url.lower():
                                        ext = '.mp4'
                                    else:
                                        ext = '.jpg'  # Default to jpg for images
                                    
                                    output_file = os.path.join(temp_dir, f"instagram_media_{i}{ext}")
                                    
                                    # Download the file
                                    media_response = session.get(media_url, timeout=30, stream=True)
                                    if media_response.status_code == 200:
                                        with open(output_file, 'wb') as f:
                                            for chunk in media_response.iter_content(8192):
                                                f.write(chunk)
                                        
                                        downloaded_files.append(output_file)
                                        logging.info(f"Successfully downloaded media to {output_file}")
                                    else:
                                        logging.warning(f"Failed to download media, status code: {media_response.status_code}")
                                
                                except Exception as e:
                                    logging.error(f"Error downloading media {media_url}: {e}")
                            
                            if downloaded_files:
                                logging.info(f"GraphQL API method successfully downloaded {len(downloaded_files)} files with hash {query_hash}")
                                return downloaded_files
                            
                    except Exception as e:
                        logging.error(f"Error parsing GraphQL response with hash {query_hash}: {e}")
                elif response.status_code == 401:
                    logging.error(f"Authentication error (401) from GraphQL API with hash {query_hash}")
                else:
                    logging.error(f"Error from GraphQL API with hash {query_hash}: {response.status_code}")
            
            # Try one more approach: public HTML page as a visitor
            try:
                # Use a totally different user agent to mimic mobile browser
                mobile_headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache'
                }
                
                # Create new clean session
                clean_session = requests.Session()
                clean_session.headers.update(mobile_headers)
                
                # Try to access post directly
                post_url = f"https://www.instagram.com/p/{shortcode}/"
                response = clean_session.get(post_url)
                
                if response.status_code == 200:
                    page_content = response.text
                    
                    # Try to extract image URLs from the page
                    img_urls = re.findall(r'https://scontent[^"\']+\.(?:jpg|mp4|webp)[^"\'\s]*', page_content)
                    if img_urls:
                        logging.info(f"Found {len(img_urls)} media URLs from clean public visit")
                        
                        # Download the first few images
                        downloaded_files = []
                        for i, media_url in enumerate(img_urls[:5]):  # Limit to first 5 to avoid duplicates
                            try:
                                # Determine file extension based on URL
                                if '.mp4' in media_url.lower():
                                    ext = '.mp4'
                                else:
                                    ext = '.jpg'  # Default to jpg for images
                                
                                output_file = os.path.join(temp_dir, f"instagram_public_{i}{ext}")
                                
                                # Download the file
                                media_response = clean_session.get(media_url, timeout=30, stream=True)
                                if media_response.status_code == 200:
                                    with open(output_file, 'wb') as f:
                                        for chunk in media_response.iter_content(8192):
                                            f.write(chunk)
                                    
                                    downloaded_files.append(output_file)
                                    logging.info(f"Successfully downloaded media to {output_file}")
                            except Exception as e:
                                logging.error(f"Error downloading public media {media_url}: {e}")
                        
                        if downloaded_files:
                            logging.info(f"Public visit method successfully downloaded {len(downloaded_files)} files")
                            return downloaded_files
            except Exception as e:
                logging.error(f"Error during public page visit: {e}")
            
            # If all attempts fail, create a text file indicating the issue
            error_file = os.path.join(temp_dir, "instagram_auth_error.txt")
            with open(error_file, 'w') as f:
                f.write(f"Failed to download Instagram post {shortcode} due to authentication errors (HTTP 401). Instagram is blocking access to this content.")
            logging.info(f"Created authentication error explanation file: {error_file}")
            return [error_file]
            
        except Exception as e:
            logging.error(f"Instagram web API download failed: {e}")
            
            # Create an error file with more details
            error_file = os.path.join(temp_dir, "instagram_error.txt")
            with open(error_file, 'w') as f:
                f.write(f"Instagram error: {str(e)}")
            return [error_file]
    
    def download_with_browser(self, url):
        """
        Download Instagram media using a real browser (Selenium)
        This method mimics a real user visiting Instagram, which can bypass API restrictions
        """
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        logging.info(f"Attempting browser-based download from {url}")
        
        try:
            # Extract post shortcode from URL
            match = re.search(r'instagram.com/(?:p|reel|tv)/([^/?]+)', url)
            if not match:
                logging.error(f"Could not extract shortcode from URL: {url}")
                return None
            
            shortcode = match.group(1)
            
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            # Don't use headless mode - Instagram often blocks headless browsers
            # chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            # Use a common mobile user-agent that's less likely to be detected as a bot
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1")
            
            # Instead of mobile emulation which can be detected, use a regular browser
            # with a good user agent
            
            # Initialize Chrome browser
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.set_page_load_timeout(60)  # Increased timeout for slower connections
            
            try:
                # First load the Instagram login page
                login_success = False
                if self.username and self.password:
                    try:
                        driver.get("https://www.instagram.com/accounts/login/")
                        time.sleep(5)  # Wait longer for page to load
                        
                        # Wait for the username field and enter credentials
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.NAME, "username"))
                        )
                        
                        username_field = driver.find_element(By.NAME, "username")
                        password_field = driver.find_element(By.NAME, "password")
                        
                        # Clear fields first
                        username_field.clear()
                        password_field.clear()
                        
                        # Type credentials slowly like a human
                        for char in self.username:
                            username_field.send_keys(char)
                            time.sleep(0.05)
                        
                        for char in self.password:
                            password_field.send_keys(char)
                            time.sleep(0.05)
                        
                        # Find and click the login button
                        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                        login_button.click()
                        
                        # Wait for login to complete (longer wait)
                        time.sleep(8)
                        
                        # Check if login was successful
                        if "Login" not in driver.title:
                            logging.info("Successfully logged in to Instagram with browser")
                            login_success = True
                            
                            # Save cookies for future use
                            cookie_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in driver.get_cookies()])
                            with open(self.session_file, 'w') as f:
                                f.write(cookie_str)
                        else:
                            logging.warning("Browser login to Instagram failed")
                    except Exception as e:
                        logging.error(f"Error during browser login: {e}")
                
                # Print current page source for debugging
                logging.info(f"Current URL after login attempt: {driver.current_url}")
                
                # Now navigate to the post
                post_url = f"https://www.instagram.com/p/{shortcode}/"
                driver.get(post_url)
                
                # Wait for content to load
                time.sleep(8)
                
                # Print page title and URL for debugging
                logging.info(f"Loaded page with title: {driver.title}, URL: {driver.current_url}")
                
                # Check if post exists
                if "Page Not Found" in driver.title or "Instagram" not in driver.title:
                    logging.error("Post not found or page error")
                    # Save page source to analyze
                    with open(os.path.join(temp_dir, "error_page.html"), 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logging.info(f"Saved error page to {os.path.join(temp_dir, 'error_page.html')}")
                    
                    # Take screenshot before quitting
                    screenshot_file = os.path.join(temp_dir, f"error_page_{shortcode}.png")
                    driver.save_screenshot(screenshot_file)
                    
                    driver.quit()
                    
                    # Create error text file
                    error_file = os.path.join(temp_dir, "post_not_found.txt")
                    with open(error_file, 'w') as f:
                        f.write(f"The Instagram post {shortcode} was not found or is not accessible.")
                    return [error_file, screenshot_file]
                
                # Save the page source for analysis
                with open(os.path.join(temp_dir, "page_source.html"), 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                logging.info(f"Saved page source to {os.path.join(temp_dir, 'page_source.html')}")
                
                # Now try to find all media elements
                media_urls = []
                
                # First try to find video elements
                try:
                    video_elements = driver.find_elements(By.TAG_NAME, "video")
                    for video in video_elements:
                        src = video.get_attribute("src")
                        if src and src.startswith("http"):
                            media_urls.append(src)
                    logging.info(f"Found {len(video_elements)} video elements")
                except Exception as e:
                    logging.warning(f"Error finding video elements: {e}")
                
                # Then try to find image elements with more comprehensive selectors
                try:
                    # Look for various image selectors that match Instagram's current layout
                    image_selectors = [
                        "img._aagt", # Common Instagram image class
                        "img[decoding='auto']",
                        "img.FFVAD",
                        "img.EmbeddedMediaImage",
                        "img._aa-6",  # Another Instagram image class
                        "img[sizes]",  # Images with sizes attribute
                        "img[srcset]", # Images with srcset
                        "img"  # Fallback to all images
                    ]
                    
                    for selector in image_selectors:
                        try:
                            image_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for img in image_elements:
                                src = img.get_attribute("src")
                                if src and src.startswith("http") and ("scontent" in src or "cdninstagram" in src):
                                    media_urls.append(src)
                        except Exception:
                            continue
                    
                    logging.info(f"Found {len(media_urls)} image elements")
                except Exception as e:
                    logging.warning(f"Error finding image elements: {e}")
                
                # Even if we found media URLs, always take a screenshot as fallback
                screenshot_file = os.path.join(temp_dir, f"instagram_post_{shortcode}.png")
                driver.save_screenshot(screenshot_file)
                logging.info(f"Saved screenshot to {screenshot_file}")
                
                # If no media found, return the screenshot
                if not media_urls:
                    logging.info("No media elements found, using screenshot instead")
                    return [screenshot_file]
                
                # Download all found media
                downloaded_files = [screenshot_file]  # Include screenshot in downloaded files
                
                for i, media_url in enumerate(media_urls):
                    try:
                        # Determine file extension based on URL or content
                        if '.mp4' in media_url.lower() or 'video' in media_url.lower():
                            ext = '.mp4'
                        else:
                            ext = '.jpg'
                        
                        output_file = os.path.join(temp_dir, f"instagram_browser_{i}{ext}")
                        
                        # Download using requests with the browser's cookies
                        media_response = requests.get(
                            media_url, 
                            headers={
                                'User-Agent': driver.execute_script("return navigator.userAgent"),
                                'Referer': post_url
                            },
                            cookies={cookie['name']: cookie['value'] for cookie in driver.get_cookies()},
                            stream=True,
                            timeout=30
                        )
                        
                        if media_response.status_code == 200:
                            with open(output_file, 'wb') as f:
                                for chunk in media_response.iter_content(8192):
                                    f.write(chunk)
                            
                            # Verify the file was downloaded successfully
                            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                                downloaded_files.append(output_file)
                                logging.info(f"Successfully downloaded media to {output_file}")
                            else:
                                logging.warning(f"Downloaded file is empty or does not exist: {output_file}")
                        else:
                            logging.warning(f"Failed to download media, status code: {media_response.status_code}")
                    
                    except Exception as e:
                        logging.error(f"Error downloading media {media_url}: {e}")
                
                # Return downloaded files
                if len(downloaded_files) > 1:  # We have media files besides the screenshot
                    logging.info(f"Browser method successfully downloaded {len(downloaded_files)-1} files plus screenshot")
                    return downloaded_files
                else:
                    # If only the screenshot was saved, return that
                    logging.info(f"No media downloaded, using screenshot")
                    return downloaded_files
            
            finally:
                # Always quit the driver to clean up resources
                try:
                    driver.quit()
                except Exception:
                    pass
        
        except Exception as e:
            logging.error(f"Browser-based download failed: {e}")
            
            # Create a detailed error file
            error_file = os.path.join(temp_dir, "browser_error.txt")
            with open(error_file, 'w') as f:
                f.write(f"Browser automation error: {str(e)}\n\nThis Instagram post could not be accessed even with browser automation. It may be fully restricted, private, or deleted.")
            return [error_file]
    
    def download(self, url):
        """
        Download media from Instagram URL
        Try multiple methods in sequence, falling back to the next if one fails
        Methods are ordered from most effective to least effective
        """
        logging.info(f"Attempting to download media from {url}")
        
        # Method 1: Try the browser-based method first (most reliable but slower)
        try:
            files = self.download_with_browser(url)
            if files:
                logging.info("Successfully downloaded using browser-based method")
                return files
            logging.warning("Browser-based method failed, trying yt-dlp...")
        except Exception as e:
            logging.error(f"Error downloading with browser-based method: {e}")
        
        # Method 2: Try with yt-dlp
        try:
            files = self.download_with_ytdlp(url)
            if files:
                logging.info("Successfully downloaded using yt-dlp")
                return files
            logging.warning("yt-dlp method failed, trying instaloader...")
        except Exception as e:
            logging.error(f"Error downloading with yt-dlp: {e}")
        
        # Method 3: Try with instaloader
        try:
            files = self.download_with_instaloader(url)
            if files:
                logging.info("Successfully downloaded using instaloader")
                return files
            logging.warning("instaloader method failed, trying Instagram web API...")
        except Exception as e:
            logging.error(f"Error downloading with instaloader: {e}")
            
        # Method 4: Try Instagram web API
        try:
            files = self.download_with_instagram_web_api(url)
            if files:
                logging.info("Successfully downloaded using Instagram web API")
                return files
            logging.warning("Instagram web API method failed, trying direct requests...")
        except Exception as e:
            logging.error(f"Error downloading with Instagram web API: {e}")
        
        # Method 5: Try direct web requests as last resort
        try:
            files = self.download_with_direct_requests(url)
            if files:
                logging.info("Successfully downloaded using direct web requests")
                return files
            logging.warning("Direct web requests method failed")
        except Exception as e:
            logging.error(f"Error downloading with direct requests: {e}")
        
        # If all methods fail, create a generic text file with error
        download_id = str(uuid.uuid4())
        temp_dir = os.path.join(config.DOWNLOAD_PATH, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        error_file = os.path.join(temp_dir, "download_failed.txt")
        try:
            with open(error_file, 'w') as f:
                f.write(f"Instagram has blocked access to this post. This post may be private, deleted, or protected by Instagram's security measures. All download methods have been tried and failed.")
            return [error_file]
        except Exception as e:
            logging.error(f"Failed to create error file: {e}")
        
        logging.error("All download methods failed")
        return None 