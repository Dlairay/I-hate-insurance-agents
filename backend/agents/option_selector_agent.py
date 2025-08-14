"""
option_selector_agent.py
========================
Smart AI agent that interprets natural language and maps to questionnaire options
"""

import asyncio
import json
from typing import Dict, Any, List, Optional

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Ollama model  
ollama_model = LiteLlm(model="ollama_chat/llama3")

def analyze_user_input(user_description: str, question_data: dict) -> dict:
    """
    Tool to analyze user's natural language input against available options
    """
    print(f"🔍 Analyzing: '{user_description}' for question: {question_data.get('id', 'unknown')}")
    
    return {
        "user_input": user_description,
        "question": question_data.get('question_text', ''),
        "question_id": question_data.get('id', ''),
        "available_options": [
            {
                "value": opt.get("value", ""),
                "label": opt.get("label", ""),
                "description": opt.get("description", "")
            }
            for opt in question_data.get('options', [])
        ]
    }

# Create the Natural Language Interpreter Agent
option_selector_agent = Agent(
    name="option_selector",
    model=ollama_model,
    description="Expert at interpreting natural language and mapping to questionnaire options",
    instruction=(
        "You are an expert at understanding what people mean when they describe their situation in natural language.\n\n"
        
        "Your job is to:\n"
        "1. READ the user's description carefully\n"
        "2. UNDERSTAND what they really mean\n"
        "3. MATCH it to the most appropriate option from the available choices\n"
        "4. RETURN only the option VALUE (not the label)\n\n"
        
        "Examples of natural language interpretation:\n"
        "- 'I go skiing once a year in Hokkaido' → 'none' (occasional recreational skiing isn't high-risk)\n"
        "- 'I do competitive motor racing on weekends' → 'racing' (clearly high-risk activity)\n"
        "- 'I rock climb every weekend' → 'climbing' (regular dangerous activity)\n"
        "- 'I scuba dive on vacations' → 'scuba' (underwater diving is inherently risky)\n\n"
        "- 'Don't want to be financially crippled by unexpected expenses' → 'fill_gaps' (covering financial gaps)\n"
        "- 'Never had insurance, need guidance' → 'first_time' (first-time buyer)\n"
        "- 'Getting married next month' → 'life_change' (major life change)\n"
        "- 'Want to save money on my current policy' → 'save_money' (cost reduction)\n\n"
        "- 'I make 60k and want decent coverage but not crazy expensive' → budget based on income percentage\n"
        "- 'I'm pretty healthy, exercise regularly' → 'good' (good health status)\n"
        "- 'I quit smoking 2 years ago' → 'quit_over_year' (quit over a year ago)\n\n"
        
        "IMPORTANT:\n"
        "- Focus on the ESSENCE of what they're describing\n"
        "- Consider FREQUENCY and RISK LEVEL for activities\n"
        "- Consider FINANCIAL SITUATION for budget questions\n"
        "- Consider INTENT and MOTIVATION for insurance needs\n"
        "- Always return just the option VALUE, never the label\n"
        "- If unclear, choose the most conservative/safe option\n"
    ),
    tools=[analyze_user_input],
)

class OptionSelectorHelper:
    """Helper class for natural language option selection"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "option_selector"
        self.runner = None
        self.session_initialized = False
    
    async def initialize(self):
        """Initialize the agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                session_id="default",
                user_id="user"
            )
            self.runner = Runner(
                agent=option_selector_agent,
                app_name=self.app_name,
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def select_option(self, user_description: str, question: dict, previous_answers: dict = None) -> str:
        """
        Simple text matching - no AI bullshit needed
        """
        return self._rule_based_fallback(user_description, question)
    
    def _rule_based_fallback(self, user_description: str, question: dict) -> str:
        """
        Rule-based fallback for option selection when AI fails
        """
        user_input = user_description.lower()
        question_id = question.get('id', '')
        options = question.get('options', [])
        
        if not options:
            return ""
        
        # High-risk activities patterns
        if question_id == 'high_risk_activities':
            if any(word in user_input for word in ['ski', 'snowboard', 'slope']) and 'racing' not in user_input:
                return 'none'  # Recreational skiing isn't high-risk
            elif any(word in user_input for word in ['race', 'racing', 'track', 'speedway']):
                return 'racing'
            elif any(word in user_input for word in ['climb', 'climbing', 'mountain', 'rock']):
                return 'climbing'
            elif any(word in user_input for word in ['dive', 'diving', 'scuba', 'underwater']):
                return 'scuba'
            elif any(word in user_input for word in ['sky', 'jump', 'parachute', 'skydiving']):
                return 'skydiving'
            elif any(word in user_input for word in ['martial', 'fight', 'boxing', 'mma']):
                return 'martial_arts'
            elif any(word in user_input for word in ['fly', 'flying', 'pilot', 'plane']):
                return 'flying'
            elif any(word in user_input for word in ['extreme', 'dangerous']):
                return 'extreme_sports'
            else:
                return 'none'
        
        # Primary need patterns
        elif question_id == 'primary_need':
            if any(word in user_input for word in ['save', 'cheaper', 'reduce', 'lower cost']):
                return 'save_money'
            elif any(word in user_input for word in ['gap', 'cover', 'protect', 'unexpected', 'crippled']):
                return 'fill_gaps'
            elif any(word in user_input for word in ['first', 'never', 'new', 'guidance', 'help']):
                return 'first_time'
            elif any(word in user_input for word in ['married', 'baby', 'job', 'change', 'family']):
                return 'life_change'
            elif any(word in user_input for word in ['compare', 'options', 'shopping']):
                return 'compare_options'
            else:
                return 'first_time'
        
        # Health status patterns
        elif question_id == 'health_status':
            if any(word in user_input for word in ['excellent', 'great', 'perfect', 'amazing']):
                return 'excellent'
            elif any(word in user_input for word in ['good', 'healthy', 'fine', 'okay', 'decent']):
                return 'good'
            elif any(word in user_input for word in ['fair', 'some issues', 'managed', 'controlled']):
                return 'fair'
            elif any(word in user_input for word in ['poor', 'bad', 'problems', 'multiple']):
                return 'poor'
            else:
                return 'good'
        
        # Smoking patterns
        elif question_id == 'smoking_vaping_habits':
            if any(word in user_input for word in ['never', 'no', 'dont', "don't"]):
                return 'never'
            elif any(word in user_input for word in ['quit', 'stopped']) and any(word in user_input for word in ['year', 'years']):
                return 'quit_over_year'
            elif any(word in user_input for word in ['quit', 'stopped']) and any(word in user_input for word in ['month', 'recently']):
                return 'quit_under_year'
            elif any(word in user_input for word in ['occasional', 'sometimes', 'social']):
                return 'occasional'
            elif any(word in user_input for word in ['regular', 'weekly']):
                return 'regular'
            elif any(word in user_input for word in ['daily', 'every day', 'pack']):
                return 'daily'
            else:
                return 'never'
        
        # Default: return first option
        return options[0].get('value', '') if options else ""

# Global instance
option_selector = OptionSelectorHelper()

# Compatibility wrapper for existing code
class QuestionnaireHelper:
    """Wrapper that uses the option selector for natural language interpretation"""
    
    async def help_select_answer(self, question: dict, user_description: str, previous_answers: dict) -> str:
        """
        Help select the best option based on user's natural language description
        """
        return await option_selector.select_option(user_description, question, previous_answers)
    
    async def explain_answer_choice(self, question: dict, selected_answer: str, user_description: str) -> str:
        """
        Explain why a particular answer was chosen
        """
        # Find the selected option label
        selected_label = selected_answer
        for opt in question.get('options', []):
            if opt.get('value') == selected_answer:
                selected_label = opt.get('label', selected_answer)
                break
        
        return f"Based on your description '{user_description}', I selected '{selected_label}' as the best match for your situation."