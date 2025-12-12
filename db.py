import os
from pymongo import MongoClient, DESCENDING
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MongoDB:
    def __init__(self, atlas_uri: str = None, db_name: str = None):
        """Initialize MongoDB connection with Atlas URI."""
        # Use provided values or fall back to environment variables
        self.uri = atlas_uri or os.getenv("ATLAS_URI")
        self.db_name = db_name or os.getenv("ALLOWED_DB")
        self.allowed_collections = os.getenv("ALLOWED_COLLECTIONS", "").split(",")
        self.event_collection = os.getenv("EVENT_COLLECTION")
        self.post_process_collection = os.getenv("POST_PROCESS_COLLECTION")
        
        if not self.uri:
            raise ValueError("MongoDB Atlas URI is required")
        if not self.db_name:
            raise ValueError("Database name is required")
        if not self.event_collection:
            raise ValueError("EVENT_COLLECTION is required")
            
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
    
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single event document by its _id."""
        collection = self.db[self.event_collection]
        return collection.find_one({"_id": id})
    
    def get_cursor(self) -> Any:
        collection = self.db[self.event_collection]
        return collection.find({}, batch_size=50)
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        collection = self.db[self.event_collection]
        return collection.find().sort({ "_id": -1 }).limit(1)
    
    def get_post_process(self, raw_data_id: str) -> List[Dict]:
        collection = self.db[self.post_process_collection]
        return collection.find({"raw_data_id": raw_data_id})

    
    def get_by_url(self, start_url: str) -> Optional[Dict[str, Any]]:
        collection = self.get_event_collection()
        return collection.find({"start_url": start_url})
        
    def get_event_collection(self):
        """Get the event collection object."""
        return self.db[self.event_collection]
        
    def get_allowed_collections(self) -> List[str]:
        """Return list of allowed collections."""
        return self.allowed_collections
    
    def insert_post_process(self, documents: List[Dict[str, Any]]) -> str:
        collection = self.db[self.post_process_collection]
        result = collection.insert_many(documents)
        print('result: ', result)
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()