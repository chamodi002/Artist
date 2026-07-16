import os
from dotenv import load_dotenv
SECRET_KEY = os.getenv("JWT_SECRET", "focalid-ticketing-secret-signature-token-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60