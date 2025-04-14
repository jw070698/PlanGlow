from openai import OpenAI
import sys
import os
import json
import time
import re
import firebase_admin
from firebase_admin import credentials, firestore
db = firestore.client()

class ChatApp:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.messages = [
            {"role": "system", 
            "content": (
                    "You are an intelligent assistant specializing in creating metacognition-driven, customized, and detailed study plans tailored to user-specific requirements. \
                        Your primary objective is to enhance the user's ability to think about their own thinking by embedding metacognitive strategies into their study plan, considering their topic, current background knowledge, daily time availability, and total study duration. \
                        This includes helping users plan, monitor, and assess their learning process effectively.\
                        Each plan must be well-structured, practical, and reflective, directly aligned with the user’s inputs and their ability to regulate their cognitive processes."
                    "Approach this systematically:\
                        1. Start by thoroughly analyzing the user’s input to assess their topic of interest, existing knowledge level, and daily availability.\
                        2. Use this information to structure the study plan week by week, with detailed daily breakdowns, ensuring each day’s content is both achievable and engaging.\
                        3. When recommending resources, ensure they are accessible, appropriate for the user’s background, and diverse; avoid using the same resource repeatedly unless explicitly justified.\
                        4. Adjust the complexity and depth of the study material to match the user's expertise, gradually increasing difficulty when appropriate."
                    "Ensure the following criteria are met:\
                        1. Each week consists of exactly five study days, and a month includes four weeks.\
                        2. The 'studyPlan_Overview' section should concisely describe the focus of each week.\
                        3. Ensure every plan encourages metacognitive activities (planning, monitoring, assessing)\
                        4. Must use a structured JSON format, clearly separating the study plan overview from the day-by-day breakdown.\
                        5. Validate all YouTube links to ensure they are active and appropriate for the user’s level, and support metacognitive learning."

                    "The JSON must be strictly valid and formatted as specified below:"
                    "{\
                      \"studyPlan_Overview\": {\
                        \"Week1\": \"Overview of topics for week 1\",\
                        ...\
                      },\
                      \"studyPlan\": {\
                        \"Week 1: Introduction to Python\": [\
                          {\
                            \"day\": \"Day 1\",\
                            \"topic\": \"specific topic\",\
                            \"Time\": \"x hours\",\
                            \"resources\": {\
                              \"YouTube\": [\
                                {\
                                  \"title\": 'Advanced OOP Concepts in Python',\
                                  \"link\": 'https://youtu.be/BJ-VvGyQxho'\
                                },\
                                { ... }\
                            }\
                          },\
                          ...\
                        ]\
                      }\
                    }"
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
            {"role": "system", "content": "You are a study plan evaluator.\n"
            f"Here's my initial study plan response: {parsed_json}. \n"
            "Evaluate this plan by focusing on the following criteria:\
                1. Knowles’ Five Assumptions of Adult Learners: Knowles theory of andragogy identified five assumptions that teachers should make about adult learners.\
                    1) Self-Concept – Because adults are at a mature developmental stage, they have a more secure self-concept than children. This allows them to take part in directing their own learning.\
                    2) Past Learning Experience – Adults have a vast array of experiences to draw on as they learn, as opposed to children who are in the process of gaining new experiences.\
                    3) Readiness to Learn – Many adults have reached a point in which they see the value of education and are ready to be serious about and focused on learning.\
                    4) Practical Reasons to Learn – Adults are looking for practical, problem-centered approaches to learning. Many adults return to continuing education for specific practical reasons, such as entering a new field.\
                    5) Driven by Internal Motivation – While many children are driven by external motivators – such as punishment if they get bad grades or rewards if they get good grades – adults are more internally motivated.\
                2. Four Principles of Andragogy: Based on these assumptions about adult learners, Knowles discussed four principles that  educators should consider when teaching adults.\
                    1) Since adults are self-directed, they should have a say in the content and process of their learning.\
                    2) Because adults have so much experience to draw from, their learning should focus on adding to what they have already learned in the past.\
                    3) Since adults are looking for practical learning, content should focus on issues related to their work or personal life.\
                    4) Additionally, learning should be centered on solving problems instead of memorizing content.\
                3. The following are proposed as the components of an ideal study guide assignment(Duchastel, P. (1983). Toward the ideal study guide: An exploration of the functions and components of study guides. British Journal of Educational Technology, 14(3), 216-231.):\
                    1) Purpose, significance, and goals\
                    2) Text references\
                    3) Outline of the subject matter\
                    4) Questions on the subject matter\
                    5) Key words and phrases\
                    6) Application problem\
                    7) Assignment test"
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
        parsed_json_str = json.dumps(parsed_json)
        critique_str = critique_response.strip()
        improvement_prompt = [
        {
            "role": "system",
            "content": (
                "You are an assistant tasked with improving a study plan based on the following:\n"
                f"Your primary task is to enhance study plans to meet the user’s unique needs, which are described as {user_message}, based on {critique_str}.\n"
                "Do not modify the study duration."
                "Please retain the existing structure in the 'studyPlan_Overview' and 'studyPlan' sections.\n "
                f"Initial user request: {user_message}\n"
                f"Initial Study Plan (keep structure):\n{parsed_json_str}\n\n"
                f"Critique Summary:\n{critique_str}\n\n"
                "Each week should include 5 study days, and each month should consist of 4 weeks.\n"
                "Resources other than YouTube are prohibited"
                "Use the following structure for your JSON output to represent the entire duration of the study plan without additional explanations or formatting: \n"
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

    def chat_response(self, user_chat, participantId):
        # json match -> critique -> get_improved_response
        # else: markdown
        try:
            session_ref = db.collection("messages").document(participantId)
            session_data = session_ref.get().to_dict() if session_ref.get().exists else {}
            conversation_history = session_data.get("history", [])
            history_as_text = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conversation_history]) if conversation_history else "No conversation history available."
        except Exception as e:
            print(f"Error retrieving session data for {participantId}: {e}")
            conversation_history = []
            history_as_text = "Unable to retrieve conversation history."

        system_prompt = (
            "You are a helpful assistant tasked with guiding the user toward a comprehensive study plan."
            "Follow the user's request carefully. "
            f"Here is the full conversation history for this user:\n{history_as_text}\n"
            "If the user asks a general question, provide a direct and helpful answer using Markdown, instead of JSON format."
            "ELSE If the user wants to fix or improve the current plan, your output should be in JSON format, structured as follows:\n\n"
            "{\
                \"studyPlan_Overview\": {\
                    \"Week1\": \"Overview of topics for week 1\",\
                        ...\
                },\
                \"studyPlan\": {\
                    \"Week 1: Introduction to Python\": [\
                        {\
                            \"day\": \"Day 1\",\
                            \"topic\": \"specific topic\",\
                            \"Time\": \"x hours\",\
                            \"resources\": {\
                              \"YouTube\": [\
                                {\
                                  \"title\": 'Advanced OOP Concepts in Python',\
                                  \"link\": 'https://youtu.be/BJ-VvGyQxho'\
                                },\
                                { ... }\
                            }\
                          },\
                          ...\
                    ]\
                }\
            }"
        )
        # Create the full prompt for the assistant
        full_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_chat}
        ]
       
        try:
            response = self.generate_response(
                prompt=full_prompt, 
                temperature=0.0, 
                top_p=0.8, 
                frequency_penalty=0.2, 
                presence_penalty=0.1)
            print("Initial response received:", response)

            # Check user intent
            if "improve" in user_chat.lower() or "fix" in user_chat.lower() or "update" in user_chat.lower() or "change" in user_chat.lower() or "revise" in user_chat.lower():
                # Process JSON responses for improvement
                json_match = re.search(r'```json([\s\S]*?)```', response)
                if json_match:
                    json_text = json_match.group(1).strip()
                    try:
                        parsed_json = json.loads(json_text)
                        print("Parsed JSON response:", parsed_json)

                        # Proceed to critique
                        critique = self.get_critique_response(parsed_json)
                        print("Critique response:", critique)

                        # Proceed to improvement
                        improved_response = self.get_improved_response(user_chat, parsed_json, critique)
                        print("Improved response:", improved_response)

                        return improved_response
                    except json.JSONDecodeError:
                        print("JSON parsing error. Proceeding with raw JSON for critique.")
                        critique = self.get_critique_response(json_text)
                        print("Critique response for raw JSON:", critique)

                        # Proceed to improvement
                        improved_response = self.get_improved_response(user_chat, json_text, critique)
                        print("Improved response from raw JSON:", improved_response)

                        return improved_response
                else:
                    print("No JSON block found. Proceeding with raw response.")
                    critique = self.get_critique_response(response)
                    print("Critique response for raw response:", critique)

                    improved_response = self.get_improved_response(user_chat, response, critique)
                    print("Improved response from raw response:", improved_response)

                    return improved_response
            else:
                # General question, return response as Markdown
                return response

        except Exception as e:
            print(f"Unexpected error during chat response: {e}")
            return {"error": "An unexpected error occurred.", "details": str(e)}
