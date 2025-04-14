# YouTube_request.py
# YouTube Data API v3
# Input: subject from previous stage
# Output: videoId, title, description, thumbnails, channelTitle, publishtime
import json
from googleapiclient.discovery import build
import os
import re
import random
'''
# Get all environment variables
env_vars = os.environ
env_vars_dict = dict(env_vars)

# Filter keys that start with 'YOUTUBE_API_KEY'
youtube_api_keys = [k for k in env_vars_dict if k.startswith("YOUTUBE_API_KEY")]
'''
from dotenv import load_dotenv
load_dotenv()
youtube_api_keys = [k for k in os.environ if k.startswith("YOUTUBE_API_KEY")]

def get_random_api_key():
    """Retrieve a random YouTube API key from the environment variables."""
    if youtube_api_keys:
        selected_key = random.choice(youtube_api_keys)
        api_key = os.getenv(selected_key)
        if not api_key:
            raise ValueError("YouTube API key is missing in environment variables.")
        return api_key
    else:
        raise ValueError("No YOUTUBE_API_KEY found in environment variables.")

def get_youtube_client():
    """Create and return a YouTube API client using a random API key."""
    while youtube_api_keys:
        try:
            selected_key = random.choice(youtube_api_keys)
            api_key = os.getenv(selected_key)
            youtube = build('youtube', 'v3', developerKey=api_key)
            # Test the key with a simple request to check if it has quota
            youtube.videos().list(part="snippet", id="Ks-_Mh1QhMc").execute()
            return youtube
        except Exception as e:
            print(f"API key {selected_key} quota exceeded or invalid, trying another. Error: {e}")
            youtube_api_keys.remove(selected_key)
    raise ValueError("All API keys have exceeded quota or are invalid.")

def get_search_response(query):
    youtube = get_youtube_client()  # Initialize YouTube client
    max_duration_seconds = extract_available_time(query)
    if max_duration_seconds is None:
        print("Not available time")
        return []
    print(max_duration_seconds)
    if max_duration_seconds <= 240:  
        video_duration = "short"
    elif max_duration_seconds <= 1200:  
        video_duration = "medium"
    else:
        video_duration = "long"
    print(query)
    search_response = youtube.search().list(
        q=query,
        order="relevance",
        part="snippet",
        type="video",
        regionCode="US",
        maxResults=10,
        safeSearch="strict"
    ).execute()

    return search_response

def extract_available_time(query):
    match = re.search(r'(\d+)\s*hours', query)
    if match:
        hours = int(match.group(1))
        return hours * 3600  # Convert hours to seconds
    return None

def get_video_info(search_response):
    result_json = {}
    idx = 0
    for item in search_response['items']:
        if item['id']['kind'] == 'youtube#video':
            # Fetch thumbnails from various sizes and provide a fallback URL
            thumbnails = item['snippet']['thumbnails']
            thumbnail_url = (
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url') or
                'https://via.placeholder.com/120'
            )
            
            result_json[idx] = info_to_dict(
                item['id']['videoId'],
                item['snippet']['title'],
                item['snippet']['description'],
                thumbnail_url,
                item['snippet']['channelTitle'],
                item['snippet']['publishTime']
            )
            idx += 1
    return result_json

def info_to_dict(videoId, title, description, thumbnail, channelTitle, publishtime):
    result = {
        "videoId": videoId,
        "title": title,
        "description": description,
        "thumbnail": thumbnail,
        "channelTitle": channelTitle,
        "publishtime": publishtime
    }
    return result

def extract_video_id(url):
    video_id_match = re.search(r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})|(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/)?([a-zA-Z0-9_-]{11})', url)
    if video_id_match:
        return video_id_match.group(1) or video_id_match.group(2)
    else:
        raise ValueError("Invalid YouTube URL")

def get_video_thumbnail(video_id):
    youtube = get_youtube_client()  # Initialize YouTube client
    video_response = youtube.videos().list(
        part="snippet",
        id=video_id
    ).execute()

    if 'items' in video_response and len(video_response['items']) > 0:
        video_details = video_response['items'][0]['snippet']
        thumbnail_url = video_details.get('thumbnails', {}).get('high', {}).get('url', 'No Thumbnail')
        return thumbnail_url
    else:
        print(f"No thumbnail found for ID: {video_id}")
        return 'https://via.placeholder.com/120'

def search_similar_videos(query):
    youtube = get_youtube_client()  # Initialize YouTube client
    print("search_similar_videos", query)
    try:
        search_response = youtube.search().list(
            q=query,
            order="rating",
            part="snippet",
            type="video",
            regionCode="US",
            maxResults=1,
            safeSearch="strict"
        ).execute()

        print("items", search_response['items'])

        items = search_response.get('items', [])
        if not items:
            return {
                'exists': False,
                'message': 'No similar videos found.'
            }

        # Process the first video in the items list
        video_details = items[0]['snippet']
        video_id = items[0]['id'].get('videoId', 'No Video ID')
        if not video_id:
            return {
                'exists': False,
                'message': 'No video ID found in the search result.'
            }
        thumbnail_url = video_details.get('thumbnails', {}).get('high', {}).get('url', 'No Thumbnail')
        title = video_details.get('title', 'No Title')
        description = video_details.get('description', 'No Description')
        channel_title = video_details.get('channelTitle', 'No Channel Title')
        publish_time = video_details.get('publishTime', 'No Publish Time')

        return {
            "exists": True,
            "videoId": video_id,
            "title": title,
            "description": description,
            "thumbnails": thumbnail_url,
            "channelTitle": channel_title,
            "publishTime": publish_time
        }
            
    except Exception as e:
        return {"exists": False, "message": f"An error occurred during search: {e}"}

def check_resource_availability(url, query):
    youtube = get_youtube_client()  # Initialize YouTube client
    try:
        video_id = extract_video_id(url)
        if not video_id or len(video_id) != 11:
            return {
                "exists": False,
                "message": f"Invalid video ID extracted from URL: {url}"
            }
        print("Check_resoure_availailbity in YouTube_request.py: ",video_id)
        video_response = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()

        if 'items' in video_response and len(video_response['items']) > 0:
            video_details = video_response['items'][0]['snippet']
            thumbnail_url = video_details.get('thumbnails', {}).get('high', {}).get('url', 'No Thumbnail')
            title = video_details.get('title', 'No Title')
            description = video_details.get('description', 'No Description')
            channel_title = video_details.get('channelTitle', 'No Channel Title')
            publish_time = video_details.get('publishTime', 'No Publish Time')
            
            return {
                "videoId": video_id,
                "title": title,
                "description": description,
                "thumbnails": thumbnail_url,
                "channelTitle": channel_title,
                "publishTime": publish_time
            }
        else:
            return {
                "exists": False,
                "message": f"No video found for ID: {video_id}"
            }
    except Exception as e:
        return {
            "exists": False,
            "message": f"An error occurred: {e}"
        }

def get_video_stats(video_id):
    youtube = get_youtube_client()  # Initialize YouTube client
    request = youtube.videos().list(
        part="statistics",
        id=video_id
    )
    response = request.execute()
    
    if "items" in response and len(response["items"]) > 0:
        stats = response["items"][0]["statistics"]
        view_count = stats.get("viewCount", "N/A")
        like_count = stats.get("likeCount", "N/A")
        return {"views": view_count, "likes": like_count}
    else:
        return {"views": "N/A", "likes": "N/A"}
