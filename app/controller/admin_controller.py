import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from bson import ObjectId, errors

from app.config.database import admin_collection, bookings_collection
from app.model.schemas import (
    AdminLoginRequest,
    EventCreate,
    SettlePaymentRequest,
    TicketTierBase,
)
from app.repository.booking_repository import BookingRepository
from app.repository.event_repository import EventRepository
from app.util.security_utils import create_access_token, verify_password, get_current_admin

# Main router included in main.py
admin_router = APIRouter(prefix="/admin", tags=["Admin / Bookings"])


def safe_object_id(id_str: str) -> Any:
    """Helper to safely convert a string to an ObjectId if valid, else returns the original string."""
    try:
        return ObjectId(id_str.strip('"\' '))
    except (errors.InvalidId, AttributeError):
        return id_str.strip('"\' ')


# ---------------- PUBLIC AUTH ENDPOINT ----------------
@admin_router.post("/login")
def login(payload: AdminLoginRequest):
    user = admin_collection.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": payload.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


# ---------------- PROTECTED EVENT ROUTING ----------------
@admin_router.post("/events", status_code=201)
def create_new_event(payload: EventCreate, admin=Depends(get_current_admin)):
    try:
        event_data = payload.model_dump()
        if "image_url" in event_data and isinstance(event_data["image_url"], str):
            event_data["image_url"] = event_data["image_url"].strip('"\' ')

        event_id = EventRepository.create(event_data)
        return {"event_id": str(event_id), "message": "Event created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.patch("/events/{id}")
def edit_event(id: str, update_data: dict, admin=Depends(get_current_admin)):
    allowed_fields = ["title", "venue", "city", "country", "date", "description", "image_url", "status", "tiers"]
    filtered_updates = {k: v for k, v in update_data.items() if k in allowed_fields}

    if "image_url" in filtered_updates and isinstance(filtered_updates["image_url"], str):
        filtered_updates["image_url"] = filtered_updates["image_url"].strip('"\' ')

    if "date" in filtered_updates and isinstance(filtered_updates["date"], str):
        try:
            date_str = filtered_updates["date"].replace("Z", "+00:00")
            filtered_updates["date"] = datetime.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format structure passed.")

    if "tiers" in filtered_updates and isinstance(filtered_updates["tiers"], list):
        cleaned_tiers = []
        for tier in filtered_updates["tiers"]:
            total_qty = int(tier.get("total_quantity", tier.get("quantity", 0)))
            cleaned_tiers.append({
                "name": str(tier.get("name", "")),
                "price": float(tier.get("price", 0.0)),
                "total_quantity": total_qty,
                "remaining_seats": int(tier.get("remaining_seats", total_qty))
            })
        filtered_updates["tiers"] = cleaned_tiers

    success = EventRepository.update(id, filtered_updates)
    if not success:
        raise HTTPException(status_code=404, detail="Event configuration parameters not found.")

    return {"status": "Updated successfully"}


@admin_router.post("/events/{id}/tiers", status_code=201)
def add_ticket_tier(id: str, payload: TicketTierBase, admin=Depends(get_current_admin)):
    success = EventRepository.add_tier(id, payload.model_dump())
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "Tier added successfully"}


@admin_router.patch("/tiers/{event_id}/{tier_name}")
def update_ticket_tier(event_id: str, tier_name: str, update_data: dict, admin=Depends(get_current_admin)):
    allowed_fields = ["price", "total_quantity", "remaining_seats"]
    filtered_updates = {k: v for k, v in update_data.items() if k in allowed_fields}

    success = EventRepository.update_tier_by_name(event_id, tier_name, filtered_updates)
    if not success:
        raise HTTPException(status_code=404, detail="Tier not found")
    return {"status": "Tier updated successfully"}


# ---------------- PROTECTED DATA AGGREGATION ----------------
@admin_router.get("/events/{id}/bookings")
def view_event_bookings(id: str, status: Optional[str] = None, page: Optional[int] = 1, limit: Optional[int] = 50, admin=Depends(get_current_admin)):
    try:
        clean_id = id.strip('"\' ')
        if clean_id == "id" or not clean_id:
            return []

        current_page = page if page and page >= 1 else 1
        max_limit = limit if limit and limit >= 1 else 50

        raw_bookings = BookingRepository.find_by_event(event_id=clean_id, status=status, page=current_page, limit=max_limit)
        return jsonable_encoder(raw_bookings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database aggregation exception: {str(e)}")


@admin_router.get("/bookings")
def view_all_system_bookings(status: Optional[str] = None, page: Optional[int] = 1, limit: Optional[int] = 100, admin=Depends(get_current_admin)):
    try:
        current_page = page if page and page >= 1 else 1
        max_limit = limit if limit and limit >= 1 else 100

        raw_bookings = BookingRepository.find_all_bookings(status=status, page=current_page, limit=max_limit)
        return jsonable_encoder(raw_bookings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global system data transmission exception: {str(e)}")


# ---------------- PUBLIC CUSTOMER/CHECKOUT PIPELINE ----------------
@admin_router.post("/bookings/create", status_code=201)
def create_checkout_booking(payload: Dict[str, Any]):
    try:
        event_id = payload.get("eventId") or payload.get("event_id")
        tier_name = payload.get("bookingId") or payload.get("tier_name") or "General Pass"
        price = float(payload.get("price") or 300.0)
        quantity = int(payload.get("qty") or payload.get("quantity") or 1)
        
        if not event_id:
            raise HTTPException(status_code=400, detail="Missing required eventId.")

        generated_ref = f"REF-{secrets.randbelow(900000) + 100000}"

        new_booking = {
            "booking_reference": generated_ref,
            "event_id": str(event_id),
            "payment_status": "PENDING",
            "total_amount": price * quantity,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "event_title": payload.get("event_title") or "Artist Live Event",
            "event_venue": payload.get("event_venue") or "Main Arena Gate",
            "contact": payload.get("contact") or {
                "name": payload.get("name") or "Verified Guest",
                "email": payload.get("email") or "guest@checkout.com"
            },
            "items": [
                {
                    "tier_name": str(tier_name),
                    "price": price,
                    "quantity": quantity
                }
            ]
        }

        insert_result = bookings_collection.insert_one(new_booking)
        
        return jsonable_encoder({
            "status": "SUCCESS",
            "booking_id": str(insert_result.inserted_id),
            "booking_reference": generated_ref,
            "redirect_url": f"/confirmation/{generated_ref}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- PROTECTED SETTLEMENT & VERIFICATION ----------------
@admin_router.post("/bookings/settle", status_code=status.HTTP_200_OK)
def settle_booking_payment(payload: SettlePaymentRequest, admin=Depends(get_current_admin)):
    try:
        booking_id = payload.booking_id.strip('"\' ') if isinstance(payload.booking_id, str) else payload.booking_id

        booking = None
        if isinstance(booking_id, str) and (booking_id.startswith("REF-") or booking_id.startswith("INV-")):
            booking = bookings_collection.find_one({"booking_reference": booking_id})
            if not booking:
                booking = bookings_collection.find_one({"_id": safe_object_id(booking_id)})
        else:
            booking = BookingRepository.get_by_id(booking_id)

        if not booking:
            raise HTTPException(status_code=404, detail=f"Target booking record '{booking_id}' not found.")

        target_key = str(booking.get("_id"))

        if booking.get("booking_reference"):
            generated_reference = str(booking.get("booking_reference"))
        else:
            random_suffix = secrets.token_hex(2).upper()
            current_year = datetime.now(timezone.utc).year
            generated_reference = f"INV-{current_year}-{random_suffix}"

        success = BookingRepository.update_settlement(target_key, generated_reference)
        if not success:
            raise HTTPException(status_code=500, detail="Database write state synchronization failed.")

        return {
            "status": "SUCCESS",
            "booking_reference": str(generated_reference),
            "payment_status": "PAID"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/bookings/{booking_id}/verify")
def get_booking_reference(booking_id: str, admin=Depends(get_current_admin)):
    try:
        clean_booking_id = booking_id.strip('"\' ') if isinstance(booking_id, str) else booking_id

        booking = None
        if isinstance(clean_booking_id, str) and (clean_booking_id.startswith("REF-") or clean_booking_id.startswith("INV-")):
            booking = bookings_collection.find_one({"booking_reference": clean_booking_id})
        else:
            booking = BookingRepository.get_by_id(clean_booking_id) or bookings_collection.find_one({"_id": safe_object_id(clean_booking_id)})

        if not booking:
            raise HTTPException(status_code=404, detail="File tracking record unresolvable.")

        response_data = {
            "booking_reference": str(booking.get("booking_reference") or "UNASSIGNED"),
            "payment_status": str(booking.get("payment_status") or "PAID"),
            "event_title": str(booking.get("event_title") or "Artist Live Event"),
            "event_venue": str(booking.get("event_venue") or "Main Arena Gate"),
            "event_date": str(booking.get("event_date")) if booking.get("event_date") else None,
            "contact": booking.get("contact") or {"name": "Guest Checkout", "email": "—"},
            "items": booking.get("items") or [{"tier_name": "General Admission", "quantity": 1}]
        }
        
        return jsonable_encoder(response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))