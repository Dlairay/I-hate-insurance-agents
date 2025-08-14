"""
response_parser_agent.py
========================
AI agent using Ollama to parse insurance API responses into standardized cards
"""

import os
import asyncio
import warnings
import json
from typing import Dict, Any, List, Optional
import sys
import os

# Add parent directory to path to import shared models
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Suppress Pydantic warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

from backend.shared.models import ApplicantProfile
from backend.agents.scoring_agent import get_scoring_agent, PolicyScore, QuotePlan

# Load environment variables
load_dotenv()

# Suppress logs
import logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("google.adk").setLevel(logging.ERROR)

# Initialize Ollama model
ollama_model = LiteLlm(model="ollama_chat/gpt-oss:20b")


def extract_plan_features(plan_data: dict) -> dict:
    """
    Tool to extract key features from insurance plan data
    
    Args:
        plan_data: Raw plan data from insurance API
        
    Returns:
        Dict with extracted features
    """
    print(f"--- Tool: extract_plan_features called ---")
    
    # Extract basic information
    company_name = plan_data.get('company_name', 'Unknown Insurance')
    plan_name = plan_data.get('plan_name', 'Insurance Plan')
    monthly_premium = plan_data.get('total_monthly_premium', 0)
    coverage_amount = plan_data.get('coverage_amount', 0)
    
    # Extract coverage details
    coverage_details = plan_data.get('coverage_details', {})
    coverage_types = coverage_details.get('coverage_types', [])
    
    return {
        "company_name": company_name,
        "plan_name": plan_name,
        "monthly_premium": monthly_premium,
        "coverage_amount": coverage_amount,
        "coverage_types": coverage_types,
        "raw_data": plan_data
    }


def calculate_value_score(plan_data: dict, user_preferences: dict) -> dict:
    """
    Tool to calculate a value score for an insurance plan
    
    Args:
        plan_data: Plan information
        user_preferences: User's preferences and priorities
        
    Returns:
        Dict with calculated value score and factors
    """
    print(f"--- Tool: calculate_value_score called ---")
    
    score = 50.0  # Base score
    factors = []
    
    # Cost factor
    monthly_premium = plan_data.get('total_monthly_premium', 500)
    budget = user_preferences.get('preferences_budget', 'flexible')
    
    if budget in ['50', '100'] and monthly_premium < 150:
        score += 20
        factors.append("Fits budget")
    elif budget in ['500+', 'flexible'] and monthly_premium > 300:
        score += 10
        factors.append("Premium plan")
    
    # Company rating factor
    company_rating = plan_data.get('company_rating', 4.0)
    if company_rating >= 4.5:
        score += 15
        factors.append("High-rated company")
    
    # Coverage factor
    coverage_amount = plan_data.get('coverage_amount', 0)
    if coverage_amount >= 1000000:
        score += 15
        factors.append("High coverage")
    
    return {
        "score": min(100, max(0, score)),
        "factors": factors,
        "monthly_premium": monthly_premium,
        "company_rating": company_rating
    }


def categorize_benefits(coverage_types: List[str], riders: List[str] = None) -> dict:
    """
    Tool to categorize and format insurance benefits
    
    Args:
        coverage_types: List of coverage types
        riders: List of additional riders
        
    Returns:
        Dict with categorized benefits
    """
    print(f"--- Tool: categorize_benefits called ---")
    
    # Map technical terms to user-friendly benefits
    benefit_mapping = {
        "hospitalization": "Hospital coverage",
        "emergency": "Emergency care",
        "preventive_care": "Preventive care included",
        "prescription_basic": "Prescription coverage",
        "prescription_full": "Full prescription benefits", 
        "specialist": "Specialist visits",
        "mental_health": "Mental health coverage",
        "death_benefit": "Death benefit protection",
        "terminal_illness": "Terminal illness coverage",
        "cash_value": "Cash value growth",
        "cancer": "Cancer coverage",
        "heart_attack": "Heart attack coverage",
        "stroke": "Stroke coverage"
    }
    
    key_benefits = []
    for coverage_type in coverage_types[:4]:  # Limit to top 4
        if coverage_type in benefit_mapping:
            key_benefits.append(benefit_mapping[coverage_type])
    
    # Add rider benefits
    rider_mapping = {
        "DENTAL": "Dental coverage",
        "VISION": "Vision coverage",
        "WELLNESS": "Wellness benefits",
        "CRITICAL_ILLNESS": "Critical illness rider",
        "DISABILITY": "Disability coverage",
        "ACCIDENTAL_DEATH": "Accidental death benefit"
    }
    
    if riders:
        for rider in riders[:2]:  # Add up to 2 riders
            if rider in rider_mapping:
                key_benefits.append(rider_mapping[rider])
    
    # Ensure minimum benefits
    if len(key_benefits) < 2:
        key_benefits.append("Comprehensive coverage")
    
    return {
        "key_benefits": key_benefits[:4],  # Maximum 4 benefits
        "total_coverage_types": len(coverage_types),
        "total_riders": len(riders) if riders else 0
    }


# Create the Response Parser Agent
response_parser_agent = Agent(
    name="response_parser",
    model=ollama_model,
    description="AI assistant that parses insurance API responses into user-friendly cards",
    instruction=(
        "You are an intelligent insurance response parser. Your role is to:\n"
        "1. Take raw insurance API responses\n"
        "2. Extract the most important information for customers\n"
        "3. Create standardized, user-friendly insurance cards\n"
        "4. Assign appropriate labels (Best Value, Fastest Approval, etc.)\n\n"
        "When processing insurance plans:\n"
        "- Focus on what customers care about most: cost, coverage, company reputation\n"
        "- Translate technical terms into plain English\n"
        "- Highlight the most compelling benefits (max 4)\n"
        "- Calculate fair value scores based on multiple factors\n"
        "- Assign special labels based on standout features\n\n"
        "Always prioritize clarity and helpfulness for insurance shoppers."
    ),
    tools=[extract_plan_features, calculate_value_score, categorize_benefits],
)


class ResponseParserAgent:
    """AI agent for parsing insurance API responses"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "insurance_parser"
        self.runner = None
        self.session_initialized = False
    
    async def initialize(self):
        """Initialize the agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id="parser_user",
                session_id="session_001"
            )
            self.runner = Runner(
                agent=response_parser_agent,
                app_name=self.app_name,
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def parse_insurance_response(self, raw_response: Dict[str, Any], 
                                     user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse raw insurance API response into standardized cards
        
        Args:
            raw_response: Raw response from insurance API
            user_preferences: User preferences from questionnaire
            
        Returns:
            List of standardized insurance cards
        """
        await self.initialize()
        
        # Extract plans from response
        plans = raw_response.get("recommended_plans", [])
        if not plans:
            plans = raw_response.get("plans", [])
        
        if not plans:
            return []
        
        parsed_cards = []
        
        for i, plan in enumerate(plans):
            # Create context for the agent
            context = f"""
Parse this insurance plan into a user-friendly card:

Raw Plan Data:
{json.dumps(plan, indent=2)}

User Preferences:
- Budget: {user_preferences.get('preferences_budget', 'flexible')}
- Priority: {user_preferences.get('preferences_priority', 'best_coverage')}
- Approval Speed: {user_preferences.get('preferences_approval_speed', 'flexible')}

Create a standardized insurance card with:
1. Clear monthly cost (formatted as $XXX/month)
2. Coverage amount (formatted as $XXX,XXX)
3. Top 3-4 key benefits (in plain English)
4. Value score (0-100 based on cost, coverage, company rating)
5. Special labels if applicable (Best Value, Fastest Approval, Recommended)

Return the parsed card information in a clear, structured format.
"""
            
            content = types.Content(role='user', parts=[types.Part(text=context)])
            
            parsed_card = None
            try:
                async for event in self.runner.run_async(
                    user_id="parser_user",
                    session_id="session_001",
                    new_message=content
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            response_text = event.content.parts[0].text
                            parsed_card = self._create_card_from_response(
                                response_text, plan, user_preferences, i
                            )
                        break
            except Exception as e:
                print(f"Parser agent error: {e}")
                # Fallback to rule-based parsing
                parsed_card = self._fallback_parse_plan(plan, user_preferences, i)
            
            if parsed_card:
                parsed_cards.append(parsed_card)
        
        # Apply rankings and labels
        parsed_cards = self._apply_rankings_and_labels(parsed_cards, user_preferences)
        
        return parsed_cards
    
    def _create_card_from_response(self, response_text: str, plan: Dict[str, Any], 
                                  user_preferences: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create insurance card from agent response"""
        
        # Extract key information
        plan_id = plan.get("plan_id", f"plan_{index}")
        company_name = plan.get("company_name", "Unknown Insurance")
        plan_name = plan.get("plan_name", "Insurance Plan")
        
        # Format monetary values
        monthly_premium = plan.get("total_monthly_premium", 0)
        coverage_amount = plan.get("coverage_amount", 0)
        
        monthly_cost = f"${monthly_premium:,.0f}/month"
        coverage_amount_str = f"${coverage_amount:,.0f}"
        
        # Extract benefits (use AI response or fallback)
        key_benefits = self._extract_benefits_from_plan(plan)
        
        # Calculate value score
        value_score = self._calculate_simple_value_score(plan, user_preferences)
        
        # Get additional details
        company_rating = plan.get("company_rating", 4.0)
        instant_approval = plan.get("instant_approval", False)
        deductible = plan.get("deductible")
        
        return {
            "plan_id": plan_id,
            "company_name": company_name,
            "plan_name": plan_name,
            "monthly_cost": monthly_cost,
            "coverage_amount": coverage_amount_str,
            "key_benefits": key_benefits,
            "instant_approval": instant_approval,
            "company_rating": company_rating,
            "value_score": value_score,
            "deductible": f"${deductible:,.0f} deductible" if deductible else None,
            "waiting_period": self._format_waiting_periods(plan.get("waiting_periods", {})),
            "recommended": False,  # Will be set by ranking logic
            "best_value": False,   # Will be set by ranking logic
            "fastest_approval": False  # Will be set by ranking logic
        }
    
    def _extract_benefits_from_plan(self, plan: Dict[str, Any]) -> List[str]:
        """Extract key benefits from plan data"""
        benefits = []
        
        # Check coverage details
        coverage_details = plan.get("coverage_details", {})
        coverage_types = coverage_details.get("coverage_types", [])
        
        # Map to user-friendly terms
        benefit_mapping = {
            "hospitalization": "Hospital coverage",
            "emergency": "Emergency care", 
            "preventive_care": "Preventive care included",
            "prescription_basic": "Prescription coverage",
            "prescription_full": "Full prescription benefits",
            "specialist": "Specialist visits",
            "mental_health": "Mental health coverage",
            "death_benefit": "Death benefit protection",
            "terminal_illness": "Terminal illness coverage",
            "cash_value": "Cash value growth"
        }
        
        for coverage_type in coverage_types[:3]:
            if coverage_type in benefit_mapping:
                benefits.append(benefit_mapping[coverage_type])
        
        # Add rider benefits
        rider_premiums = plan.get("rider_premiums", {})
        rider_mapping = {
            "DENTAL": "Dental coverage",
            "VISION": "Vision coverage", 
            "WELLNESS": "Wellness benefits"
        }
        
        for rider in list(rider_premiums.keys())[:2]:
            if rider in rider_mapping:
                benefits.append(rider_mapping[rider])
        
        # Ensure minimum benefits
        if len(benefits) < 2:
            product_type = coverage_details.get("product_type", "")
            if "HEALTH" in product_type:
                benefits.extend(["Medical coverage", "Healthcare benefits"])
            elif "LIFE" in product_type:
                benefits.extend(["Life protection", "Family security"])
        
        return benefits[:4]  # Maximum 4 benefits
    
    def _calculate_simple_value_score(self, plan: Dict[str, Any], 
                                     user_preferences: Dict[str, Any]) -> float:
        """Calculate value score"""
        score = 50.0
        
        # Price factor
        monthly_premium = plan.get("total_monthly_premium", 500)
        if monthly_premium < 200:
            score += 20
        elif monthly_premium > 400:
            score -= 15
        
        # Company rating factor
        company_rating = plan.get("company_rating", 4.0)
        score += (company_rating - 4.0) * 15
        
        # Coverage amount factor
        coverage_amount = plan.get("coverage_amount", 0)
        if coverage_amount >= 1000000:
            score += 15
        elif coverage_amount >= 500000:
            score += 10
        
        # Instant approval bonus
        if plan.get("instant_approval", False):
            score += 10
        
        return max(0, min(100, score))
    
    def _format_waiting_periods(self, waiting_periods: Dict[str, int]) -> Optional[str]:
        """Format waiting periods"""
        if not waiting_periods:
            return None
        
        general = waiting_periods.get("general", 0)
        if general == 0:
            return "No waiting period"
        elif general <= 30:
            return f"{general} day waiting period"
        elif general <= 365:
            months = general // 30
            return f"{months} month waiting period"
        else:
            years = general // 365
            return f"{years} year waiting period"
    
    def _apply_rankings_and_labels(self, cards: List[Dict[str, Any]], 
                                  user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply special labels and rankings"""
        if not cards:
            return cards
        
        # Sort by value score
        cards.sort(key=lambda x: x["value_score"], reverse=True)
        
        # Apply labels
        if cards:
            cards[0]["recommended"] = True  # Top card is recommended
        
        # Find best value (highest value score)
        best_value_card = max(cards, key=lambda x: x["value_score"])
        best_value_card["best_value"] = True
        
        # Find fastest approval
        instant_cards = [c for c in cards if c["instant_approval"]]
        if instant_cards:
            fastest = max(instant_cards, key=lambda x: x["value_score"])
            fastest["fastest_approval"] = True
        
        return cards
    
    def _fallback_parse_plan(self, plan: Dict[str, Any], user_preferences: Dict[str, Any], 
                           index: int) -> Dict[str, Any]:
        """Fallback parsing when AI fails"""
        return self._create_card_from_response("", plan, user_preferences, index)


# Synchronous wrapper for FastAPI
class ResponseParser:
    """Synchronous wrapper for the async agent"""
    
    def __init__(self):
        self.agent = ResponseParserAgent()
    
    async def parse_insurance_response(self, raw_response: Dict[str, Any],
                                     user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse insurance response and include scoring"""
        
        # Get basic cards from AI parsing
        cards = await self.agent.parse_insurance_response(raw_response, user_preferences)
        
        # Create ApplicantProfile from user preferences for scoring
        applicant = self._create_applicant_profile(user_preferences)
        
        # Create InsurancePlan objects from raw response
        plans = self._create_insurance_plans(raw_response)
        
        # Score the plans
        scoring_agent = get_scoring_agent()
        scored_plans = scoring_agent.score_multiple_policies(plans, applicant)
        
        # Enhance cards with scoring information
        enhanced_cards = self._enhance_cards_with_scores(cards, scored_plans)
        
        return enhanced_cards
    
    def _create_applicant_profile(self, user_preferences: Dict[str, Any]) -> ApplicantProfile:
        """Create ApplicantProfile from questionnaire responses"""
        
        # Extract fields with sensible defaults
        profile_data = {
            "first_name": user_preferences.get("personal_first_name", "User"),
            "last_name": user_preferences.get("personal_last_name", "Person"),
            "dob": user_preferences.get("personal_dob", "1990-01-01"),
            "gender": user_preferences.get("personal_gender", "OTHER"),
            "email": user_preferences.get("personal_email", "user@example.com"),
            "phone": user_preferences.get("personal_phone", "000-000-0000"),
            "address_line1": user_preferences.get("address_line1", "123 Main St"),
            "city": user_preferences.get("address_city", "Anytown"),
            "state": user_preferences.get("address_state", "CA"),
            "postal_code": user_preferences.get("address_postal_code", "12345"),
            "annual_income": float(user_preferences.get("annual_income", 50000))
        }
        
        # Add health and lifestyle data
        smoking_habits = user_preferences.get("smoking_vaping_habits", "never")
        profile_data["smoker"] = smoking_habits not in ["never", "quit_over_year"]
        
        # Map exercise habits
        exercise_mapping = {
            "daily": "daily",
            "regular": "3-5x per week", 
            "occasional": "1-2x per week",
            "minimal": "rarely",
            "sedentary": "never"
        }
        profile_data["exercise_frequency"] = exercise_mapping.get(
            user_preferences.get("exercise_habits"), "unknown"
        )
        
        # Map alcohol consumption
        alcohol_mapping = {
            "none": "never",
            "rare": "rarely",
            "light": "light",
            "moderate": "moderate", 
            "regular": "regular",
            "heavy": "heavy"
        }
        profile_data["alcohol_consumption"] = alcohol_mapping.get(
            user_preferences.get("alcohol_consumption"), "unknown"
        )
        
        return ApplicantProfile(**profile_data)
    
    def _create_insurance_plans(self, raw_response: Dict[str, Any]) -> List[QuotePlan]:
        """Create QuotePlan objects from raw API response"""
        plans = []
        
        # Extract quotes from raw response
        quotes_list = raw_response.get("quotes", [])
        
        for quote_data in quotes_list:
            try:
                # Extract recommended_plans from each quote
                recommended_plans = quote_data.get("recommended_plans", [])
                for plan_data in recommended_plans:
                    # Map raw data to QuotePlan model
                    plan = QuotePlan(
                        plan_id=plan_data.get("plan_id", "unknown"),
                        plan_name=plan_data.get("plan_name", "Unknown Plan"),
                        company_id=quote_data.get("company_id", "unknown"),
                        company_name=quote_data.get("company_name", "Unknown Company"),
                        company_rating=quote_data.get("company_rating", 3.5),
                        coverage_amount=plan_data.get("coverage_amount", 100000),
                        deductible=plan_data.get("deductible", 0),
                        base_premium=plan_data.get("base_premium", 0),
                        rider_premiums=plan_data.get("rider_premiums", {}),
                        taxes_fees=plan_data.get("taxes_fees", 0),
                        total_monthly_premium=plan_data.get("total_monthly_premium", 0),
                        total_annual_premium=plan_data.get("total_annual_premium", 0),
                        coverage_details=plan_data.get("coverage_details", {}),
                        exclusions=plan_data.get("exclusions", []),
                        waiting_periods=plan_data.get("waiting_periods", {})
                    )
                    plans.append(plan)
            except Exception as e:
                print(f"Error creating QuotePlan: {e}")
                continue
        
        return plans
    
    def _enhance_cards_with_scores(self, cards: List[Dict[str, Any]], 
                                  scored_plans: List[PolicyScore]) -> List[Dict[str, Any]]:
        """Enhance insurance cards with scoring information"""
        
        # Create lookup map by plan_id
        score_map = {score.plan_id: score for score in scored_plans}
        
        enhanced_cards = []
        
        for card in cards:
            plan_id = card.get("plan_id", "")
            
            if plan_id in score_map:
                score = score_map[plan_id]
                
                # Add scoring information to card
                card["scores"] = {
                    "overall_score": score.overall_score,
                    "overall_category": score.overall_category.value,
                    "affordability_score": score.affordability_score,
                    "ease_of_claims_score": score.ease_of_claims_score,
                    "coverage_ratio_score": score.coverage_ratio_score,
                    "income_percentage": score.income_percentage,
                    "value_proposition": score.value_proposition
                }
                
                # Update existing fields with score-based insights
                card["value_score"] = score.overall_score
                
                # Add badges based on scores
                if score.affordability_score >= 85:
                    card["badges"] = card.get("badges", []) + ["Great Value"]
                if score.ease_of_claims_score >= 90:
                    card["badges"] = card.get("badges", []) + ["Easy Claims"]
                if score.coverage_ratio_score >= 85:
                    card["badges"] = card.get("badges", []) + ["Excellent Coverage"]
                
                # Update recommendation flags
                if score.overall_score >= 85:
                    card["recommended"] = True
                if score.affordability_score >= 90:
                    card["best_value"] = True
            
            enhanced_cards.append(card)
        
        # Sort by overall score (descending)
        enhanced_cards.sort(key=lambda x: x.get("scores", {}).get("overall_score", 0), reverse=True)
        
        return enhanced_cards