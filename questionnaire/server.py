"""
questionnaire/server.py
=======================
Questionnaire server that runs on port 8001
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import (
    QuestionnaireSession, QuestionnaireResponse, 
    ApplicantProfile, InsuranceRequest, ProductType
)
from questionnaire.questions import INSURANCE_QUESTIONS, should_show_question
from agents.questionnaire_agent import QuestionnaireHelper
from agents.response_parser_agent import ResponseParser
from agents.recommendation_agent import RecommendationEngine

app = FastAPI(
    title="Insurance Questionnaire Server",
    description="Interactive questionnaire with AI helpers",
    version="1.0.0"
)

# Mount static files and templates
import os
# Use absolute paths to ensure they work regardless of working directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(project_root, "frontend", "static")
templates_dir = os.path.join(project_root, "frontend", "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"❌ Static directory not found: {static_dir}")

if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
else:
    templates = None
    print(f"❌ Templates directory not found: {templates_dir}")

# In-memory storage for sessions (in production, use database)
sessions: Dict[str, QuestionnaireSession] = {}

# AI agents will be initialized lazily
questionnaire_helper = None
response_parser = None
recommendation_engine = None

def get_questionnaire_helper():
    global questionnaire_helper
    if questionnaire_helper is None:
        questionnaire_helper = QuestionnaireHelper()
    return questionnaire_helper

def get_response_parser():
    global response_parser
    if response_parser is None:
        response_parser = ResponseParser()
    return response_parser

def get_recommendation_engine():
    global recommendation_engine
    if recommendation_engine is None:
        recommendation_engine = RecommendationEngine()
    return recommendation_engine

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main questionnaire page"""
    if templates:
        return templates.TemplateResponse("questionnaire.html", {"request": request})
    else:
        # Fallback HTML if templates not found
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Insurance Questionnaire</title></head>
        <body>
            <h1>Insurance Questionnaire Demo</h1>
            <p>Template files not found. API endpoints are still available at:</p>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li>POST /api/start-session - Start questionnaire</li>
            </ul>
        </body>
        </html>
        """)

@app.post("/api/start-session")
async def start_session():
    """Start a new questionnaire session"""
    session_id = str(uuid.uuid4())
    session = QuestionnaireSession(session_id=session_id)
    sessions[session_id] = session
    
    # Get the first question
    first_question = INSURANCE_QUESTIONS[0]
    
    return {
        "session_id": session_id,
        "current_question": first_question.dict(),
        "progress": {"current": 1, "total": len(INSURANCE_QUESTIONS)}
    }

@app.post("/api/start-session-with-profile")
async def start_session_with_profile(profile_data: Dict[str, Any]):
    """Start questionnaire session with pre-filled profile data"""
    session_id = str(uuid.uuid4())
    session = QuestionnaireSession(session_id=session_id)
    
    # Pre-fill personal information from uploaded profile
    personal_questions = [
        ("personal_first_name", "first_name"),
        ("personal_last_name", "last_name"), 
        ("personal_dob", "dob"),
        ("personal_gender", "gender"),
        ("personal_email", "email"),
        ("personal_phone", "phone"),
        ("address_line1", "address_line1"),
        ("address_city", "city"),
        ("address_state", "state"),
        ("address_postal_code", "postal_code")
    ]
    
    for question_id, profile_key in personal_questions:
        if profile_key in profile_data:
            response = QuestionnaireResponse(
                question_id=question_id,
                answer=profile_data[profile_key],
                needs_help=False
            )
            session.responses.append(response)
    
    # Find first question after personal and address (should be lifestyle questions)
    insurance_start_index = 0
    skippable_categories = {"personal", "address"}
    
    for i, question in enumerate(INSURANCE_QUESTIONS):
        if question.category not in skippable_categories:
            insurance_start_index = i
            break
    
    session.current_question_index = insurance_start_index
    sessions[session_id] = session
    
    # Get the first actual insurance question (lifestyle/priorities/etc)
    current_question = INSURANCE_QUESTIONS[insurance_start_index]
    
    # Calculate progress: only count the remaining questions (not the skipped ones)
    total_insurance_questions = len([q for q in INSURANCE_QUESTIONS if q.category not in skippable_categories])
    
    return {
        "session_id": session_id,
        "current_question": current_question.dict(),
        "progress": {"current": 1, "total": total_insurance_questions}
    }

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    current_question = get_current_question(session)
    
    return {
        "session": session.dict(),
        "current_question": current_question.dict() if current_question else None,
        "progress": calculate_progress(session)
    }

@app.post("/api/session/{session_id}/answer")
async def submit_answer(session_id: str, answer_data: Dict[str, Any]):
    """Submit an answer to the current question"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    current_question = get_current_question(session)
    
    if not current_question:
        raise HTTPException(status_code=400, detail="No current question")
    
    # Create response
    response = QuestionnaireResponse(
        question_id=current_question.id,
        answer=answer_data.get("answer"),
        needs_help=answer_data.get("needs_help", False),
        help_description=answer_data.get("help_description")
    )
    
    # If user needs help, use AI agent to select answer
    if response.needs_help and response.help_description:
        try:
            # Convert Question model to dictionary for the AI agent
            question_dict = current_question.dict() if current_question else {}
            
            ai_answer = await get_questionnaire_helper().help_select_answer(
                question_dict, 
                response.help_description,
                get_response_dict(session)
            )
            if ai_answer:
                response.answer = ai_answer
                response.ai_selected = True
        except Exception as e:
            print(f"AI helper error: {e}")
            # Continue without AI help
    
    # Update session
    session.responses.append(response)
    session.current_question_index += 1
    session.updated_at = datetime.utcnow()
    
    # Move to next appropriate question (skip conditional questions)
    while (session.current_question_index < len(INSURANCE_QUESTIONS) and 
           not should_show_question(
               INSURANCE_QUESTIONS[session.current_question_index], 
               get_response_dict(session)
           )):
        session.current_question_index += 1
    
    # Check if questionnaire is complete
    if session.current_question_index >= len(INSURANCE_QUESTIONS):
        session.completed = True
        
        # Process completed questionnaire
        try:
            insurance_response = await process_completed_questionnaire(session)
            return {
                "completed": True,
                "insurance_response": insurance_response,
                "progress": {"current": len(INSURANCE_QUESTIONS), "total": len(INSURANCE_QUESTIONS)}
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing questionnaire: {str(e)}")
    
    # Get next question
    next_question = get_current_question(session)
    
    return {
        "completed": False,
        "next_question": next_question.dict() if next_question else None,
        "progress": calculate_progress(session)
    }

@app.post("/api/session/{session_id}/get-help")
async def get_question_help(session_id: str, help_request: Dict[str, str]):
    """Get AI help for answering a question or general insurance guidance"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    current_question = get_current_question(session)
    user_description = help_request.get("description", "")
    
    # If no current question (user asking for help from welcome screen), provide general guidance
    if not current_question:
        guidance = await provide_general_insurance_guidance(user_description)
        return {
            "suggested_answer": guidance["recommendation"],
            "explanation": guidance["explanation"],
            "confidence": 0.8
        }
    
    # Normal question-specific help
    try:
        # Convert Question model to dictionary for the AI agent
        question_dict = current_question.dict() if current_question else {}
        
        suggested_answer = await get_questionnaire_helper().help_select_answer(
            question_dict,
            user_description,
            get_response_dict(session)
        )
        
        explanation = await get_questionnaire_helper().explain_answer_choice(
            question_dict,
            suggested_answer,
            user_description
        )
        
        return {
            "suggested_answer": suggested_answer,
            "explanation": explanation,
            "confidence": 0.8
        }
    except Exception as e:
        print(f"AI helper error: {e}")
        # Fallback to general guidance if AI helper fails
        guidance = await provide_general_insurance_guidance(user_description)
        return {
            "suggested_answer": guidance["recommendation"], 
            "explanation": guidance["explanation"] + " (Note: Our AI helper is having trouble with this specific question, but here's some general guidance.)",
            "confidence": 0.6
        }

# Helper functions
def calculate_progress(session: QuestionnaireSession) -> Dict[str, int]:
    """Calculate progress for a session, accounting for skipped questions"""
    # Check if this session started with profile upload (has pre-filled personal/address responses)
    personal_address_responses = [r for r in session.responses 
                                if any(r.question_id.startswith(prefix) 
                                      for prefix in ['personal_', 'address_'])]
    
    if personal_address_responses:
        # JSON upload session - only count non-personal/address questions
        skippable_categories = {"personal", "address"}
        total_insurance_questions = len([q for q in INSURANCE_QUESTIONS if q.category not in skippable_categories])
        
        # Calculate how many insurance questions have been answered
        insurance_responses = [r for r in session.responses 
                             if not any(r.question_id.startswith(prefix) 
                                       for prefix in ['personal_', 'address_'])]
        
        return {
            "current": len(insurance_responses) + 1,  # +1 for current question
            "total": total_insurance_questions
        }
    else:
        # Regular session - count all questions
        return {
            "current": session.current_question_index + 1,
            "total": len(INSURANCE_QUESTIONS)
        }

def get_current_question(session: QuestionnaireSession):
    """Get the current question for a session"""
    if session.current_question_index >= len(INSURANCE_QUESTIONS):
        return None
    return INSURANCE_QUESTIONS[session.current_question_index]

def get_response_dict(session: QuestionnaireSession) -> Dict[str, Any]:
    """Convert session responses to dictionary for easy lookup"""
    return {r.question_id: r.answer for r in session.responses}

async def process_completed_questionnaire(session: QuestionnaireSession) -> Dict[str, Any]:
    """Process completed questionnaire and get insurance quotes"""
    responses = get_response_dict(session)
    
    # Convert responses to ApplicantProfile
    try:
        applicant = convert_responses_to_applicant(responses)
    except Exception as e:
        raise Exception(f"Error converting responses to applicant profile: {str(e)}")
    
    # Intelligently determine insurance needs from conversational responses
    coverage_amount = determine_coverage_amount(responses, applicant)
    product_type = determine_product_type(responses)
    
    # Create insurance request
    insurance_request = InsuranceRequest(
        product_type=product_type,
        applicant=applicant,
        coverage_amount=coverage_amount,
        deductible=None,  # Let insurance companies suggest appropriate deductibles
        term_years=None,  # Let insurance companies suggest appropriate terms
        riders=[],
        beneficiaries=[]
    )
    
    # Send request to insurance API
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/quote",
                json=insurance_request.dict(),
                timeout=30.0
            )
            response.raise_for_status()
            raw_insurance_response = response.json()
    except Exception as e:
        raise Exception(f"Error calling insurance API: {str(e)}")
    
    # Parse response with AI agent
    try:
        parsed_cards = await get_response_parser().parse_insurance_response(
            raw_insurance_response,
            responses  # Pass user preferences for context
        )
    except Exception as e:
        print(f"Error parsing insurance response: {e}")
        parsed_cards = []  # Fallback to empty list
    
    # Generate recommendations
    try:
        recommendations = await get_recommendation_engine().generate_recommendations(
            parsed_cards,
            responses,
            applicant
        )
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        recommendations = []  # Fallback to empty list
    
    return {
        "raw_response": raw_insurance_response,
        "insurance_cards": parsed_cards,
        "recommendations": recommendations,
        "session_id": session.session_id
    }

async def provide_general_insurance_guidance(user_description: str) -> Dict[str, str]:
    """Provide general insurance guidance based on user's description"""
    
    # Simple rule-based guidance (could be enhanced with AI later)
    description_lower = user_description.lower()
    
    if any(word in description_lower for word in ['young', 'single', 'just started', 'first job', 'college']):
        return {
            "recommendation": "Basic health and term life insurance",
            "explanation": "As a young person starting out, I'd recommend focusing on basic health insurance to protect against medical bills, and a small term life policy to cover any debts or final expenses. Start with what you can afford - you can always increase coverage later as your income grows."
        }
    
    elif any(word in description_lower for word in ['married', 'spouse', 'partner', 'wedding']):
        return {
            "recommendation": "Health insurance for both partners and life insurance",
            "explanation": "As a couple, you'll want to make sure both of you have health coverage. Consider life insurance to protect each other financially - even if one person doesn't work, they provide value through household management, childcare, etc."
        }
    
    elif any(word in description_lower for word in ['kids', 'children', 'baby', 'family', 'pregnant']):
        return {
            "recommendation": "Comprehensive family coverage with adequate life insurance",
            "explanation": "With children depending on you, life insurance becomes much more important. Consider 10-12 times your annual income to ensure your family can maintain their lifestyle and cover future expenses like education."
        }
    
    elif any(word in description_lower for word in ['mortgage', 'house', 'bought home', 'debt']):
        return {
            "recommendation": "Life insurance to cover debts and mortgage",
            "explanation": "Having a mortgage or significant debt means your family could lose the home if something happens to you. Life insurance should cover these debts plus ongoing living expenses for your dependents."
        }
    
    elif any(word in description_lower for word in ['business', 'self employed', 'entrepreneur']):
        return {
            "recommendation": "Business protection and personal coverage",
            "explanation": "As a business owner, you need both personal coverage for your family and business protection. Consider key person insurance and coverage that protects your business partners and employees too."
        }
    
    elif any(word in description_lower for word in ['health problems', 'medical', 'condition', 'doctor']):
        return {
            "recommendation": "Focus on health insurance with good coverage",
            "explanation": "With health concerns, comprehensive health insurance should be your top priority. For life insurance, be honest about your conditions - many companies still offer coverage, and working with an agent can help find the right fit."
        }
    
    elif any(word in description_lower for word in ['budget', 'tight', 'afford', 'cheap', 'expensive']):
        return {
            "recommendation": "Start with basic term life insurance",
            "explanation": "Insurance doesn't have to be expensive. Basic term life insurance can provide good protection for $25-50/month. Start with what you can afford - some protection is better than none, and you can always add more later."
        }
    
    else:
        return {
            "recommendation": "Let's start with the questionnaire",
            "explanation": "Based on what you've shared, I'd like to learn more about your specific situation. Our questionnaire will help me understand your needs better and recommend the right type and amount of coverage for you."
        }

def determine_coverage_amount(responses: Dict[str, Any], applicant: ApplicantProfile) -> float:
    """Intelligently determine appropriate coverage amount based on user's situation"""
    
    # Base calculation factors
    annual_income = applicant.annual_income or 50000
    dependents = responses.get("financial_dependents", "none")
    main_concern = responses.get("main_concern", "income_replacement")
    life_stage = responses.get("life_stage", "young_single")
    budget = responses.get("monthly_budget", "flexible")
    
    # Income replacement multiplier based on dependents and life stage
    if dependents == "none":
        income_multiplier = 3  # Basic coverage for debts and final expenses
    elif dependents in ["spouse", "parents"]:
        income_multiplier = 6  # Support one dependent
    elif dependents in ["spouse_kids", "children_only"]:
        income_multiplier = 10  # Support family with children
    elif dependents in ["extended", "multiple"]:
        income_multiplier = 12  # Multiple dependents
    else:
        income_multiplier = 5  # Default
    
    # Adjust based on main concern
    if main_concern == "income_replacement":
        concern_multiplier = 1.2
    elif main_concern == "mortgage_debt":
        concern_multiplier = 1.5  # Need to cover large debts
    elif main_concern == "children_future":
        concern_multiplier = 1.3  # Education costs
    elif main_concern == "medical_bills":
        concern_multiplier = 0.8  # Health insurance focus
    elif main_concern == "burial_costs":
        concern_multiplier = 0.3  # Final expenses only
    elif main_concern == "business_protection":
        concern_multiplier = 1.4  # Business needs
    else:
        concern_multiplier = 1.0
    
    # Life stage adjustments
    if life_stage in ["new_parents", "growing_family"]:
        stage_multiplier = 1.2  # Higher needs with young children
    elif life_stage == "established_family":
        stage_multiplier = 1.1  # Peak earning years
    elif life_stage in ["empty_nesters", "pre_retirement"]:
        stage_multiplier = 0.7  # Lower needs as kids are independent
    else:
        stage_multiplier = 1.0
    
    # Calculate base coverage
    base_coverage = annual_income * income_multiplier * concern_multiplier * stage_multiplier
    
    # Budget constraints
    if budget in ["25", "50"]:
        # Budget-conscious: cap at reasonable level
        base_coverage = min(base_coverage, 250000)
    elif budget == "100":
        base_coverage = min(base_coverage, 500000)
    elif budget == "200":
        base_coverage = min(base_coverage, 1000000)
    # No cap for 'flexible' budget
    
    # Round to reasonable amounts
    if base_coverage <= 100000:
        return round(base_coverage / 25000) * 25000  # Round to nearest 25k
    elif base_coverage <= 500000:
        return round(base_coverage / 50000) * 50000  # Round to nearest 50k
    else:
        return round(base_coverage / 100000) * 100000  # Round to nearest 100k

def determine_product_type(responses: Dict[str, Any]) -> ProductType:
    """Determine appropriate insurance product type from conversational responses"""
    
    main_concern = responses.get("main_concern", "income_replacement")
    dependents = responses.get("financial_dependents", "none")
    life_stage = responses.get("life_stage", "young_single")
    budget = responses.get("monthly_budget", "flexible")
    
    # Health insurance focus
    if main_concern == "medical_bills":
        return ProductType.HEALTH_BASIC
    
    # Life insurance logic
    if dependents != "none" or life_stage in ["new_parents", "growing_family", "established_family"]:
        # Has dependents - likely needs life insurance
        if budget in ["25", "50"] or main_concern == "burial_costs":
            return ProductType.LIFE_TERM  # Term is more affordable
        else:
            return ProductType.LIFE_TERM  # Start with term, can upgrade later
    else:
        # Single person - might need health insurance or basic life coverage
        if life_stage == "young_single":
            return ProductType.HEALTH_BASIC
        else:
            return ProductType.LIFE_TERM

def convert_responses_to_applicant(responses: Dict[str, Any]) -> ApplicantProfile:
    """Convert conversational questionnaire responses to technical ApplicantProfile"""
    
    # Translate conversational smoking habits to technical format
    smoking_response = responses.get("smoking_habits", "never")
    smoker = None
    if smoking_response == "regular":
        smoker = True
    elif smoking_response in ["never", "quit"]:
        smoker = False
    elif smoking_response == "recent_quit":
        smoker = True  # Recent quitters often still rated as smokers
    elif smoking_response == "occasional":
        smoker = True  # Occasional smoking still counts
    
    # Translate health conditions from conversational to medical terms
    health_response = responses.get("health_conditions", "none")
    pre_existing_conditions = []
    if health_response == "minor":
        pre_existing_conditions = ["allergies", "mild_asthma"]
    elif health_response == "managed":
        pre_existing_conditions = ["controlled_condition"]
    elif health_response == "serious":
        pre_existing_conditions = ["chronic_condition"]
    elif health_response == "prefer_discuss":
        pre_existing_conditions = ["undisclosed_condition"]
    
    # Estimate physical stats based on health description
    health_overall = responses.get("health_overall", "good")
    base_height = 170.0  # Default height in cm
    base_weight = 75.0   # Default weight in kg
    
    if health_overall == "excellent":
        weight_modifier = 0.9  # Healthier people often maintain better weight
    elif health_overall in ["poor", "improving"]:
        weight_modifier = 1.1  # Health issues might affect weight
    else:
        weight_modifier = 1.0
    
    # Estimate income based on life stage and dependents
    life_stage = responses.get("life_stage", "young_single")
    dependents = responses.get("financial_dependents", "none")
    
    if life_stage in ["young_single", "young_couple"]:
        estimated_income = 45000
    elif life_stage in ["new_parents", "growing_family"]:
        estimated_income = 65000
    elif life_stage == "established_family":
        estimated_income = 85000
    elif life_stage == "empty_nesters":
        estimated_income = 75000
    else:
        estimated_income = 55000
    
    # Adjust income based on dependents
    if dependents in ["spouse_kids", "multiple"]:
        estimated_income *= 1.3
    elif dependents in ["spouse", "parents"]:
        estimated_income *= 1.1
    
    # Determine occupation from life stage
    occupation_mapping = {
        "young_single": "entry_level",
        "young_couple": "professional",
        "new_parents": "professional",
        "growing_family": "manager",
        "established_family": "senior_professional",
        "empty_nesters": "senior_professional",
        "pre_retirement": "executive"
    }
    occupation = occupation_mapping.get(life_stage, "professional")
    
    # Translate lifestyle risk to travel frequency
    lifestyle_risk = responses.get("lifestyle_risk", "low_risk")
    if lifestyle_risk == "travel":
        travel_frequency = "international"
    elif lifestyle_risk in ["regular_risk", "high_risk"]:
        travel_frequency = "frequent_domestic"
    else:
        travel_frequency = "domestic"
    
    return ApplicantProfile(
        first_name=responses.get("personal_first_name", ""),
        last_name=responses.get("personal_last_name", ""),
        dob=responses.get("personal_dob", "1990-01-01"),
        gender=responses.get("personal_gender", "M"),
        email=responses.get("personal_email", ""),
        phone=responses.get("personal_phone", ""),
        
        address_line1=responses.get("address_line1", ""),
        address_line2=None,
        city=responses.get("address_city", ""),
        state=responses.get("address_state", "CA"),
        postal_code=responses.get("address_postal_code", ""),
        country="US",
        
        smoker=smoker,
        height_cm=base_height,
        weight_kg=base_weight * weight_modifier,
        occupation=occupation,
        annual_income=estimated_income,
        
        pre_existing_conditions=pre_existing_conditions,
        medications=[],  # Will be inferred from health conditions
        hospitalizations_last_5_years=0 if health_overall in ["excellent", "good"] else 1,
        family_medical_history=[],  # Not asked in conversational format
        
        exercise_frequency="weekly" if health_overall in ["excellent", "good"] else "monthly",
        alcohol_consumption="social",  # Default assumption
        travel_frequency=travel_frequency
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)