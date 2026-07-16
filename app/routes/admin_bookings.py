from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from app.config.database import bookings_collection
from app.repository.booking_repository import BookingRepository
from app.util.security_utils import get_current_admin

router = APIRouter(
    prefix="/admin/bookings",
    tags=["Admin Bookings"]
)

# 1. Secured Settlement Endpoint
@router.post("/settle", status_code=status.HTTP_200_OK)
def settle_booking(
    data: dict,
    admin=Depends(get_current_admin)
):
    booking_id = data.get("booking_id")
    print("SETTLE REQUEST FOR ID/REF:", booking_id)

    if not booking_id:
        raise HTTPException(
            status_code=400,
            detail="booking_id is required"
        )

    # Repository lookup handles matching either string ID or booking_reference string smoothly
    booking = BookingRepository.get_by_id(booking_id)

    if not booking:
        print("BOOKING NOT FOUND IN DB:", booking_id)
        raise HTTPException(
            status_code=404,
            detail=f"Booking not found: {booking_id}"
        )

    # Safely retrieve key regardless of whether it's serialized as 'id' or raw '_id'
    db_id = booking.get("_id") or booking.get("id")

    # Sync settlement state via your fixed Repository method
    generated_ref = booking.get("booking_reference") or f"REF-{booking_id[:8].upper()}"
    success = BookingRepository.update_settlement(db_id, generated_ref)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Database write state synchronization failed."
        )

    return {
        "success": True,
        "booking_reference": generated_ref
    }


# 2. Secured Verification Endpoint
@router.get("/{booking_id}/verify")
def verify_booking(
    booking_id: str,
    admin=Depends(get_current_admin)
):
    print("VERIFY REQUEST FOR ID/REF:", booking_id)

    # Safe repository pattern wrapper call prevents BSON object casting mismatch crashes
    booking = BookingRepository.get_by_id(booking_id)

    if not booking:
        print(f"AVAILABLE BOOKINGS DEBUG LOG:")
        for item in bookings_collection.find().limit(5):
            print(f"ID: {item.get('_id')} | REF: {item.get('booking_reference')}")

        raise HTTPException(
            status_code=404,
            detail=f"Booking tracking record unresolvable for: {booking_id}"
        )

    return booking