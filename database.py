from pymongo import MongoClient
from datetime import datetime
import config
import logging

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users_collection = None
        self.downloads_collection = None
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB Atlas database"""
        if not config.MONGO_URI:
            logging.warning("MONGO_URI not provided. Database features disabled.")
            return
        
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client.instagram_downloader
            self.users_collection = self.db.users
            self.downloads_collection = self.db.downloads
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            # Reset to None to ensure we don't try to use these collections
            self.client = None
            self.db = None
            self.users_collection = None
            self.downloads_collection = None
    
    def add_user(self, user_id, username, first_name):
        """Add or update user in the database"""
        if self.users_collection is None:
            return
        
        try:
            self.users_collection.update_one(
                {"_id": str(user_id)},
                {
                    "$set": {
                        "username": username,
                        "first_name": first_name,
                        "last_active": datetime.utcnow()
                    }
                },
                upsert=True
            )
            logging.info(f"User {user_id} added/updated in database")
        except Exception as e:
            logging.error(f"Failed to add/update user in database: {e}")
    
    def log_download(self, user_id, instagram_url, file_path):
        """Log a successful download in the database"""
        if self.downloads_collection is None:
            return
        
        try:
            self.downloads_collection.insert_one({
                "user_id": str(user_id),
                "instagram_url": instagram_url,
                "file_path": file_path,
                "timestamp": datetime.utcnow()
            })
            logging.info(f"Download logged for user {user_id}: {instagram_url}")
        except Exception as e:
            logging.error(f"Failed to log download in database: {e}")
    
    def get_user_stats(self, user_id):
        """Get statistics for a specific user"""
        if self.downloads_collection is None:
            return {"downloads_count": 0}
        
        try:
            downloads_count = self.downloads_collection.count_documents({"user_id": str(user_id)})
            return {"downloads_count": downloads_count}
        except Exception as e:
            logging.error(f"Failed to get user stats: {e}")
            return {"downloads_count": 0}
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed") 