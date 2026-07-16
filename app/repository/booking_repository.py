from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from app.config.database import bookings_collection

class BookingRepository:
    
    @staticmethod
    def create(booking_data: dict) -> Optional[dict]:
        try:
            payload = booking_data.copy()
            if "timestamp" not in payload:
                payload["timestamp"] = datetime.utcnow().isoformat()
            
            result = bookings_collection.insert_one(payload)
            if result.inserted_id:
                doc = bookings_collection.find_one({"_id": result.inserted_id})
                if doc:
                    return BookingRepository._serialize_doc(doc)
            return None
        except Exception as e:
            print(f" REPOSITORY INSERTION EXCEPTION: {str(e)}")
            return None

    @staticmethod
    def get_by_id(booking_id: str) -> Optional[dict]:
        if not booking_id:
            return None
        try:
            if ObjectId.is_valid(booking_id):
                query = {"_id": ObjectId(booking_id)}
            else:
                query = {
                    "$or": [
                        {"_id": booking_id},
                        {"booking_reference": booking_id}
                    ]
                }
                
            doc = bookings_collection.find_one(query)
            if doc:
                return BookingRepository._serialize_doc(doc)
            return None
        except Exception:
            return None

    @staticmethod
    def find_by_id(booking_id: str) -> Optional[dict]:
        return BookingRepository.get_by_id(booking_id)

    # 2. Add this to BookingRepository
    @staticmethod
    def lookup_booking(reference: str, email: str):
        try:
            doc = bookings_collection.find_one({
                "booking_reference": reference,
                "contact.email": email
            })

            if not doc:
                return None

            return BookingRepository._serialize_doc(doc)
        except Exception as e:
            print("LOOKUP ERROR:", e)
            return None

    @staticmethod
    def update_status(booking_id: str, payment_status: str, booking_reference: Optional[str] = None) -> bool:
        try:
            query = {"_id": booking_id}
            update_payload = {
                "payment_status": payment_status,
                "updated_at": datetime.utcnow()
            }
            if booking_reference:
                update_payload["booking_reference"] = booking_reference

            result = bookings_collection.update_one(query, {"$set": update_payload})
            return result.matched_count > 0
        except Exception as e:
            print(f" REPOSITORY STATUS UPDATE EXCEPTION: {str(e)}")
            return False

    @staticmethod
    def update_settlement(booking_id: str, reference_num: str) -> bool:
        if not booking_id:
            return False
        try:
            if ObjectId.is_valid(booking_id):
                query_selector = {"_id": ObjectId(booking_id)}
            else:
                query_selector = {
                    "$or": [
                        {"_id": booking_id},
                        {"booking_reference": booking_id}
                    ]
                }

            result = bookings_collection.update_one(
                query_selector,
                {
                    "$set": {
                        "payment_status": "PAID", 
                        "booking_reference": str(reference_num),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.matched_count > 0
        except Exception as e:
            print(f" REPOSITORY SETTLEMENT EXCEPTION: {str(e)}")
            return False

    @staticmethod
    def find_by_event(event_id: str, status: Optional[str] = None, page: int = 1, limit: int = 50) -> List[dict]:
        try:
            query = {"event_id": event_id}
            if status and status != "ALL":
                query["payment_status"] = status.upper()
                
            skip = (page - 1) * limit
            docs = list(bookings_collection.find(query).sort("_id", -1).skip(skip).limit(limit))
            return [BookingRepository._serialize_doc(d) for d in docs]
        except Exception:
            return []

    @staticmethod
    def find_all_bookings(status: Optional[str] = None, page: int = 1, limit: int = 100) -> List[dict]:
        try:
            query = {}
            if status and status != "ALL":
                query["payment_status"] = status.upper()
                
            skip = (page - 1) * limit
            docs = list(bookings_collection.find(query).sort("_id", -1).skip(skip).limit(limit))
            return [BookingRepository._serialize_doc(d) for d in docs]
        except Exception as e:
            print(f" REPOSITORY EXCEPTION: {str(e)}")
            return []

    @staticmethod
    def _serialize_doc(doc: dict) -> dict:
        if not doc:
            return {}
        
        serialized = {}
        for key, value in doc.items():
            if key == "_id":
                serialized["id"] = str(value)
                serialized["_id"] = str(value)
            elif hasattr(value, "__str__") and value.__class__.__name__ == "ObjectId":
                serialized[key] = str(value)
            elif isinstance(value, dict):
                serialized[key] = BookingRepository._serialize_doc(value)
            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_list.append(BookingRepository._serialize_doc(item))
                    elif hasattr(item, "__str__") and item.__class__.__name__ == "ObjectId":
                        cleaned_list.append(str(item))
                    else:
                        cleaned_list.append(item)
                serialized[key] = cleaned_list
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value

        if "id" not in serialized: serialized["id"] = "unknown"
        if "booking_reference" not in serialized: serialized["booking_reference"] = None
        if "payment_status" not in serialized: serialized["payment_status"] = "PENDING"
        if "event_title" not in serialized: serialized["event_title"] = "Artist Live Event"
        if "event_venue" not in serialized: serialized["event_venue"] = "Main Arena Gate"
        
        if "contact" not in serialized or not serialized["contact"]:
            serialized["contact"] = {"name": "Guest Checkout", "email": "—"}
        if "items" not in serialized or not serialized["items"]:
            serialized["items"] = [{"tier_name": "General Admission", "quantity": 1}]
            
        # 3. Update _serialize_doc()
        if "total_amount" not in serialized:
            serialized["total_amount"] = 0

        if "total_paid" not in serialized:
            serialized["total_paid"] = serialized["total_amount"]
            
        return serialized