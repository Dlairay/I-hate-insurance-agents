"""
smart_questionnaire_agent.py
============================
Enhanced AI agent with insurance domain knowledge and context awareness
"""

import os
import asyncio
import warnings
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

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

# Initialize Ollama model
ollama_model = LiteLlm(model="ollama_chat/llama3:latest")


class InsuranceKnowledgeBase:
    """Domain knowledge about insurance concepts and recommendations"""
    
    OCCUPATION_RISK_LEVELS = {
        "office_professional": {"risk": "low", "description": "Desk job, low physical risk"},
        "healthcare": {"risk": "medium", "description": "Exposure to illnesses, moderate stress"},
        "education": {"risk": "low", "description": "Safe environment, low risk"},
        "retail_service": {"risk": "low", "description": "Customer-facing, generally safe"},
        "transportation": {"risk": "high", "description": "Driving/transport, higher accident risk"},
        "construction": {"risk": "high", "description": "Physical labor, machinery, high risk"},
        "law_enforcement": {"risk": "high", "description": "Public safety, high risk profession"},
        "self_employed": {"risk": "medium", "description": "Variable income, moderate risk"}
    }
    
    SMOKING_IMPACT = {
        "never": {"premium_impact": "none", "description": "No smoking penalty"},
        "quit_over_year": {"premium_impact": "low", "description": "Minimal penalty, shows commitment"},
        "quit_under_year": {"premium_impact": "medium", "description": "Recent quitter, still some risk"},
        "occasional": {"premium_impact": "high", "description": "Considered smoker by most insurers"},
        "regular": {"premium_impact": "very_high", "description": "Significant premium increase"},
        "daily": {"premium_impact": "maximum", "description": "Highest penalty, major health risk"}
    }
    
    BUDGET_RECOMMENDATIONS = {
        "low_income": {"max_percentage": 4, "focus": "basic_coverage", "avoid": "premium_plans"},
        "medium_income": {"max_percentage": 6, "focus": "balanced_coverage", "avoid": "excessive_coverage"},
        "high_income": {"max_percentage": 8, "focus": "comprehensive_coverage", "avoid": "under_insurance"}
    }
    
    HIGH_RISK_ACTIVITIES = {
        "scuba": {"risk_level": "medium", "premium_impact": 5},
        "skydiving": {"risk_level": "high", "premium_impact": 15}, 
        "racing": {"risk_level": "very_high", "premium_impact": 25},
        "climbing": {"risk_level": "medium", "premium_impact": 8},
        "martial_arts": {"risk_level": "low", "premium_impact": 3},
        "flying": {"risk_level": "high", "premium_impact": 12},
        "extreme_sports": {"risk_level": "very_high", "premium_impact": 30}
    }


def analyze_user_context(description: str, question: dict, previous_answers: dict) -> dict:
    """
    Enhanced tool that analyzes user situation with insurance domain knowledge
    
    Args:
        description: User's description of their situation
        question: Current question object
        previous_answers: All previous answers for context
        
    Returns:
        Rich context analysis for the AI agent
    """
    print(f"🔍 Analyzing user context for: {question.get('id', 'unknown')}")
    
    # Extract financial context
    financial_context = {}
    if 'basic_info' in previous_answers:
        basic_info = previous_answers['basic_info']
        if isinstance(basic_info, str):
            # Parse age and income from basic_info
            import re
            numbers = re.findall(r'\d+', basic_info.replace(',', ''))
            if len(numbers) >= 2:
                nums = [int(n) for n in numbers]
                nums.sort()
                age = nums[0] if nums[0] <= 100 else 30
                income = nums[-1] if nums[-1] >= 1000 else 50000
                financial_context = {"age": age, "annual_income": income}
    
    # Determine income category for budget recommendations
    income = financial_context.get('annual_income', 50000)
    if income < 40000:
        income_category = "low_income"
    elif income < 80000:
        income_category = "medium_income"
    else:
        income_category = "high_income"
    
    # Get question-specific context
    question_id = question.get('id', '')
    question_type = question.get('question_type', '')
    options = question.get('options', [])
    
    return {
        "user_description": description,
        "question_context": {
            "id": question_id,
            "text": question.get('question_text', ''),
            "type": question_type,
            "options": [{"value": opt.get("value"), "label": opt.get("label")} for opt in options],
            "category": question.get('category', '')
        },
        "financial_context": financial_context,
        "income_category": income_category,
        "previous_answers": previous_answers,
        "insurance_knowledge": {
            "occupation_risks": InsuranceKnowledgeBase.OCCUPATION_RISK_LEVELS,
            "smoking_impacts": InsuranceKnowledgeBase.SMOKING_IMPACT,
            "budget_guidelines": InsuranceKnowledgeBase.BUDGET_RECOMMENDATIONS,
            "activity_risks": InsuranceKnowledgeBase.HIGH_RISK_ACTIVITIES
        }
    }


def calculate_budget_recommendation(annual_income: float, question_id: str) -> dict:
    """
    Tool to calculate smart budget recommendations based on income
    
    Args:
        annual_income: User's annual income
        question_id: Current question ID
        
    Returns:
        Budget recommendation with reasoning
    """
    print(f"💰 Calculating budget recommendation for income: ${annual_income:,.0f}")
    
    # Insurance budget guidelines: 2-8% of annual income
    conservative_budget = annual_income * 0.02 / 12  # 2% annually = monthly
    moderate_budget = annual_income * 0.04 / 12      # 4% annually = monthly  
    comprehensive_budget = annual_income * 0.06 / 12 # 6% annually = monthly
    
    # Map to budget ranges
    budget_mapping = []
    if conservative_budget >= 50:
        if conservative_budget <= 100:
            budget_mapping.append(("under_100", "Conservative choice"))
        if moderate_budget <= 200:
            budget_mapping.append(("100_200", "Balanced approach"))
        if comprehensive_budget <= 400:
            budget_mapping.append(("200_400", "Comprehensive coverage"))
        if comprehensive_budget > 400:
            budget_mapping.append(("400_plus", "Maximum protection"))
    
    return {
        "annual_income": annual_income,
        "monthly_budgets": {
            "conservative": round(conservative_budget),
            "moderate": round(moderate_budget), 
            "comprehensive": round(comprehensive_budget)
        },
        "recommended_ranges": budget_mapping,
        "reasoning": f"Based on ${annual_income:,.0f} income, insurance should be 2-6% of income (${conservative_budget:.0f}-${comprehensive_budget:.0f}/month)"
    }


def assess_risk_factors(answers: dict) -> dict:
    """
    Tool to assess overall risk profile based on answers
    
    Args:
        answers: Dictionary of all user answers
        
    Returns:
        Risk assessment with recommendations
    """
    print("⚡ Assessing risk factors...")
    
    risk_score = 0
    risk_factors = []
    
    # Age risk (from basic_info)
    if 'basic_info' in answers:
        import re
        numbers = re.findall(r'\d+', answers['basic_info'].replace(',', ''))
        if numbers:
            age = min([int(n) for n in numbers if int(n) <= 100], default=30)
            if age > 60:
                risk_score += 20
                risk_factors.append("Age over 60 - higher health risk")
            elif age > 45:
                risk_score += 10
                risk_factors.append("Age 45+ - moderate health risk")
    
    # Occupation risk
    if 'occupation' in answers:
        occupation = answers['occupation']
        if occupation in InsuranceKnowledgeBase.OCCUPATION_RISK_LEVELS:
            risk_info = InsuranceKnowledgeBase.OCCUPATION_RISK_LEVELS[occupation]
            if risk_info['risk'] == 'high':
                risk_score += 15
                risk_factors.append(f"High-risk occupation: {risk_info['description']}")
            elif risk_info['risk'] == 'medium':
                risk_score += 8
                risk_factors.append(f"Medium-risk occupation: {risk_info['description']}")
    
    # Smoking risk
    if 'smoking_vaping_habits' in answers:
        smoking = answers['smoking_vaping_habits']
        if smoking in InsuranceKnowledgeBase.SMOKING_IMPACT:
            impact = InsuranceKnowledgeBase.SMOKING_IMPACT[smoking]
            if impact['premium_impact'] in ['high', 'very_high', 'maximum']:
                risk_score += 20
                risk_factors.append(f"Smoking/vaping: {impact['description']}")
    
    # High-risk activities
    if 'high_risk_activities' in answers:
        activities = answers['high_risk_activities']
        if isinstance(activities, list) and 'none' not in activities:
            for activity in activities:
                if activity in InsuranceKnowledgeBase.HIGH_RISK_ACTIVITIES:
                    activity_info = InsuranceKnowledgeBase.HIGH_RISK_ACTIVITIES[activity]
                    risk_score += activity_info['premium_impact']
                    risk_factors.append(f"High-risk activity: {activity}")
    
    risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
    
    return {
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendations": {
            "low": "Qualify for standard rates, many options available",
            "medium": "May need underwriting, some premium increase expected",
            "high": "Detailed underwriting required, significant premium impact"
        }.get(risk_level, "Unknown risk level")
    }


# Create the Enhanced Smart Agent
smart_questionnaire_agent = Agent(
    name="smart_insurance_helper",
    model=ollama_model,
    description="Expert insurance advisor with domain knowledge and context awareness",
    instruction=(
        "You are an expert insurance advisor helping users make informed decisions. You have deep knowledge of:\n"
        "- Insurance products and pricing\n" 
        "- Risk assessment and underwriting\n"
        "- Budget planning relative to income\n"
        "- Industry best practices\n\n"
        
        "When helping users:\n"
        "1. ANALYZE their financial context (age, income) from previous answers\n"
        "2. CONSIDER their risk profile (occupation, health, activities)\n"
        "3. PROVIDE income-relative recommendations\n"
        "4. EXPLAIN the insurance reasoning behind your choice\n"
        "5. WARN about premium impacts when relevant\n\n"
        
        "For budget questions: Use the calculate_budget_recommendation tool and recommend based on income percentage.\n"
        "For risk questions: Use assess_risk_factors to understand their profile.\n"
        "For all questions: Use analyze_user_context to get full context.\n\n"
        
        "Always return just the option VALUE (not label) as your answer.\n"
        "Provide clear explanations with specific insurance reasoning.\n"
        "Be honest about premium impacts and trade-offs."
    ),
    tools=[analyze_user_context, calculate_budget_recommendation, assess_risk_factors],
)


class SmartQuestionnaireHelper:
    """Enhanced wrapper class with insurance expertise"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "smart_insurance_questionnaire"
        self.runner = None
        self.session_initialized = False
    
    async def initialize(self):
        """Initialize the smart agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                session_id="default",
                user_id="questionnaire_user"
            )
            self.runner = Runner(
                app_name=self.app_name,
                agents=[smart_questionnaire_agent],
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def help_select_answer(self, question: dict, user_description: str, previous_answers: dict) -> str:
        """
        Get smart recommendation for answering a question
        
        Args:
            question: Question object with options
            user_description: User's description of their situation
            previous_answers: All previous questionnaire answers
            
        Returns:
            Recommended answer value
        """
        await self.initialize()
        
        prompt = f"""
        QUESTION: {question.get('question_text', '')}
        USER SITUATION: "{user_description}"
        
        I need help selecting the best answer from these options:
        {json.dumps([opt.get('label', '') + ' (' + opt.get('value', '') + ')' for opt in question.get('options', [])], indent=2)}
        
        Please analyze my situation using the available tools and recommend the most appropriate option VALUE.
        Consider my financial context and risk profile from previous answers.
        Explain your insurance reasoning.
        """
        
        try:
            session = await self.session_service.get_session(
                app_name=self.app_name, 
                session_id="default"
            )
            
            result = await self.runner.process_message(
                session=session,
                message=prompt
            )
            
            # Extract the recommended answer value from the response
            response_text = result.response if hasattr(result, 'response') else str(result)
            
            # Try to find the answer value in the response
            option_values = [opt.get('value', '') for opt in question.get('options', [])]
            for value in option_values:
                if value in response_text:
                    return value
            
            # Fallback: return first option if no clear match
            return option_values[0] if option_values else ""
            
        except Exception as e:
            print(f"❌ Smart agent error: {e}")
            # Fallback to simple recommendation
            return await self._fallback_recommendation(question, user_description, previous_answers)
    
    async def explain_answer_choice(self, question: dict, selected_answer: str, user_description: str) -> str:
        """
        Explain why a particular answer was chosen
        
        Args:
            question: Question object
            selected_answer: The selected answer value
            user_description: User's original description
            
        Returns:
            Explanation of the choice
        """
        await self.initialize()
        
        # Find the selected option label
        selected_label = "Unknown"
        for opt in question.get('options', []):
            if opt.get('value') == selected_answer:
                selected_label = opt.get('label', selected_answer)
                break
        
        prompt = f"""
        Explain why "{selected_label}" is the best choice for this question:
        
        QUESTION: {question.get('question_text', '')}
        SELECTED: {selected_label} ({selected_answer})
        USER SITUATION: "{user_description}"
        
        Provide a clear explanation of:
        1. Why this choice fits their situation
        2. What insurance implications this choice has
        3. Any premium impacts they should know about
        """
        
        try:
            session = await self.session_service.get_session(
                app_name=self.app_name,
                session_id="default"
            )
            
            result = await self.runner.process_message(
                session=session,
                message=prompt
            )
            
            return result.response if hasattr(result, 'response') else str(result)
            
        except Exception as e:
            print(f"❌ Smart explanation error: {e}")
            return f"I recommended '{selected_label}' based on your situation. This choice should align with your insurance needs and risk profile."
    
    async def _fallback_recommendation(self, question: dict, user_description: str, previous_answers: dict) -> str:
        """Fallback recommendation when AI fails"""
        
        question_id = question.get('id', '')
        options = question.get('options', [])
        
        if not options:
            return ""
        
        # Simple fallback logic based on question type
        if question_id == 'health_status':
            return "good"  # Most common health status
        elif question_id == 'smoking_vaping_habits':
            return "never"  # Safest default
        elif question_id == 'alcohol_consumption':
            return "social"  # Most common moderate choice
        elif question_id == 'exercise_frequency':
            return "weekly"  # Reasonable default
        elif question_id == 'primary_need':
            return "first_time"  # Safe default for uncertain users
        elif question_id == 'coverage_priority':
            return "health_medical"  # Most common priority
        else:
            # Return first option as fallback
            return options[0].get('value', '') if options else ""


# Global instance for easy import
smart_helper = SmartQuestionnaireHelper()


# Compatibility layer for existing code
class QuestionnaireHelper:
    """Compatibility wrapper that uses the smart helper"""
    
    async def help_select_answer(self, question: dict, user_description: str, previous_answers: dict) -> str:
        return await smart_helper.help_select_answer(question, user_description, previous_answers)
    
    async def explain_answer_choice(self, question: dict, selected_answer: str, user_description: str) -> str:
        return await smart_helper.explain_answer_choice(question, selected_answer, user_description)