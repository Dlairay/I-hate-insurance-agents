"""
questionnaire/server.py
=======================
python -m uvicorn backend.questionnaire_server:app --host 0.0.0.0 --port 8001 --reload
Questionnaire server that runs on port 8001
"""

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from pydantic import BaseModel

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Simple demo auth models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class AuthResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    message: str
    user_data: Optional[Dict[str, Any]] = None

from backend.shared.models import (
    QuestionnaireSession, QuestionnaireResponse, 
    ApplicantProfile, InsuranceRequest, ProductType,
    UserProfile, ExistingPolicyAssessment, NeedsEvaluationSchema, PolicyScore
)
from backend.questions import INSURANCE_QUESTIONS, should_show_question
from backend.agents.option_selector_agent import QuestionnaireHelper
from backend.agents.response_parser_agent import ResponseParser
from backend.agents.recommendation_agent import RecommendationEngine
from backend.agents.pdf_parser_agent import get_pdf_parser, PDFExtractionResult
from backend.agents.scoring_agent import get_scoring_agent, score_insurance_policies

app = FastAPI(
    title="Insurance Questionnaire Server",
    description="Interactive questionnaire with AI helpers",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Database-persistent sessions instead of in-memory
sessions: Dict[str, QuestionnaireSession] = {}

async def save_session_to_db(session: QuestionnaireSession):
    """Save session to database for persistence"""
    try:
        session_doc = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "responses": [resp.dict() for resp in session.responses],
            "completed": session.completed,
            "current_question_index": session.current_question_index,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "metadata": session.metadata or {}
        }
        
        await async_db[Collections.QUESTIONNAIRE_SESSIONS].replace_one(
            {"session_id": session.session_id},
            session_doc,
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ Failed to save session to database: {e}")

async def load_session_from_db(session_id: str) -> Optional[QuestionnaireSession]:
    """Load session from database"""
    try:
        doc = await async_db[Collections.QUESTIONNAIRE_SESSIONS].find_one({"session_id": session_id})
        if not doc:
            return None
            
        # Reconstruct session object
        session = QuestionnaireSession(session_id=session_id)
        session.user_id = doc.get("user_id")
        session.completed = doc.get("completed", False)
        session.current_question_index = doc.get("current_question_index", 0)
        session.created_at = doc.get("created_at")
        session.updated_at = doc.get("updated_at")
        session.metadata = doc.get("metadata", {})
        
        # Reconstruct responses
        session.responses = []
        for resp_data in doc.get("responses", []):
            response = QuestionnaireResponse(
                question_id=resp_data["question_id"],
                answer=resp_data["answer"],
                needs_help=resp_data.get("needs_help", False),
                help_description=resp_data.get("help_description"),
                ai_selected=resp_data.get("ai_selected", False)
            )
            session.responses.append(response)
            
        return session
    except Exception as e:
        print(f"⚠️ Failed to load session from database: {e}")
        return None

async def get_persistent_session(session_id: str) -> Optional[QuestionnaireSession]:
    """Get session from memory or database"""
    # Try memory first
    if session_id in sessions:
        return sessions[session_id]
    
    # Try database
    session = await load_session_from_db(session_id)
    if session:
        sessions[session_id] = session
    await save_session_to_db(session)  # Cache in memory
    
    return session

# Import database models for persistence
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.database import (
    async_db, Collections, QuestionnaireSessionRecord, 
    PDFExtractionRecord, PolicyScoreRecord, User
)
import hashlib
import uuid

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
    """Landing page"""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        # Fallback HTML if templates not found
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>AI Insurance Broker</title></head>
        <body>
            <h1>AI Insurance Broker</h1>
            <p>Insurance made easy, just for you!</p>
            <p>Template files not found. API endpoints are still available at:</p>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li><a href="/questionnaire">Questionnaire</a></li>
                <li><a href="/login">Login</a></li>
            </ul>
        </body>
        </html>
        """)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    if templates:
        return templates.TemplateResponse("login.html", {"request": request})
    else:
        return HTMLResponse("<h1>Login page not available - templates not found</h1>")

@app.get("/dashboard", response_class=HTMLResponse)  
async def dashboard_page(request: Request):
    """User dashboard page"""
    if templates:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    else:
        return HTMLResponse("<h1>Dashboard page not available - templates not found</h1>")

@app.get("/questionnaire", response_class=HTMLResponse)
async def questionnaire_page(request: Request):
    """Questionnaire page (alternative route)"""
    if templates:
        return templates.TemplateResponse("questionnaire.html", {"request": request})
    else:
        return HTMLResponse("<h1>Questionnaire page not available - templates not found</h1>")

@app.get("/claims", response_class=HTMLResponse)
async def claims_page(request: Request):
    """Claims management page"""
    if templates:
        return templates.TemplateResponse("claims.html", {"request": request})
    else:
        return HTMLResponse("<h1>Claims page not available - templates not found</h1>")

@app.get("/claims-dashboard", response_class=HTMLResponse)
async def claims_dashboard_page(request: Request):
    """Claims dashboard page"""
    if templates:
        return templates.TemplateResponse("claims_dashboard.html", {"request": request})
    else:
        return HTMLResponse("<h1>Claims dashboard page not available - templates not found</h1>")

@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    """FAQ/Support page"""
    if templates:
        return templates.TemplateResponse("faq.html", {"request": request})
    else:
        return HTMLResponse("<h1>FAQ page not available - templates not found</h1>")

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Checkout/Shopping cart page"""
    if templates:
        return templates.TemplateResponse("checkout.html", {"request": request})
    else:
        return HTMLResponse("<h1>Checkout page not available - templates not found</h1>")

@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request):
    """Payment page"""
    if templates:
        return templates.TemplateResponse("payment.html", {"request": request})
    else:
        return HTMLResponse("<h1>Payment page not available - templates not found</h1>")

@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    """Payment success page"""
    if templates:
        return templates.TemplateResponse("success.html", {"request": request})
    else:
        return HTMLResponse("<h1>Success page not available - templates not found</h1>")

@app.post("/api/start-session")
async def start_session():
    """Start a new questionnaire session"""
    session_id = str(uuid.uuid4())
    session = QuestionnaireSession(session_id=session_id)
    # Initialize user_profile as None - will be created when first answer submitted
    session.user_profile = None
    
    # Track that no PDF was uploaded - auto-answer existing coverage questions
    session.metadata = {"has_pdf_upload": False}
    
    # Auto-fill existing coverage questions since no PDF was uploaded
    auto_responses = [
        QuestionnaireResponse(
            question_id="existing_coverage",
            answer="none",
            needs_help=False
        ),
        QuestionnaireResponse(
            question_id="current_coverage_amount", 
            answer="none",
            needs_help=False
        )
    ]
    session.responses.extend(auto_responses)
    
    sessions[session_id] = session
    await save_session_to_db(session)
    
    # Find first unanswered question (skip auto-answered ones)
    answered_question_ids = {resp.question_id for resp in session.responses}
    first_unanswered_question = None
    session.current_question_index = 0
    
    for i, question in enumerate(INSURANCE_QUESTIONS):
        if question.id not in answered_question_ids:
            first_unanswered_question = question
            session.current_question_index = i
            break
    
    # Update session with current index
    sessions[session_id] = session
    await save_session_to_db(session)
    
    # Calculate progress 
    answered_count = len(session.responses)
    total_questions = len(INSURANCE_QUESTIONS)
    
    return {
        "session_id": session_id,
        "current_question": first_unanswered_question.dict() if first_unanswered_question else None,
        "progress": {"current": answered_count + 1, "total": total_questions},
        "auto_answered": list(answered_question_ids)
    }

@app.post("/api/start-session-with-profile")
async def start_session_with_profile(profile_data: Dict[str, Any]):
    """Start questionnaire session with pre-filled profile data"""
    print(f"DEBUG: Received profile_data: {profile_data}")
    session_id = str(uuid.uuid4())
    session = QuestionnaireSession(session_id=session_id)
    # Initialize user_profile as None - will be created when first answer submitted
    session.user_profile = None
    
    # Track that no PDF was uploaded - auto-answer existing coverage questions
    # Store the original profile data for later use
    session.metadata = {"has_pdf_upload": False, "original_profile": profile_data}
    
    # Auto-fill questions based on profile data
    auto_responses = []
    
    print(f"DEBUG: Profile data keys: {list(profile_data.keys())}")
    print(f"DEBUG: Full profile data: {profile_data}")
    
    # Add personal information to session for ApplicantProfile conversion
    personal_fields = {}
    
    # Handle name - split full_name into first and last
    if "full_name" in profile_data:
        name_parts = profile_data["full_name"].strip().split()
        personal_fields["personal_first_name"] = name_parts[0] if name_parts else ""
        personal_fields["personal_last_name"] = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        print(f"DEBUG: Split name '{profile_data['full_name']}' into first='{personal_fields['personal_first_name']}', last='{personal_fields['personal_last_name']}'")
    
    # Handle contact info
    if "email" in profile_data:
        personal_fields["personal_email"] = profile_data["email"]
    if "phone" in profile_data:
        personal_fields["personal_phone"] = profile_data["phone"]
    
    # Handle age and create DOB
    age_str = ""
    if "age" in profile_data:
        age_str = str(profile_data["age"])
        # Create approximate DOB from age
        from datetime import date
        current_year = date.today().year
        birth_year = current_year - int(profile_data["age"])
        personal_fields["personal_dob"] = f"{birth_year}-01-01"
        print(f"DEBUG: Found age: {age_str}, created DOB: {personal_fields['personal_dob']}")
    elif "dob" in profile_data:
        personal_fields["personal_dob"] = profile_data["dob"]
        from datetime import date
        try:
            birth = date.fromisoformat(profile_data["dob"])
            today = date.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            age_str = str(age)
        except:
            pass
    
    # Handle address - flatten nested address object
    if "address" in profile_data:
        addr = profile_data["address"]
        if "street" in addr:
            personal_fields["address_line1"] = addr["street"]
        if "city" in addr:
            personal_fields["address_city"] = addr["city"]
        if "state" in addr:
            personal_fields["address_state"] = addr["state"]
        if "zip_code" in addr:
            personal_fields["address_postal_code"] = addr["zip_code"]
        print(f"DEBUG: Mapped address: {personal_fields}")
    
    # Store personal fields in session metadata for ApplicantProfile conversion
    session.metadata.update({"personal_fields": personal_fields})
    
    # Handle income
    income_str = ""
    if "annual_income" in profile_data:
        income_str = str(profile_data["annual_income"])
        personal_fields["annual_income"] = float(profile_data["annual_income"])
        print(f"DEBUG: Found annual_income: {income_str}")
    
    # Create basic_info response
    if age_str or income_str:
        combined_answer = f"{age_str} years old, income ${income_str}".strip()
        print(f"DEBUG: Creating basic_info response: {combined_answer}")
        auto_responses.append(QuestionnaireResponse(
            question_id="basic_info",
            answer=combined_answer,
            needs_help=False
        ))
    else:
        print("DEBUG: No age or income found, not creating basic_info response")
    
    # 2. Handle occupation mapping
    if "occupation" in profile_data:
        occupation = profile_data["occupation"].lower()
        print(f"DEBUG: Found occupation: {occupation}")
        occupation_mapping = {
            "software engineer": "office_professional",
            "engineer": "office_professional", 
            "developer": "office_professional",
            "programmer": "office_professional",
            "analyst": "office_professional",
            "manager": "office_professional",
            "doctor": "healthcare",
            "nurse": "healthcare",
            "teacher": "education",
            "professor": "education",
            "instructor": "education",
            "driver": "transportation",
            "pilot": "transportation",
            "construction": "construction",
            "builder": "construction",
            "police": "law_enforcement",
            "officer": "law_enforcement",
            "security": "law_enforcement"
        }
        
        occupation_value = "other"  # default
        for key, value in occupation_mapping.items():
            if key in occupation:
                occupation_value = value
                break
                
        print(f"DEBUG: Mapped occupation '{occupation}' to '{occupation_value}'")
        auto_responses.append(QuestionnaireResponse(
            question_id="occupation",
            answer=occupation_value,
            needs_help=False
        ))
    
    # 3. Handle smoking status from health_info (only basic health facts)
    if "health_info" in profile_data and "smoker" in profile_data["health_info"]:
        is_smoker = profile_data["health_info"]["smoker"]
        smoking_answer = "yes_cigarettes" if is_smoker else "never"
        auto_responses.append(QuestionnaireResponse(
            question_id="smoking_vaping_habits",
            answer=smoking_answer,
            needs_help=False
        ))
    
    # DO NOT auto-fill insurance preferences - that's what the questionnaire is for!
    # Only auto-fill basic personal info to speed up the process
    
    # Auto-fill existing coverage questions since no PDF was uploaded (if not already answered)
    existing_question_ids = {resp.question_id for resp in auto_responses}
    
    if "existing_coverage" not in existing_question_ids:
        auto_responses.append(QuestionnaireResponse(
            question_id="existing_coverage",
            answer="none",
            needs_help=False
        ))
    
    if "current_coverage_amount" not in existing_question_ids:
        auto_responses.append(QuestionnaireResponse(
            question_id="current_coverage_amount", 
            answer="none",
            needs_help=False
        ))
    
    # Add all auto-responses (now includes coverage questions)
    print(f"DEBUG: Created {len(auto_responses)} auto-responses:")
    for resp in auto_responses:
        print(f"  - {resp.question_id}: {resp.answer}")
    session.responses.extend(auto_responses)
    
    # Find first unanswered question
    answered_question_ids = {resp.question_id for resp in session.responses}
    session.current_question_index = 0
    
    for i, question in enumerate(INSURANCE_QUESTIONS):
        if question.id not in answered_question_ids:
            session.current_question_index = i
            break
    
    sessions[session_id] = session
    await save_session_to_db(session)
    
    # Get the current question (skipping answered ones)
    if session.current_question_index < len(INSURANCE_QUESTIONS):
        current_question = INSURANCE_QUESTIONS[session.current_question_index]
    else:
        current_question = None
    
    # Calculate progress based on actual remaining questions
    total_questions = len(INSURANCE_QUESTIONS)
    answered_count = len(session.responses)
    remaining_questions = total_questions - answered_count
    
    return {
        "session_id": session_id,
        "current_question": current_question.dict() if current_question else None,
        "progress": {"current": answered_count + 1, "total": total_questions},
        "skipped_questions": list(answered_question_ids),
        "remaining_questions": remaining_questions
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
    
    # Store extraction result in session metadata (convert Pydantic model to dict for MongoDB)
    try:
        extraction_dict = extraction_result.dict() if hasattr(extraction_result, 'dict') else extraction_result.__dict__
    except Exception as e:
        print(f"⚠️  Warning: Could not serialize PDF extraction result: {e}")
        extraction_dict = {
            "error": f"Serialization failed: {str(e)}",
            "confidence_score": 0.0,
            "extracted_fields": {}
        }
    
    session.metadata = {
        "has_pdf_upload": True,
        "pdf_extraction": extraction_dict,
        "pdf_filename": pdf_file.filename
    }
    
    # Pre-fill questions based on extracted data
    extracted_fields = extraction_result.extracted_fields
    
    # Store extracted fields in session metadata for ApplicantProfile conversion (same pattern as JSON)
    personal_fields = {}
    
    # Map PDF fields to personal fields format
    pdf_to_personal_mappings = [
        ("first_name", "personal_first_name"),
        ("last_name", "personal_last_name"), 
        ("dob", "personal_dob"),
        ("gender", "personal_gender"),
        ("email", "personal_email"),
        ("phone", "personal_phone"),
        ("address_line1", "address_line1"),
        ("city", "address_city"),
        ("state", "address_state"),
        ("postal_code", "address_postal_code"),
        ("annual_income", "annual_income"),
    ]
    
    for pdf_field, personal_field in pdf_to_personal_mappings:
        if pdf_field in extracted_fields:
            personal_fields[personal_field] = extracted_fields[pdf_field]
    
    # Also merge with any JSON profile data
    if json_profile and profile_data:
        # Apply same JSON mapping logic to PDF case
        if "full_name" in profile_data:
            name_parts = profile_data["full_name"].strip().split()
            personal_fields["personal_first_name"] = name_parts[0] if name_parts else personal_fields.get("personal_first_name", "")
            personal_fields["personal_last_name"] = " ".join(name_parts[1:]) if len(name_parts) > 1 else personal_fields.get("personal_last_name", "")
        
        if "annual_income" in profile_data:
            personal_fields["annual_income"] = float(profile_data["annual_income"])
    
    # Store in session metadata for ApplicantProfile conversion
    session.metadata.update({"personal_fields": personal_fields})
    print(f"DEBUG: Stored personal fields from PDF+JSON: {personal_fields}")
    
    # Map extracted fields to questionnaire responses (for questionnaire flow)
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
    
    # Handle existing coverage questions based on PDF extraction
    if "existing_coverage_type" in extracted_fields or "policy_number" in extracted_fields:
        # PDF contains existing coverage information - answer existing_coverage appropriately
        if "existing_coverage_type" in extracted_fields:
            coverage_type = extracted_fields["existing_coverage_type"].lower()
            if "health" in coverage_type or "medical" in coverage_type:
                existing_answer = "individual_basic"
            elif "comprehensive" in coverage_type:
                existing_answer = "individual_comprehensive"
            elif "employer" in coverage_type:
                existing_answer = "employer_only"
            else:
                existing_answer = "individual_basic"  # Default for any existing coverage
        else:
            existing_answer = "individual_basic"  # Has policy number, assume individual coverage
        
        coverage_responses = [
            QuestionnaireResponse(
                question_id="existing_coverage",
                answer=existing_answer,
                needs_help=False
            )
        ]
        
        # Try to determine coverage amount from PDF if available
        if "coverage_amount" in extracted_fields:
            amount = extracted_fields["coverage_amount"]
            if isinstance(amount, str):
                amount = amount.replace("$", "").replace(",", "")
                try:
                    amount_num = float(amount)
                    if amount_num < 50000:
                        amount_answer = "under_50k"
                    elif amount_num < 100000:
                        amount_answer = "50k_100k"
                    elif amount_num < 250000:
                        amount_answer = "100k_250k"
                    elif amount_num < 500000:
                        amount_answer = "250k_500k"
                    else:
                        amount_answer = "over_500k"
                except:
                    amount_answer = "50k_100k"  # Default moderate coverage
            else:
                amount_answer = "50k_100k"  # Default moderate coverage
        else:
            amount_answer = "50k_100k"  # Default when no amount in PDF
        
        coverage_responses.append(QuestionnaireResponse(
            question_id="current_coverage_amount",
            answer=amount_answer,
            needs_help=False
        ))
        
        session.responses.extend(coverage_responses)
    else:
        # PDF uploaded but no existing coverage found - user has no existing coverage
        no_coverage_responses = [
            QuestionnaireResponse(
                question_id="existing_coverage",
                answer="none",
                needs_help=False
            ),
            QuestionnaireResponse(
                question_id="current_coverage_amount",
                answer="none",
                needs_help=False
            )
        ]
        session.responses.extend(no_coverage_responses)
    
    # Find first unanswered question
    answered_question_ids = {resp.question_id for resp in session.responses}
    first_unanswered_index = 0
    
    for i, question in enumerate(INSURANCE_QUESTIONS):
        if question.id not in answered_question_ids:
            first_unanswered_index = i
            break
    
    session.current_question_index = first_unanswered_index
    sessions[session_id] = session
    await save_session_to_db(session)
    
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
async def get_session_endpoint(session_id: str):
    """Get current session state"""
    session = await get_persistent_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current_question = get_current_question(session)
    
    return {
        "session": session.dict(),
        "current_question": current_question.dict() if current_question else None,
        "progress": calculate_progress(session)
    }

@app.post("/api/session/{session_id}/answer")
async def submit_answer(session_id: str, answer_data: Dict[str, Any]):
    """Submit an answer to the current question"""
    session = await get_persistent_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
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
    
    # Get all answered question IDs (including auto-answered ones)
    answered_question_ids = {r.question_id for r in session.responses}
    
    # Move to next unanswered question (skip both auto-answered and conditional questions)
    while session.current_question_index < len(INSURANCE_QUESTIONS):
        next_question = INSURANCE_QUESTIONS[session.current_question_index]
        
        # Skip if question was already answered (auto-answered) or shouldn't be shown
        if (next_question.id not in answered_question_ids and 
            should_show_question(next_question, get_response_dict(session))):
            break
            
        session.current_question_index += 1
    
    # Check if questionnaire is complete
    if session.current_question_index >= len(INSURANCE_QUESTIONS):
        session.completed = True
        
        # Process completed questionnaire with agentic approach
        try:
            print("DEBUG: Starting questionnaire completion processing...")
            insurance_response = await process_completed_questionnaire_agentic(session)
            print("DEBUG: Successfully processed completed questionnaire")
            return {
                "completed": True,
                "redirect_to": f"/recommendations?session={session.session_id}",
                "insurance_response": insurance_response,
                "progress": {"current": len(INSURANCE_QUESTIONS), "total": len(INSURANCE_QUESTIONS)}
            }
        except Exception as e:
            print(f"DEBUG: Error processing completed questionnaire: {str(e)}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error processing questionnaire: {str(e)}")
    
    # Get next question
    next_question = get_current_question(session)
    
    return {
        "completed": False,
        "next_question": next_question.dict() if next_question else None,
        "progress": calculate_progress(session)
    }

@app.post("/api/session/{session_id}/back")
async def go_back_question(session_id: str):
    """Go back to the previous question"""
    session = await get_persistent_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Can't go back if we're at the first question
    if session.current_question_index <= 0:
        raise HTTPException(status_code=400, detail="Already at the first question")
    
    # Remove the last response
    if session.responses:
        last_response = session.responses.pop()
        print(f"🔙 Removed response for question: {last_response.question_id}")
    
    # Move back to the previous question
    session.current_question_index -= 1
    
    # Get the previous question
    current_question = get_current_question(session)
    
    return {
        "success": True,
        "current_question": current_question.dict() if current_question else None,
        "progress": calculate_progress(session)
    }

@app.post("/api/session/{session_id}/previous")
async def go_back_question(session_id: str):
    """Go back to the previous question"""
    try:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Find the current question index
        current_index = session.current_question_index
        
        if current_index <= 0:
            raise HTTPException(status_code=400, detail="Already at first question")
        
        # Remove the last response to "undo" it
        if session.responses:
            session.responses.pop()
            
        # Move back to previous question
        session.current_question_index = current_index - 1
        
        # Update session
        sessions[session_id] = session
        await save_session_to_db(session)
        
        # Get the previous question
        previous_question = None
        if session.current_question_index < len(INSURANCE_QUESTIONS):
            previous_question = INSURANCE_QUESTIONS[session.current_question_index]
        
        return {
            "success": True,
            "previous_question": previous_question.dict() if previous_question else None,
            "progress": calculate_progress(session)
        }
        
    except Exception as e:
        print(f"DEBUG: Error going back: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to go back: {str(e)}")

@app.post("/api/session/{session_id}/get-help")
async def get_question_help(session_id: str, help_request: Dict[str, str]):
    """Get AI help for answering a question or general insurance guidance"""
    session = await get_persistent_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
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

@app.post("/api/session/{session_id}/add-pdf")  
async def add_pdf_to_session(
    session_id: str,
    pdf_file: UploadFile = File(...)
):
    """Add PDF data to existing questionnaire session"""
    print(f"DEBUG: Adding PDF to existing session {session_id}")
    
    # Get existing session
    session = await get_persistent_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate PDF file
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read PDF content
    pdf_content = await pdf_file.read()
    
    try:
        # Process PDF using the existing agent
        from backend.agents.pdf_parser_agent import PDFParserAgent
        pdf_agent = PDFParserAgent()
        
        # Extract from PDF with existing profile context
        existing_profile = session.metadata.get("original_profile", {}) if session.metadata else {}
        print(f"DEBUG: Existing profile context: {existing_profile}")
        
        # Use the correct method name and parameter
        extraction_result = await pdf_agent.extract_insurance_fields_async(
            pdf_content, 
            json_profile=existing_profile
        )
        print(f"DEBUG: PDF extraction result: {extraction_result}")
        
        # Save PDF extraction to database
        extraction_id = await save_pdf_extraction(
            session_id, pdf_file.filename, pdf_content, extraction_result
        )
        
        # Update session metadata to indicate PDF was processed
        if not session.metadata:
            session.metadata = {}
        
        # Convert extraction result to dict for MongoDB storage
        try:
            extraction_dict = extraction_result.dict() if hasattr(extraction_result, 'dict') else extraction_result.__dict__
        except Exception as e:
            print(f"⚠️  Warning: Could not serialize PDF extraction result: {e}")
            extraction_dict = {"error": f"Serialization failed: {str(e)}"}
        
        session.metadata["has_pdf_upload"] = True
        session.metadata["pdf_extraction_id"] = extraction_id
        session.metadata["pdf_extraction"] = extraction_dict
        
        # Create personal fields from PDF extraction (same pattern as other endpoints)
        extracted_fields = extraction_result.extracted_fields
        personal_fields = session.metadata.get("personal_fields", {})
        
        # Map PDF fields to personal fields format
        pdf_to_personal_mappings = [
            ("first_name", "personal_first_name"),
            ("last_name", "personal_last_name"), 
            ("dob", "personal_dob"),
            ("gender", "personal_gender"),
            ("email", "personal_email"),
            ("phone", "personal_phone"),
            ("address_line1", "address_line1"),
            ("city", "address_city"),
            ("state", "address_state"),
            ("postal_code", "address_postal_code"),
            ("annual_income", "annual_income"),
        ]
        
        for pdf_field, personal_field in pdf_to_personal_mappings:
            if pdf_field in extracted_fields:
                personal_fields[personal_field] = extracted_fields[pdf_field]
        
        session.metadata["personal_fields"] = personal_fields
        print(f"DEBUG: Updated personal fields with PDF data: {personal_fields}")
        
        # Update the existing coverage questions based on PDF data
        # Convert Pydantic model to dict if needed
        extracted_data = extraction_result.extracted_fields if hasattr(extraction_result, 'extracted_fields') else extraction_result
        
        if extracted_data.get("has_existing_coverage"):
            print("DEBUG: PDF shows existing coverage, updating responses...")
            # Find and update existing coverage responses that were set to "none"
            for response in session.responses:
                if response.question_id == "existing_coverage" and response.answer == "none":
                    response.answer = "employer_comprehensive"
                    print(f"DEBUG: Updated existing_coverage from 'none' to 'employer_comprehensive'")
                elif response.question_id == "current_coverage_amount" and response.answer == "none":
                    coverage = extracted_data.get("coverage_amount", "")
                    if "$1,000,000" in coverage:
                        response.answer = "over_500k"
                        print(f"DEBUG: Updated current_coverage_amount from 'none' to 'over_500k'")
        
        # Save updated session
        sessions[session_id] = session
        await save_session_to_db(session)
        
        # Get current question (should skip more now)
        answered_question_ids = {resp.question_id for resp in session.responses}
        current_question_index = 0
        
        for i, question in enumerate(INSURANCE_QUESTIONS):
            if question.id not in answered_question_ids:
                current_question_index = i
                break
        
        current_question = INSURANCE_QUESTIONS[current_question_index] if current_question_index < len(INSURANCE_QUESTIONS) else None
        total_questions = len(INSURANCE_QUESTIONS)
        answered_count = len(session.responses)
        
        print(f"DEBUG: After PDF processing - answered {answered_count} questions, current question: {current_question.id if current_question else 'None'}")
        
        return {
            "success": True,
            "session_id": session_id,
            "pdf_extraction_result": {
                "extraction_id": extraction_id,
                "confidence_score": getattr(extraction_result, 'confidence_score', 0),
                "extracted_fields": extracted_data
            },
            "current_question": current_question.dict() if current_question else None,
            "progress": {"current": answered_count + 1, "total": total_questions},
            "skipped_questions": list(answered_question_ids),
            "remaining_questions": total_questions - answered_count
        }
        
    except Exception as e:
        print(f"DEBUG: PDF processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

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
        return await process_mvp_questionnaire(responses, session)
    
    # Legacy: Handle original 25-question format
    return await process_legacy_questionnaire(responses)

async def process_mvp_questionnaire(responses: Dict[str, Any], session: QuestionnaireSession = None) -> Dict[str, Any]:
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
    
    # Extract gender from original profile if available
    gender = "OTHER"  # Default
    if hasattr(session, 'metadata') and session.metadata and 'original_profile' in session.metadata:
        original_profile = session.metadata['original_profile']
        gender = original_profile.get('gender', 'OTHER')
        print(f"🔍 Found original profile gender: {gender}")
    
    # Create minimal applicant profile for API
    applicant = create_minimal_applicant(age, annual_income, health_status, gender)
    
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
            applicant=applicant.model_dump() if hasattr(applicant, 'model_dump') else applicant,
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
        applicant = convert_responses_to_applicant(responses, session)
    except Exception as e:
        raise Exception(f"Error converting responses to applicant profile: {str(e)}")
    
    # Intelligently determine insurance needs from conversational responses
    coverage_amount = determine_coverage_amount(responses, applicant)
    product_type = determine_product_type(responses)
    
    # Create insurance request
    insurance_request = InsuranceRequest(
        product_type=product_type,
        applicant=applicant.model_dump() if hasattr(applicant, 'model_dump') else applicant,
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
    
    # Convert ApplicantProfile to ApplicantData format expected by backend
    request_data = insurance_request.model_dump()
    
    # Map ApplicantProfile fields to ApplicantData fields
    if "applicant" in request_data and isinstance(request_data["applicant"], dict):
        applicant = request_data["applicant"]
        
        # Ensure required fields are present with defaults if missing
        applicant_data = {
            "first_name": applicant.get("first_name", "Unknown"),
            "last_name": applicant.get("last_name", "User"),
            "dob": applicant.get("dob", "1990-01-01"),
            "gender": applicant.get("gender", "OTHER"),
            "email": applicant.get("email", "user@example.com"),
            "phone": applicant.get("phone", "000-000-0000"),
            "address_line1": applicant.get("address_line1", "123 Main St"),
            "address_line2": applicant.get("address_line2"),
            "city": applicant.get("city", "Anytown"),
            "state": applicant.get("state", "CA"),
            "postal_code": applicant.get("postal_code", "00000"),
        }
        
        # Copy additional fields that exist in both models
        for field in ["annual_income", "occupation", "health_status", "smoker_status"]:
            if field in applicant:
                applicant_data[field] = applicant[field]
        
        request_data["applicant"] = applicant_data
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/quote",
            json=request_data,
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

def create_minimal_applicant(age: int, annual_income: float, health_status: str, gender: str = "OTHER") -> ApplicantProfile:
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
        gender=gender,
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
        
        # Initialize user profile with defaults if not exists
        if session.user_profile is None:
            from shared.models import UserProfile
            session.user_profile = UserProfile(
                age=age,
                annual_income=income,
                health_status="good",
                existing_coverage_type="none", 
                existing_coverage_amount="none",
                primary_need="first_time",
                monthly_budget="show_all",
                coverage_priority="unsure",
                urgency="exploring",
                
                # New lifestyle and risk factor fields with defaults
                occupation="office_professional",
                smoking_status="never",
                alcohol_consumption="social", 
                exercise_frequency="weekly",
                high_risk_activities=["none"],
                monthly_premium_budget="flexible",
                desired_add_ons=["none"]
            )
        else:
            session.user_profile.age = age
            session.user_profile.annual_income = income
        return
    
    # Direct field mappings for enhanced 15-question questionnaire
    field_mappings = {
        # Original 8 questions
        "existing_coverage": "existing_coverage_type",
        "current_coverage_amount": "existing_coverage_amount", 
        "health_status": "health_status",
        "primary_need": "primary_need",
        "budget": "monthly_budget",
        "coverage_priority": "coverage_priority", 
        "timeline": "urgency",
        
        # New lifestyle and risk factor questions
        "occupation": "occupation",
        "smoking_vaping_habits": "smoking_status", 
        "alcohol_consumption": "alcohol_consumption",
        "exercise_frequency": "exercise_frequency",
        "high_risk_activities": "high_risk_activities",
        "monthly_premium_budget": "monthly_premium_budget",
        "desired_add_ons": "desired_add_ons"
    }
    
    if question_id in field_mappings:
        # Initialize profile with defaults if not exists
        if session.user_profile is None:
            from shared.models import UserProfile
            session.user_profile = UserProfile(
                age=30,  # Default age
                annual_income=50000.0,  # Default income
                health_status="good",
                existing_coverage_type="none", 
                existing_coverage_amount="none",
                primary_need="first_time",
                monthly_budget="show_all",
                coverage_priority="unsure",
                urgency="exploring",
                
                # New lifestyle and risk factor fields with defaults
                occupation="office_professional",
                smoking_status="never",
                alcohol_consumption="social", 
                exercise_frequency="weekly",
                high_risk_activities=["none"],
                monthly_premium_budget="flexible",
                desired_add_ons=["none"]
            )
        
        profile_field = field_mappings[question_id]
        
        print(f"DEBUG: update_user_profile_directly - question_id={question_id}, profile_field={profile_field}, answer_value='{answer_value}' (type: {type(answer_value)})")
        
        # Handle list fields that need conversion from string to list
        if profile_field in ["high_risk_activities", "desired_add_ons", "special_coverage_needs"]:
            print(f"DEBUG: Processing list field {profile_field}")
            if isinstance(answer_value, str):
                if answer_value.lower() in ["none", "no", ""]:
                    processed_value = []
                else:
                    processed_value = [answer_value]  # Convert single string to list
                print(f"DEBUG: Converted {profile_field} from '{answer_value}' (str) to {processed_value} (list)")
            elif isinstance(answer_value, list):
                processed_value = answer_value
                print(f"DEBUG: {profile_field} already a list: {processed_value}")
            else:
                processed_value = []
                print(f"DEBUG: {profile_field} defaulted to empty list")
            setattr(session.user_profile, profile_field, processed_value)
            print(f"DEBUG: After setattr, {profile_field} = {getattr(session.user_profile, profile_field)}")
        else:
            setattr(session.user_profile, profile_field, answer_value)
            print(f"DEBUG: Set {profile_field} = {answer_value}")

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
    
    # Add debug logging for the entire agentic flow
    print(f"DEBUG: existing_coverage_type = {user_profile.existing_coverage_type}")
    
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
    
    print(f"DEBUG: needs_analysis.should_get_quotes = {needs_analysis.should_get_quotes}")
    print(f"DEBUG: needs_analysis.reasoning = {needs_analysis.reasoning}")
    
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
                applicant=applicant_data.model_dump() if hasattr(applicant_data, 'model_dump') else applicant_data,
                coverage_amount=coverage_amount,
                deductible=None,
                term_years=None,
                riders=[],
                beneficiaries=[]
            )
            
            # Get quotes
            print(f"DEBUG: Fetching quotes with request: {insurance_request}")
            quotes_data = await fetch_insurance_quotes_simple(insurance_request)
            print(f"DEBUG: Got quotes_data: {quotes_data}")
            
            # Convert quotes to insurance cards for frontend display with scoring
            if quotes_data.get("recommended_plans"):
                print(f"DEBUG: Converting {len(quotes_data['recommended_plans'])} plans to insurance cards")
                insurance_cards = []
                
                # Score all the plans using the scoring agent
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
                from insurance_backend.insurance_backend_mongo import QuotePlan
                
                quote_plans = []
                for plan in quotes_data["recommended_plans"]:
                    # Ensure all required fields are present with defaults
                    plan_data = {
                        "plan_id": plan.get("plan_id", f"plan_{len(quote_plans)}"),
                        "plan_name": plan.get("plan_name", "Insurance Plan"),
                        "company_id": plan.get("company_id", "company_1"),
                        "company_name": plan.get("company_name", "Insurance Company"),
                        "company_rating": plan.get("company_rating", 4.0),
                        "coverage_amount": plan.get("coverage_amount", 100000.0),
                        "deductible": plan.get("deductible", 1000.0),
                        "base_premium": plan.get("base_premium", plan.get("total_monthly_premium", 100.0)),
                        "rider_premiums": plan.get("rider_premiums", {}),
                        "taxes_fees": plan.get("taxes_fees", plan.get("total_monthly_premium", 100.0) * 0.1),
                        "total_monthly_premium": plan.get("total_monthly_premium", 100.0),
                        "total_annual_premium": plan.get("total_annual_premium", plan.get("total_monthly_premium", 100.0) * 12),
                        "coverage_details": plan.get("coverage_details", {}),
                        "exclusions": plan.get("exclusions", []),
                        "waiting_periods": plan.get("waiting_periods", {})
                    }
                    quote_plan = QuotePlan(**plan_data)
                    quote_plans.append(quote_plan)
                
                # Convert user_profile to ApplicantProfile for scoring
                applicant_profile = user_profile.to_applicant_data()
                
                # Score all plans
                scored_plans = score_insurance_policies(quote_plans, applicant_profile)
                print(f"DEBUG: Scored {len(scored_plans)} plans with metrics")
                
                # Create insurance cards with scoring - no fallbacks, this must work
                for i, plan in enumerate(quotes_data["recommended_plans"]):
                    # Get corresponding score
                    plan_score = scored_plans[i]
                    
                    card = {
                        "company_name": plan["company_name"],
                        "plan_name": plan["plan_name"],
                        "coverage_amount": f"${plan['coverage_amount']:,.0f}",
                        "monthly_cost": f"${plan['total_monthly_premium']:.2f}/month",
                        "key_benefits": [
                            "Critical Illness Coverage",
                            f"{plan['coverage_details']['product_type'].replace('_', ' ').title()} Protection",
                            "Instant Approval" if plan['coverage_details'].get('instant_approval') else "Standard Processing"
                        ],
                        "company_rating": plan["company_rating"],
                        "deductible": plan.get("deductible", "None"),
                        "plan_id": plan["plan_id"],
                        "metrics": {
                            "affordability_score": plan_score.affordability_score,
                            "ease_of_claims_score": plan_score.ease_of_claims_score,
                            "coverage_ratio_score": plan_score.coverage_ratio_score
                        }
                    }
                    
                    print(f"DEBUG: Added metrics to {plan['company_name']}: A={plan_score.affordability_score:.1f}, C={plan_score.ease_of_claims_score:.1f}, R={plan_score.coverage_ratio_score:.1f}")
                    insurance_cards.append(card)

                result["insurance_cards"] = insurance_cards
                print(f"DEBUG: Created {len(insurance_cards)} insurance cards with metrics")
            
            result["new_quotes"] = quotes_data
            
            # Store the results in session for the recommendations page
            session.metadata["final_recommendations"] = {
                "quotes": quotes_data.get("quotes", []),
                "recommended_plans": quotes_data.get("recommended_plans", []),
                "insurance_cards": insurance_cards,
                "user_profile": user_profile.dict(),
                "needs_analysis": needs_analysis.dict()
            }
            await save_session_to_db(session)
            
        except Exception as e:
            print(f"Quote fetching failed: {e}")
            result["quotes_error"] = f"Error fetching quotes: {str(e)}"
    else:
        print(f"DEBUG: Quotes skipped because should_get_quotes = {needs_analysis.should_get_quotes}")
        result["quotes_skipped"] = needs_analysis.reasoning
    
    print(f"DEBUG: Final result keys: {result.keys()}")
    return result

@app.get("/recommendations")
async def serve_recommendations_page():
    """Serve the insurance recommendations page"""
    try:
        with open("frontend/templates/insurance_recommendations.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Recommendations page template not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving recommendations page: {str(e)}")

@app.get("/api/recommendations/{session_id}")
async def get_recommendations(session_id: str):
    """Get recommendations data for a completed session"""
    try:
        session = await get_persistent_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.metadata or "final_recommendations" not in session.metadata:
            raise HTTPException(status_code=404, detail="No recommendations found for this session")
        
        recommendations = session.metadata["final_recommendations"]
        
        return {
            "success": True,
            "recommendations": {
                "quotes": recommendations.get("quotes", []),
                "recommended_plans": recommendations.get("recommended_plans", []),
                "insurance_cards": recommendations.get("insurance_cards", [])
            },
            "profile": recommendations.get("user_profile", {}),
            "needs_analysis": recommendations.get("needs_analysis", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recommendations: {str(e)}")

@app.post("/api/purchase-request")
async def submit_purchase_request(purchase_data: Dict[str, Any]):
    """Handle insurance purchase requests"""
    try:
        # In a real system, this would integrate with the insurance company's purchase API
        # For now, we'll just log the request and return success
        
        purchase_record = {
            "purchase_id": str(uuid.uuid4()),
            "plan_id": purchase_data.get("plan_id"),
            "customer": purchase_data.get("customer", {}),
            "status": "pending",
            "request_date": datetime.utcnow(),
            "notes": "Purchase request submitted via AI Insurance Broker"
        }
        
        # Store in database
        await async_db["purchase_requests"].insert_one(purchase_record)
        
        print(f"DEBUG: Purchase request submitted: {purchase_record}")
        
        return {
            "success": True,
            "purchase_id": purchase_record["purchase_id"],
            "message": "Purchase request submitted successfully. An agent will contact you within 24 hours."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting purchase request: {str(e)}")

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
    
    # Convert ApplicantProfile to ApplicantData format expected by backend
    request_data = insurance_request.model_dump()
    
    # Map ApplicantProfile fields to ApplicantData fields
    if "applicant" in request_data and isinstance(request_data["applicant"], dict):
        applicant = request_data["applicant"]
        
        # Ensure required fields are present with defaults if missing
        applicant_data = {
            "first_name": applicant.get("first_name", "Unknown"),
            "last_name": applicant.get("last_name", "User"),
            "dob": applicant.get("dob", "1990-01-01"),
            "gender": applicant.get("gender", "OTHER"),
            "email": applicant.get("email", "user@example.com"),
            "phone": applicant.get("phone", "000-000-0000"),
            "address_line1": applicant.get("address_line1", "123 Main St"),
            "address_line2": applicant.get("address_line2"),
            "city": applicant.get("city", "Anytown"),
            "state": applicant.get("state", "CA"),
            "postal_code": applicant.get("postal_code", "00000"),
        }
        
        # Copy additional fields that exist in both models
        for field in ["annual_income", "occupation", "health_status", "smoker_status"]:
            if field in applicant:
                applicant_data[field] = applicant[field]
        
        request_data["applicant"] = applicant_data
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/quote",
            json=request_data,
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

def convert_responses_to_applicant(responses: Dict[str, Any], session: Optional[QuestionnaireSession] = None) -> ApplicantProfile:
    """Convert conversational questionnaire responses to enhanced ApplicantProfile"""
    
    # Handle both old and new smoking fields for backward compatibility  
    # Priority: smoking_vaping_habits > smoking_status > smoking_habits > smoker_status
    smoking_response = responses.get("smoking_vaping_habits") or responses.get("smoking_status") or responses.get("smoking_habits", "never")
    
    # Handle conflicting smoking fields by using the most recent/specific one
    if responses.get("smoking_status") and responses.get("smoker_status"):
        print(f"DEBUG: Conflicting smoking fields - smoking_status: {responses.get('smoking_status')}, smoker_status: {responses.get('smoker_status')}")
        # Use smoking_status as it's more specific than smoker_status
        smoking_response = responses.get("smoking_status")
    
    smoker = None
    if smoking_response in ["regular", "daily", "occasional"]:  # Include occasional as smoker
        smoker = True
    elif smoking_response in ["never", "quit_over_year"]:
        smoker = False
    elif smoking_response in ["quit_under_year"]:
        smoker = True  # Recent quitters still rated as smokers
    
    print(f"DEBUG: Final smoking determination - response: {smoking_response}, smoker: {smoker}")
    
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
    
    # Get personal fields from session metadata (for JSON/PDF uploads)
    personal_fields = {}
    if session and session.metadata and "personal_fields" in session.metadata:
        personal_fields = session.metadata["personal_fields"]
        print(f"DEBUG: Using personal fields from session: {personal_fields}")
    
    # Use actual annual income if provided (check personal fields first, then responses), otherwise estimate
    actual_income = personal_fields.get("annual_income") or responses.get("annual_income")
    if actual_income and isinstance(actual_income, (int, float)) and actual_income > 0:
        annual_income = float(actual_income)
    else:
        annual_income = estimated_income
    
    print(f"DEBUG: Final annual_income: {annual_income} (actual: {actual_income}, estimated: {estimated_income})")
    
    # Fix list fields that may come as strings from UserProfile schema
    def ensure_list_field(field_value, default_list=None):
        """Convert string fields to lists for ApplicantProfile compatibility"""
        if default_list is None:
            default_list = []
        
        if field_value is None:
            return default_list
        elif isinstance(field_value, list):
            return field_value
        elif isinstance(field_value, str):
            if field_value.lower() in ["none", "no", ""]:
                return []
            else:
                return [field_value]  # Convert single string to list
        else:
            return default_list
    
    # Process list fields with proper conversion
    high_risk_activities_raw = responses.get("high_risk_activities", ["none"])
    high_risk_activities_list = ensure_list_field(high_risk_activities_raw, ["none"])
    
    desired_add_ons_raw = responses.get("desired_add_ons", [])
    desired_add_ons_list = ensure_list_field(desired_add_ons_raw, [])
    
    special_coverage_needs_raw = responses.get("special_coverage_needs", [])
    special_coverage_needs_list = ensure_list_field(special_coverage_needs_raw, [])
    
    print(f"DEBUG: Converted list fields - high_risk_activities: {high_risk_activities_list}, desired_add_ons: {desired_add_ons_list}")
    
    return ApplicantProfile(
        # Personal Information - use session metadata first, then responses
        first_name=personal_fields.get("personal_first_name") or responses.get("personal_first_name", "User"),
        last_name=personal_fields.get("personal_last_name") or responses.get("personal_last_name", "Person"),
        dob=personal_fields.get("personal_dob") or responses.get("personal_dob", "1990-01-01"),
        gender=personal_fields.get("personal_gender") or responses.get("personal_gender", "M"),
        email=personal_fields.get("personal_email") or responses.get("personal_email", "user@example.com"),
        phone=personal_fields.get("personal_phone") or responses.get("personal_phone", "000-000-0000"),
        
        # Address - use session metadata first, then responses
        address_line1=personal_fields.get("address_line1") or responses.get("address_line1", "123 Main St"),
        address_line2=None,
        city=personal_fields.get("address_city") or responses.get("address_city", "Anytown"),
        state=personal_fields.get("address_state") or responses.get("address_state", "CA"),
        postal_code=personal_fields.get("address_postal_code") or responses.get("address_postal_code", "12345"),
        country="US",
        
        # Financial Information
        annual_income=annual_income,
        occupation=responses.get("occupation", occupation),  # Use actual occupation from enhanced questionnaire, fallback to estimated
        
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
        
        # Lifestyle Risk Factors (Phase 1) - Map from enhanced questionnaire
        alcohol_consumption=responses.get("alcohol_consumption", "social"),
        exercise_frequency=responses.get("exercise_frequency", "weekly" if health_overall in ["excellent", "good"] else "monthly"),
        dietary_habits=responses.get("dietary_habits"),
        high_risk_activities=high_risk_activities_list,
        travel_frequency=travel_frequency,
        
        # Coverage Gaps & Transition Status (Phase 2)
        current_coverage_status=responses.get("current_coverage_status"),
        parents_policy_end_date=responses.get("parents_policy_end_date"),
        employer_coverage_expectation=responses.get("employer_coverage_expectation"),
        hospital_preference=responses.get("hospital_preference"),
        special_coverage_needs=special_coverage_needs_list,
        
        # Preferences & Budget (Phase 3)
        coverage_vs_premium_priority=responses.get("coverage_vs_premium_priority"),
        desired_add_ons=desired_add_ons_list,
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
                extraction_result = await pdf_parser.extract_insurance_fields_async(file_content)
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
                coverage_adequacy="adequately_insured",
                monthly_cost_assessment="reasonable",
                coverage_gaps=["Unable to fully analyze document"],
                over_coverage_areas=[],
                primary_action="get_new_coverage" if extracted_data else "no_action",
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

# ============================================
# MINIMAL DEMO AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/api/auth/register", response_model=AuthResponse)
async def register_user(request: RegisterRequest):
    """Register a new user (demo-level auth)"""
    try:
        # Check if user already exists
        existing_user = await async_db[Collections.USERS].find_one({"email": request.email})
        if existing_user:
            return AuthResponse(
                success=False,
                message="Email already registered"
            )
        
        # Create new user
        user_id = f"USER_{uuid.uuid4().hex[:8].upper()}"
        user_doc = {
            "user_id": user_id,
            "email": request.email,
            "full_name": request.full_name,
            "password": request.password,  # DEMO: Plain text (never do this in production!)
            "profile_data": {},
            "is_active": True,
            "last_login": None,
            "customer_id": None,
            "purchased_policies": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await async_db[Collections.USERS].insert_one(user_doc)
        
        return AuthResponse(
            success=True,
            user_id=user_id,
            message="Registration successful",
            user_data={
                "user_id": user_id,
                "email": request.email,
                "full_name": request.full_name
            }
        )
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return AuthResponse(
            success=False,
            message="Registration failed. Please try again."
        )

@app.post("/api/auth/login", response_model=AuthResponse)
async def login_user(request: LoginRequest):
    """Login user (demo-level auth)"""
    try:
        # Find user
        user_doc = await async_db[Collections.USERS].find_one({"email": request.email})
        
        if not user_doc:
            return AuthResponse(
                success=False,
                message="Invalid email or password"
            )
        
        # Verify password (demo: plain text comparison)
        if user_doc["password"] != request.password:
            return AuthResponse(
                success=False,
                message="Invalid email or password"
            )
        
        # Update last login
        await async_db[Collections.USERS].update_one(
            {"user_id": user_doc["user_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        return AuthResponse(
            success=True,
            user_id=user_doc["user_id"],
            message="Login successful",
            user_data={
                "user_id": user_doc["user_id"],
                "email": user_doc["email"],
                "full_name": user_doc["full_name"],
                "profile_data": user_doc.get("profile_data", {}),
                "purchased_policies": user_doc.get("purchased_policies", [])
            }
        )
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return AuthResponse(
            success=False,
            message="Login failed. Please try again."
        )

@app.get("/api/user/{user_id}/policies")
async def get_user_policies_proxy(user_id: str):
    """Proxy endpoint to get user policies from backend"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8000/v1/user/{user_id}/policies")
            return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch user policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user policies")

@app.post("/api/claims/file")
async def file_claim_proxy(claim_data: Dict[str, Any]):
    """Proxy endpoint to file claims via backend"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/claims/file",
                json=claim_data
            )
            return response.json()
    except Exception as e:
        print(f"❌ Failed to file claim: {e}")
        raise HTTPException(status_code=500, detail="Failed to file claim")

@app.get("/api/user/{user_id}/claims")
async def get_user_claims_proxy(user_id: str):
    """Proxy endpoint to get user claims from backend"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8000/v1/user/{user_id}/claims")
            return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch user claims: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user claims")

@app.post("/api/policies/purchase")
async def purchase_policy_proxy(purchase_data: Dict[str, Any]):
    """Proxy endpoint to purchase policies via backend"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/policy/purchase",
                json=purchase_data
            )
            return response.json()
    except Exception as e:
        print(f"❌ Failed to purchase policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to purchase policy")

@app.get("/api/auth/user/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile data"""
    try:
        user_doc = await async_db[Collections.USERS].find_one({"user_id": user_id})
        
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": user_doc["user_id"],
            "email": user_doc["email"], 
            "full_name": user_doc["full_name"],
            "profile_data": user_doc.get("profile_data", {}),
            "purchased_policies": user_doc.get("purchased_policies", []),
            "last_login": user_doc.get("last_login")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get user profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@app.put("/api/auth/user/{user_id}/profile")
async def update_user_profile(user_id: str, profile_data: Dict[str, Any]):
    """Update user profile data"""
    try:
        result = await async_db[Collections.USERS].update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "profile_data": profile_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)