import json
import uuid
from firebase_admin import firestore
db = firestore.client()
# TODO: Define the session
# update_time, session_ref = db.collection("messages").add({"history": []})

def create_session(participant_id):
    session_ref = db.collection("messages").document(participant_id)
    session_ref.set({"history": []})
    return session_ref

# Get recent messages 
'''def get_recent_messages():

    # Define file name 
    file_name = "stored_data.json"
    instructions = {"role": "system", "content": "You are suggesting study plan based on user's needs and preference. \
             Try to suggest best possible fit in terms of time limitation, type of resources, their base knowledge. Return the result in json format. \
              Each day title as key, the topic and related resources as values.Do not put anything else in your response. \
             Example of result:{'Day 1': {'topic': 'Variables','content title':'introduction to variables in python', 'link':'link to content'}"}
    
    # Initialize messages
    messages = []
    messages.append(instructions)
    
    #Get last messages
    try:
       with open(file_name, "r") as user_file:
            data = json.load(user_file)
            if data:
                for item in data:
                    messages.append(item)
    except Exception as e:
        print(e)

    return messages'''


# Store Messages 
def store_messages(participant_id, request_message, response_message):
    # Get session reference
    session_ref = db.collection("messages").document(participant_id)

    # Add messages to session
    user_message = {"role": "user", "content": request_message}
    assistant_message = {"role": "assistant", "content": response_message}
    try:
        # Check if the document exists
        if not session_ref.get().exists:
            # If document does not exist, create it with initial history
            session_ref.set({"history": [user_message, assistant_message]})
        else:
            # If document exists, append to the existing history
            session_ref.update({"history": firestore.ArrayUnion([user_message, assistant_message])})
        
        print("Messages stored successfully.")
    
    except Exception as e:
        print(f"Error storing messages for participant {participant_id}: {e}")

#   # Define the file name
#   file_name = "stored_data.json"

#   # Get recent messages
#   messages = get_recent_messages()[1:]

#   # Add messages to data
#   user_message = {"role": "user", "content": request_message}
#   assistant_message = {"role": "assistant", "content": response_message}
#   messages.append(user_message)
#   messages.append(assistant_message)

#   # Save the updated file
#   with open(file_name, "w") as f:
#     json.dump(messages, f)

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