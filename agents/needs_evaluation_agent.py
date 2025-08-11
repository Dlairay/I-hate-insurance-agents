"""
Needs Evaluation Agent
======================
Agent that evaluates user's insurance needs and determines next steps using schema-enforced LLM
"""

import logging
from typing import Optional, List
import asyncio
import warnings
import json

# Suppress Pydantic warnings (consistent with other agents)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

# Google ADK imports (same pattern as other agents)  
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress logs (consistent with other agents)
logging.basicConfig(level=logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("google.adk").setLevel(logging.ERROR)

# Initialize Ollama model (following same pattern)
ollama_model = LiteLlm(model="ollama_chat/llama3:latest")

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import UserProfile, ExistingPolicyAssessment, NeedsEvaluationSchema

logger = logging.getLogger(__name__)

def analyze_coverage_needs(user_profile: dict, existing_analysis: dict) -> dict:
    """
    Tool function to analyze user's coverage needs
    
    Args:
        user_profile: UserProfile data as dict
        existing_analysis: ExistingPolicyAssessment data as dict or None
        
    Returns:
        Dict with coverage analysis
    """
    print(f"--- Tool: analyze_coverage_needs called ---")
    
    age = user_profile.get('age', 30)
    income = user_profile.get('annual_income', 50000)
    existing_coverage = user_profile.get('existing_coverage_type', 'none')
    primary_need = user_profile.get('primary_need', 'first_time')
    
    # Basic coverage need calculation
    recommended_life_coverage = income * (12 if age < 40 else 10 if age < 50 else 8)
    recommended_health_coverage = max(income * 2, 100000)
    
    should_get_quotes = True
    reasoning = ""
    
    # Decision logic
    if existing_coverage == "none":
        should_get_quotes = True
        reasoning = "No existing coverage - definitely need insurance quotes"
    elif primary_need == "save_money":
        should_get_quotes = True
        reasoning = "User wants to save money - compare current vs new options"
    elif primary_need == "compare_options":
        should_get_quotes = True
        reasoning = "User explicitly wants to compare options"
    elif existing_analysis and existing_analysis.get('primary_action') == 'no_action':
        should_get_quotes = False
        reasoning = "Existing coverage is adequate - no quotes needed"
    
    return {
        "should_get_quotes": should_get_quotes,
        "reasoning": reasoning,
        "recommended_life_coverage": recommended_life_coverage,
        "recommended_health_coverage": recommended_health_coverage,
        "coverage_gap_analysis": {
            "has_life_gap": existing_coverage in ["none", "employer_basic"],
            "has_health_gap": existing_coverage == "none",
            "has_critical_illness_gap": "critical" not in existing_coverage
        }
    }

def determine_priority_actions(coverage_analysis: dict, user_timeline: str) -> dict:
    """
    Tool function to determine priority actions for the user
    
    Args:
        coverage_analysis: Results from coverage needs analysis
        user_timeline: User's urgency level
        
    Returns:
        Dict with prioritized actions
    """
    print(f"--- Tool: determine_priority_actions called ---")
    
    actions = []
    urgency_mapping = {
        "immediately": "immediate",
        "within_month": "soon", 
        "within_3_months": "soon",
        "exploring": "no_rush"
    }
    
    urgency = urgency_mapping.get(user_timeline, "can_wait")
    
    if coverage_analysis.get("should_get_quotes"):
        if coverage_analysis.get("coverage_gap_analysis", {}).get("has_health_gap"):
            actions.append("Get health insurance quotes immediately")
        if coverage_analysis.get("coverage_gap_analysis", {}).get("has_life_gap"):
            actions.append("Consider term life insurance")
        actions.append("Compare 3-5 insurance providers")
    else:
        actions.append("Your current coverage appears adequate")
        actions.append("Focus on other financial priorities")
    
    if urgency == "immediate":
        actions.insert(0, "⚠️ Act quickly to avoid coverage gaps")
    
    return {
        "urgency_level": urgency,
        "priority_actions": actions[:4],  # Max 4 actions
        "timeline_advice": f"Based on your timeline ({user_timeline}), {'immediate action recommended' if urgency == 'immediate' else 'you have time to compare options'}"
    }

class NeedsEvaluationAgent:
    """Agent that evaluates user's insurance needs using schema-enforced LLM"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.app_name = "needs_evaluation"
        self.runner = None
        self.session_initialized = False
        
        # Create the agent with tools
        self.agent = Agent(
            name="needs_evaluator",
            model=ollama_model,
            description="Insurance needs assessment expert",
            instruction="""
You are an insurance needs assessment expert. Your job is to analyze a user's profile and existing coverage to determine what they actually need.

Key Responsibilities:
1. Determine if they need new insurance quotes (don't push unnecessary insurance)
2. Calculate appropriate coverage amounts based on income, age, and situation
3. Identify their biggest insurance priority
4. Provide specific, actionable next steps

Decision Guidelines:
- GET QUOTES if: no coverage, significant gaps, wants to save money, major life changes
- SKIP QUOTES if: well covered, no significant savings opportunity, just exploring without need
- Be conservative - don't push insurance on people who are already well-covered
- Consider their timeline and urgency level

Use the provided tools to analyze their situation systematically.
Your output MUST conform exactly to the NeedsEvaluationSchema.
            """,
            tools=[analyze_coverage_needs, determine_priority_actions]
        )
    
    async def initialize(self):
        """Initialize the agent session"""
        if not self.session_initialized:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id="needs_user",
                session_id="session_001"
            )
            self.runner = Runner(
                agent=self.agent,
                app_name=self.app_name,
                session_service=self.session_service
            )
            self.session_initialized = True
    
    async def evaluate_insurance_needs(
        self, 
        user_profile: UserProfile, 
        existing_policy_analysis: Optional[ExistingPolicyAssessment] = None
    ) -> NeedsEvaluationSchema:
        """
        Evaluate user's insurance needs using schema-enforced LLM
        
        Args:
            user_profile: User's questionnaire data
            existing_policy_analysis: Analysis of existing coverage (if any)
            
        Returns:
            NeedsEvaluationSchema with structured recommendations
        """
        await self.initialize()
        
        # Prepare context for the agent
        context = f"""
Evaluate insurance needs for this user:

USER PROFILE:
- Age: {user_profile.age} years old
- Annual Income: ${user_profile.annual_income:,}
- Health Status: {user_profile.health_status}
- Current Coverage: {user_profile.existing_coverage_type} (amount: {user_profile.existing_coverage_amount})
- Primary Need: {user_profile.primary_need}
- Budget: {user_profile.monthly_budget} per month
- Coverage Priority: {user_profile.coverage_priority} 
- Timeline: {user_profile.urgency}

EXISTING POLICY ANALYSIS:
{json.dumps(existing_policy_analysis.dict() if existing_policy_analysis else None, indent=2)}

TASK:
Use the analyze_coverage_needs and determine_priority_actions tools to evaluate their situation.
Then provide a structured assessment following NeedsEvaluationSchema format.

Key Questions:
1. Should we get new insurance quotes for this person?
2. What type of coverage do they need most?
3. How much coverage is appropriate for their situation?
4. What should they do next?

Be realistic and conservative - don't recommend unnecessary insurance.
        """
        
        content = types.Content(role='user', parts=[types.Part(text=context)])
        
        try:
            result = None
            async for event in self.runner.run_async(
                user_id="needs_user",
                session_id="session_001",
                new_message=content
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                        result = self._parse_agent_response(response_text, user_profile, existing_policy_analysis)
                    break
                    
            return result if result else self._create_fallback_evaluation(user_profile, existing_policy_analysis)
            
        except Exception as e:
            logger.error(f"Needs evaluation agent failed: {e}")
            return self._create_fallback_evaluation(user_profile, existing_policy_analysis)
    
    def _parse_agent_response(
        self, 
        response_text: str, 
        user_profile: UserProfile,
        existing_analysis: Optional[ExistingPolicyAssessment]
    ) -> NeedsEvaluationSchema:
        """Parse agent response into structured schema"""
        
        # Try to extract structured data from response
        should_get_quotes = "should get quotes" in response_text.lower() or user_profile.existing_coverage_type == "none"
        
        # Determine priority product type
        product_mapping = {
            "health_medical": "HEALTH_BASIC",
            "life_protection": "LIFE_TERM", 
            "critical_illness": "CRITICAL_ILLNESS",
            "comprehensive_all": "HEALTH_PREMIUM",
            "unsure": "HEALTH_BASIC"
        }
        priority_product = product_mapping.get(user_profile.coverage_priority, "HEALTH_BASIC")
        
        # Calculate recommended coverage
        if priority_product in ["LIFE_TERM"]:
            recommended_coverage = user_profile.annual_income * (12 if user_profile.age < 40 else 10)
        else:
            recommended_coverage = max(user_profile.annual_income * 2, 100000)
        
        # Generate main recommendation
        if not should_get_quotes and existing_analysis:
            main_rec = "Your current coverage appears adequate - focus on other financial goals"
        elif user_profile.existing_coverage_type == "none":
            main_rec = "You need basic insurance coverage to protect against financial risks"
        else:
            main_rec = f"Consider {priority_product.lower().replace('_', ' ')} to address your {user_profile.primary_need} goals"
        
        return NeedsEvaluationSchema(
            should_get_quotes=should_get_quotes,
            reasoning=self._extract_reasoning(response_text, should_get_quotes),
            recommended_coverage_amount=recommended_coverage,
            priority_product_type=priority_product,
            urgency_level=self._map_urgency(user_profile.urgency),
            main_recommendation=main_rec,
            action_items=self._extract_action_items(response_text, user_profile)
        )
    
    def _extract_reasoning(self, response_text: str, should_get_quotes: bool) -> str:
        """Extract reasoning from agent response"""
        if "no coverage" in response_text.lower():
            return "You have no existing coverage and need basic protection"
        elif "save money" in response_text.lower():
            return "Comparing options could help you save money on premiums"
        elif should_get_quotes:
            return "Your situation suggests exploring new coverage options would be beneficial"
        else:
            return "Your current coverage appears to meet your needs"
    
    def _map_urgency(self, timeline: str) -> str:
        """Map timeline to urgency level"""
        mapping = {
            "immediately": "immediate",
            "within_month": "soon",
            "within_3_months": "soon", 
            "exploring": "no_rush"
        }
        return mapping.get(timeline, "can_wait")
    
    def _extract_action_items(self, response_text: str, user_profile: UserProfile) -> List[str]:
        """Extract action items from response"""
        actions = []
        
        if user_profile.existing_coverage_type == "none":
            actions.append("Get basic health insurance immediately")
            if user_profile.age < 45:
                actions.append("Consider term life insurance")
        elif user_profile.primary_need == "save_money":
            actions.append("Get quotes from 3-4 different insurers")
            actions.append("Compare your current premium to new options")
        else:
            actions.append("Review your current coverage details")
            actions.append("Identify any gaps in protection")
        
        if user_profile.urgency == "immediately":
            actions.insert(0, "⚠️ Act quickly to avoid coverage gaps")
        
        return actions[:4]  # Max 4 actions
    
    def _create_fallback_evaluation(
        self, 
        user_profile: UserProfile,
        existing_analysis: Optional[ExistingPolicyAssessment]
    ) -> NeedsEvaluationSchema:
        """Create fallback evaluation when agent fails"""
        
        should_get_quotes = (
            user_profile.existing_coverage_type == "none" or 
            user_profile.primary_need in ["save_money", "fill_gaps", "compare_options"]
        )
        
        return NeedsEvaluationSchema(
            should_get_quotes=should_get_quotes,
            reasoning="Basic needs assessment based on your profile",
            recommended_coverage_amount=max(user_profile.annual_income * 5, 100000),
            priority_product_type="HEALTH_BASIC",
            urgency_level=self._map_urgency(user_profile.urgency),
            main_recommendation="Consider basic insurance coverage for financial protection",
            action_items=[
                "Review your insurance needs",
                "Compare available options", 
                "Consider your budget constraints",
                "Make an informed decision"
            ]
        )

# Singleton instance
_needs_evaluation_agent = None

def get_needs_evaluation_agent() -> NeedsEvaluationAgent:
    """Get singleton needs evaluation agent instance"""
    global _needs_evaluation_agent
    if _needs_evaluation_agent is None:
        _needs_evaluation_agent = NeedsEvaluationAgent()
    return _needs_evaluation_agent

# Helper function for easy usage
async def evaluate_user_needs(
    user_profile: UserProfile,
    existing_policy_analysis: Optional[ExistingPolicyAssessment] = None
) -> NeedsEvaluationSchema:
    """
    Evaluate user's insurance needs
    
    Args:
        user_profile: User's questionnaire responses in schema format
        existing_policy_analysis: Analysis of existing coverage
        
    Returns:
        NeedsEvaluationSchema with structured recommendations
    """
    agent = get_needs_evaluation_agent()
    return await agent.evaluate_insurance_needs(user_profile, existing_policy_analysis)

if __name__ == "__main__":
    # Test the agent
    async def test():
        from shared.models import UserProfile
        
        test_profile = UserProfile(
            age=28,
            annual_income=65000,
            health_status="good",
            existing_coverage_type="employer_basic",
            existing_coverage_amount="100k_250k",
            primary_need="save_money",
            monthly_budget="200_400",
            coverage_priority="health_medical",
            urgency="within_month"
        )
        
        result = await evaluate_user_needs(test_profile)
        print(f"Needs evaluation result: {result}")
    
    asyncio.run(test())