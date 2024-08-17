#app.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re, os
from openai import OpenAI
from src.components.OpenAI_request import ChatApp
# from src.components.Database import get_recent_messages, store_messages
from src.components.YouTube_request import get_search_response, get_video_info, info_to_dict, extract_video_id, get_video_thumbnail, check_resource_availability
from src.components.GoogleSearch_request import google_search_availability

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

class YouTubeLink(BaseModel):
    link_message: str

class CheckRequest(BaseModel):
    check_message: str

class CheckRequestBlog(BaseModel):
    check_message_blog: str

def extract_topic(user_message):
    match = re.search(r'Create a study plan for a .* student on (.+?) using', user_message)
    if match:
        return match.group(1)
    return None


@app.post("/response")
async def generate_response(request: MessageRequest):
    if request.user_message:
        response_text = chat_app.chat(request.user_message)
        # store_messages(request.user_message,response_text) # Store user message & study plan
    elif request.user_input:
        response_text = chat_app.chat(request.user_input) 
        # store_messages(request.user_input,response_text) # Store user input & study plan
        print("Received user_input")
    else:
        response_text = 'No message'
    return {"response": response_text}

@app.post("/info")
async def generate_info_response(request: InfoRequest):
    print(f"Received info_message: {request.info_message}")
    try: 
        if not request.info_message:
            raise HTTPException(status_code=400, detail="No info message provided")
        else:
            response = client.chat.completions.create(model="gpt-4o", messages=[
                {"role": "system", "content": "You are a helpful assistant. You will let user know about the difference of background knowledge level of 'absolute beginner, beginner, intermediate, advanced' of the topic as a table. Please be concise."},
                {"role": "user", "content": request.info_message}
            ])
            response_received = response.choices[0].message.content
            print(response_received)
            return {"response": response_received}
    except Exception as e:
        print(f"Error: {str(e)}")

@app.post("/search")
async def generate_search_response(request: SearchRequest):
    search_message = request.search_message
    response_resources = get_search_response(search_message)
    return {"response": response_resources}

@app.post("/thumbnails")
async def generate_thumbnails(request: YouTubeLink):
    try:
        link_message = request.link_message
        response_thumbnail = get_video_thumbnail(link_message)
        if response_thumbnail:
            return {"response": response_thumbnail}
        else:
            return {"response": 'none'}
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"response": 'none', "error": str(e)}

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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)