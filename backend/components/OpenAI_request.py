from openai import OpenAI
import sys
import os
import json
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("API_KEY1")
client = OpenAI(api_key=api_key)

class ChatApp:
    def __init__(self):
        self.client = client
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant to create study plans based on user's needs and preference. \
            If user asks create study plans or change plan, try to suggest best possible fit in terms of time limitation, type of resources, their knowledge base.\
            Show the overview of the generated plans, and then detailed daily plans. \
            The recommended resources should be with accessible and available links, and the one that came out before shouldn't come out after that. Don't use same resources for the all plan.\
            In addition, match resources with the each day topic, and you can recommend more than 1 resource each day, based on user's available time per day.\
            The available time per day means users can study input hours per a day. Make plan matches with this input time.\
            Make sure: 1 week have to be consisted of 5 days, 1 month have to be consisted of 4 weeks.\
            For example, if users want to study 4 weeks 4 days available time per day = 2 hours, then the plan should be 4 weeks and 4 days with available time of 2 hours daily.\
            Depends on user preferences, show the resources, and separate resources' title and link.\
            Please showing results only with JSON by valid format for future parsing, do not include any other format, do not include Unexpected token \'`\', \"```json:\
            studyPlan_Overview = {\"Week1: week1 overview\", ...}\
            studyPlan = {\"Week 1: Introduction to Python\": [\
                            {\
                                day: \"Day 1\",\
                                topic: something, \
                                Time: x hours,\
                                resources: {\
                                    YouTube: {\
                                        title: Advanced OOP Concepts in Python,\
                                        link: https://youtu.be/BJ-VvGyQxho\
                                    },\
                                    YouTube: {\
                                        title: ,\
                                        link: \
                                    },\
                            },"}
        ]

    def chat(self, message):
        self.messages.append({"role": "user", "content": message})
        try:
            response = self.client.chat.completions.create(model="gpt-4o", messages=self.messages, temperature=0)
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API request error: {e}")
            return "Error occurred while communicating with the AI."
