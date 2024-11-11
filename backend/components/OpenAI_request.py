from openai import OpenAI
from openai import OpenAIError
import sys
import os
import json
#from dotenv import load_dotenv
import time
import re
#load_dotenv()
api_key = os.getenv("API_KEY1")
client = OpenAI(api_key=api_key)

class ChatApp:
    def __init__(self):
        self.client = client
        self.messages = [
            {"role": "system", 
            "content": (
                    "You are a helpful assistant specializing in creating tailored study plans based on user needs and preferences. "
                    "Your task is to design study plans that fit user limitations on time, knowledge base, and resource preferences. "
                    "Use a step-by-step approach to carefully construct the study plan, reasoning through each choice of topics, resources, and schedule. "
                    "Start by assessing the user's requirements, and then outline the structure of the study plan week by week, with daily details as necessary. "
                    "When selecting resources, ensure they are accessible and unique—do not reuse resources across different days or weeks unless justified. "
                    "For days when the user has >=3 hours, feel free to recommend multiple resources. "
                    "Always align the content with the user's available study time per day. "
                    "\n\n"
                    "Make sure the following criteria are met:\n"
                    "1. Each week should contain 5 study days, and each month should have 4 weeks.\n"
                    "2. Use a consistent JSON format, separating 'studyPlan_Overview' and 'studyPlan' for easier parsing later. "
                    "Show only valid JSON results without additional explanations or formatting.\n"
                    "\n\n"
                    "Use the following structure for your JSON output:\n"
                    "{\n"
                    "  'studyPlan_Overview': {\n"
                    "    'Week1': 'Overview of topics for week 1',\n"
                    "    ...\n"
                    "  },\n"
                    "  'studyPlan': {\n"
                    "    'Week 1: Introduction to Python': [\n"
                    "      {\n"
                    "        'day': 'Day 1',\n"
                    "        'topic': 'specific topic',\n"
                    "        'Time': 'x hours',\n"
                    "        'resources': {\n"
                    "          'YouTube': [\n"
                    "            {\n"
                    "              'title': 'Advanced OOP Concepts in Python',\n"
                    "              'link': 'https://youtu.be/BJ-VvGyQxho'\n"
                    "            },\n"
                    "            { ... }\n"
                    "          ],\n"
                    "          'Articles': [\n"
                    "            { 'title': 'Introduction to Python', 'link': '...' }\n"
                    "          ]\n"
                    "        }\n"
                    "      },\n"
                    "      ...\n"
                    "    ]\n"
                    "  }\n"
                    "}\n"
                    "\n\n"
                    "When planning, start by reasoning out loud about the structure and content, clarifying each decision you make. "
                    "Once you complete your reasoning, output only the JSON format without any extra comments or formatting."
                )
            }
        ]

    def generate_response(self, prompt, **kwargs):
        try:
            response = self.client.with_options(timeout=300.0).chat.completions.create(
                model="gpt-4o",
                messages=prompt,
                **kwargs
            )
            response_text = response.choices[0].message.content
            print("API response:", response_text)
            return response_text
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None


    def chat(self, message):
        self.messages.append({"role": "user", "content": message})
        # Step 1: initial response
        initial_response = self.generate_response(
            prompt=self.messages,
            temperature=0.0,
            top_p=0.8,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        print("OpenAI initial response:", initial_response)
        if initial_response:
            json_match = re.search(r'```json([\s\S]*?)```', initial_response)
            if json_match:
                json_text = json_match.group(1).strip()
                try:
                    parsed_json = json.loads(json_text)
                    print("Parsed JSON response:", parsed_json)
                    return parsed_json
                except json.JSONDecodeError:
                    print("JSON parsing error. Returning raw response.")
                    return initial_response
            else:
                print("No JSON block found, returning raw response.")
                return initial_response  
        else:
            return {"error": "An error occurred while generating the response."} 

    # step 2 critique
    def get_critique_response(self, initial_response):
        critique_prompt = [
            {"role": "system", "content": "You are an evaluator."},
            {"role": "user", "content": 
            f"Here's my initial study plan response: {initial_response}. \n"
            "Critique this response and suggest improvements focusing on disciplinary core ideas, crosscutting concepts and scientific practices examining phenomena. \n"
            "Please provide a short critique of this response. Focus only on the main areas for improvement in 2-3 sentences. \n"
            "Make sure the critique is concise, constructive, and avoids unnecessary detail. \n"
            "Study materials only accepted YouTube resources."}
        ]
        try:
            critique_text = self.generate_response(critique_prompt, temperature=0.0)
            print("Critique response:", critique_text)
            return critique_text
        except Exception as e:
            print(f"Error during critique generation: {e}")
            return "An error occurred while generating the critique."

    # step 3 improved response
    def get_improved_response(self, initial_response, critique_response):
        improvement_prompt = [
            {"role": "system", "content": "You are an assistant aiming to improve based on feedback."},
            {"role": "user", "content": 
            f"Here's the initial answer: {initial_response}. Here's the critique: {critique_response}. \n"
            "Now, generate an improved response based on the critique. Return study plan in json type. \n"
            "Make sure the following criteria are met:\n"
                    "1. Each week should contain 5 study days, and each month should have 4 weeks.\n"
                    "2. Use a consistent JSON format, separating 'studyPlan_Overview' and 'studyPlan' for easier parsing later. "
                    "Show only valid JSON results without additional explanations or formatting.\n"
            "Use the following structure for your JSON output:\n"
                    "{\n"
                    "  'studyPlan_Overview': {\n"
                    "    'Week1': 'Overview of topics for week 1',\n"
                    "    ...\n"
                    "  },\n"
                    "  'studyPlan': {\n"
                    "    'Week 1: Introduction to Python': [\n"
                    "      {\n"
                    "        'day': 'Day 1',\n"
                    "        'topic': 'specific topic',\n"
                    "        'Time': 'x hours',\n"
                    "        'resources': {\n"
                    "          'YouTube': [\n"
                    "            {\n"
                    "              'title': 'Advanced OOP Concepts in Python',\n"
                    "              'link': 'https://youtu.be/BJ-VvGyQxho'\n"
                    "            },\n"
                    "            { ... }\n"
                    "          ],\n"
                    "          'Articles': [\n"
                    "            { 'title': 'Introduction to Python', 'link': '...' }\n"
                    "          ]\n"
                    "        }\n"
                    "      },\n"
                    "      ...\n"
                    "    ]\n"
                    "  }\n"
                    "}\n"
                    "\n\n"
                    "Once you complete your reasoning, output only the JSON format without any extra comments or formatting."}
        ]
        return self.generate_response(improvement_prompt, temperature=0.0, top_p=0.8, frequency_penalty=0.2, presence_penalty=0.1)

        