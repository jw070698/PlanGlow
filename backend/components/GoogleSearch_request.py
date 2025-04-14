# Google Custom Search API
# input: subject with method (e.g., python with blogs)
from googleapiclient.discovery import build
import json
import os
import random
cse_id = os.getenv('CSE_ID1')

# Get all environment variables
env_vars = os.environ
env_vars_dict = dict(env_vars)

# Filter keys that start with 'YOUTUBE_API_KEY'
youtube_api_keys = [k for k in env_vars_dict if k.startswith("YOUTUBE_API_KEY")]

# Sort keys by the numerical suffix
sorted_keys = sorted(youtube_api_keys)

selected_key = random.choice(sorted_keys)
YOUTUBE_API_KEY = os.environ[selected_key]

def google_search_availability(search_term):
    service = build("customsearch", "v1", developerKey=YOUTUBE_API_KEY)
    try:
        res = service.cse().list(q=search_term, cx=cse_id, num=10, start=1).execute()
        return res.get('items', [])
    except Exception as e:
        print(f"An error occurred: {e}")
        return []