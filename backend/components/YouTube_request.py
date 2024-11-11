# YouTube Data API v3
# Input: subject from previous stage
# Output: videoId, title, description, thumbnails, channelTitle, publishtime
import json
from googleapiclient.discovery import build
import os
import re
import random
# Get all environment variables
env_vars = os.environ
env_vars_dict = dict(env_vars)

# Filter keys that start with 'YOUTUBE_API_KEY'
youtube_api_keys = [k for k in env_vars_dict if k.startswith("YOUTUBE_API_KEY")]

#from dotenv import load_dotenv
#load_dotenv()
#youtube_api_keys = [k for k in os.environ if k.startswith("YOUTUBE_API_KEY")]

#

sorted_keys = sorted(youtube_api_keys)
selected_key = random.choice(sorted_keys)
YOUTUBE_API_KEY = os.environ[selected_key]

if youtube_api_keys:
    sorted_keys = sorted(youtube_api_keys)
    selected_key = random.choice(sorted_keys)
    YOUTUBE_API_KEY = os.getenv(selected_key)
else:
    raise ValueError("No YOUTUBE_API_KEY found in environment variables")

youtube = build('youtube', 'v3', developerKey = YOUTUBE_API_KEY)
# youtube = None
# pylint: disable=maybe-no-member

def get_search_response(query):
    search_response = youtube.search().list(
        q = query,
        order = "relevance",
        part = "snippet",
        type="video",
        regionCode="US",
        maxResults = 10
    ).execute()
    return search_response

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


def extract_video_id(url): # Extracts video ID from a YouTube URL.
    video_id_match = re.search(r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})|(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/)?([a-zA-Z0-9_-]{11})', url)
    if video_id_match:
        return video_id_match.group(1) or video_id_match.group(2)
    else:
        raise ValueError("Invalid YouTube URL")


def get_video_thumbnail(video_id): # Returns the thumbnail URL for a given YouTube video URL.
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
        thumbnail_url = 'https://via.placeholder.com/120'
        return thumbnail_url

def check_resource_availability(url):
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")

        video_response = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()

        if 'items' in video_response and len(video_response['items']) > 0:
            video_details = video_response['items'][0]['snippet']
            thumbnail_url = video_details.get('thumbnails', {}).get('high', {}).get('url', 'No Thumbnail')
            
            # Extract other details with default values if the key is missing
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

def get_video_stats(video_id): # Count of views and likes    
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
