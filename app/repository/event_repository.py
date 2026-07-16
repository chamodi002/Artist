from bson import ObjectId
from typing import Optional, List
from datetime import datetime
from app.config.database import events_collection
from app.entity.models import MongoEntity

class EventRepository:
    @staticmethod
    def find_all(city: Optional[str] = None, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[dict]:
        query = {}
        if city:
            query["city"] = {"$regex": city, "$options": "i"}
        if from_date or to_date:
            query["date"] = {}
            if from_date:
                query["date"]["$get"] = from_date
            if to_date:
                query["date"]["$lte"] = to_date
        
        cursor = events_collection.find(query).sort("date", 1)
        if limit:
            cursor = cursor.limit(limit)
            
        return MongoEntity.serialize_list(list(cursor))

    @staticmethod
    def find_by_id(event_id: str) -> Optional[dict]:
        if not ObjectId.is_valid(event_id):
            return None
        doc = events_collection.find_one({"_id": ObjectId(event_id)})
        return MongoEntity.serialize_id(doc) if doc else None

    @staticmethod
    def create(event_data: dict) -> str:
        for tier in event_data.get("tiers", []):
            tier["remaining_seats"] = tier["total_quantity"]
        result = events_collection.insert_one(event_data)
        return str(result.inserted_id)

    @staticmethod
    def update(event_id: str, update_fields: dict) -> bool:
        if not ObjectId.is_valid(event_id):
            return False
        result = events_collection.update_one({"_id": ObjectId(event_id)}, {"$set": update_fields})
        return result.matched_count > 0

    @staticmethod
    def add_tier(event_id: str, tier_data: dict) -> bool:
        if not ObjectId.is_valid(event_id):
            return False
        tier_data["remaining_seats"] = tier_data["total_quantity"]
        result = events_collection.update_one(
            {"_id": ObjectId(event_id)},
            {"$push": {"tiers": tier_data}}
        )
        return result.matched_count > 0

    @staticmethod
    def update_tier_by_name(event_id: str, tier_name: str, update_fields: dict) -> bool:
        if not ObjectId.is_valid(event_id):
            return False
        
        query = {"_id": ObjectId(event_id), "tiers.name": tier_name}
        set_fields = {}
        for key, value in update_fields.items():
            set_fields[f"tiers.$.{key}"] = value

        result = events_collection.update_one(query, {"$set": set_fields})
        return result.matched_count > 0