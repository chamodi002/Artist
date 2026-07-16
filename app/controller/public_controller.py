from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from app.model.schemas import BookingCreate, PaymentRequest
from app.repository.event_repository import EventRepository
from app.repository.booking_repository import BookingRepository
from app.service.ticketing_service import TicketingService

public_router = APIRouter()

@public_router.get("/events")
def list_events(city: Optional[str] = None, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None, limit: Optional[int] = None):
    return EventRepository.find_all(city, from_date, to_date, limit=limit)

@public_router.get("/events/{id}")
def get_event(id: str):
    event = EventRepository.find_by_id(id)
    if not event:
        raise HTTPException(status_code=404, detail="Requested event page metrics could not be located.")
    return event

@public_router.post("/bookings", status_code=201)
def reserve_tickets(payload: BookingCreate):
    return TicketingService.process_booking_intent(payload)

@public_router.post("/bookings/{id}/pay")
def pay_booking(id: str, payload: PaymentRequest):
    return TicketingService.authorize_dummy_payment(id, payload)

@public_router.get("/bookings/lookup")
def find_ticket(reference: str = Query(...), email: str = Query(...)):
    # Invokes the newly integrated lookup engine method within the Booking Repository layer
    booking = BookingRepository.lookup_booking(reference, email)
    
    # Raises a proper 404 response if the database returns no matched document structure
    if not booking:
        raise HTTPException(status_code=404, detail="Verified matching booking verification log context not found.")
        
    return booking