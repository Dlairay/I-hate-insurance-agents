"""
questionnaire_agent.py
======================
AI agent using Ollama with Google ADK to help users with questionnaire
"""

import os
import asyncio
import warnings
import json
from typing import Dict, Any, Optional, List

# Suppress Pydantic warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress logs
import logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("google.adk").setLevel(logging.ERROR)

# Initialize Ollama model (following testagent.py pattern)
ollama_model = LiteLlm(model="ollama_chat/llama3:latest")


def analyze_user_description(description: str, question: dict, previous_answers: dict) -> dict:
    """
    Tool function to analyze user's description and select the best answer
    
    Args:
        description: User's free-text description of their situation
        question: The current question object with options
        previous_answers: Previous questionnaire answers for context
    
    Returns:
        Dict with selected answer and confidence score
    """
    print(f"--- Tool: analyze_user_description called ---")
    print(f"Description: {description}")
    print(f"Question: {question.get('question_text', '')}")
    
    # Return structured response for the agent to process
    return {
        "description": description,
        "question": question,
        "previous_context": previous_answers,
        "needs_selection": True
    }


def validate_answer(answer: str, question_type: str, options: Optional[List[dict]] = None) -> dict:
    """
    Tool to validate if an answer is appropriate for the question type
    
    Args:
        answer: The proposed answer
        question_type: Type of question (mcq_single, text, date, etc)
        options: Available options for MCQ questions
    
    Returns:
        Dict with validation result
    """
    print(f"--- Tool: validate_answer called ---")
    
    if question_type == "mcq_single" and options:
        valid_values = [opt.get("value") for opt in options]
        is_valid = answer in valid_values
        
        return {
            "is_valid": is_valid,
            "answer": answer,
            "valid_options": valid_values,
            "message": "Valid selection" if is_valid else f"Invalid - must be one of {valid_values}"
        }
    
    elif question_type == "text":
        is_valid = isinstance(answer, str) and len(answer) > 0
        return {
            "is_valid": is_valid,
            "answer": answer,
            "message": "Valid text input" if is_valid else "Text cannot be empty"
        }
    
    elif question_type == "date":
        # Basic date validation
        import re
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        is_valid = bool(re.match(date_pattern, answer))
        return {
            "is_valid": is_valid,
            "answer": answer,
            "message": "Valid date format" if is_valid else "Date must be YYYY-MM-DD format"
        }
    
    return {
        "is_valid": False,
        "answer": answer,
        "message": f"Unknown question type: {question_type}"
    }


# Create the Questionnaire Helper Agent
questionnaire_agent = Agent(
    name="questionnaire_helper",
    model=ollama_model,
    description="AI assistant that helps users answer insurance questionnaire questions",
    instruction=(
        "You are an intelligent insurance questionnaire assistant. Your role is to:\n"
        "1. Analyze user descriptions of their situation\n"
        "2. Map their descriptions to the most appropriate questionnaire answer\n"
        "3. Explain your reasoning clearly\n\n"
        "When a user describes their situation:\n"
        "- Carefully analyze what they're saying\n"
        "- Consider the context from previous answers\n"
        "- Select the MOST APPROPRIATE option from the available choices\n"
        "- Return ONLY the option value (not the label)\n"
        "- Provide a brief explanation of why you chose that answer\n\n"
        "For health questions, be conservative and accurate.\n"
        "For lifestyle questions, interpret common phrases correctly.\n"
        "Always prioritize accuracy for insurance purposes."
    ),
    tools=[analyze_user_description, validate_answer],
)


class QuestionnaireHelperAgent:
    """Wrapper class for the questionnaire helper agent"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "insurance_questionnaire"
        self.runner = None
        self.session_initialized = False
    
    async def initialize(self):
        """Initialize the agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id="questionnaire_user",
                session_id="session_001"
            )
            self.runner = Runner(
                agent=questionnaire_agent,
                app_name=self.app_name,
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def help_select_answer(self, question: Dict[str, Any], user_description: str, 
                                 previous_responses: Dict[str, Any]) -> Optional[str]:
        """
        Help user select the most appropriate answer based on their description
        
        Args:
            question: The current question object
            user_description: User's description of their situation
            previous_responses: Previous answers for context
            
        Returns:
            The most appropriate answer value
        """
        await self.initialize()
        
        # Build context for the agent
        context = f"""
The user needs help answering this insurance questionnaire question:

Question: {question.get('question_text', '')}
Question Type: {question.get('question_type', '')}
Category: {question.get('category', '')}

Available Options:
{json.dumps(question.get('options', []), indent=2)}

User's Description: "{user_description}"

Previous Context:
- Age: {self._calculate_age(previous_responses.get('personal_dob'))} years old
- Gender: {previous_responses.get('personal_gender', 'Not specified')}
- Occupation: {previous_responses.get('lifestyle_occupation', 'Not specified')}

Based on the user's description, select the MOST APPROPRIATE option value.
Return ONLY the option value, not the label.
"""
        
        # Create message for agent
        content = types.Content(role='user', parts=[types.Part(text=context)])
        
        selected_answer = None
        try:
            async for event in self.runner.run_async(
                user_id="questionnaire_user",
                session_id="session_001",
                new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                        # Extract the answer value from the response
                        selected_answer = self._extract_answer_from_response(
                            response_text, question.get('options', [])
                        )
                    break
        except Exception as e:
            print(f"Agent error: {e}")
            # Fallback to rule-based selection
            selected_answer = self._fallback_selection(
                question, user_description, previous_responses
            )
        
        return selected_answer
    
    async def explain_answer_choice(self, question: Dict[str, Any], selected_answer: str, 
                                   user_description: str) -> str:
        """
        Explain why a particular answer was chosen
        
        Args:
            question: The question that was answered
            selected_answer: The answer that was selected
            user_description: User's original description
            
        Returns:
            Human-readable explanation
        """
        await self.initialize()
        
        prompt = f"""
Explain why this answer was selected for an insurance questionnaire:

Question: {question.get('question_text', '')}
User Said: "{user_description}"
Selected Answer: {selected_answer}

Provide a brief, helpful explanation (1-2 sentences) of why this answer best matches what the user described.
Be reassuring and informative.
"""
        
        content = types.Content(role='user', parts=[types.Part(text=prompt)])
        
        explanation = "Based on your description, this appears to be the most accurate choice."
        try:
            async for event in self.runner.run_async(
                user_id="questionnaire_user",
                session_id="session_001",
                new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        explanation = event.content.parts[0].text
                    break
        except Exception as e:
            print(f"Explanation error: {e}")
        
        return explanation
    
    def _calculate_age(self, dob: Optional[str]) -> int:
        """Calculate age from date of birth"""
        if not dob:
            return 30  # Default age
        try:
            from datetime import date
            birth_date = date.fromisoformat(dob)
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except:
            return 30
    
    def _extract_answer_from_response(self, response_text: str, options: List[dict]) -> Optional[str]:
        """Extract the answer value from agent's response"""
        if not options:
            return response_text.strip()
        
        # Check if any option value is directly mentioned in the response
        for option in options:
            value = option.get('value', '')
            if value and value in response_text:
                return value
        
        # Try to find the answer in various formats
        response_lower = response_text.lower()
        for option in options:
            value = option.get('value', '')
            label = option.get('label', '').lower()
            if value and (value.lower() in response_lower or label in response_lower):
                return value
        
        return None
    
    def _fallback_selection(self, question: Dict[str, Any], user_description: str, 
                           previous_responses: Dict[str, Any]) -> Optional[str]:
        """Rule-based fallback when AI fails"""
        question_id = question.get('id', '')
        description_lower = user_description.lower()
        options = question.get('options', [])
        
        # Health smoking question
        if 'smoker' in question_id:
            if any(word in description_lower for word in ['smoke', 'cigarette', 'tobacco', 'vape']):
                return 'true'
            elif any(word in description_lower for word in ['quit', 'former', 'used to']):
                return 'former'
            else:
                return 'false'
        
        # Exercise frequency
        elif 'exercise' in question_id:
            if any(word in description_lower for word in ['daily', 'every day', 'gym']):
                return 'daily'
            elif any(word in description_lower for word in ['week', 'few times']):
                return 'several_times_week'
            elif any(word in description_lower for word in ['rarely', 'never', "don't"]):
                return 'rarely'
        
        # Default to first option
        if options:
            return options[0].get('value')
        
        return None


# Create a synchronous wrapper for use in FastAPI
class QuestionnaireHelper:
    """Synchronous wrapper for the async agent"""
    
    def __init__(self):
        self.agent = QuestionnaireHelperAgent()
    
    async def help_select_answer(self, question: Dict[str, Any], user_description: str,
                                previous_responses: Dict[str, Any]) -> Optional[str]:
        """Async method for FastAPI"""
        return await self.agent.help_select_answer(question, user_description, previous_responses)
    
    async def explain_answer_choice(self, question: Dict[str, Any], selected_answer: str,
                                   user_description: str) -> str:
        """Async method for FastAPI"""
        return await self.agent.explain_answer_choice(question, selected_answer, user_description)