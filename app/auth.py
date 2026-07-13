import os
import firebase_admin
import pyrebase
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# --- Firebase Admin SDK (for Firestore database access) ---
SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "..", "firebase-service-account.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Pyrebase (for email/password auth) ---
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": f"{os.getenv('FIREBASE_PROJECT_ID')}.firebaseapp.com",
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": f"{os.getenv('FIREBASE_PROJECT_ID')}.appspot.com",
    "databaseURL": "",  # not using Realtime Database, only Firestore
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()


def sign_up(email: str, password: str) -> dict:
    """Create a new user. Returns Firebase user data including uid and idToken."""
    user = auth.create_user_with_email_and_password(email, password)
    # Create their Firestore user document
    db.collection("users").document(user["localId"]).set({
        "email": email,
        "groq_api_key": "",
    })
    return user


def log_in(email: str, password: str) -> dict:
    """Log in an existing user. Returns Firebase user data including uid and idToken."""
    return auth.sign_in_with_email_and_password(email, password)


if __name__ == "__main__":
    print("Firestore connected:", db is not None)
    print("Pyrebase auth initialized:", auth is not None)