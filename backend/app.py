#app.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, os, json, aiohttp, random
from urllib.parse import urlparse, parse_qs
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore, auth
from components.YouTube_request import search_similar_videos

# Initialize Firebase Admin SDK
# cred = credentials.Certificate("serviceAccountKey.json")

service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

from components.OpenAI_request import ChatApp
from components.Database import db, create_session, store_messages, get_recent_messages
from components.YouTube_request import search_similar_videos, get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability, get_video_stats
from components.GoogleSearch_request import google_search_availability


from dotenv import load_dotenv
load_dotenv()
youtube_api_keys = [k for k in os.environ if k.startswith("YOUTUBE_API_KEY")]
YOUTUBE_URL_PATTERN = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")

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
        # Database
        participantId = request.participantId
        session_ref = db.collection("messages").document(participantId)
        if not session_ref.get().exists:
            create_session(participantId)
            print("Session created for", participantId)
        else:
            print("Session already exists for", participantId)

        user_chat = None
        # Separate user_message and user_chat
        user_message = request.user_message
        if user_message and user_message.startswith("Create a study plan for a"):
            # Treat as user_message
            print("Detected as user_message:", user_message)
        else: 
            user_chat = user_message

        # If chatting,
        if user_chat:
            print("Chatting")
            session_ref.set({"user_input": user_chat}, merge=True)
            response_chat = chat_app.chat_response(user_chat, participantId)
            if not response_chat:
                raise HTTPException(status_code=500, detail="Failed to generate improved response")
                
            # Process the improved response to check and replace invalid YouTube videos
            updated_improved_response = await process_improved_response(user_chat, response_chat)

            # Store the updated improved response
            
            store_messages(participantId, user_chat, updated_improved_response)
            print("Stored improved response with valid YouTube video IDs")
            print(updated_improved_response)
            return {"response": updated_improved_response}
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        print("Submitted")
        # Step 1
        # Generate response and store it
        response_text = chat_app.chat(user_message)
        if not response_text:
            raise HTTPException(status_code=500, detail="No response received from OpenAI")
        
        # Store the message and response in Firestore (append to history)
        store_messages(participantId, user_message, response_text)
        session_ref.set({"user_message": user_message}, merge=True)
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
        session_ref = db.collection("messages").document(participantId)
        user_message = request.user_message or session_ref.get().to_dict().get("user_message")
        print("USER MESSAGE in /response/improved", user_message)

        messages = get_recent_messages(participantId)
        initial_response = messages[-2]['content']  
        critique_response = messages[-1]['content']

        improved_response = chat_app.get_improved_response(user_message, initial_response, critique_response)
        if not improved_response:
            raise HTTPException(status_code=500, detail="Failed to generate improved response")
            
        print("START UPDATED IMPROVED RESPONSE")
        # Process the improved response to check and replace invalid YouTube videos
        updated_improved_response = await process_improved_response(user_message, improved_response)

        # Store the updated improved response
        store_messages(participantId, "Improved Response", updated_improved_response)
        print("Stored improved response with valid YouTube video IDs")
        print(updated_improved_response)
        return {"response": updated_improved_response}

    except TypeError as e:
        print(f"TypeError in improved response: {e}")
        raise HTTPException(status_code=500, detail="Type error encountered while generating improved response")

    except Exception as e:
        print(f"Error in improved response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate improved response")

async def process_improved_response(user_message: str, improved_response: str) -> str:
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

    except json.JSONDecodeError:
        # If parsing fails, return the response as is
        print("Improved response is not valid JSON")
        return improved_response
    except Exception as e:
        print(f"Error parsing improved_response: {e}")
        return improved_response 

    # Process the study plan
    if 'studyPlan' in response_data:
        study_plan = response_data['studyPlan']
        print("before calling check_and_replace_invalid_videos")
        updated_study_plan = await check_and_replace_invalid_videos(user_message, study_plan)
        response_data['studyPlan'] = updated_study_plan
        # Convert back to JSON string
        updated_response_text = json.dumps(response_data, indent=2)
        return updated_response_text
    else:
        # If no study plan, return the response as is
        return improved_response

async def check_and_replace_invalid_videos(user_message: str, study_plan: dict) -> dict:
    print("THIS IS A STUDY PLAN", study_plan)
    invalid_urls_cache = set()
    resources_sumup = []

    for week_key, week_value in study_plan.items():
        for day in week_value:
            resources = day.get('resources', {})
            if 'YouTube' in resources:
                youtube_resources = resources['YouTube']
                if not isinstance(youtube_resources, list):
                    youtube_resources = [youtube_resources]

                for idx, resource in enumerate(youtube_resources):
                    link = resource.get('link')
                    if link in invalid_urls_cache:
                        continue  # Skip URLs that have already been processed

                    try:
                        video_id = extract_video_id(link)
                    except Exception as e:
                        print(f"Error extracting video ID from {link}: {e}")
                        video_id = None

                    # Check if the video is valid
                    if link and video_id and await check_video_validity(video_id):
                        resources_sumup.append(resource)
                        continue  # Valid video, move to next resource

                    # Invalid links
                    print(f"Invalid YouTube URL detected: {link}")
                    invalid_urls_cache.add(link)

                    topic = day.get('topic', '')

                    # Loop to find a unique replacement video
                    max_attempts = 5  # Limit to avoid infinite loops
                    attempts = 0
                    while attempts < max_attempts:
                        similar_video = await find_replacement_video(user_message, topic)
                        attempts += 1

                        if similar_video:
                            similar_link = similar_video.get('link')
                            # Check if the similar video's link is already in resources_sumup
                            if any(res.get('link') == similar_link for res in resources_sumup):
                                print("It already exists, trying to find another video...")
                                continue  # Try to find another video
                            else:
                                youtube_resources[idx] = similar_video  # Replace invalid with valid
                                print(f"Replaced invalid video with {similar_video['link']}")
                                resources_sumup.append(similar_video)
                                break  # Found a unique video, exit loop
                        else:
                            print(f"No similar video found for topic: {topic}")
                            break  # Exit loop if no video found

                    else:
                        # If max_attempts reached without finding a unique video
                        print(f"Could not find a unique replacement video for topic: {topic}")
                        # youtube_resources[idx] = None  # Remove invalid resource

                # Clean up None entries from youtube_resources
                youtube_resources = [res for res in youtube_resources if res is not None]
                resources['YouTube'] = youtube_resources
                day['resources'] = resources

    print("All resources collected:", resources_sumup)
    return study_plan




async def find_replacement_video(user_message:str, topic: str) -> dict:
    # Finds a similar video for the given topic by querying the search function.
    print("USER MESSAGE IN FIND_REPLACEMENT_VIDEO", user_message)
    proficiency_match = re.search(r"(Novice|Advanced Beginner|Competence|Proficiency|Expertise|Mastery)", user_message, re.IGNORECASE)
    proficiency = proficiency_match.group(1) if proficiency_match else "unknown level"
    topic_match = re.search(r"on (\w+)", user_message, re.IGNORECASE)
    extracted_topic = topic_match.group(1) if topic_match else "unknown topic"
    duration_match = re.search(r"over (\d+) months?, (\d+) weeks?, and (\d+) days?", user_message, re.IGNORECASE)
    duration = {
        "months": int(duration_match.group(1)) if duration_match else 0,
        "weeks": int(duration_match.group(2)) if duration_match else 0,
        "days": int(duration_match.group(3)) if duration_match else 0
    }
    hours_match = re.search(r"(\d+) hours? available per day", user_message, re.IGNORECASE)
    hours_per_day = int(hours_match.group(1)) if hours_match else 0
    full_query = f"{topic} in {extracted_topic} for a {proficiency} in {hours_per_day} hours"

    result = await search_similar_video(full_query)
    if result:
        return result

    return None


async def check_video_validity(video_id: str) -> bool:
    if not video_id:
        return False
    api_key = None
    if youtube_api_keys:
        selected_key = random.choice(youtube_api_keys)
        api_key = os.getenv(selected_key)
    if not api_key:
        return False

    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=id"
    async with aiohttp.ClientSession() as session:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 403:
                        print("Quota exceeded or access forbidden.")
                        return False
                    elif response.status != 200:
                        print(f"HTTP error: {response.status}")
                        return False

                    data = await response.json()
                    items = data.get("items", [])
                    return len(items) > 0
        except Exception as e:
            print(f"Error while checking video validity: {e}")
            return False


async def search_similar_video(search_query: str) -> dict:
    # First attempt with full query
    response = await execute_search_query(search_query)
    if response:
        return response
    return None

async def execute_search_query(query: str) -> dict:
    try:
        # Directly call the function that searches for similar videos
        similar_video_response = search_similar_videos(query)
        if similar_video_response.get('exists'):
            video_id = similar_video_response.get('videoId')
            title = similar_video_response.get('title')
            link = f"https://www.youtube.com/watch?v={video_id}"
            return {'title': title, 'link': link}
        else:
            print(f"No video found for query: {query}")
            return None
    except Exception as e:
        print(f"Error in search: {e}")
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
                        "You are a helpful assistant to explain background knowledge based on the subject that users want to study. " 
                        "Here we have 6 levels of background expertise ('novice', 'advanced beginner', 'competence', 'proficiency', 'expertise', 'mastery'). "
                        "1. Novice: Novices rely heavily on context-free rules and step-by-step instructions. Their performance tends to be slow, clumsy, and requires conscious effort. Novices struggle to adapt when situations don't align with the instructions. A novice cook strictly follows recipe measurements and timing, regardless of variations in ingredients or peculiarities of the oven. A novice driver might rigidly maintain speed limits without considering traffic flow or the presence of pedestrians. Novices have a detached approach to outcomes. To progress, novices need to keep gaining experience and making mistakes in a variety of situations.\n"
                        "2. Advanced Beginner: Advanced beginners recognize situation-specific nuances and can apply experience-based maxims beyond general rules. For instance, an advanced beginner cook might adjust heat based on the smell and look of the food as it is cooking rather than just the instructions in the recipe. They have had enough experience to recognize the smell of burning oil and can now apply the maxim that “the smell of burning oil usually means the heat is too high.”  An advanced beginner chess player begins to recognize such aspects of situation such as \'weakened king’s side\' and can apply the maxim to \'attack a weakened king\’s side.\' The performance of an advanced beginner is more sophisticated than novice, but it is still analytical. They continue to struggle with unfamiliar situations. At the same time, they begin to feel more emotionally engaged, often becoming overwhelmed or frustrated. Progression requires building further emotional involvement and commitment to outcomes.\n"
                        "3. Competence: Competent performers choose specific goals and adopt an overall perspective on what their situation calls for. A competent cook can choose to have the cold dishes ready before the hot ones. A competent chess player could choose an attacking strategy, focusing on the moves and pieces that support this plan. Success and failure now partially depend on the performer’s choice of perspective and not just on how well they follow rules. This leads to higher emotional involvement, with competent performers feeling joy or regret according to the outcomes. While more fluid than advanced beginners, competent performance still proceeds by analysis, calculation, and deliberate rule-following. Competent performers show improved coordination and anticipation but may rigidly stick to chosen perspectives even when circumstances change. To advance to proficiency, more risks need to be taken with letting go of rules and procedures while trusting one’s emerging intuition.\n" 
                        "4. Proficiency: Proficient performers intuitively grasp what a situation calls for but consciously decide responses. When a perspective intuitively occurs to them, proficient nurses can instantly sense a patient\'s deterioration before vital signs change. However, they then deliberately consider treatment options. Proficient drivers instinctively tell they\'re going too fast on a rainy curve but then consciously decide whether to brake or decelerate. Proficient performers adapt better to changing circumstances but still rely on rule-based decision-making for actions. The transition to expertise requires further letting go of rules and procedures while gaining more direct experience learning which intuited perspectives work in which kind of situation.\n"
                        "5. Expertise: Experts demonstrate seamless integration of perception and action. An expert chef creates dishes without recipes, intuitively adjusting techniques and ingredients based on specific circumstances. Expert drivers intuitively lift their foot off the accelerator rather than braking. Their performance happens without deliberation or decision-making. Experts often struggle to precisely explain their actions. When circumstances abruptly change, experts smoothly adapt and shift perspectives in a \"reflexive reorientation.\" For example, expert nurses constantly attend to subtle transitions in a patient’s condition. They intuitively shift perspectives and initiate a corresponding shift in treatment when solicited by transitions in the patient’s condition.\n"
                        "6. Mastery:  Masters seek to expand and refine their repertoire of intuitive perspectives. In doing so, they sometimes create new possibilities of performing and transform the style of their domain. For example, Cézanne expanded the possibilities for the painting of form and perspective, Stephen Curry altered the style of play in basketball by making the 3-point shot central rather than marginal, and B.B. King transformed the space of possibilities in music by harnessing the previously marginal capacity of the electric guitar to sustain notes. Masters identify overlooked aspects of a practice and experiment with new approaches, accepting short-term drops in particular performances for long-term expansions in their intuition.\n"
                        "Format your response as a clean **HTML <table>**."
                        "The table should have two columns: Level and Description."
                        "Using table format below and make it easy to read." 
                        "Each description should contain bullet points inside an unordered list (`<ul><li>…</li></ul>`)."
                        "Each sentence starts with a new bullet point."
                        "Be concise."
                        "Use proper HTML tags and indentation."
                        "Here are the 6 levels to include:\
                        - Novice\
                        - Advanced Beginner\
                        - Competence\
                        - Proficiency\
                        - Expertise\
                        - Mastery\
                        Start directly with `<table>...</table>`, and make sure the output is valid HTML."
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

        return similar_video_response

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
                        f"You are a helpful assistant. Please review the study plan provided based on {study_plan_response} and generate detailed explanations for each week, focusing on three distinct aspects: Learning Objectives, Content Selection, and Connection.\n"
                        "Provide concise explanations in complete sentences and separate the reasoning into JSON format as follows:\n\n"
                        "1. Learning Objectives: Your task is to generate clear and concise learning objectives for each week using Bloom's Taxonomy.\n\
                            Please refer these guidance: these 6 levels can be used to structure the learning outcomes, lessons, and assessments of your course.\
                            1) Remembering: Retrieving, recognizing, and recalling relevant knowledge from long‐term memory.\
                            2) Understanding: Constructing meaning from oral, written, and graphic messages through interpreting, exemplifying, classifying, summarizing, inferring, comparing, and explaining.\
                            3) Applying: Carrying out or using a procedure for executing, or implementing.\
                            4) Analyzing: Breaking material into constituent parts, determining how the parts relate to one another and to an overall structure or purpose through differentiating, organizing, and attributing.\
                            5) Evaluating: Making judgments based on criteria and standards through checking and critiquing.\
                            6) Creating: Putting elements together to form a coherent or functional whole; reorganizing elements into a new pattern or structure through generating, planning, or producing.\
                            Bloom’s is hierarchical, meaning that learning at the higher levels is dependent on having attained prerequisite knowledge and skills at lower levels.\
                            How Bloom’s can aid in study plan design? Bloom’s taxonomy is a powerful tool to help develop learning outcomes because it explains the process of learning:\
                                1) Before you can understand a concept, you must remember it.\
                                2) To apply a concept you must first understand it.\
                                3) In order to evaluate a process, you must have analyzed it.\
                                4) To create an accurate conclusion, you must have completed a thorough evaluation.\
                                However, we don’t always start with lower order skills and step all the way through the entire taxonomy for each concept you present in your course. That approach would become tedious–for both you and your students! Instead, start by considering the level of learners in your course:\
                                    - Is this an “Introduction to…” course? If so, many your learning outcomes may target the lower order Bloom’s skills, because your students are building foundational knowledge. However, even in this situation we would strive to move a few of your outcomes into the applying and analyzing level, but getting too far up in the taxonomy could create frustration and unachievable goals.\
                                    - Do your students have a solid foundation in much of the terminology and processes you will be working on your course? If so, then you should not have many remembering and understanding level outcomes. You may need a few, for any radically new concepts specific to your course. However, these advanced students should be able to master higher-order learning objectives. Too many lower level outcomes might cause boredom or apathy.\
                            Steps towards writing effective learning outcomes:\
                                1) Make sure there is one measurable verb in each objective.\
                                2) Each outcome needs one verb. Either a student can master the outcome , or they fail to master it. If an outcome has two verbs (say, define and apply), what happens if a student can define, but not apply? Are they demonstrating mastery?\
                                3) Ensure that the verbs in the course level outcome are at least at the highest Bloom’s Taxonomy as the highest lesson level outcomes that support it. (Because we can’t verify they can evaluate if our lessons only taught them (and assessed) to define.)\
                                4) Strive to keep all your learning outcomes measurable, clear and concise."
                        "2. Content Selection:\n"
                            "Justify the reasons for the selection of resources based on the following:\
                                1) Personalization: Resources should match the learner's current abilities and gradually introduce complexity\
                                2) Diversity and Accessibility: Easy access through platforms ensures flexibility.\
                                3) Engagement and Interactivity: Interactive elements like quizzes, discussions, and hands-on exercises increase retention and understanding.\
                                4) Quality Content: Resources should be accurate, well-structured, and created by credible experts.\
                                5) Encouraging Potential: Content should not be too easy or too difficult; it must push learners slightly beyond their comfort zone to foster growth without overwhelming them.\
                                6) Alignment with Goals: Resources should be relevant to the learner's academic, professional, or personal objectives."
                        "3. Connection:\n"
                            "Explain how the content relates to previously covered material to ensure continuity and coherence.\
                            Focus on an aligned approach to planning and implementing strategies where all elements—goals, actions, resources, and assessments—are interconnected and mutually reinforcing."
                            "Highlight how this week’s content sets the foundation for subsequent learning, enabling skill progression. "
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
                        "For each section, ensure that do not mention theory explicitly in the results"
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
                        f"You are a helpful assistant to explain why the topic '{topic}' is important and essential in the context of this study plan '{recent_plan}'.\n"
                        "Please provide accurate and relevant explanations for the reasons for studying each topic by referring to these guidelines:\
                            - To direct and assist the student in learning the content of each assignment, it is useful first to consider the learning needs of students in studying an assignment and, hence, to examine what functions various components might play in fulfilling these needs.\
                            - Orientation: It is beneficial for students to begin studying an assignment with a general idea of what they will encounter in the assignment. \
                            This approach is ingrained in contemporary educational thinking and supported by research on learning (Hartley and Davis, 1976). Ausubel (1968) has strongly argued that a preliminary framework of what is to come—what he calls an \"advance organizer\"—can greatly facilitate learning, and he has demonstrated its practical utility.\
                            A general framework sets the scope of the assignment and shows how it fits into the overall course. It also illustrates how the topics within the assignment are partitioned and interrelated. Furthermore, it can highlight the relevance of the assignment for the student.\
                            Another aspect of orientation is goal-setting. It is helpful for students to be aware of the goals they are expected to achieve while studying an assignment (Melton, 1978). \
                            This awareness enables them to focus their efforts on reaching those goals and helps them maintain perspective on their learning progress throughout the assignment. \
                            Consider the contrast between goal-directed study and a situation where the student is unsure of the relative importance of different parts of the assignment content. \
                            Goal awareness leads to more organized study and improved learning outcomes for the student (Duchastel and Merrill, 1973)."
                        f"Only provide **reason for study this '{topic}'**; Do not repeat the study plan content; Do not mention theory explicitly in the results; Be concise, as fewer as possible."
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
                        f"You are a helpful assistant. This is a study plan with specific topics: '{recent_plan}'." 
                        f"Your task is to generate clear and concise learning objectives with as fewer points as possible for the topic '{topic}' using Bloom's Taxonomy."                    
                        "Please refer these guidance: these 6 levels can be used to structure the learning outcomes, lessons, and assessments of your course.\
                            1. Remembering: Retrieving, recognizing, and recalling relevant knowledge from long‐term memory.\
                            2. Understanding: Constructing meaning from oral, written, and graphic messages through interpreting, exemplifying, classifying, summarizing, inferring, comparing, and explaining.\
                            3. Applying: Carrying out or using a procedure for executing, or implementing.\
                            4. Analyzing: Breaking material into constituent parts, determining how the parts relate to one another and to an overall structure or purpose through differentiating, organizing, and attributing.\
                            5. Evaluating: Making judgments based on criteria and standards through checking and critiquing.\
                            6. Creating: Putting elements together to form a coherent or functional whole; reorganizing elements into a new pattern or structure through generating, planning, or producing."
                        "Bloom’s is hierarchical, meaning that learning at the higher levels is dependent on having attained prerequisite knowledge and skills at lower levels."
                        "How Bloom’s can aid in study plan design? Bloom’s taxonomy is a powerful tool to help develop learning outcomes because it explains the process of learning:\
                            1. Before you can understand a concept, you must remember it.\
                            2. To apply a concept you must first understand it.\
                            3. In order to evaluate a process, you must have analyzed it.\
                            4. To create an accurate conclusion, you must have completed a thorough evaluation.\
                            However, we don’t always start with lower order skills and step all the way through the entire taxonomy for each concept you present in your course. That approach would become tedious–for both you and your students! Instead, start by considering the level of learners in your course:\
                                - Is this an “Introduction to…” course? If so, many your learning outcomes may target the lower order Bloom’s skills, because your students are building foundational knowledge. However, even in this situation we would strive to move a few of your outcomes into the applying and analyzing level, but getting too far up in the taxonomy could create frustration and unachievable goals.\
                                - Do your students have a solid foundation in much of the terminology and processes you will be working on your course? If so, then you should not have many remembering and understanding level outcomes. You may need a few, for any radically new concepts specific to your course. However, these advanced students should be able to master higher-order learning objectives. Too many lower level outcomes might cause boredom or apathy."
                        "Steps towards writing effective learning outcomes:\
                            1. Make sure there is one measurable verb in each objective.\
                            2. Each outcome needs one verb. Either a student can master the outcome , or they fail to master it. If an outcome has two verbs (say, define and apply), what happens if a student can define, but not apply? Are they demonstrating mastery?\
                            3. Ensure that the verbs in the course level outcome are at least at the highest Bloom’s Taxonomy as the highest lesson level outcomes that support it. (Because we can’t verify they can evaluate if our lessons only taught them (and assessed) to define.)\
                            4. Strive to keep all your learning outcomes measurable, clear and concise."
                        "Validate whether these learning objectives can be achieved within the hours the user wants to study. If not, reduce them."                        
                        "Must include only learning objectives. Numbering all learning objectives."
                        "For example, \
                            1. learning objective\
                            2. learning objective\
                            ..."
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