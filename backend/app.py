#app.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, os
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

from components.OpenAI_request import ChatApp
from components.Database import create_session, store_messages, get_recent_messages
from components.YouTube_request import get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability, get_video_stats
from components.GoogleSearch_request import google_search_availability

#from dotenv import load_dotenv
#load_dotenv()
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

chat_app = ChatApp()

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

def extract_topic(user_message):
    match = re.search(r'Create a study plan for a .* student on (.+?) using', user_message)
    if match:
        return match.group(1)
    return None

@app.post("/response")
async def generate_response(request: MessageRequest):
    try:
        participantId = request.participantId
        create_session(participantId)
        print("session created to", participantId)
        if request.user_message:
            response_text = chat_app.chat(request.user_message)
            store_messages(participantId, request.user_message, response_text)  # Store user message & study plan
        elif request.user_input:
            response_text = chat_app.chat(request.user_input) 
            store_messages(participantId, request.user_input, response_text) # Store user input & study plan
        else:
            response_text = 'No message'
        if not response_text:
            raise HTTPException(status_code=500, detail="No response received from OpenAI")

        return {"response": response_text}
    except HTTPException as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except Exception as e:
        # General error logging
        print(f"Unexpected error occurred in /response endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

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
        print(thumbnail_url)
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
        recent_messages = get_recent_messages(request.custom_id)
        if not recent_messages:
            raise HTTPException(status_code=404, detail="No recent messages found")

        recent_plan = recent_messages[-1]['content']

        prompt = (
            f"You are a helpful assistant. Please review the study plan provided and explain how you selected the content for each week. "
            f"Do not show me the study plan in your answer. Just explain how you select and mention the connections between the content for each week."
            f"\n\nStudy Plan: {recent_plan}"
        )
        # Call the GPT-4 API with the prompt
        response = chat_app.chat(prompt)  
        # Return the GPT-4 response
        return {"response": response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/topic-explanations")
async def generate_topic_explanation(request: UserMessageRequest):
    try:
        # Retrieve the most recent study plan
        recent_messages = get_recent_messages(request.custom_id)
        if not recent_messages:
            raise HTTPException(status_code=404, detail="No study plan found")

        recent_plan = recent_messages[-1]['content']

        # Extract the topic from the request
        topic = request.user_message
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided in the request")

        # Generate the prompt for GPT-4o
        prompt = (
            f"You are a helpful assistant. Below is a study plan. Please explain why the topic '{topic}' is important. Please give concise answers using 3 bullet points."
            f"in the context of this study plan.\n\nStudy Plan: {recent_plan}. Just give the explanation. Do not give the study plan"
        )
        response = chat_app.chat(prompt)
        return {"explanation": response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/generate-objectives")
async def generate_learning_objectives(request: UserMessageRequest):
    try:
        recent_messages = get_recent_messages(request.custom_id)
        if not recent_messages:
            raise HTTPException(status_code=404, detail="No study plan found")

        recent_plan = recent_messages[-1]['content']

        # Extract the topic from the request
        topic = request.user_message
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided in the request")

        # Generate the prompt for GPT-4o
        prompt = (
            f"You are a helpful assistant. Below is a study plan. Please generate clear and concise learning objectives (at most 3) using Bloom's Taxonomy verbs. "
            f"Begin with the objectives immediately. Do not say 'Objectives for the topic 'xxx':' for the topic '{topic}' in the context of this study plan.\n\nStudy Plan: {recent_plan}"
        )
        response = chat_app.chat(prompt)
        return {"objectives": response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)