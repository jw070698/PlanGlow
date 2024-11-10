from openai import OpenAI
from openai import OpenAIError
import sys
import os
import json
#from dotenv import load_dotenv
import time
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
    def chat_with_retry(self, prompt, retries=3, delay=5, **kwargs):
        for attempt in range(retries):
            try:
                response = self.client.with_options(timeout=120.0).chat.completions.create(
                    model="gpt-4o",
                    messages=prompt,
                    **kwargs
                )
                print("chat with retry")
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise

    def chat(self, message):
        self.messages.append({"role": "user", "content": message})
        try:
            # Step 1: initial response
            initial_response = self.chat_with_retry(
                prompt=self.messages,
                temperature=0.0,
                top_p=0.8,
                frequency_penalty=0.2,
                presence_penalty=0.1
            )
            print("OpenAI initial response:", initial_response)

            # Step 2: critique of the initial response
            critique_prompt = [
                {"role": "system", "content": "You are an evaluator."},
                {"role": "user", "content": f"Here's my answer: {initial_response}. Critique this response and suggest improvements."}
            ]
            critique_response = self.chat_with_retry(
                prompt=critique_prompt,
                temperature=0.0
            )
            print("OpenAI critique response:", critique_response)
            '''
            # Step 3: improved response
            improvement_prompt = [
                {"role": "system", "content": "You are an assistant aiming to improve based on feedback."},
                {"role": "user", "content": f"Here's the initial answer: {initial_response}. Here's the critique: {critique_response}. Now, generate an improved response based on the critique."}
            ]
            improved_response = self.chat_with_retry(
                prompt=improvement_prompt,
                temperature=0.0,
                top_p=0.8,
                frequency_penalty=0.2,
                presence_penalty=0.1
            )
            print("OpenAI improved response:", improved_response)
            '''
            '''# Update messages and return final response
            self.messages.append({"role": "assistant", "content": initial_response})
            self.messages.append({"role": "assistant", "content": critique_response})
            self.messages.append({"role": "assistant", "content": improved_response})
            '''
            return initial_response

        except Exception as e:
            print(f"OpenAI API request error: {e}")
            return {"error": "Error occurred while communicating with the AI."}
