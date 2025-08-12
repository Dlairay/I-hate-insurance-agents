"""
recommendation_agent.py
=======================
AI agent using Ollama to generate personalized insurance recommendations
"""

import os
import asyncio
import warnings
import json
from typing import Dict, Any, List, Optional

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

# Initialize Ollama model
ollama_model = LiteLlm(model="ollama_chat/llama3:latest")


def analyze_user_profile(questionnaire_responses: dict, applicant_data: dict) -> dict:
    """
    Tool to analyze user profile from questionnaire responses
    
    Args:
        questionnaire_responses: Raw questionnaire responses
        applicant_data: Parsed applicant profile data
        
    Returns:
        Dict with analyzed user profile
    """
    print(f"--- Tool: analyze_user_profile called ---")
    
    # Calculate age
    try:
        from datetime import date
        birth_date = date.fromisoformat(applicant_data.get('dob', '1990-01-01'))
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        age = 30
    
    # Determine profile characteristics
    if age < 30:
        age_group = "young"
    elif age < 55:
        age_group = "middle_aged"
    else:
        age_group = "senior"
    
    # Health risk level
    risk_factors = 0
    if applicant_data.get('smoker'):
        risk_factors += 2
    if applicant_data.get('pre_existing_conditions'):
        risk_factors += len(applicant_data['pre_existing_conditions'])
    
    risk_level = "high" if risk_factors >= 4 else "medium" if risk_factors >= 2 else "low"
    
    # Financial capacity
    budget = questionnaire_responses.get('preferences_budget', 'flexible')
    income = applicant_data.get('annual_income', 50000)
    
    if budget in ['50', '100'] or income < 40000:
        financial_capacity = "budget"
    elif budget in ['500+', 'flexible'] or income > 150000:
        financial_capacity = "premium" 
    else:
        financial_capacity = "moderate"
    
    return {
        "age": age,
        "age_group": age_group,
        "risk_level": risk_level,
        "financial_capacity": financial_capacity,
        "budget": budget,
        "priority": questionnaire_responses.get('preferences_priority', 'best_coverage'),
        "approval_speed": questionnaire_responses.get('preferences_approval_speed', 'flexible')
    }


def calculate_plan_match_score(plan: dict, user_profile: dict) -> dict:
    """
    Tool to calculate how well a plan matches a user's profile
    
    Args:
        plan: Insurance plan data
        user_profile: User profile characteristics
        
    Returns:
        Dict with match score and factors
    """
    print(f"--- Tool: calculate_plan_match_score called ---")
    
    score = 50.0
    factors = []
    
    monthly_premium = plan.get('total_monthly_premium', 500)
    company_rating = plan.get('company_rating', 4.0)
    instant_approval = plan.get('instant_approval', False)
    
    # Budget matching
    budget = user_profile.get('budget', 'flexible')
    budget_limits = {'50': 50, '100': 100, '200': 200, '300': 300, '500': 500}
    
    if budget in budget_limits:
        limit = budget_limits[budget]
        if monthly_premium <= limit:
            score += 20
            factors.append("Fits within budget")
        elif monthly_premium > limit * 1.5:
            score -= 20
            factors.append("Over budget")
    
    # Age group matching
    age_group = user_profile.get('age_group', 'middle_aged')
    if age_group == 'young' and monthly_premium < 200:
        score += 10
        factors.append("Affordable for young adults")
    elif age_group == 'senior' and company_rating >= 4.5:
        score += 15
        factors.append("Trusted company for seniors")
    
    # Risk level matching
    risk_level = user_profile.get('risk_level', 'low')
    if risk_level == 'high' and not instant_approval:
        score += 10
        factors.append("Accepts higher risk applicants")
    elif risk_level == 'low' and instant_approval:
        score += 15
        factors.append("Quick approval for low-risk profile")
    
    # Priority matching
    priority = user_profile.get('priority', 'best_coverage')
    if priority == 'lowest_cost' and monthly_premium < 250:
        score += 20
        factors.append("Low cost matches priority")
    elif priority == 'company_reputation' and company_rating >= 4.5:
        score += 20
        factors.append("High-rated company matches priority")
    elif priority == 'fast_approval' and instant_approval:
        score += 20
        factors.append("Instant approval matches priority")
    
    return {
        "match_score": max(0, min(100, score)),
        "factors": factors,
        "monthly_premium": monthly_premium,
        "company_rating": company_rating
    }


def generate_recommendation_reasons(plan: dict, user_profile: dict, match_score: float) -> dict:
    """
    Tool to generate specific reasons why a plan is recommended
    
    Args:
        plan: Insurance plan data
        user_profile: User profile
        match_score: Calculated match score
        
    Returns:
        Dict with recommendation reasons, pros, and cons
    """
    print(f"--- Tool: generate_recommendation_reasons called ---")
    
    company_name = plan.get('company_name', 'Insurance Company')
    monthly_premium = plan.get('total_monthly_premium', 0)
    company_rating = plan.get('company_rating', 4.0)
    coverage_amount = plan.get('coverage_amount', 0)
    
    # Generate reasons based on user profile
    reasons = []
    pros = []
    cons = []
    
    # Cost-related reasons
    if monthly_premium < 200:
        reasons.append(f"Affordable premium of ${monthly_premium}/month fits budget-conscious approach")
        pros.append("Very affordable monthly premium")
    elif monthly_premium > 400:
        cons.append("Higher monthly cost")
    
    # Company reputation
    if company_rating >= 4.5:
        reasons.append(f"{company_name} has excellent {company_rating}/5.0 rating for reliability")
        pros.append("Highly rated insurance company")
    elif company_rating < 4.0:
        cons.append("Lower company rating")
    
    # Coverage
    if coverage_amount >= 1000000:
        reasons.append(f"Comprehensive ${coverage_amount:,.0f} coverage provides strong protection")
        pros.append("High coverage amount")
    elif coverage_amount < 250000:
        cons.append("Limited coverage amount")
    
    # Instant approval
    if plan.get('instant_approval', False):
        reasons.append("Instant approval process gets you covered immediately")
        pros.append("No waiting - instant approval")
    else:
        cons.append("May require underwriting review")
    
    # Profile-specific reasons
    age_group = user_profile.get('age_group', 'middle_aged')
    if age_group == 'young' and monthly_premium < 250:
        reasons.append("Plan is well-suited for young professionals starting their careers")
    elif age_group == 'senior':
        reasons.append("Reliable coverage for retirees and seniors")
    
    # Ensure minimum items
    if len(pros) < 2:
        pros.append("Competitive insurance option")
    if len(cons) == 0:
        cons.append("Standard industry terms apply")
    
    return {
        "reasons": reasons[:3],  # Top 3 reasons
        "pros": pros[:4],        # Max 4 pros
        "cons": cons[:3],        # Max 3 cons
        "match_score": match_score
    }


# Create the Recommendation Agent
recommendation_agent = Agent(
    name="recommendation_engine",
    model=ollama_model,
    description="AI assistant that generates personalized insurance recommendations",
    instruction=(
        "You are an intelligent insurance recommendation specialist. Your role is to:\n"
        "1. Analyze user profiles from questionnaire data\n"
        "2. Match insurance plans to user needs and preferences\n"
        "3. Generate personalized recommendations with clear explanations\n"
        "4. Rank plans by how well they fit the user's specific situation\n\n"
        "When creating recommendations:\n"
        "- Consider the user's age, health, budget, and priorities\n"
        "- Explain WHY each plan is recommended in simple terms\n"
        "- Be honest about pros and cons\n"
        "- Prioritize plans that truly fit the user's needs\n"
        "- Provide confidence scores based on how well plans match\n\n"
        "Focus on being helpful, transparent, and acting in the user's best interest."
    ),
    tools=[analyze_user_profile, calculate_plan_match_score, generate_recommendation_reasons],
)


class RecommendationAgent:
    """AI agent for generating personalized insurance recommendations"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "insurance_recommendations"
        self.runner = None
        self.session_initialized = False
    
    async def initialize(self):
        """Initialize the agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id="recommendation_user",
                session_id="session_001"
            )
            self.runner = Runner(
                agent=recommendation_agent,
                app_name=self.app_name,
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def generate_recommendations(self, insurance_cards: List[Dict[str, Any]], 
                                     questionnaire_responses: Dict[str, Any],
                                     applicant_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations for insurance plans
        
        Args:
            insurance_cards: List of standardized insurance cards
            questionnaire_responses: Raw questionnaire responses
            applicant_data: Parsed applicant profile
            
        Returns:
            List of recommendations with rankings and explanations
        """
        await self.initialize()
        
        if not insurance_cards:
            return []
        
        recommendations = []
        
        for rank, card in enumerate(insurance_cards, 1):
            # Create context for the agent
            context = f"""
Generate a personalized recommendation for this insurance plan:

Insurance Plan:
- Company: {card.get('company_name', '')}
- Plan: {card.get('plan_name', '')}
- Cost: {card.get('monthly_cost', '')}
- Coverage: {card.get('coverage_amount', '')}
- Rating: {card.get('company_rating', 0)}/5.0
- Benefits: {', '.join(card.get('key_benefits', []))}
- Instant Approval: {card.get('instant_approval', False)}
- Value Score: {card.get('value_score', 0)}

User Profile:
- Age: Calculated from DOB {applicant_data.get('dob', '')}
- Smoker: {applicant_data.get('smoker', False)}
- Health Conditions: {applicant_data.get('pre_existing_conditions', [])}
- Budget Preference: {questionnaire_responses.get('preferences_budget', '')}
- Priority: {questionnaire_responses.get('preferences_priority', '')}
- Speed Need: {questionnaire_responses.get('preferences_approval_speed', '')}

Create a recommendation that includes:
1. Why this plan is suitable for this user (2-3 specific reasons)
2. Confidence score (0-100) for how well it matches their needs
3. Top 3 pros for this user specifically
4. Top 2 cons or considerations
5. A summary recommendation in 1-2 sentences

Be specific about why this plan works for THIS user's situation.
"""
            
            content = types.Content(role='user', parts=[types.Part(text=context)])
            
            recommendation = None
            try:
                async for event in self.runner.run_async(
                    user_id="recommendation_user",
                    session_id="session_001",
                    new_message=content
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            response_text = event.content.parts[0].text
                            recommendation = self._create_recommendation_from_response(
                                response_text, card, rank, questionnaire_responses, applicant_data
                            )
                        break
            except Exception as e:
                print(f"Recommendation agent error: {e}")
                # Fallback to rule-based recommendation
                recommendation = self._fallback_generate_recommendation(
                    card, rank, questionnaire_responses, applicant_data
                )
            
            if recommendation:
                recommendations.append(recommendation)
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        
        # Update ranks
        for i, rec in enumerate(recommendations):
            rec['rank'] = i + 1
        
        return recommendations
    
    def _create_recommendation_from_response(self, response_text: str, card: Dict[str, Any],
                                           rank: int, responses: Dict[str, Any], 
                                           applicant: Dict[str, Any]) -> Dict[str, Any]:
        """Create recommendation from agent response"""
        
        plan_id = card.get('plan_id', f'plan_{rank}')
        
        # Extract or calculate confidence score
        confidence = self._calculate_confidence_score(card, responses)
        
        # Generate fallback content (AI response parsing could be added here)
        reasons = self._generate_fallback_reasons(card, responses, applicant)
        pros = self._generate_fallback_pros(card, responses)
        cons = self._generate_fallback_cons(card, responses)
        summary = self._generate_fallback_summary(card, reasons)
        
        return {
            "plan_id": plan_id,
            "rank": rank,
            "confidence_score": confidence,
            "reasons": reasons,
            "profile_match_score": confidence,  # Use same as confidence for simplicity
            "cost_effectiveness": self._calculate_cost_effectiveness(card),
            "recommendation_summary": summary,
            "pros": pros,
            "cons": cons,
            "ai_response": response_text[:500]  # Store partial AI response for debugging
        }
    
    def _calculate_confidence_score(self, card: Dict[str, Any], responses: Dict[str, Any]) -> float:
        """Calculate confidence score"""
        score = 60.0  # Base confidence
        
        monthly_cost = card.get('monthly_cost', '$500/month')
        monthly_amount = float(monthly_cost.replace('$', '').replace('/month', '').replace(',', ''))
        
        # Budget matching
        budget = responses.get('preferences_budget', 'flexible')
        budget_limits = {'50': 50, '100': 100, '200': 200, '300': 300, '500': 500}
        
        if budget in budget_limits and monthly_amount <= budget_limits[budget]:
            score += 20
        
        # Priority matching
        priority = responses.get('preferences_priority', 'best_coverage')
        if priority == 'lowest_cost' and monthly_amount < 250:
            score += 15
        elif priority == 'company_reputation' and card.get('company_rating', 0) >= 4.5:
            score += 15
        elif priority == 'fast_approval' and card.get('instant_approval', False):
            score += 15
        
        # Value score factor
        value_score = card.get('value_score', 50)
        score += (value_score - 50) * 0.3
        
        return max(0, min(100, score))
    
    def _generate_fallback_reasons(self, card: Dict[str, Any], responses: Dict[str, Any], 
                                  applicant: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendation reasons"""
        reasons = []
        
        monthly_cost = card.get('monthly_cost', '$0/month')
        company_name = card.get('company_name', 'This company')
        company_rating = card.get('company_rating', 4.0)
        
        # Cost reason
        if 'budget' in responses.get('preferences_priority', '').lower():
            reasons.append({
                "factor": "cost",
                "weight": 0.8,
                "description": f"Affordable {monthly_cost} fits your budget-conscious approach"
            })
        
        # Company reputation reason
        if company_rating >= 4.5:
            reasons.append({
                "factor": "reputation", 
                "weight": 0.7,
                "description": f"{company_name} has excellent {company_rating}/5.0 rating"
            })
        
        # Coverage reason
        coverage_amount = card.get('coverage_amount', '$0')
        if '500,000' in coverage_amount or '1,000,000' in coverage_amount:
            reasons.append({
                "factor": "coverage",
                "weight": 0.6,
                "description": f"Comprehensive {coverage_amount} provides strong protection"
            })
        
        return reasons[:3]  # Top 3 reasons
    
    def _generate_fallback_pros(self, card: Dict[str, Any], responses: Dict[str, Any]) -> List[str]:
        """Generate pros list"""
        pros = []
        
        monthly_cost = card.get('monthly_cost', '$500/month')
        monthly_amount = float(monthly_cost.replace('$', '').replace('/month', '').replace(',', ''))
        
        if monthly_amount < 200:
            pros.append("Very affordable monthly premium")
        
        if card.get('company_rating', 0) >= 4.5:
            pros.append("Highly rated insurance company")
        
        if card.get('instant_approval', False):
            pros.append("Instant approval available")
        
        if len(card.get('key_benefits', [])) >= 4:
            pros.append("Comprehensive benefit package")
        
        if card.get('best_value', False):
            pros.append("Best overall value")
        
        return pros[:4]
    
    def _generate_fallback_cons(self, card: Dict[str, Any], responses: Dict[str, Any]) -> List[str]:
        """Generate cons list"""
        cons = []
        
        monthly_cost = card.get('monthly_cost', '$0/month')
        monthly_amount = float(monthly_cost.replace('$', '').replace('/month', '').replace(',', ''))
        
        if monthly_amount > 400:
            cons.append("Higher monthly premium")
        
        if card.get('company_rating', 5.0) < 4.0:
            cons.append("Lower company rating")
        
        if not card.get('instant_approval', True):
            cons.append("May require underwriting review")
        
        if not cons:
            cons.append("Standard industry terms apply")
        
        return cons[:3]
    
    def _generate_fallback_summary(self, card: Dict[str, Any], reasons: List[Dict[str, Any]]) -> str:
        """Generate recommendation summary"""
        company_name = card.get('company_name', 'This plan')
        monthly_cost = card.get('monthly_cost', '')
        
        if reasons:
            key_factor = reasons[0]['factor']
            if key_factor == 'cost':
                return f"{company_name} at {monthly_cost} offers excellent affordability for budget-conscious customers."
            elif key_factor == 'reputation':
                return f"{company_name} provides reliable coverage from a highly-rated insurance provider."
            elif key_factor == 'coverage':
                return f"{company_name} delivers comprehensive protection with strong coverage benefits."
        
        return f"{company_name} at {monthly_cost} provides a balanced insurance solution."
    
    def _calculate_cost_effectiveness(self, card: Dict[str, Any]) -> float:
        """Calculate cost effectiveness score"""
        monthly_cost = card.get('monthly_cost', '$500/month')
        monthly_amount = float(monthly_cost.replace('$', '').replace('/month', '').replace(',', ''))
        coverage_amount_str = card.get('coverage_amount', '$500,000')
        coverage_amount = float(coverage_amount_str.replace('$', '').replace(',', ''))
        
        # Calculate cost per $1000 of coverage
        cost_ratio = monthly_amount / (coverage_amount / 1000) if coverage_amount > 0 else 10
        
        # Convert to 0-100 scale (lower cost ratio = higher effectiveness)
        if cost_ratio < 0.5:
            return 90
        elif cost_ratio < 1.0:
            return 75
        elif cost_ratio < 2.0:
            return 60
        else:
            return 40
    
    def _fallback_generate_recommendation(self, card: Dict[str, Any], rank: int,
                                        responses: Dict[str, Any], 
                                        applicant: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback recommendation when AI fails"""
        return self._create_recommendation_from_response("", card, rank, responses, applicant)


# Synchronous wrapper for FastAPI
class RecommendationEngine:
    """Synchronous wrapper for the async agent"""
    
    def __init__(self):
        self.agent = RecommendationAgent()
    
    async def generate_recommendations(self, insurance_cards: List[Dict[str, Any]],
                                     questionnaire_responses: Dict[str, Any],
                                     applicant_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async method for FastAPI"""
        return await self.agent.generate_recommendations(
            insurance_cards, questionnaire_responses, applicant_data
        )