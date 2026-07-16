from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from app.enums.status import AvailabilityStatus

# ==========================================
# EVENT TIER SCHEMAS
# ==========================================
class TicketTierBase(BaseModel):
    name: str
    price: float
    total_quantity: int

class TicketTierResponse(TicketTierBase):
    remaining_seats: int

class EventCreate(BaseModel):
    title: str
    venue: str
    city: str
    country: str
    date: datetime
    description: str
    image_url: str
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    tiers: List[TicketTierBase] = []


# ==========================================
# BOOKING & CHECKOUT SCHEMAS
# ==========================================
class BookingItem(BaseModel):
    tier_name: str
    quantity: int = Field(..., gt=0, le=8)

class ContactDetails(BaseModel):
    name: str
    email: EmailStr
    phone: str

class BookingCreate(BaseModel):
    event_id: str
    items: List[BookingItem]
    contact: ContactDetails

class PaymentRequest(BaseModel):
    card_number: str
    expiry: str
    cvv: str


# ==========================================
# NEW: BACKEND REF TRACKING SYSTEM SCHEMAS
# ==========================================
class SettlePaymentRequest(BaseModel):
    """
    Payload sent right after successful payment processing 
    to trigger server-side reference key creation.
    """
    booking_id: str

class BookingVerificationResponse(BaseModel):
    """
    Structured data returned to the frontend confirmation page
    guaranteeing matching server states.
    """
    booking_reference: str
    payment_status: str


# ==========================================
# SECURITY / ADMIN AUTH SCHEMAS
# ==========================================
class AdminLoginRequest(BaseModel):
    username: str
    password: str