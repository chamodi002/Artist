from enum import Enum

class AvailabilityStatus(str, Enum):
    AVAILABLE = "Available"
    SELLING_FAST = "Selling Fast"
    SOLD_OUT = "Sold Out"
    CANCELLED = "Cancelled"

class PaymentStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    FAILED = "Failed"