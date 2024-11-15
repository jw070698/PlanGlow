#app.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, os, json, aiohttp, random
from urllib.parse import urlparse, parse_qs
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore, auth
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:1350')
# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

from components.OpenAI_request import ChatApp
from components.Database import db, create_session, store_messages, get_recent_messages
from components.YouTube_request import search_similar_videos, get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability, get_video_stats
from components.GoogleSearch_request import google_search_availability


from dotenv import load_dotenv
load_dotenv()
youtube_api_keys = [k for k in os.environ if k.startswith("YOUTUBE_API_KEY")]
YOUTUBE_URL_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=)?([a-zA-Z0-9_-]{11})')

api_key = os.getenv('API_KEY1')
client = OpenAI(api_key=api_key)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_app = ChatApp(api_key=api_key)

@app.get('/')
def hello_world():
    return "Hello,World"

class MessageRequest(BaseModel):
    user_message: str = None
    participantId: str

class InfoRequest(BaseModel):
    info_message: str

class SearchRequest(BaseModel):
    search_message: str

class YouTubeVideoID(BaseModel):
    video_id: str

class YouTubeLink(BaseModel):
    url: str

class CheckRequest(BaseModel):
    check_message: str
    participantsId: str
    research_query: str

class PlanRequest(BaseModel):
    info_message: str
    participantId: str

class UserMessageRequest(BaseModel):
    user_message: str
    participantId: str

@app.post("/response")
async def generate_response(request: MessageRequest):
    try:
        participantId = request.participantId
        # Check if session exists; if not, create a new session
        session_ref = db.collection("messages").document(participantId)

        if not session_ref.get().exists:
            create_session(participantId)
            print("Session created for", participantId)
        else:
            print("Session already exists for", participantId)
        
        # Handle user message input
        user_message = request.user_message or request.user_input
        if not user_message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        # Step 1
        # Generate response and store it
        response_text = chat_app.chat(user_message)
        if not response_text:
            raise HTTPException(status_code=500, detail="No response received from OpenAI")
        
        # Store the message and response in Firestore (append to history)
        store_messages(participantId, user_message, response_text)
        print("Stored initial response")

        return {"response": response_text}

    except Exception as e:
        # General error logging
        print(f"Unexpected error occurred in /response endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


@app.post("/response/critique")
async def generate_critique_response(request: MessageRequest):
    try:
        participantId = request.participantId
        initial_response = get_recent_messages(participantId)[-1]['content']  # Get the last message if stored

        critique_response = chat_app.get_critique_response(initial_response)
        if critique_response:
            store_messages(participantId, "Critique of Initial Response", critique_response)
            print("Stored critique response")

        return {"response": critique_response}

    except Exception as e:
        print(f"Error in critique response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate critique response")

@app.post("/response/improved")
async def generate_improved_response(request: MessageRequest):
    try:
        participantId = request.participantId
        messages = get_recent_messages(participantId)
        initial_response = messages[-2]['content']  
        critique_response = messages[-1]['content']

        improved_response = chat_app.get_improved_response(initial_response, critique_response)
        if not improved_response:
            raise HTTPException(status_code=500, detail="Failed to generate improved response")

        # Process the improved response to check and replace invalid YouTube videos
        updated_improved_response = await process_improved_response(improved_response)

        # Store the updated improved response
        store_messages(participantId, "Improved Response", updated_improved_response)
        print("Stored improved response with valid YouTube video IDs")
        return {"response": updated_improved_response}

    except TypeError as e:
        print(f"TypeError in improved response: {e}")
        raise HTTPException(status_code=500, detail="Type error encountered while generating improved response")

    except Exception as e:
        print(f"Error in improved response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate improved response")

async def process_improved_response(improved_response: str) -> str:
    # Parse the improved response as JSON
    try:
        # Attempt to find JSON in the response
        json_match = re.search(r'```json([\s\S]*?)```', improved_response)
        if json_match:
            json_text = json_match.group(1).strip()
        else:
            json_text = improved_response.strip()
        
        if not isinstance(json_text, str):
            print("json_text is not a string.")
            return improved_response

        response_data = json.loads(json_text)
    except Exception as e:
        print(f"Error parsing improved_response: {e}")
        return improved_response 

    except json.JSONDecodeError:
        # If parsing fails, return the response as is
        print("Improved response is not valid JSON")
        return improved_response

    # Process the study plan
    if 'studyPlan' in response_data:
        study_plan = response_data['studyPlan']
        updated_study_plan = await check_and_replace_invalid_videos(study_plan)
        response_data['studyPlan'] = updated_study_plan
        # Convert back to JSON string
        updated_response_text = json.dumps(response_data, indent=2)
        return updated_response_text
    else:
        # If no study plan, return the response as is
        return improved_response

async def check_and_replace_invalid_videos(study_plan: dict) -> dict:
    print("THIS IS A STUDY PLAN", study_plan)
    for week_key, week_value in study_plan.items():
        for day in week_value:
            resources = day.get('resources', {})
            if 'YouTube' in resources:
                youtube_resources = resources['YouTube']
                if not isinstance(youtube_resources, list):
                    youtube_resources = [youtube_resources]
                updated_resources = []
                for resource in youtube_resources:
                    link = resource.get('link')
                    if not link or not YOUTUBE_URL_PATTERN.match(link):
                        print(f"Invalid YouTube URL detected: {link}")
                        topic = day.get('topic', '')
                        full_query = f"{topic} in studying overall topic"
                        similar_video = await search_similar_video(full_query)
                        if similar_video:
                            updated_resources.append(similar_video)
                            print(f"Replaced invalid video with {similar_video['link']}")
                        else:
                            updated_resources.append(resource)
                            print(f"No similar video found for topic: {topic}")
                    else:
                        video_id = extract_video_id(link)
                        is_valid = await check_video_validity(video_id)
                        if is_valid:
                            updated_resources.append(resource)
                        else:
                            topic = day.get('topic', '')
                            full_query = f"{topic} in studying overall topic"
                            similar_video = await search_similar_video(full_query)
                            if similar_video:
                                updated_resources.append(similar_video)
                                print(f"Replaced invalid video with {similar_video['link']}")
                            else:
                                updated_resources.append(resource)
                                print(f"No similar video found for topic: {topic}")
                resources['YouTube'] = updated_resources if len(updated_resources) > 1 else updated_resources[0]
                day['resources'] = resources
    return study_plan

async def check_video_validity(video_id: str) -> bool:
    if not video_id:
        return False
    api_key = None
    if youtube_api_keys:
        selected_key = random.choice(youtube_api_keys)
        api_key = os.getenv(selected_key)
    if not api_key:
        print("YouTube API key is not set")
        return False

    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=id"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 403:
                    print("Quota exceeded or access forbidden; try a different API key.")
                    return False
                elif resp.status != 200:
                    print(f"Error fetching video data: {resp.status}")
                    return False

                data = await resp.json()
                items = data.get('items', [])
                return len(items) > 0
        except Exception as e:
            print(f"Exception occurred while checking video validity: {e}")
            return False

async def search_similar_video(search_query: str) -> dict:
    # First attempt with full query
    response = await execute_search_query(search_query)
    if response:
        return response
    
    # Fallback with a simplified query
    simple_query = search_query.split(':')[0].split('-')[0].strip()
    response = await execute_search_query(simple_query)
    return response

async def execute_search_query(query: str) -> dict:
    url = f"{API_BASE_URL}/search_similar_videos"
    payload = {'search_message': query}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get('exists'):
                    items = data.get('items', [])
                    if items:
                        first_item = items[0]
                        video_id = first_item['id']['videoId']
                        title = first_item['snippet']['title']
                        link = f"https://www.youtube.com/watch?v={video_id}"
                        return {'title': title, 'link': link}
        except Exception as e:
            print(f"Error in search: {e}")
            return None
    return None

@app.post("/info")
async def generate_info_response(request: InfoRequest):
    try: 
        if not request.info_message:
            raise HTTPException(status_code=400, detail="No info message provided")
        else:
            response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant." 
                        "You will let the user know about the difference in background knowledge levels based on Bloom's taxonomy, especially: domain of knowledge levels. "
                        "Knowledge Level: At this level the teacher is attempting to determine whether the students can recognize and recall information. Example: What countries were involved in the War of 1812?"
                        "Here we have 4 levels of background knowledge ('absolute beginner', 'beginner', 'intermediate', 'advanced'). "
                        "Please be concise, with each description at most 2 bullet points. Start directly with the Level and description "
                        "Using table format below and make it easy to read. "
                        "| Level             | Description                                                                      |\n"
                        "|-------------------|----------------------------------------------------------------------------------|\n"
                        "| Absolute Beginner | - Description                                                                    |\n"
                        "|                   | - Description                                                                    |\n"
                        "|-------------------|----------------------------------------------------------------------------------|\n"
                        "| Beginner          | - Description                                                                    |\n"
                        "|                   | - Description                                                                    |\n"
                        "|-------------------|----------------------------------------------------------------------------------|\n"
                        "| Intermediate      | - Description                                                                    |\n"
                        "|                   | - Description                                                                    |\n"
                        "|-------------------|----------------------------------------------------------------------------------|\n"
                        "| Advanced          | - Description                                                                    |\n"
                        "|                   | - Description                                                                    |\n"
                    )
                },
                {"role": "user", "content": request.info_message}
            ],
            temperature=0.2,
            top_p=0.6,
            frequency_penalty=0.2,
            presence_penalty=0.1)

        response_received = response.choices[0].message.content
        return {"response": response_received}
    except Exception as e:
        print(f"Error: {str(e)}")

@app.post("/search")
async def generate_search_response(request: SearchRequest):
    search_message = request.search_message
    response_resources = get_search_response(search_message)
    return {"response": response_resources}

@app.post('/get_thumbnail')
async def get_thumbnail(request: YouTubeVideoID):
    video_id = request.video_id
    if not video_id:
        raise HTTPException(status_code=400, detail="No URL provided")

    thumbnail_url = get_video_thumbnail(video_id)
    if thumbnail_url:
        return {"thumbnail": thumbnail_url}
    else:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.post("/video_stats")
async def get_video_statistics(request: YouTubeVideoID):
    try:
        video_id = request.video_id
        stats = get_video_stats(video_id)
        if not stats:  # If stats are unavailable, fall back to similar videos
            similar_video = search_similar_videos(video_id)
            return {
                "views": similar_video.get("views", "N/A"),
                "likes": similar_video.get("likes", "N/A"),
                "thumbnail": similar_video.get("thumbnail", "https://via.placeholder.com/120"),
                "fallback": True
            }
        return {"views": stats['views'], "likes": stats['likes'], "fallback": False}
    except Exception as e:
        print(f"Error occurred while fetching video stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch video statistics")

@app.post("/search_similar_videos")
async def find_similar_videos(request: SearchRequest):
    search_message = request.search_message
    print("Finding similar videos for:", search_message)

    try:
        # Get a random API key
        selected_key = random.choice(youtube_api_keys)
        YOUTUBE_API_KEY = os.getenv(selected_key)

        # Call the search_similar_videos function from YouTube_request.py
        similar_video_response = search_similar_videos(search_message)

        # Check if a similar video was found
        if not similar_video_response.get("exists"):
            return {
                "exists": False,
                "message": "No similar videos found."
            }

        # Return details of the similar video found
        return {
            "exists": True,
            "items": [similar_video_response]
        }
    except Exception as e:
        print(f"Error finding similar videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar videos")


@app.post("/checkResource")
async def generate_check_response(request: CheckRequest):
    check_message = request.check_message
    research_query = request.research_query
    participantId = request.participantsId
    try:
        response_check = check_resource_availability(check_message, research_query)
        return {"response": response_check}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/plan-reasoning")
async def generate_plan_reasoning(request: PlanRequest):
    try:
        # Retrieve the most recent study plan from storage
        recent_messages = get_recent_messages(request.participantId)
        improved_response_message = None
        study_plan_response = None

        for i, msg in enumerate(recent_messages):
            if msg.get('content') == 'Improved Response' and msg.get('role') == 'user':
                improved_response_message = msg['content']
                if i + 1 < len(recent_messages) and recent_messages[i + 1].get('role') == 'assistant':
                    study_plan_response = recent_messages[i + 1]['content']
                break

        if not improved_response_message or not study_plan_response:
            raise HTTPException(status_code=404, detail="No 'Improved Response' message found")

        try:
            study_plan_response = json.loads(study_plan_response)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse study plan response as JSON")
        study_plan_overview = study_plan_response.get('studyPlan_Overview', {})
        study_plan_overview_str = json.dumps(study_plan_overview)
        response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. Please review the study plan provided and generate detailed explanations for each week, focusing on three distinct aspects: Learning Objectives, Content Selection, and Connection.\n"
                        "Your responses should demonstrate a thorough understanding of constructivist learning principles, including Andragogy which is the theory of adult learning by Knowles Malcolm and Constructivism by Jean Piaget. "
                        "Provide concise explanations in complete sentences and separate the reasoning into JSON format as follows:\n\n"
                        "1. Learning Objectives:\n"
                        "Clearly define measurable outcomes for learners."
                        "Ensure objectives are relevant to adult learners' needs for actionable and goal-oriented outcomes, aligning with principles of Andragogy. "
                        "Use specific verbs from Bloom's Taxonomy.\n"
                        "2. Content Selection:\n"
                        "Justify the selection of activities, topics, or resources based on their relevance, developmental appropriateness."
                        "Emphasize their alignment with Constructivism, focusing on building upon learners' prior experiences, encouraging exploration, and enabling active engagement. "
                        "Address how the content supports adult learners by being immediately relevant and practically useful (Andragogy).\n"
                        "3. Connection:\n"
                        "Explain how the content relates to previously covered material to ensure continuity and coherence."
                        "Highlight how this week’s content sets the foundation for subsequent learning, enabling gradual mastery and skill progression. "
                        "Focus on how the progression helps build a comprehensive understanding of the subject and supports gradual mastery.\n"                      
                        "Provide the response in this structured JSON format: "
                        "{\n"
                        "    \"Week1\": \"- Learning objective: Describe what learners will achieve this week, using Bloom's verbs.\n"
                        "               - Content selection: Explain why this specific content was chosen to meet the objective.\n"
                        "               - Connection: Describe how this week’s content prepares learners for the next week or builds on prior knowledge.\",\n"
                        "    \"Week2\": \"- Learning objective...\n"
                        "               - Content selection...\n"
                        "               - Connection...\n\",\n"
                        "    \"Week3\": \"- Learning objective...\n"
                        "               - Content selection...\n"
                        "               - Connection...\n\",\n"
                        "    \"Week4\": \"- Learning objective...\n"
                        "               - Content selection...\n"
                        "               - Connection...\n\"\n"
                        "}\n\n"
                        "For each section, ensure that:\n"
                        "- Learning Objectives: Are specific, measurable, and aligned with Bloom's Taxonomy.\n"
                        "- Content Selection: Reflects developmental appropriateness, relevance, and scaffolding techniques.\n"
                        "- Connection: Emphasizes how prior learning is reinforced and future learning is prepared for.\n"
                        "Do not mention theory explicitly in the results"
                    )
                },
                {"role": "user", "content": study_plan_overview_str}
            ],
            temperature=0.0,
            top_p=0.6,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        response_received = response.choices[0].message.content

        return {"response": response_received}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/topic-explanations")
async def generate_topic_explanation(request: UserMessageRequest):
    try:
        recent_messages = get_recent_messages(request.participantId)
        # Data - recent improved study plan
        improved_study_plan = None
        for message in reversed(recent_messages):
            # Check if this is the improved response containing 'studyPlan'
            if message.get("role") == "assistant" and isinstance(message.get("content"), dict):
                content = message["content"]
                if "studyPlan" in content:
                    improved_study_plan = content["studyPlan"]
                    break
        recent_plan = json.dumps(improved_study_plan) if improved_study_plan else "No study plan available."
        topic = request.user_message
        response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful assistant. Below is a study plan with specific topics." 
                        "For each topic, explain why the topic '{topic}' is important and essential. "
                        f"Please give concise answers using 3 bullet points in the context of this study plan '{recent_plan}'. "
                        "Please refer these guidance: "
                        "Explain how this topic aligns with Andragogy which is theory of adult learning by Knowles Malcolm. Describe how the topic meets learners at their current skill level and challenges them appropriately for growth."  
                        "Outline how this topic supports specific cognitive objectives using Bloom’s Taxonomy. Focus on how the topic enables students to build skills from foundational to advanced levels."
                        "Describe how this topic acts as a Jerome Bruner's theory of Scaffolding in Education for upcoming material, providing necessary skills or background knowledge. Highlight how it encourages Flavell's metacognition and self-regulated learning to foster independent learning and readiness for more complex topics."
                        f"Please respond with concise explanations for each topic using the above structure with 3 bullet points. Only provide **reason for study this '{topic}'** based on the theories; do not repeat the study plan content; do not mention theory explicitly in the results; be concise."
                        )
                    },
                    {"role": "user", "content": recent_plan}
            ],
            temperature=0.0,
            top_p=0.6,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        response_received = response.choices[0].message.content
        return {"explanation": response_received}        
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/generate-objectives")
async def generate_learning_objectives(request: UserMessageRequest):
    try:
        recent_messages = get_recent_messages(request.participantId)
        if not recent_messages:
            raise HTTPException(status_code=404, detail="No study plan found")

        # Data - recent improved study plan
        improved_study_plan = None
        for message in reversed(recent_messages):
            # Check if this is the improved response containing 'studyPlan'
            if message.get("role") == "assistant" and isinstance(message.get("content"), dict):
                content = message["content"]
                if "studyPlan" in content:
                    improved_study_plan = content["studyPlan"]
                    break
        recent_plan = json.dumps(improved_study_plan) if improved_study_plan else "No study plan available."
        topic = request.user_message

        # Generate the prompt for GPT-4o
        response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful assistant. Below is a study plan '{recent_plan}'. Please generate clear and concise learning objectives "
                        f"(at most 3) using Bloom's Taxonomy verbs for the topic '{topic}'. "
                        "Begin with the objectives immediately. Do not say 'Objectives for the topic' in the context of this study plan."
                    )
                },
                {"role": "user", "content": recent_plan}
            ],
            temperature=0.0,
            top_p=0.6,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        response_received = response.choices[0].message.content
        return {"objectives": response_received}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)