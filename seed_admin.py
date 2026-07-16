from app.config.database import admin_collection
from app.util.security_utils import hash_password


def create_admin():

    username = "admin"
    password = "admin123"

    try:

        existing_admin = admin_collection.find_one(
            {"username": username}
        )

        if existing_admin:
            print("Admin already exists")
            return

        hashed_password = hash_password(password)

        admin_data = {
            "username": username,
            "hashed_password": hashed_password,
            "role": "admin"
        }

        result = admin_collection.insert_one(admin_data)

        if result.inserted_id:
            print("\nAdmin created successfully")
            print("---------------------------")
            print("Username : admin")
            print("Password : admin123")
            print("Role     : admin")
            print("---------------------------")

    except Exception as e:
        print("Failed to create admin")
        print("Error:", e)


if __name__ == "__main__":
    create_admin()