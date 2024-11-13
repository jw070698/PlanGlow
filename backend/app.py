#app.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, os, json
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

from components.OpenAI_request import ChatApp
from components.Database import db, create_session, store_messages, get_recent_messages
from components.YouTube_request import get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability, get_video_stats
from components.GoogleSearch_request import google_search_availability

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
        initial_response = messages[-2]['content']  # Assuming the last two entries are initial and critique
        critique_response = messages[-1]['content']

        improved_response = chat_app.get_improved_response(initial_response, critique_response)
        if improved_response:
            store_messages(participantId, "Improved Response", improved_response)
            print("Stored improved response")
        else:
            print("No improved response.")
        return {"response": improved_response}

    except Exception as e:
        print(f"Error in improved response: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate improved response")


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
                        "You are a helpful assistant. You will let the user know about the difference in background knowledge levels "
                        "('absolute beginner', 'beginner', 'intermediate', 'advanced') for the topic as a table. "
                        "Please be concise, with each description at most 2 bullet points. Start directly with the Level and description "
                        "using table format. "
                        "Please be pretty, simple, and easy to read."
                        "\n\n"
                        "For example:\n"
                        "| Level             | Description                                                                 |\n"
                        "|-------------------|-----------------------------------------------------------------------------|\n"
                        "| Absolute Beginner | - No prior programming experience.                                          |\n"
                        "|                   | - Unfamiliar with Python and data analysis concepts.                        |\n"
                        "|-------------------|-----------------------------------------------------------------------------|\n"
                        "| Beginner          | - Basic understanding of Python syntax and simple scripts.                  |\n"
                        "|                   | - Familiar with basic data structures (lists, dictionaries).                |\n"
                        "|-------------------|-----------------------------------------------------------------------------|\n"
                        "| Intermediate      | - Comfortable with Python libraries like Pandas and NumPy.                  |\n"
                        "|                   | - Can perform basic data manipulation and visualization.                    |\n"
                        "|-------------------|-----------------------------------------------------------------------------|\n"
                        "| Advanced          | - Proficient in using advanced libraries (e.g., SciPy, Scikit-learn).       |\n"
                        "|                   | - Capable of complex data analysis, machine learning, and optimization.     |\n"
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

    # Assuming get_video_thumbnail is your function to retrieve the thumbnail
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
        return {"views": stats['views'], "likes": stats['likes']}
    except Exception as e:
        print(f"Error occurred while fetching video stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch video statistics")

@app.post("/checkResource")
async def generate_check_response(request: CheckRequest):
    check_message = request.check_message
    print("Received request for /checkResource")
    try:
        response_check = check_resource_availability(check_message)
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

        study_plan_overview = study_plan_response.get('studyPlan_Overview', {})
        study_plan_overview_str = json.dumps(study_plan_overview)
        print(study_plan_overview_str)
        response = client.with_options(timeout=120.0).chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. Please review the study plan provided and explain how you selected the content for each week. "
                        "Do not show me the study plan in your answer. Just explain how you select and mention the connections between the content for each week."
                        "Each explanation should clarify the purpose of that week's content and how it builds on prior learning."
                        "Should use Bloom's Taxonomy verbs for Learning objectives"
                        "Provide concise explanations in complete sentences. "
                        "Separate your reason by each week json type: "
                        "{\n"
                        "    \"Week1\": \"- Learning objective...\n - Content selection...\n - Connection...\n\",\n"
                        "    \"Week2\": \"- Learning objective...\n - Content selection...\n - Connection...\n\",\n"
                        "    \"Week3\": \"- Learning objective...\n - Content selection...\n - Connection...\n\",\n"
                        "    \"Week4\": \"- Learning objective...\n - Content selection...\n - Connection...\n\"\n"
                        "}\n\n"

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
        print(response_received)

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
                        f"You are a helpful assistant. Below is a study plan. Please explain why the topic '{topic}' is important. "
                        f"Please give concise answers using 3 bullet points in the context of this study plan '{recent_plan}'. "
                        "Just give the explanation. Do not give the study plan."                    )
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