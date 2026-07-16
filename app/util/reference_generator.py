from datetime import datetime
import random


def generate_booking_reference():

    year = datetime.now().year
    number = random.randint(100000, 999999)

    return f"REF-{year}-{number}"