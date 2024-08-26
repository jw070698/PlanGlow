import json
import uuid
from firebase_admin import firestore
db = firestore.client()
# TODO: Define the session
# update_time, session_ref = db.collection("messages").add({"history": []})
def generate_custom_id():
    # Example custom ID 
    custom_id = f"session-{uuid.uuid4().hex[:8]}"
    return custom_id

custom_id = generate_custom_id()
session_ref = db.collection("messages").document(custom_id)
session_ref.set({"history": []})

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
def store_messages(request_message, response_message):
    # Add messages to data
    '''user_message = {"role": "user", "content": request_message}
    assistant_message = {"role": "assistant", "content": response_message}
    session_ref.update({"history": firestore.ArrayUnion([user_message, assistant_message])})'''

    try:
        # Add messages to data
        user_message = {"role": "user", "content": request_message}
        assistant_message = {"role": "assistant", "content": response_message}
        session_ref.update({"history": firestore.ArrayUnion([user_message, assistant_message])})
        print("Messages stored successfully.")
    except Exception as e:
        print(f"Error storing messages: {e}")

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
def get_recent_messages():
    try:
        # Assuming that `session_ref` refers to the current session, and history is an array of messages
        session_doc = session_ref.get()
        session_data = session_doc.to_dict()
        
        if 'history' in session_data:
            # Get the last few messages (you can specify how many, here I get the last 10)
            recent_messages = session_data['history'][-10:]
            return recent_messages
        
        return []
    
    except Exception as e:
        print(f"Error retrieving recent messages: {e}")
        return []