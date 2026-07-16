import uuid
from datetime import datetime
from fastapi import HTTPException
from app.repository.event_repository import EventRepository
from app.repository.booking_repository import BookingRepository
from app.model.schemas import BookingCreate, PaymentRequest
from app.enums.status import PaymentStatus, AvailabilityStatus
from app.config.database import events_collection

class TicketingService:
    @staticmethod
    def process_booking_intent(payload: BookingCreate) -> dict:
        event = EventRepository.find_by_id(payload.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Target show event parameters not found.")

        total_tickets = sum(item.quantity for item in payload.items)
        if total_tickets > 8:
            raise HTTPException(status_code=400, detail="Maximum 8 tickets allowed per checkout transaction.")

        tier_map = {t["name"]: t for t in event["tiers"]}
        for item in payload.items:
            if item.tier_name not in tier_map:
                raise HTTPException(status_code=400, detail=f"Tier '{item.tier_name}' does not exist.")
            if item.quantity > tier_map[item.tier_name]["remaining_seats"]:
                raise HTTPException(status_code=400, detail=f"Insufficient inventory available for tier '{item.tier_name}'.")

        booking_id = str(uuid.uuid4())
        # Fix 1: Generate reference string instantly at intent stage
        booking_reference = f"REF-{uuid.uuid4().hex[:8].upper()}"
        total_amount = sum(tier_map[item.tier_name]["price"] * item.quantity for item in payload.items)

        new_booking = {
            "_id": booking_id,
            "event_id": payload.event_id,
            "event_title": event["title"],
            "items": [item.model_dump() for item in payload.items],
            "contact": payload.contact.model_dump(),
            "total_amount": total_amount,
            "payment_status": PaymentStatus.PENDING.value,
            "booking_reference": booking_reference,  # No longer saving None
            "created_at": datetime.utcnow()
        }

        BookingRepository.create(new_booking)
        return {
            "booking_id": booking_id, 
            "booking_reference": booking_reference, 
            "total_amount": total_amount
        }

    @staticmethod
    def authorize_dummy_payment(booking_id: str, payload: PaymentRequest) -> dict:
        booking = BookingRepository.find_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking transaction session tracking reference failed.")

        if booking["payment_status"] == PaymentStatus.PAID.value:
            return {"status": "Success", "booking_reference": booking["booking_reference"]}

        if payload.card_number.strip().endswith("0000"):
            BookingRepository.update_status(booking_id, PaymentStatus.FAILED.value)
            raise HTTPException(status_code=400, detail="Payment declined: Simulated bank transaction failure exception.")

        event = EventRepository.find_by_id(booking["event_id"])
        updated_tiers = []
        for tier in event["tiers"]:
            for item in booking["items"]:
                if tier["name"] == item["tier_name"]:
                    if tier["remaining_seats"] < item["quantity"]:
                        raise HTTPException(status_code=400, detail="Inventory exhausted during runtime transaction window.")
                    tier["remaining_seats"] -= item["quantity"]
            updated_tiers.append(tier)

        all_sold_out = all(t["remaining_seats"] == 0 for t in updated_tiers)
        new_event_status = AvailabilityStatus.SOLD_OUT.value if all_sold_out else event["status"]

        from bson import ObjectId
        events_collection.update_one(
            {"_id": ObjectId(booking["event_id"])},
            {"$set": {"tiers": updated_tiers, "status": new_event_status}}
        )

        # Uses pre-existing or builds a fall-back if needed
        booking_ref = booking.get("booking_reference") or f"REF-{uuid.uuid4().hex[:8].upper()}"
        BookingRepository.update_status(booking_id, PaymentStatus.PAID.value, booking_reference=booking_ref)

        return {"status": "Success", "booking_reference": booking_ref}