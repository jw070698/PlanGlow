#app.py

from fastapi import FastAPI, HTTPException
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
from components.Database import get_recent_messages, store_messages
from components.YouTube_request import get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability, get_video_stats
from components.GoogleSearch_request import google_search_availability

from dotenv import load_dotenv
load_dotenv()
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
    user_input: str = None

class InfoRequest(BaseModel):
    info_message: str

class SearchRequest(BaseModel):
    search_message: str

class YouTubeVideoID(BaseModel):
    video_id: str

class YouTubeLink(BaseModel):
    link_message: str

class CheckRequest(BaseModel):
    check_message: str

class UserMessageRequest(BaseModel):
    user_message: str

# A dictionary to store the most recent study plan
stored_plans = {}

def extract_topic(user_message):
    match = re.search(r'Create a study plan for a .* student on (.+?) using', user_message)
    if match:
        return match.group(1)
    return None

@app.post("/response")
async def generate_response(request: MessageRequest):
    if request.user_message:
        response_text = chat_app.chat(request.user_message)
        store_messages(request.user_message, response_text)  # Store user message & study plan
        stored_plans['last_plan'] = response_text  # Store the most recent plan
    elif request.user_input:
        response_text = chat_app.chat(request.user_input) 
        store_messages(request.user_input, response_text)  # Store user input & study plan
        stored_plans['last_plan'] = response_text  # Store the most recent plan
    else:
        response_text = 'No message'
    return {"response": response_text}


@app.post("/info")
async def generate_info_response(request: InfoRequest):
    try: 
        if not request.info_message:
            raise HTTPException(status_code=400, detail="No info message provided")
        else:
            response = client.chat.completions.create(model="gpt-4o", messages=[
                {"role": "system", "content": "You are a helpful assistant. You will let user know about the difference of background knowledge level of 'absolute beginner, beginner, intermediate, advanced' of the topic as a table. \
                    Please be concise, each description at most 2 bullet points. Please start directly with the Level and description using table format.\
                    Please be pretty, simple, and easy to read. \
                    For example, \
                    | Level             | Description                                                                 |\
                    |-------------------|-----------------------------------------------------------------------------|\
                    | Absolute Beginner | - No prior programming experience.                                          |\
                    |                   | - Unfamiliar with Python and data analysis concepts.                        |\
                    |-------------------|-----------------------------------------------------------------------------|\
                    | Beginner          | - Basic understanding of Python syntax and simple scripts.                  |\
                    |                   | - Familiar with basic data structures (lists, dictionaries).                |\
                    |-------------------|-----------------------------------------------------------------------------|\
                    | Intermediate      | - Comfortable with Python libraries like Pandas and NumPy.                  |\
                    |                   | - Can perform basic data manipulation and visualization.                    |\
                    |-------------------|-----------------------------------------------------------------------------|\
                    | Advanced          | - Proficient in using advanced libraries (e.g., SciPy, Scikit-learn).       |\
                    |                   | - Capable of complex data analysis, machine learning, and optimization.     |\
                    |-------------------|-----------------------------------------------------------------------------|"},
                {"role": "user", "content": request.info_message}
            ], temperature=0)
            response_received = response.choices[0].message.content
            return {"response": response_received}
    except Exception as e:
        print(f"Error: {str(e)}")

@app.post("/search")
async def generate_search_response(request: SearchRequest):
    search_message = request.search_message
    response_resources = get_search_response(search_message)
    return {"response": response_resources}

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
async def generate_plan_reasoning(request: InfoRequest):
    try:
        # Retrieve the most recent study plan from storage
        recent_messages = get_recent_messages()
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
        recent_plan = stored_plans.get('last_plan', None)        
        if not recent_plan:
            raise HTTPException(status_code=404, detail="No study plan found")
        # Extract the topic from the request
        print("request",request)
        topic = request.user_message
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided in the request")
        # Generate the prompt for GPT-4o
        prompt = (
            f"You are a helpful assistant. Below is a study plan. Please explain why the topic '{topic}' is important. Please give concise answers with using 3 bullet points."
            f"in the context of this study plan.\n\nStudy Plan: {recent_plan}. Just give the explanation. Do not give the study plan" 
        )
        # Use GPT to generate an explanation for the topic in the study plan
        response = chat_app.chat(prompt)         
        # Return the generated explanation
        return {"explanation": response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/generate-objectives")
async def generate_learning_objectives(request: UserMessageRequest):
    try:
        # Retrieve the most recent study plan
        recent_plan = stored_plans.get('last_plan', None)
        if not recent_plan:
            raise HTTPException(status_code=404, detail="No study plan found")
        # Extract the topic from the request
        topic = request.user_message
        if not topic:
            raise HTTPException(status_code=400, detail="No topic provided in the request")
        # Generate the prompt for GPT-4o
        prompt = (
            f"You are a helpful assistant. Below is a study plan. Please generate clear and concise learning objectives one by one at most 3. Please start directly with the objectives. Begin with the objectives immediately. Do not say 'Objectives for the topic 'xxx':'"
            f"for the topic '{topic}' in the context of this study plan.\n\nStudy Plan: {recent_plan}"
        )
        # Use GPT to generate learning objectives for the topic in the study plan
        response = chat_app.chat(prompt)
        
        # Return the generated learning objectives
        return {"objectives": response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)