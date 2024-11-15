from openai import OpenAI
import sys
import os
import json
import time
import re

class ChatApp:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.messages = [
            {"role": "system", 
            "content": (
                    "You are an intelligent assistant specializing in creating customized and detailed study plans tailored to user-specific requirements. \
                        Your primary task is to design study plans that meet the user’s unique needs, considering their topic, current background knowledge, daily time availability, and total study duration. \
                        Every plan you create must be well-structured and practical, directly aligned with the user’s inputs"
                    "Approach this systematically:\
                        1. Start by thoroughly analyzing the user’s input to assess their topic of interest, existing knowledge level, and daily availability.\
                        2. Use this information to structure the study plan week by week, with detailed daily breakdowns, ensuring each day’s content is both achievable and engaging.\
                        3. When recommending resources, ensure they are accessible, appropriate for the user’s background, and diverse; avoid using the same resource repeatedly unless explicitly justified.\
                        4. For days where the user has three or more hours of availability, include multiple resources and topics to maximize their learning.\
                        5. Adjust the complexity and depth of the study material to match the user's expertise, gradually increasing difficulty when appropriate."
                    "Ensure the following criteria are met:\
                        Each week consists of exactly five study days, and a month includes four weeks.\
                        Use a structured JSON format, clearly separating the study plan overview from the day-by-day breakdown."
                    "The JSON must be strictly valid and formatted as specified below:"
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
                    "        }\n"
                    "      },\n"
                    "      ...\n"
                    "    ]\n"
                    "  }\n"
                    "}\n"
                    "\n\n"
                    "When delivering the study plan:\
                        The 'studyPlan_Overview' section should concisely describe the focus of each week.\
                        Validate all YouTube links to ensure they are active and appropriate for the user’s level."
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
    def get_critique_response(self, parsed_json):
        critique_prompt = [
            {"role": "system", "content": "You are an evaluator.\n"
            f"Here's my initial study plan response: {parsed_json}. \n"
            "Critique this response by focusing on the following criteria:"
            "- Are the resources exclusively YouTube-based, as required?\n"
            "- Do the resources provide accurate, reliable, and engaging content for the intended topics?\n"
            "- Are the selected resources well-aligned with the study goals and learning outcomes?\n\n"
            "- Does the plan have a logical progression of topics that builds on previous knowledge?\n"
            "- Is the daily breakdown of study time and resources clear, manageable, and realistic for the intended audience?\n"
            "- Are there gaps or redundancies in the structure that might hinder the learner's understanding or engagement?\n\n"
            "- Does the plan facilitate a clear understanding of core concepts and phenomena?\n"
            "Provide actionable and constructive feedback addressing these areas. Keep the critique concise but specific, highlighting the most critical improvements needed. Avoid unnecessary elaboration or repetition."
            }
        ]
        try:
            critique_text = self.generate_response(critique_prompt, temperature=0.0)
            print("Critique response:", critique_text)
            return critique_text
        except Exception as e:
            print(f"Error during critique generation: {e}")
            return "An error occurred while generating the critique."

    # step 3 improved response
    def get_improved_response(self, user_message, parsed_json, critique_response):
        print("USER MESSAGE in GET IMPROVED RESWPONSE",user_message)
        parsed_json_str = json.dumps(parsed_json)
        critique_str = critique_response.strip()
        improvement_prompt = [
        {
            "role": "system",
            "content": (
                "You are an assistant improving a study plan based on the following critique. "
                f"Your primary task is to improve study plans that meet the user’s unique needs which is {user_message} based on {critique_str}."
                "DO NOT CHANGE STUDY DURATION"
                "Please use the existing structure in 'studyPlan_Overview' and 'studyPlan' sections, "
                f"Initial user request: {user_message}\n" ##### add initial prompts
                f"Initial Study Plan (keep structure):\n{parsed_json_str}\n\n"
                f"Critique Summary:\n{critique_str}\n\n"
                "Each week should contain 5 study days, and each month should have 4 weeks.\n"
                "Resources other than YouTube is prohibitted"
                "Use the following structure for your JSON output to have all duration of study plan without additional explanations or formatting: \n"
                    "{\
                      \"studyPlan_Overview\": {\
                        \"Week1\": '',\
                        ...\
                      },\
                      \"studyPlan\": {\
                        \"Week 1: \": [\
                          {\
                            \"day\": \"Day 1\",\
                            \"topic\": \"specific topic\",\
                            \"Time\": \"x hours\",\
                            \"resources'\" {\
                              \"YouTube\": [\
                                {\
                                  \"title\": \"title of videos\",\
                                  \"link\": \"link of videos\"\
                                },\
                                { ... }\
                              ],\
                            }\
                          },\
                          ...\
                        ]\
                      }\
                    }"
                    "Note: Only recommend one YouTube video per day if the user's availability is <=1 hour per day."

            )
        }
    ]
        try:
            response = self.generate_response(improvement_prompt, temperature=0.0)

            # Search for JSON in the response (in case it's wrapped in code blocks)
            json_match = re.search(r'```json([\s\S]*?)```', response)
            if json_match:
                json_text = json_match.group(1).strip()
            else:
                # If no code block is found, assume the entire response is the JSON text
                json_text = response.strip()

            # Parse the JSON response
            try:
                improved_json = json.loads(json_text)
                print("Parsed JSON improved response:", improved_json)
                return json.dumps(improved_json)
            except json.JSONDecodeError:
                print("JSON parsing error. Returning raw response.")
                return response

        except Exception as e:
            print(f"Error during improved response generation: {e}")
            return "An error occurred while generating the improved response."