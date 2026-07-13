import os
import firebase_admin
import pyrebase
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# --- Firebase Admin SDK (for Firestore database access) ---
import json
import streamlit as st

if not firebase_admin._apps:
    if "firebase_service_account" in st.secrets:
        # Running on Streamlit Cloud — credentials come from secrets
        service_account_info = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(service_account_info)
    else:
        # Running locally — use the local JSON file
        SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "..", "firebase-service-account.json")
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Pyrebase (for email/password auth) ---
firebase_api_key = st.secrets.get("FIREBASE_API_KEY", os.getenv("FIREBASE_API_KEY"))
firebase_project_id = st.secrets.get("FIREBASE_PROJECT_ID", os.getenv("FIREBASE_PROJECT_ID"))

firebase_config = {
    "apiKey": firebase_api_key,
    "authDomain": f"{firebase_project_id}.firebaseapp.com",
    "projectId": firebase_project_id,
    "storageBucket": f"{firebase_project_id}.appspot.com",
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