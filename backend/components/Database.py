import json
import uuid
import firebase_admin
from firebase_admin import credentials, firestore

db = firestore.client()

def create_session(participant_id):
    try:
        session_ref = db.collection("messages").document(participant_id)
        session_ref.set({
            "history": [],
            "submit_count": 0,
            "send_count": 0,
            "additional_resources_count": 0,
            "inline_count": 0
        })
        print(f"Session created for participant {participant_id}.")
        return session_ref
    except Exception as e:
        print(f"Error creating session for participant {participant_id}: {e}")

# Store Messages 
def store_messages(participant_id, request_message, response_message):
    session_ref = db.collection("messages").document(participant_id)

    # Prepare messages
    user_message = {"role": "user", "content": request_message}
    assistant_message = {"role": "assistant", "content": response_message}

    try:
        # Check if document exists
        if not session_ref.get().exists:
            # Create the document if it doesn't exist
            session_ref.set({"history": [user_message, assistant_message]})
            print(f"New document created for participant {participant_id}.")
        else:
            # Update existing document
            session_ref.update({"history": firestore.ArrayUnion([user_message, assistant_message])})
            print(f"Messages appended for participant {participant_id}.")
    except Exception as e:
        print(f"Error storing messages for participant {participant_id}: {e}")

# Get recent messages
def get_recent_messages(participant_id):
    try:
        # Get session reference
        session_ref = db.collection("messages").document(participant_id)
        session_doc = session_ref.get()
        if session_doc.exists:
            session_data = session_doc.to_dict()
            if 'history' in session_data:
                # Retrieve the last 10 messages or fewer
                recent_messages = session_data['history'][-10:]
                return recent_messages
        
        print(f"No recent messages found for participant {participant_id}.")
        return []
    
    except Exception as e:
        print(f"Error retrieving recent messages for participant {participant_id}: {e}")
        return []