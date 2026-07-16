import os
from datetime import datetime, timedelta
from app.config.database import admin_collection, events_collection, db
from app.util.security_utils import hash_password

def seed_database():
    print("Flushing and re-seeding application collection indices...")
    db["admin"].drop()
    db["events"].drop()
    db["bookings"].drop()

    # Pre-populate your Compass 'admin' collection structure 
    admin_profile = {
        "username": "admin",
        "hashed_password": hash_password("admin123"),
        "role": "admin"
    }
    admin_collection.insert_one(admin_profile)
    print("✓ Admin account credentials generated successfully: Profile: admin / Pass: admin123")

    # Generate Dummy Demo Show Events
    events_mock = [
        {
            "title": "Acoustic Echoes Open Air Live",
            "venue": "The Forum Arena",
            "city": "Los Angeles",
            "country": "USA",
            "date": datetime.utcnow() + timedelta(days=30),
            "description": "An experience featuring upcoming acoustic and music tracks.",
            "image_url": "https://picsum.photos/seed/laforum/800/600",
            "status": "Available",
            "tiers": [
                {"name": "General Admission", "price": 75.0, "total_quantity": 300, "remaining_seats": 300},
                {"name": "VIP Premium Package Pass", "price": 250.0, "total_quantity": 25, "remaining_seats": 25}
            ]
        },
        {
            "title": "Symphonic Evening Orchestra Concert",
            "venue": "The Royal Albert Stage Hall",
            "city": "London",
            "country": "UK",
            "date": datetime.utcnow() + timedelta(days=15),
            "description": "Exclusive live performance set inside classic architectural frameworks.",
            "image_url": "https://picsum.photos/seed/albert/800/600",
            "status": "Selling Fast",
            "tiers": [
                {"name": "Standard Row Seats", "price": 95.0, "total_quantity": 150, "remaining_seats": 5}
            ]
        }
    ]
    events_collection.insert_many(events_mock)
    print("✓ Sample performance dates updated in your MongoDB database.")

if __name__ == "__main__":
    seed_database()