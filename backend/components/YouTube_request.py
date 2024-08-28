import json
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import re
import random

# Load environment variables
load_dotenv()

# Get YouTube API keys from environment variables
youtube_api_keys = [os.getenv(key) for key in os.environ if key.startswith("YOUTUBE_API_KEY")]

if not youtube_api_keys:
    raise ValueError("No YouTube API keys found in environment variables.")

# Function to randomly select an API key
def get_random_api_key():
    return random.choice(youtube_api_keys)

# Initialize YouTube API client
def initialize_youtube_api():
    YOUTUBE_API_KEY = get_random_api_key()
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

youtube = initialize_youtube_api()

# Function to search for YouTube videos
def get_search_response(query, max_results=10):
    try:
        search_response = youtube.search().list(
            q=query,
            order="relevance",
            part="snippet",
            type="video",
            regionCode="US",
            maxResults=max_results
        ).execute()
        return search_response
    except Exception as e:
        print(f"An error occurred during YouTube search: {e}")
        return None

# Function to extract video information from the search response
def get_video_info(search_response):
    result_json = {}
    for idx, item in enumerate(search_response['items']):
        if item['id']['kind'] == 'youtube#video':
            thumbnail_url = get_best_thumbnail_url(item['snippet']['thumbnails'])
            result_json[idx] = {
                "videoId": item['id']['videoId'],
                "title": item['snippet']['title'],
                "description": item['snippet']['description'],
                "thumbnail": thumbnail_url,
                "channelTitle": item['snippet']['channelTitle'],
                "publishTime": item['snippet']['publishTime']
            }
    return result_json

# Function to get the best available thumbnail URL
def get_best_thumbnail_url(thumbnails):
    return (
        thumbnails.get('high', {}).get('url') or
        thumbnails.get('medium', {}).get('url') or
        thumbnails.get('default', {}).get('url') or
        'https://via.placeholder.com/120'
    )

# Function to extract video ID from a YouTube URL
def extract_video_id(url):
    video_id_match = re.search(
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})|(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/)?([a-zA-Z0-9_-]{11})', 
        url
    )
    if video_id_match:
        return video_id_match.group(1) or video_id_match.group(2)
    else:
        raise ValueError("Invalid YouTube URL")

# Function to get the thumbnail URL for a given YouTube video URL
def get_video_thumbnail(url):
    try:
        video_id = extract_video_id(url)
        video_response = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()

        if video_response['items']:
            return get_best_thumbnail_url(video_response['items'][0]['snippet']['thumbnails'])
        else:
            return 'https://via.placeholder.com/120'

    except Exception as e:
        print(f"An error occurred while fetching thumbnail: {e}")
        return 'https://via.placeholder.com/120'

# Function to check if a YouTube resource is available
def check_resource_availability(url):
    try:
        video_id = extract_video_id(url)
        video_response = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()

        if video_response['items']:
            video_details = video_response['items'][0]['snippet']
            return {
                "videoId": video_id,
                "title": video_details.get('title', 'No Title'),
                "description": video_details.get('description', 'No Description'),
                "thumbnail": get_best_thumbnail_url(video_details['thumbnails']),
                "channelTitle": video_details.get('channelTitle', 'No Channel Title'),
                "publishTime": video_details.get('publishTime', 'No Publish Time')
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

# Function to get the video statistics such as views and likes
def get_video_stats(video_id):
    try:
        response = youtube.videos().list(
            part="statistics",
            id=video_id
        ).execute()

        if response['items']:
            stats = response['items'][0]['statistics']
            return {
                "views": stats.get("viewCount", "N/A"),
                "likes": stats.get("likeCount", "N/A")
            }
        else:
            return {"views": "N/A", "likes": "N/A"}

    except Exception as e:
        print(f"An error occurred while fetching video stats: {e}")
        return {"views": "N/A", "likes": "N/A"}
