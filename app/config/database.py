import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://chamodirajapaksha2_db_user:c4Ddh0VyGjpLZY8o@cluster0.mmnkmws.mongodb.net/")
DB_NAME = os.getenv("DB_NAME", "artist_ticketing_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections reflecting active MongoDB Compass state
events_collection = db["events"]
bookings_collection = db["bookings"]
admin_collection = db["admin"]
