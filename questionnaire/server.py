"""
questionnaire/server.py
=======================
Questionnaire server that runs on port 8001
"""

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
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
    ApplicantProfile, InsuranceRequest, ProductType,
    UserProfile, ExistingPolicyAssessment, NeedsEvaluationSchema, PolicyScore
)
from questionnaire.questions import INSURANCE_QUESTIONS, should_show_question
from agents.questionnaire_agent import QuestionnaireHelper
from agents.response_parser_agent import ResponseParser
from agents.recommendation_agent import RecommendationEngine
from agents.pdf_parser_agent import get_pdf_parser, PDFExtractionResult
from agents.policy_analyzer_agent import analyze_existing_policy
from agents.needs_evaluation_agent import get_needs_evaluation_agent

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

# Import database models for persistence
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.database import (
    async_db, Collections, QuestionnaireSessionRecord, 
    PDFExtractionRecord, PolicyScoreRecord
)
import hashlib

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

@app.post("/api/start-session-with-pdf")
async def start_session_with_pdf(
    pdf_file: UploadFile = File(...),
    json_profile: Optional[str] = None
):
    """Start questionnaire session with PDF document and optional JSON profile"""
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read PDF content
    pdf_content = await pdf_file.read()
    
    # Parse JSON profile if provided
    profile_data = {}
    if json_profile:
        try:
            profile_data = json.loads(json_profile)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON profile data")
    
    # Extract information from PDF
    pdf_parser = get_pdf_parser()
    extraction_result = pdf_parser.extract_insurance_fields(pdf_content, profile_data)
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Save PDF extraction results to database
    extraction_id = await save_pdf_extraction(
        session_id, pdf_file.filename, pdf_content, extraction_result
    )
    session = QuestionnaireSession(session_id=session_id)
    
    # Store extraction result in session metadata
    session.metadata = {
        "pdf_extraction": extraction_result.dict(),
        "pdf_filename": pdf_file.filename
    }
    
    # Pre-fill questions based on extracted data
    extracted_fields = extraction_result.extracted_fields
    
    # Map extracted fields to questions
    field_mappings = [
        ("personal_first_name", "first_name"),
        ("personal_last_name", "last_name"), 
        ("personal_dob", "dob"),
        ("personal_gender", "gender"),
        ("personal_email", "email"),
        ("personal_phone", "phone"),
        ("address_line1", "address_line1"),
        ("address_city", "city"),
        ("address_state", "state"),
        ("address_postal_code", "postal_code"),
        ("annual_income", "annual_income"),
    ]
    
    for question_id, field_key in field_mappings:
        if field_key in extracted_fields:
            response = QuestionnaireResponse(
                question_id=question_id,
                answer=extracted_fields[field_key],
                needs_help=False
            )
            session.responses.append(response)
    
    # Find first unanswered question
    answered_question_ids = {resp.question_id for resp in session.responses}
    first_unanswered_index = 0
    
    for i, question in enumerate(INSURANCE_QUESTIONS):
        if question.id not in answered_question_ids:
            first_unanswered_index = i
            break
    
    session.current_question_index = first_unanswered_index
    sessions[session_id] = session
    
    # Get the first unanswered question
    current_question = INSURANCE_QUESTIONS[first_unanswered_index] if first_unanswered_index < len(INSURANCE_QUESTIONS) else None
    
    # Calculate progress
    total_questions = len(INSURANCE_QUESTIONS)
    current_progress = len(session.responses) + 1
    
    response_data = {
        "session_id": session_id,
        "pdf_extraction_result": extraction_result.dict(),
        "current_question": current_question.dict() if current_question else None,
        "progress": {"current": current_progress, "total": total_questions},
        "pre_filled_fields": list(extracted_fields.keys())
    }
    
    return response_data

@app.post("/api/parse-pdf")
async def parse_pdf_only(
    pdf_file: UploadFile = File(...),
    json_profile: Optional[str] = None
):
    """Parse PDF and return extracted fields without starting a session"""
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read PDF content
    pdf_content = await pdf_file.read()
    
    # Parse JSON profile if provided
    profile_data = {}
    if json_profile:
        try:
            profile_data = json.loads(json_profile)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON profile data")
    
    # Extract information from PDF
    pdf_parser = get_pdf_parser()
    extraction_result = pdf_parser.extract_insurance_fields(pdf_content, profile_data)
    
    return {
        "extraction_result": extraction_result.dict(),
        "filename": pdf_file.filename
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
    
    # NEW: Direct schema population as user answers
    populate_user_profile_field(session, current_question.id, response.answer)
    
    session.current_question_index += 1
    session.updated_at = datetime.utcnow()
    
    print(f"Schema update: {current_question.id} = {response.answer}")  # Debug
    
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
        
        # Process completed questionnaire with agentic approach
        try:
            insurance_response = await process_completed_questionnaire_agentic(session)
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

async def save_completed_session(session: QuestionnaireSession, applicant: ApplicantProfile, 
                                 source: str = "manual", pdf_info: Optional[Dict] = None):
    """Save completed questionnaire session to MongoDB"""
    try:
        # Create session record
        session_record = QuestionnaireSessionRecord(
            session_id=session.session_id,
            applicant_profile=applicant.dict(),
            source=source,
            pdf_filename=pdf_info.get("filename") if pdf_info else None,
            pdf_extraction_confidence=pdf_info.get("confidence_score") if pdf_info else None
        )
        
        # Insert into MongoDB
        await async_db[Collections.QUESTIONNAIRE_SESSIONS].insert_one(
            session_record.dict(exclude={"id"})
        )
        
        print(f"✅ Saved questionnaire session {session.session_id} to database")
        
    except Exception as e:
        print(f"⚠️ Failed to save session to database: {e}")
        # Don't fail the entire process if saving fails

async def save_pdf_extraction(session_id: str, pdf_filename: str, pdf_content: bytes,
                             extraction_result) -> str:
    """Save PDF extraction results to MongoDB"""
    try:
        # Generate extraction ID and file hash
        extraction_id = str(uuid.uuid4())
        file_hash = hashlib.md5(pdf_content).hexdigest()
        
        # Create extraction record
        extraction_record = PDFExtractionRecord(
            extraction_id=extraction_id,
            session_id=session_id,
            filename=pdf_filename,
            file_size_bytes=len(pdf_content),
            file_hash=file_hash,
            extracted_fields=extraction_result.extracted_fields,
            confidence_score=extraction_result.confidence_score,
            processing_time_seconds=extraction_result.processing_time_seconds,
            missing_required_fields=extraction_result.missing_fields,
            warnings=extraction_result.warnings,
            extraction_method="gemini" if extraction_result.confidence_score > 50 else "fallback"
        )
        
        # Insert into MongoDB
        await async_db[Collections.PDF_EXTRACTIONS].insert_one(
            extraction_record.dict(exclude={"id"})
        )
        
        print(f"✅ Saved PDF extraction {extraction_id} to database")
        return extraction_id
        
    except Exception as e:
        print(f"⚠️ Failed to save PDF extraction: {e}")
        return ""

async def save_policy_scores(session_id: str, scored_plans, user_income: float):
    """Save policy scoring results to MongoDB for analytics"""
    try:
        for score in scored_plans:
            score_record = PolicyScoreRecord(
                score_id=str(uuid.uuid4()),
                session_id=session_id,
                plan_id=score.plan_id,
                overall_score=score.overall_score,
                affordability_score=score.affordability_score,
                ease_of_claims_score=score.ease_of_claims_score,
                coverage_ratio_score=score.coverage_ratio_score,
                user_annual_income=user_income,
                income_percentage=score.income_percentage,
                company_name=score.company_name,
                plan_name=score.plan_name,
                monthly_premium=0,  # Extract from plan data
                coverage_amount=0,  # Extract from plan data
                scoring_weights={"affordability": 0.4, "ease_of_claims": 0.25, "coverage_ratio": 0.35}
            )
            
            await async_db[Collections.POLICY_SCORES].insert_one(
                score_record.dict(exclude={"id"})
            )
        
        print(f"✅ Saved {len(scored_plans)} policy scores to database")
        
    except Exception as e:
        print(f"⚠️ Failed to save policy scores: {e}")

async def process_completed_questionnaire(session: QuestionnaireSession) -> Dict[str, Any]:
    """Process completed questionnaire and get insurance quotes with policy analysis"""
    responses = get_response_dict(session)
    
    # For MVP: Handle simplified 8-question format
    if is_mvp_questionnaire(responses):
        return await process_mvp_questionnaire(responses)
    
    # Legacy: Handle original 25-question format
    return await process_legacy_questionnaire(responses)

async def process_mvp_questionnaire(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Process the simplified 8-question MVP questionnaire"""
    
    # Parse MVP responses
    basic_info = responses.get("basic_info", "")
    existing_coverage = responses.get("existing_coverage", "none")
    coverage_amount = responses.get("current_coverage_amount", "none")
    health_status = responses.get("health_status", "good")
    primary_need = responses.get("primary_need", "first_time")
    budget = responses.get("budget", "show_all")
    coverage_priority = responses.get("coverage_priority", "health_medical")
    timeline = responses.get("timeline", "exploring")
    
    # Parse basic info (age and income)
    age, annual_income = parse_basic_info(basic_info)
    
    # First: Analyze existing policy if any
    policy_analysis = None
    if existing_coverage != "none":
        # Estimate current premium based on coverage type and budget
        estimated_premium = estimate_current_premium(existing_coverage, budget, annual_income)
        
        policy_analysis = analyze_existing_policy(
            existing_coverage=existing_coverage,
            coverage_amount=coverage_amount,
            monthly_premium=estimated_premium,
            annual_income=annual_income,
            age=age,
            health_status=health_status,
            primary_need=primary_need
        )
    
    # Create minimal applicant profile for API
    applicant = create_minimal_applicant(age, annual_income, health_status)
    
    # Determine if user needs new coverage or optimization
    should_get_quotes = should_fetch_new_quotes(policy_analysis, primary_need, existing_coverage)
    
    result = {
        "existing_policy_analysis": policy_analysis.dict() if policy_analysis else None,
        "recommendations": generate_mvp_recommendations(policy_analysis, primary_need, timeline)
    }
    
    # Only get new quotes if analysis suggests it's beneficial
    if should_get_quotes:
        # Determine coverage needs
        product_type = map_coverage_priority_to_product_type(coverage_priority)
        target_coverage = calculate_needed_coverage(age, annual_income, existing_coverage, coverage_amount)
        
        # Create insurance request
        insurance_request = InsuranceRequest(
            product_type=product_type,
            applicant=applicant,
            coverage_amount=target_coverage,
            deductible=None,
            term_years=None,
            riders=[],
            beneficiaries=[]
        )
        
        # Get quotes
        try:
            quotes_data = await fetch_insurance_quotes(insurance_request, responses)
            result["new_quotes"] = quotes_data
        except Exception as e:
            result["quotes_error"] = f"Error fetching quotes: {str(e)}"
    else:
        result["quotes_skipped"] = "Analysis suggests no new coverage needed"
    
    return result

async def process_legacy_questionnaire(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Process the original detailed questionnaire (25 questions)"""
    
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
    
    # Get quotes
    try:
        quotes_data = await fetch_insurance_quotes(insurance_request, responses)
        return {"new_quotes": quotes_data}
    except Exception as e:
        raise Exception(f"Error calling insurance API: {str(e)}")

async def fetch_insurance_quotes(insurance_request: InsuranceRequest, responses: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch quotes from insurance API"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/quote",
            json=insurance_request.dict(),
            timeout=30.0
        )
        response.raise_for_status()
        raw_insurance_response = response.json()
    
    # Parse response with AI agent
    try:
        parsed_cards = await get_response_parser().parse_insurance_response(
            raw_insurance_response, responses
        )
    except Exception as e:
        print(f"Response parser error: {e}")
        parsed_cards = create_fallback_cards(raw_insurance_response)
    
    # Generate recommendations
    try:
        recommendations = await get_recommendation_engine().generate_recommendations(
            parsed_cards, insurance_request.applicant
        )
    except Exception as e:
        print(f"Recommendation engine error: {e}")
        recommendations = create_fallback_recommendations(parsed_cards)
    
    return {
        "quotes": raw_insurance_response,
        "parsed_cards": parsed_cards,
        "recommendations": recommendations
    }

# MVP Helper Functions
def is_mvp_questionnaire(responses: Dict[str, Any]) -> bool:
    """Detect if this is the simplified 8-question MVP questionnaire"""
    mvp_question_ids = {
        "basic_info", "existing_coverage", "current_coverage_amount", 
        "health_status", "primary_need", "budget", "coverage_priority", "timeline"
    }
    
    # Check if we have MVP questions and don't have legacy questions
    has_mvp_questions = any(qid in responses for qid in mvp_question_ids)
    has_legacy_questions = any(qid.startswith("personal_") for qid in responses.keys())
    
    return has_mvp_questions and not has_legacy_questions

def parse_basic_info(basic_info: str) -> tuple[int, float]:
    """Parse age and income from combined basic info response"""
    import re
    
    # Default values
    age = 30
    annual_income = 50000.0
    
    # Try to extract age and income with regex
    numbers = re.findall(r'\d+', basic_info.replace(',', ''))
    
    if len(numbers) >= 2:
        # Assume first smaller number is age, larger is income
        nums = [int(n) for n in numbers]
        nums.sort()
        
        if nums[0] <= 100:  # Reasonable age range
            age = nums[0]
        if nums[-1] >= 1000:  # Reasonable income range
            annual_income = float(nums[-1])
    
    return age, annual_income

def estimate_current_premium(coverage_type: str, budget: str, annual_income: float) -> float:
    """Estimate current premium based on coverage type and budget indication"""
    
    # Base estimates by coverage type (monthly)
    base_estimates = {
        "employer_only": annual_income * 0.02 / 12,          # 2% of income
        "employer_comprehensive": annual_income * 0.04 / 12,  # 4% of income
        "individual_basic": annual_income * 0.03 / 12,       # 3% of income
        "individual_comprehensive": annual_income * 0.05 / 12, # 5% of income
        "parents": 50  # Minimal amount
    }
    
    base_premium = base_estimates.get(coverage_type, annual_income * 0.03 / 12)
    
    # Adjust based on budget indication
    if budget == "under_100":
        return min(base_premium, 90)
    elif budget == "100_200":
        return min(base_premium, 180)
    elif budget == "200_400":
        return min(base_premium, 380)
    
    return base_premium

def create_minimal_applicant(age: int, annual_income: float, health_status: str) -> ApplicantProfile:
    """Create minimal applicant profile for API call"""
    from datetime import date
    
    # Calculate birth year
    current_year = date.today().year
    birth_year = current_year - age
    
    # Map health status to smoker status (rough heuristic)
    smoker = health_status == "poor"  # Very rough mapping
    
    return ApplicantProfile(
        first_name="User",
        last_name="Person", 
        dob=f"{birth_year}-01-01",
        gender="OTHER",
        email="user@example.com",
        phone="000-000-0000",
        address_line1="123 Main St",
        city="Anytown",
        state="CA",
        postal_code="12345",
        annual_income=annual_income,
        smoker=smoker
    )

def should_fetch_new_quotes(policy_analysis, primary_need: str, existing_coverage: str) -> bool:
    """Determine if we should fetch new insurance quotes"""
    
    # Always get quotes if no existing coverage
    if existing_coverage == "none":
        return True
    
    # Check user's primary need
    if primary_need in ["save_money", "fill_gaps", "compare_options"]:
        return True
    
    # If analysis suggests action needed
    if policy_analysis:
        if policy_analysis.primary_recommendation in ["add_supplemental", "switch_provider", "get_new_coverage"]:
            return True
        if policy_analysis.can_save_money and policy_analysis.potential_monthly_savings > 20:
            return True
    
    return False

def generate_mvp_recommendations(policy_analysis, primary_need: str, timeline: str) -> List[str]:
    """Generate recommendations based on policy analysis"""
    recommendations = []
    
    if not policy_analysis:
        # No existing coverage
        recommendations.extend([
            "Start with basic health insurance to avoid medical debt",
            "Consider term life insurance if you have dependents",
            "Critical illness coverage is important for young adults"
        ])
    else:
        # Has existing coverage - use analysis
        if policy_analysis.primary_recommendation == "no_action_needed":
            recommendations.append("Your current coverage looks good - no immediate action needed")
        else:
            recommendations.append(policy_analysis.recommendation_reason)
            recommendations.extend(policy_analysis.specific_actions[:3])  # Top 3 actions
    
    # Add timeline-specific advice
    if timeline == "immediately":
        recommendations.insert(0, "⚠️ Coverage gap detected - prioritize immediate coverage")
    elif timeline == "exploring":
        recommendations.append("💡 Take time to compare options - no rush needed")
    
    return recommendations

def map_coverage_priority_to_product_type(coverage_priority: str) -> ProductType:
    """Map user's coverage priority to insurance product type"""
    mapping = {
        "health_medical": ProductType.HEALTH_BASIC,
        "life_protection": ProductType.LIFE_TERM,
        "critical_illness": ProductType.CRITICAL_ILLNESS,
        "comprehensive_all": ProductType.HEALTH_PREMIUM,
        "unsure": ProductType.HEALTH_BASIC
    }
    return mapping.get(coverage_priority, ProductType.HEALTH_BASIC)

def calculate_needed_coverage(age: int, annual_income: float, existing_coverage: str, coverage_amount: str) -> float:
    """Calculate how much coverage the user needs"""
    
    # Base coverage recommendation (10x income for life, 2x for health)
    base_health_coverage = annual_income * 2
    base_life_coverage = annual_income * 10
    
    # Adjust for age
    if age < 30:
        base_coverage = max(base_health_coverage, 100000)
    elif age < 50:
        base_coverage = max(base_life_coverage, 200000) 
    else:
        base_coverage = max(base_life_coverage * 0.8, 150000)
    
    # Subtract existing coverage to find gap
    existing_amounts = {
        "none": 0,
        "under_50k": 25000,
        "50k_100k": 75000, 
        "100k_250k": 175000,
        "250k_500k": 375000,
        "over_500k": 750000
    }
    
    existing_amount = existing_amounts.get(coverage_amount, 0)
    needed_coverage = max(base_coverage - existing_amount, 50000)  # Minimum 50k
    
    return needed_coverage

def create_fallback_cards(raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create basic cards when AI parser fails"""
    quotes = raw_response.get("quotes", [])
    cards = []
    
    for quote in quotes[:3]:  # Top 3
        card = {
            "company_name": quote.get("company_name", "Insurance Company"),
            "plan_name": quote.get("product_name", "Insurance Plan"),
            "monthly_cost": f"${quote.get('total_monthly_premium', 0):.0f}/month",
            "coverage_amount": f"${quote.get('coverage_amount', 0):,.0f}",
            "key_benefits": ["Medical coverage", "Healthcare benefits"],
            "value_score": 75,
            "recommended": len(cards) == 0  # First card is recommended
        }
        cards.append(card)
    
    return cards

def create_fallback_recommendations(cards: List[Dict[str, Any]]) -> List[str]:
    """Create basic recommendations when AI engine fails"""
    if not cards:
        return ["No suitable plans found - please adjust your criteria"]
    
    return [
        f"Consider {cards[0]['company_name']} for the best value",
        "Compare coverage details carefully", 
        "Check provider networks in your area"
    ]

# NEW: Direct Schema Population Functions

def populate_user_profile_field(session: QuestionnaireSession, question_id: str, answer_value: Any):
    """Directly populate UserProfile schema as user answers questions"""
    
    # Parse basic_info if it's the combined field
    if question_id == "basic_info" and isinstance(answer_value, str):
        age, income = parse_basic_info_direct(answer_value)
        session.user_profile.age = age
        session.user_profile.annual_income = income
        return
    
    # Direct field mappings for MVP questionnaire
    field_mappings = {
        "existing_coverage": "existing_coverage_type",
        "current_coverage_amount": "existing_coverage_amount", 
        "health_status": "health_status",
        "primary_need": "primary_need",
        "budget": "monthly_budget",
        "coverage_priority": "coverage_priority", 
        "timeline": "urgency"
    }
    
    if question_id in field_mappings:
        profile_field = field_mappings[question_id]
        setattr(session.user_profile, profile_field, answer_value)

def parse_basic_info_direct(basic_info: str) -> tuple[int, float]:
    """Parse age and income from basic_info text"""
    import re
    
    # Default values
    age = 30
    annual_income = 50000.0
    
    # Extract numbers
    numbers = re.findall(r'\d+', basic_info.replace(',', ''))
    
    if len(numbers) >= 2:
        nums = [int(n) for n in numbers]
        nums.sort()
        
        # Assume smaller number is age, larger is income
        if nums[0] <= 100:  # Reasonable age
            age = nums[0]
        if nums[-1] >= 1000:  # Reasonable income
            annual_income = float(nums[-1])
    elif len(numbers) == 1:
        num = int(numbers[0])
        if num <= 100:
            age = num
        elif num >= 1000:
            annual_income = float(num)
    
    return age, annual_income

async def process_completed_questionnaire_agentic(session: QuestionnaireSession) -> Dict[str, Any]:
    """Process questionnaire with agents - schema is already populated!"""
    
    # Schema is already populated from direct mapping - no transformation needed!
    user_profile = session.user_profile
    
    print(f"Processing with populated profile: {user_profile.dict()}")
    
    # 1. AGENT: Analyze existing policy if user has coverage
    existing_policy_analysis = None
    if user_profile.existing_coverage_type != "none":
        try:
            # Use existing policy analyzer (convert to schema format)
            estimated_premium = estimate_premium_from_budget(user_profile.monthly_budget, user_profile.annual_income)
            
            old_analysis = analyze_existing_policy(
                existing_coverage=user_profile.existing_coverage_type,
                coverage_amount=user_profile.existing_coverage_amount,
                monthly_premium=estimated_premium,
                annual_income=user_profile.annual_income,
                age=user_profile.age,
                health_status=user_profile.health_status,
                primary_need=user_profile.primary_need
            )
            
            # Convert to new schema format
            existing_policy_analysis = ExistingPolicyAssessment(
                coverage_adequacy=map_coverage_adequacy(old_analysis.coverage_status),
                monthly_cost_assessment="reasonable",
                coverage_gaps=old_analysis.uncovered_risks,
                over_coverage_areas=old_analysis.over_coverage_areas,
                primary_action=map_recommendation_to_action(old_analysis.primary_recommendation),
                potential_monthly_savings=old_analysis.potential_monthly_savings,
                confidence_score=80,
                analysis_reasoning=old_analysis.recommendation_reason,
                specific_actions=old_analysis.specific_actions
            )
        except Exception as e:
            print(f"Existing policy analysis failed: {e}")
    
    # 2. AGENT: Evaluate needs and determine next steps
    try:
        needs_agent = get_needs_evaluation_agent()
        needs_analysis = await needs_agent.evaluate_insurance_needs(
            user_profile, existing_policy_analysis
        )
    except Exception as e:
        print(f"Needs evaluation failed: {e}")
        needs_analysis = create_fallback_needs_analysis(user_profile)
    
    result = {
        "user_profile": user_profile.dict(),
        "existing_policy_analysis": existing_policy_analysis.dict() if existing_policy_analysis else None,
        "needs_analysis": needs_analysis.dict(),
        "scored_policies": []
    }
    
    # 3. Conditional: Get quotes only if analysis suggests it
    if needs_analysis.should_get_quotes:
        try:
            # Convert to API format
            applicant_data = user_profile.to_applicant_data()
            
            # Determine coverage amount and product type
            coverage_amount = needs_analysis.recommended_coverage_amount
            product_type_mapping = {
                "HEALTH_BASIC": ProductType.HEALTH_BASIC,
                "HEALTH_PREMIUM": ProductType.HEALTH_PREMIUM, 
                "LIFE_TERM": ProductType.LIFE_TERM,
                "CRITICAL_ILLNESS": ProductType.CRITICAL_ILLNESS
            }
            product_type = product_type_mapping.get(needs_analysis.priority_product_type, ProductType.HEALTH_BASIC)
            
            # Create insurance request
            insurance_request = InsuranceRequest(
                product_type=product_type,
                applicant=applicant_data,
                coverage_amount=coverage_amount,
                deductible=None,
                term_years=None,
                riders=[],
                beneficiaries=[]
            )
            
            # Get quotes
            quotes_data = await fetch_insurance_quotes_simple(insurance_request)
            result["new_quotes"] = quotes_data
            
        except Exception as e:
            print(f"Quote fetching failed: {e}")
            result["quotes_error"] = f"Error fetching quotes: {str(e)}"
    else:
        result["quotes_skipped"] = needs_analysis.reasoning
    
    return result

def estimate_premium_from_budget(budget_range: str, annual_income: float) -> float:
    """Estimate current premium from budget indication"""
    budget_mapping = {
        "under_100": 80,
        "100_200": 150,
        "200_400": 300,
        "400_plus": 500,
        "show_all": annual_income * 0.03 / 12  # 3% of income default
    }
    return budget_mapping.get(budget_range, 150)

def map_coverage_adequacy(old_status) -> str:
    """Map old coverage status to new schema"""
    mapping = {
        "over_insured": "over_insured",
        "adequately_insured": "adequately_insured", 
        "under_insured": "under_insured",
        "no_coverage": "no_coverage"
    }
    return mapping.get(str(old_status), "adequately_insured")

def map_recommendation_to_action(old_recommendation) -> str:
    """Map old recommendation to new action"""
    mapping = {
        "no_action_needed": "no_action",
        "reduce_coverage": "reduce_coverage",
        "add_supplemental": "add_supplemental", 
        "switch_provider": "switch_provider",
        "get_new_coverage": "get_new_coverage"
    }
    return mapping.get(str(old_recommendation), "no_action")

def create_fallback_needs_analysis(user_profile: UserProfile) -> NeedsEvaluationSchema:
    """Create fallback when needs agent fails"""
    return NeedsEvaluationSchema(
        should_get_quotes=user_profile.existing_coverage_type == "none",
        reasoning="Basic assessment based on your profile",
        recommended_coverage_amount=max(user_profile.annual_income * 5, 100000),
        priority_product_type="HEALTH_BASIC",
        urgency_level="can_wait",
        main_recommendation="Consider basic insurance coverage",
        action_items=["Review your needs", "Compare options", "Make informed decision"]
    )

async def fetch_insurance_quotes_simple(insurance_request: InsuranceRequest) -> Dict[str, Any]:
    """Simplified quote fetching"""
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/quote",
            json=insurance_request.dict(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()

# End of new agentic functions

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
    """Convert conversational questionnaire responses to enhanced ApplicantProfile"""
    
    # Handle both old and new smoking fields for backward compatibility
    smoking_response = responses.get("smoking_vaping_habits", responses.get("smoking_habits", "never"))
    smoker = None
    if smoking_response in ["regular", "heavy"]:
        smoker = True
    elif smoking_response in ["never", "quit_over_year"]:
        smoker = False
    elif smoking_response in ["quit_under_year", "occasional", "social"]:
        smoker = True  # Recent quitters and occasional users still rated as smokers
    
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
    
    # Use actual annual income if provided, otherwise estimate
    actual_income = responses.get("annual_income")
    if actual_income and isinstance(actual_income, (int, float)) and actual_income > 0:
        annual_income = float(actual_income)
    else:
        annual_income = estimated_income
    
    return ApplicantProfile(
        # Personal Information
        first_name=responses.get("personal_first_name", ""),
        last_name=responses.get("personal_last_name", ""),
        dob=responses.get("personal_dob", "1990-01-01"),
        gender=responses.get("personal_gender", "M"),
        email=responses.get("personal_email", ""),
        phone=responses.get("personal_phone", ""),
        
        # Address
        address_line1=responses.get("address_line1", ""),
        address_line2=None,
        city=responses.get("address_city", ""),
        state=responses.get("address_state", "CA"),
        postal_code=responses.get("address_postal_code", ""),
        country="US",
        
        # Financial Information
        annual_income=annual_income,
        occupation=occupation,
        
        # Health Information (enhanced)
        smoker=smoker,
        smoking_vaping_habits=smoking_response,
        height_cm=base_height,
        weight_kg=base_weight * weight_modifier,
        
        # Medical History
        pre_existing_conditions=pre_existing_conditions,
        medications=[],  # Will be inferred from health conditions
        hospitalizations_last_5_years=0 if health_overall in ["excellent", "good"] else 1,
        family_medical_history=[],  # Not asked in conversational format
        
        # Lifestyle Risk Factors (Phase 1)
        alcohol_consumption=responses.get("alcohol_consumption", "social"),
        exercise_frequency=responses.get("exercise_habits", "weekly" if health_overall in ["excellent", "good"] else "monthly"),
        dietary_habits=responses.get("dietary_habits"),
        high_risk_activities=responses.get("high_risk_activities", []),
        travel_frequency=travel_frequency,
        
        # Coverage Gaps & Transition Status (Phase 2)
        current_coverage_status=responses.get("current_coverage_status"),
        parents_policy_end_date=responses.get("parents_policy_end_date"),
        employer_coverage_expectation=responses.get("employer_coverage_expectation"),
        hospital_preference=responses.get("hospital_preference"),
        special_coverage_needs=responses.get("special_coverage_needs", []),
        
        # Preferences & Budget (Phase 3)
        coverage_vs_premium_priority=responses.get("coverage_vs_premium_priority"),
        desired_add_ons=responses.get("desired_add_ons", []),
        monthly_premium_budget=responses.get("monthly_premium_budget"),
        deductible_copay_preference=responses.get("deductible_copay_preference")
    )

@app.post("/api/upload-policy")
async def upload_policy_document(
    policy_file: UploadFile = File(...)
):
    """
    Upload and analyze existing insurance policy documents
    Returns policy analysis without starting questionnaire session
    """
    try:
        # Validate file type
        allowed_types = ['.pdf', '.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(policy_file.filename)[1].lower()
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_ext} not supported. Please upload PDF, JPG, PNG, or JPEG files."
            )
        
        # Read file content
        file_content = await policy_file.read()
        
        print(f"📄 Processing policy document: {policy_file.filename} ({len(file_content)} bytes)")
        
        # Extract policy information using PDF parser
        extraction_result = None
        if file_ext == '.pdf':
            try:
                pdf_parser = get_pdf_parser()
                extraction_result = await pdf_parser.extract_pdf_fields(file_content, policy_file.filename)
            except Exception as e:
                print(f"PDF parsing failed: {e}")
                # Continue with fallback analysis
        
        # Create basic policy data for analysis
        extracted_data = {}
        if extraction_result and extraction_result.extracted_fields:
            extracted_data = extraction_result.extracted_fields
        
        # Analyze the existing policy using policy analyzer agent
        try:
            analysis = await analyze_existing_policy(
                coverage_type=extracted_data.get('coverage_type', 'unknown'),
                coverage_amount=float(extracted_data.get('coverage_amount', 0)) if extracted_data.get('coverage_amount') else 0,
                monthly_premium=float(extracted_data.get('monthly_premium', 0)) if extracted_data.get('monthly_premium') else 0,
                annual_income=float(extracted_data.get('annual_income', 75000)),  # Default estimate
                age=int(extracted_data.get('age', 35)),  # Default estimate
                health_status=extracted_data.get('health_status', 'good'),
                primary_need='analyze_existing'
            )
        except Exception as e:
            print(f"Policy analysis failed: {e}")
            # Create fallback analysis
            analysis = ExistingPolicyAssessment(
                coverage_adequacy="unknown",
                monthly_cost_assessment="reasonable",
                coverage_gaps=["Unable to fully analyze document"],
                over_coverage_areas=[],
                primary_action="get_new_coverage" if extracted_data else "continue_current",
                potential_monthly_savings=0.0,
                confidence_score=30,
                analysis_reasoning="Document processed but detailed analysis unavailable. Consider getting quotes to compare your options.",
                specific_actions=[
                    "Get quotes from multiple providers",
                    "Compare coverage amounts and features",
                    "Review your current policy details",
                    "Consider your changing needs"
                ]
            )
        
        # Return analysis results
        response = {
            "success": True,
            "filename": policy_file.filename,
            "extracted_fields": extracted_data,
            "extraction_confidence": extraction_result.confidence_score if extraction_result else 0.3,
            "existing_policy_analysis": analysis.dict(),
            "recommendation": {
                "should_get_quotes": analysis.primary_action in ['get_new_coverage', 'switch_provider', 'add_supplemental'],
                "priority": "high" if analysis.primary_action == 'get_new_coverage' else "medium",
                "message": analysis.analysis_reasoning
            }
        }
        
        print(f"✅ Policy analysis complete: {analysis.primary_action} (confidence: {analysis.confidence_score}%)")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Policy upload error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process policy document: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)