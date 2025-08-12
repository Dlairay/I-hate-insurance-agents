"""
insurance_backend_mongo.py
===========================

MongoDB-backed insurance backend API that uses the populated database
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
import uuid
import random

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from motor.motor_asyncio import AsyncIOMotorClient

from database.database import (
    async_db, Collections, DatabaseOperations,
    get_company_products, get_customer_policies
)
from bson import ObjectId


def convert_objectid_to_string(data):
    """Convert MongoDB ObjectIds to strings for JSON serialization"""
    if isinstance(data, dict):
        return {key: convert_objectid_to_string(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_string(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


# Reuse the same enums and models from the original backend
class ProductType(str, Enum):
    LIFE_TERM = "LIFE_TERM"
    LIFE_WHOLE = "LIFE_WHOLE"
    HEALTH_BASIC = "HEALTH_BASIC"
    HEALTH_PREMIUM = "HEALTH_PREMIUM"
    CRITICAL_ILLNESS = "CRITICAL_ILLNESS"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    PENDING_PAYMENT = "pending_payment"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


# Request/Response Models
class ApplicantData(BaseModel):
    """Complete applicant information from questionnaire"""
    
    first_name: str
    last_name: str
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: Literal["M", "F", "OTHER"]
    email: str
    phone: str
    
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    
    smoker: Optional[bool] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    
    # Enhanced lifestyle risk factors (v2.0)
    smoking_vaping_habits: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    exercise_frequency: Optional[str] = None
    high_risk_activities: Optional[List[str]] = []
    
    pre_existing_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    hospitalizations_last_5_years: Optional[int] = 0
    
    @validator("dob")
    def validate_dob(cls, v: str) -> str:
        from datetime import date
        try:
            date.fromisoformat(v)
        except Exception as exc:
            raise ValueError(f"dob must be in YYYY-MM-DD format: {v}") from exc
        return v
    
    def age(self) -> int:
        from datetime import date
        birth = date.fromisoformat(self.dob)
        today = date.today()
        years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return years


class QuoteRequest(BaseModel):
    """Quote request with complete questionnaire data"""
    
    company_id: Optional[str] = None  # If None, query all companies
    product_type: ProductType
    applicant: ApplicantData
    
    coverage_amount: float = Field(..., gt=0)
    deductible: Optional[float] = None
    term_years: Optional[int] = None
    riders: Optional[List[str]] = []
    
    beneficiaries: Optional[List[Dict[str, Any]]] = []


class QuotePlan(BaseModel):
    """Individual insurance plan option"""
    
    plan_id: str
    plan_name: str
    company_id: str
    company_name: str
    company_rating: float
    
    coverage_amount: float
    deductible: Optional[float]
    
    base_premium: float
    rider_premiums: Dict[str, float] = {}
    taxes_fees: float
    total_monthly_premium: float
    total_annual_premium: float
    
    coverage_details: Dict[str, Any]
    exclusions: List[str] = []
    waiting_periods: Dict[str, int] = {}


class QuoteResponse(BaseModel):
    """Aggregated quote response from multiple companies"""
    
    quote_session_id: str
    quote_date: datetime
    valid_until: datetime
    
    applicant_id: str
    risk_assessment: Dict[str, Any]
    
    quotes: List[Dict[str, Any]]  # Raw quotes from each company
    recommended_plans: List[QuotePlan]  # Top recommendations
    
    comparison_matrix: Optional[Dict[str, Any]] = None


class PolicyRequest(BaseModel):
    """Request to issue a policy"""
    
    quote_session_id: str
    company_id: str
    plan_id: str
    
    payment_method: Literal["credit_card", "bank_account", "check"]
    payment_frequency: Literal["monthly", "quarterly", "annual"]
    
    terms_accepted: bool
    e_signature: str


class PolicyResponse(BaseModel):
    """Issued policy details"""
    
    policy_id: str
    policy_number: str
    company_id: str
    company_name: str
    status: str
    
    issue_date: datetime
    effective_date: datetime
    expiry_date: Optional[datetime]
    
    product_type: str
    coverage_amount: float
    deductible: Optional[float]
    riders: List[str]
    
    premium_amount: float
    payment_frequency: str
    next_payment_date: datetime
    
    documents: List[Dict[str, str]]


class ClaimRequest(BaseModel):
    """Claim submission request"""
    
    policy_id: str
    claim_type: str
    incident_date: str
    incident_description: str
    
    claim_amount: Optional[float] = None
    location: Optional[str] = None
    
    documents: List[Dict[str, str]] = []
    
    claimant_name: Optional[str] = None
    claimant_relationship: Optional[str] = None


class ClaimResponse(BaseModel):
    """Claim submission response"""
    
    claim_id: str
    claim_number: str
    status: str
    
    submission_date: datetime
    estimated_review_date: datetime
    
    required_documents: List[str] = []
    next_steps: List[str] = []


# Application
app = FastAPI(
    title="Insurance Backend API (MongoDB)",
    description="Insurance API with MongoDB backend and multi-company support",
    version="3.0.0"
)


# Helper Functions
async def get_or_create_customer(applicant: ApplicantData) -> str:
    """Get existing customer or create new one"""
    
    # Check if customer exists
    existing = await async_db[Collections.CUSTOMERS].find_one({"email": applicant.email})
    
    if existing:
        # Update customer info
        await async_db[Collections.CUSTOMERS].update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "updated_at": datetime.utcnow(),
                "health_data.height_cm": applicant.height_cm,
                "health_data.weight_kg": applicant.weight_kg,
                "health_data.smoker": applicant.smoker,
                "health_data.pre_existing_conditions": applicant.pre_existing_conditions
            }}
        )
        return existing["customer_id"]
    
    # Create new customer
    customer_id = f"CUST{uuid.uuid4().hex[:6].upper()}"
    customer = {
        "customer_id": customer_id,
        "first_name": applicant.first_name,
        "last_name": applicant.last_name,
        "email": applicant.email,
        "phone": applicant.phone,
        "dob": applicant.dob,
        "gender": applicant.gender,
        "ssn_last_four": "0000",  # Placeholder
        "address": {
            "line1": applicant.address_line1,
            "line2": applicant.address_line2,
            "city": applicant.city,
            "state": applicant.state,
            "postal_code": applicant.postal_code,
            "country": applicant.country
        },
        "health_data": {
            "height_cm": applicant.height_cm,
            "weight_kg": applicant.weight_kg,
            "bmi": (applicant.weight_kg / ((applicant.height_cm / 100) ** 2)) if applicant.height_cm and applicant.weight_kg else None,
            "smoker": applicant.smoker,
            "pre_existing_conditions": applicant.pre_existing_conditions or [],
            "medications": applicant.medications or [],
            "hospitalizations_last_5_years": applicant.hospitalizations_last_5_years or 0,
            "occupation": applicant.occupation,
            "annual_income": applicant.annual_income
        },
        "risk_score": 0,  # Will be calculated
        "risk_factors": [],
        "quote_history": [],
        "policy_history": [],
        "claim_history": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await async_db[Collections.CUSTOMERS].insert_one(customer)
    return customer_id


async def calculate_risk_score(applicant: ApplicantData, product_type: str) -> Dict[str, Any]:
    """Calculate risk score based on applicant data"""
    
    risk_score = 30.0  # Base score
    risk_factors = []
    
    age = applicant.age()
    
    # Age factors
    if age > 60:
        risk_score += 20
        risk_factors.append("Age over 60")
    elif age > 45:
        risk_score += 10
        risk_factors.append("Age 45-60")
    elif age < 25:
        risk_score += 5
        risk_factors.append("Age under 25")
    
    # Health factors
    if applicant.smoker:
        risk_score += 15
        risk_factors.append("Smoker")
    
    # BMI calculation
    if applicant.height_cm and applicant.weight_kg:
        bmi = applicant.weight_kg / ((applicant.height_cm / 100) ** 2)
        if bmi > 35:
            risk_score += 15
            risk_factors.append("BMI over 35")
        elif bmi > 30:
            risk_score += 10
            risk_factors.append("BMI over 30")
        elif bmi < 18:
            risk_score += 5
            risk_factors.append("BMI under 18")
    
    # Pre-existing conditions
    if applicant.pre_existing_conditions:
        risk_score += len(applicant.pre_existing_conditions) * 5
        risk_factors.append(f"{len(applicant.pre_existing_conditions)} pre-existing conditions")
    
    # Hospitalizations
    if applicant.hospitalizations_last_5_years and applicant.hospitalizations_last_5_years > 2:
        risk_score += 10
        risk_factors.append("Multiple hospitalizations")
    
    # NEW LIFESTYLE RISK FACTORS
    
    # Enhanced smoking/vaping assessment
    if hasattr(applicant, 'smoking_vaping_habits') and applicant.smoking_vaping_habits:
        smoking_risks = {
            "daily": 20,
            "regular": 15,
            "occasional": 8,
            "quit_under_year": 10,
            "quit_over_year": 5,
            "never": 0
        }
        smoke_risk = smoking_risks.get(applicant.smoking_vaping_habits, 0)
        if smoke_risk > 0:
            risk_score += smoke_risk
            risk_factors.append(f"Smoking/vaping: {applicant.smoking_vaping_habits}")
    
    # Occupation risk assessment
    if hasattr(applicant, 'occupation') and applicant.occupation:
        high_risk_occupations = {
            "construction": 12,
            "law_enforcement": 10,
            "transportation": 8,
            "self_employed": 5
        }
        occ_risk = high_risk_occupations.get(applicant.occupation, 0)
        if occ_risk > 0:
            risk_score += occ_risk
            risk_factors.append(f"High-risk occupation: {applicant.occupation}")
    
    # Alcohol consumption
    if hasattr(applicant, 'alcohol_consumption') and applicant.alcohol_consumption:
        alcohol_risks = {
            "daily": 12,
            "moderate": 6,
            "social": 2,
            "rare": 0,
            "never": -2  # Slight benefit for non-drinkers
        }
        alcohol_risk = alcohol_risks.get(applicant.alcohol_consumption, 0)
        risk_score += alcohol_risk
        if alcohol_risk > 0:
            risk_factors.append(f"Alcohol consumption: {applicant.alcohol_consumption}")
    
    # Exercise frequency (positive factor)
    if hasattr(applicant, 'exercise_frequency') and applicant.exercise_frequency:
        exercise_benefits = {
            "daily": -8,
            "regular": -5,
            "weekly": -2,
            "monthly": 0,
            "rarely": 3
        }
        exercise_impact = exercise_benefits.get(applicant.exercise_frequency, 0)
        risk_score += exercise_impact
        if exercise_impact < 0:
            risk_factors.append(f"Regular exercise: {applicant.exercise_frequency}")
        elif exercise_impact > 0:
            risk_factors.append(f"Sedentary lifestyle: {applicant.exercise_frequency}")
    
    # High-risk activities
    if hasattr(applicant, 'high_risk_activities') and applicant.high_risk_activities:
        if "none" not in applicant.high_risk_activities:
            high_risk_points = {
                "scuba": 5,
                "skydiving": 8,
                "racing": 10,
                "climbing": 6,
                "martial_arts": 4,
                "flying": 7,
                "extreme_sports": 10
            }
            for activity in applicant.high_risk_activities:
                activity_risk = high_risk_points.get(activity, 0)
                if activity_risk > 0:
                    risk_score += activity_risk
                    risk_factors.append(f"High-risk activity: {activity}")
    
    return {
        "score": min(risk_score, 100),
        "factors": risk_factors,
        "rating": "high" if risk_score > 70 else "medium" if risk_score > 40 else "low"
    }


async def get_quote_from_company(company: Dict, product: Dict, request: QuoteRequest, risk_assessment: Dict) -> Dict:
    """Get quote from a specific insurance company"""
    
    # Get rate table for this company and product
    rate_table = await async_db[Collections.RATE_TABLES].find_one({
        "company_id": company["company_id"],
        "product_type": request.product_type.value
    })
    
    if not rate_table:
        return None
    
    # Calculate base premium
    base_rate = product["base_rate"]
    
    # Apply age factor
    age = request.applicant.age()
    age_factor = 1.0
    for band in rate_table["age_bands"]:
        if band["min_age"] <= age <= band["max_age"]:
            age_factor = band["factor"]
            break
    
    # Apply health factors
    health_factor = 1.0
    if request.applicant.smoker:
        health_factor *= rate_table["smoker_factor"]
    
    # Apply BMI factor
    if request.applicant.height_cm and request.applicant.weight_kg:
        bmi = request.applicant.weight_kg / ((request.applicant.height_cm / 100) ** 2)
        for band in rate_table["bmi_ranges"]:
            if band["min_bmi"] <= bmi <= band["max_bmi"]:
                health_factor *= band["factor"]
                break
    
    # Apply state factor
    state_factor = rate_table["state_factors"].get(request.applicant.state, 1.0)
    
    # Apply risk factor based on risk assessment
    risk_factor = 1 + (risk_assessment["score"] / 200)  # 1.0 to 1.5
    
    # Calculate final premium
    if request.product_type in [ProductType.HEALTH_BASIC, ProductType.HEALTH_PREMIUM]:
        monthly_premium = base_rate * age_factor * health_factor * state_factor * risk_factor
    else:
        monthly_premium = (request.coverage_amount / 1000) * base_rate * age_factor * health_factor * state_factor * risk_factor
    
    # Add rider costs
    rider_premiums = {}
    for rider in request.riders:
        if rider in rate_table["rider_rates"]:
            rider_rate = rate_table["rider_rates"][rider]
            if isinstance(rider_rate, float):
                rider_premiums[rider] = (request.coverage_amount / 1000) * rider_rate * risk_factor
            else:
                rider_premiums[rider] = rider_rate
    
    total_riders = sum(rider_premiums.values())
    taxes_fees = (monthly_premium + total_riders) * 0.08
    
    # Create quote
    quote_id = f"Q{uuid.uuid4().hex[:8].upper()}"
    
    return {
        "quote_id": quote_id,
        "company_id": company["company_id"],
        "company_name": company["name"],
        "company_rating": company["rating"],
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "coverage_amount": request.coverage_amount,
        "deductible": request.deductible,
        "term_years": request.term_years,
        "base_premium": round(monthly_premium, 2),
        "rider_premiums": {k: round(v, 2) for k, v in rider_premiums.items()},
        "taxes_fees": round(taxes_fees, 2),
        "total_monthly_premium": round(monthly_premium + total_riders + taxes_fees, 2),
        "total_annual_premium": round((monthly_premium + total_riders + taxes_fees) * 12, 2),
        "underwriting_requirements": [] if risk_assessment["score"] < 70 else [
            {"type": "medical_exam", "reason": "High risk score"}
        ],
        "instant_approval": risk_assessment["score"] < 70,
        "exclusions": product["exclusions"],
        "waiting_periods": product["waiting_periods"]
    }


# API Endpoints
@app.post("/v1/quote", response_model=QuoteResponse)
async def create_quote(request: QuoteRequest) -> QuoteResponse:
    """Get quotes from multiple insurance companies"""
    
    # Get or create customer
    customer_id = await get_or_create_customer(request.applicant)
    
    # Calculate risk assessment
    risk_assessment = await calculate_risk_score(request.applicant, request.product_type.value)
    
    # Get relevant companies and products
    if request.company_id:
        companies = await DatabaseOperations.get_documents(
            Collections.COMPANIES,
            {"company_id": request.company_id}
        )
    else:
        # Get all companies offering this product type
        companies = await DatabaseOperations.get_documents(
            Collections.COMPANIES,
            {"products_offered": request.product_type.value}
        )
    
    # Get quotes from each company
    all_quotes = []
    for company in companies:
        # Get product for this company
        product = await async_db[Collections.PRODUCTS].find_one({
            "company_id": company["company_id"],
            "product_type": request.product_type.value,
            "active": True
        })
        
        if product:
            # Check if coverage amount is within limits
            if product["min_coverage"] <= request.coverage_amount <= product["max_coverage"]:
                quote = await get_quote_from_company(company, product, request, risk_assessment)
                if quote:
                    all_quotes.append(quote)
    
    # Sort quotes by premium (lowest first)
    all_quotes.sort(key=lambda x: x["total_monthly_premium"])
    
    # Create recommended plans (top 3)
    recommended_plans = []
    for quote in all_quotes[:3]:
        plan = QuotePlan(
            plan_id=f"P{uuid.uuid4().hex[:6].upper()}",
            plan_name=f"{quote['company_name']} - {quote['product_name']}",
            company_id=quote["company_id"],
            company_name=quote["company_name"],
            company_rating=quote["company_rating"],
            coverage_amount=quote["coverage_amount"],
            deductible=quote["deductible"],
            base_premium=quote["base_premium"],
            rider_premiums=quote["rider_premiums"],
            taxes_fees=quote["taxes_fees"],
            total_monthly_premium=quote["total_monthly_premium"],
            total_annual_premium=quote["total_annual_premium"],
            coverage_details={
                "product_type": request.product_type.value,
                "term_years": request.term_years,
                "riders": request.riders,
                "instant_approval": quote["instant_approval"]
            },
            exclusions=quote["exclusions"],
            waiting_periods=quote["waiting_periods"]
        )
        recommended_plans.append(plan)
    
    # Create quote session
    session_id = f"QS{uuid.uuid4().hex[:8].upper()}"
    quote_date = datetime.utcnow()
    
    # Store quote session in database
    quote_session = {
        "session_id": session_id,
        "customer_id": customer_id,
        "quotes": all_quotes,
        "recommended_plans": [plan.dict() for plan in recommended_plans],
        "risk_assessment": risk_assessment,
        "request_data": request.dict(),
        "created_at": quote_date,
        "valid_until": quote_date + timedelta(days=30)
    }
    
    await async_db["quote_sessions"].insert_one(quote_session)
    
    # Update customer quote history
    await async_db[Collections.CUSTOMERS].update_one(
        {"customer_id": customer_id},
        {"$push": {"quote_history": session_id}}
    )
    
    return QuoteResponse(
        quote_session_id=session_id,
        quote_date=quote_date,
        valid_until=quote_date + timedelta(days=30),
        applicant_id=customer_id,
        risk_assessment=risk_assessment,
        quotes=all_quotes,
        recommended_plans=recommended_plans,
        comparison_matrix={
            "lowest_premium": all_quotes[0] if all_quotes else None,
            "highest_rated": max(all_quotes, key=lambda x: x["company_rating"]) if all_quotes else None,
            "fastest_approval": next((q for q in all_quotes if q["instant_approval"]), None) if all_quotes else None
        }
    )


@app.post("/v1/policy", response_model=PolicyResponse)
async def issue_policy(request: PolicyRequest) -> PolicyResponse:
    """Issue a policy based on selected quote"""
    
    # Retrieve quote session
    session = await async_db["quote_sessions"].find_one({"session_id": request.quote_session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Quote session not found")
    
    # Find the selected plan
    selected_quote = None
    for quote in session["quotes"]:
        if quote["company_id"] == request.company_id:
            selected_quote = quote
            break
    
    if not selected_quote:
        raise HTTPException(status_code=404, detail="Quote not found for specified company")
    
    # Get company details
    company = await async_db[Collections.COMPANIES].find_one({"company_id": request.company_id})
    
    # Create policy
    policy_id = f"POL{uuid.uuid4().hex[:8].upper()}"
    policy_number = f"{datetime.now().year}{random.randint(100000, 999999)}"
    
    issue_date = datetime.utcnow()
    effective_date = issue_date + timedelta(days=1)
    
    if session["request_data"]["term_years"]:
        expiry_date = effective_date + timedelta(days=365 * session["request_data"]["term_years"])
    else:
        expiry_date = None
    
    # Determine premium based on payment frequency
    if request.payment_frequency == "monthly":
        premium_amount = selected_quote["total_monthly_premium"]
        next_payment = effective_date + timedelta(days=30)
    elif request.payment_frequency == "quarterly":
        premium_amount = selected_quote["total_monthly_premium"] * 3
        next_payment = effective_date + timedelta(days=90)
    else:  # annual
        premium_amount = selected_quote["total_annual_premium"]
        next_payment = effective_date + timedelta(days=365)
    
    # Create policy document
    policy = {
        "policy_id": policy_id,
        "policy_number": policy_number,
        "quote_id": selected_quote["quote_id"],
        "company_id": request.company_id,
        "product_id": selected_quote["product_id"],
        "customer_id": session["customer_id"],
        "status": "pending_payment",
        "issue_date": issue_date,
        "effective_date": effective_date,
        "expiry_date": expiry_date,
        "coverage_amount": selected_quote["coverage_amount"],
        "deductible": selected_quote["deductible"],
        "riders": session["request_data"]["riders"],
        "beneficiaries": session["request_data"]["beneficiaries"],
        "premium_amount": premium_amount,
        "payment_frequency": request.payment_frequency,
        "payment_method": request.payment_method,
        "next_payment_date": next_payment,
        "payments": [],
        "total_paid": 0,
        "documents": [
            {"type": "policy_document", "url": f"/documents/policies/{policy_id}.pdf"},
            {"type": "id_card", "url": f"/documents/cards/{policy_id}.pdf"}
        ],
        "created_at": issue_date,
        "updated_at": issue_date
    }
    
    # Store policy
    await async_db[Collections.POLICIES].insert_one(policy)
    
    # Update customer policy history
    await async_db[Collections.CUSTOMERS].update_one(
        {"customer_id": session["customer_id"]},
        {"$push": {"policy_history": policy_id}}
    )
    
    return PolicyResponse(
        policy_id=policy_id,
        policy_number=policy_number,
        company_id=request.company_id,
        company_name=company["name"],
        status="pending_payment",
        issue_date=issue_date,
        effective_date=effective_date,
        expiry_date=expiry_date,
        product_type=session["request_data"]["product_type"],
        coverage_amount=selected_quote["coverage_amount"],
        deductible=selected_quote["deductible"],
        riders=session["request_data"]["riders"],
        premium_amount=premium_amount,
        payment_frequency=request.payment_frequency,
        next_payment_date=next_payment,
        documents=policy["documents"]
    )


@app.get("/v1/policy/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str) -> PolicyResponse:
    """Retrieve policy details"""
    
    policy = await async_db[Collections.POLICIES].find_one({"policy_id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    company = await async_db[Collections.COMPANIES].find_one({"company_id": policy["company_id"]})
    
    return PolicyResponse(
        policy_id=policy["policy_id"],
        policy_number=policy["policy_number"],
        company_id=policy["company_id"],
        company_name=company["name"] if company else "Unknown",
        status=policy["status"],
        issue_date=policy["issue_date"],
        effective_date=policy["effective_date"],
        expiry_date=policy.get("expiry_date"),
        product_type=policy["product_id"].split("_")[-1],
        coverage_amount=policy["coverage_amount"],
        deductible=policy.get("deductible"),
        riders=policy.get("riders", []),
        premium_amount=policy["premium_amount"],
        payment_frequency=policy["payment_frequency"],
        next_payment_date=policy["next_payment_date"],
        documents=policy.get("documents", [])
    )


@app.post("/v1/claim", response_model=ClaimResponse)
async def submit_claim(request: ClaimRequest) -> ClaimResponse:
    """Submit an insurance claim"""
    
    # Verify policy exists
    policy = await async_db[Collections.POLICIES].find_one({"policy_id": request.policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Verify policy is active
    if policy["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Policy is not active (status: {policy['status']})")
    
    # Create claim
    claim_id = f"CLM{uuid.uuid4().hex[:8].upper()}"
    claim_number = f"C{datetime.now().year}{random.randint(10000, 99999)}"
    
    submission_date = datetime.utcnow()
    
    claim = {
        "claim_id": claim_id,
        "claim_number": claim_number,
        "policy_id": request.policy_id,
        "company_id": policy["company_id"],
        "customer_id": policy["customer_id"],
        "claim_type": request.claim_type,
        "incident_date": request.incident_date,
        "submission_date": submission_date,
        "description": request.incident_description,
        "status": "submitted",
        "status_history": [
            {"status": "submitted", "date": submission_date.isoformat(), "notes": "Claim received"}
        ],
        "claim_amount": request.claim_amount,
        "location": request.location,
        "documents": request.documents,
        "claimant_name": request.claimant_name,
        "claimant_relationship": request.claimant_relationship,
        "created_at": submission_date,
        "updated_at": submission_date
    }
    
    # Store claim
    await async_db[Collections.CLAIMS].insert_one(claim)
    
    # Update customer claim history
    await async_db[Collections.CUSTOMERS].update_one(
        {"customer_id": policy["customer_id"]},
        {"$push": {"claim_history": claim_id}}
    )
    
    # Determine required documents
    required_docs = ["Claim form", "Proof of loss"]
    if "medical" in request.claim_type.lower() or "health" in request.claim_type.lower():
        required_docs.extend(["Medical bills", "Doctor's report"])
    elif "death" in request.claim_type.lower():
        required_docs.extend(["Death certificate", "Medical records"])
    
    return ClaimResponse(
        claim_id=claim_id,
        claim_number=claim_number,
        status="submitted",
        submission_date=submission_date,
        estimated_review_date=submission_date + timedelta(days=5),
        required_documents=required_docs,
        next_steps=[
            "Submit any missing required documents",
            "An adjuster will contact you within 48 hours",
            "Keep all receipts and documentation"
        ]
    )


@app.get("/v1/companies")
async def list_companies():
    """List all insurance companies"""
    companies = await DatabaseOperations.get_documents(Collections.COMPANIES)
    # Convert ObjectIds to strings for JSON serialization
    companies_clean = convert_objectid_to_string(companies)
    return {"companies": companies_clean}


@app.get("/v1/products")
async def list_products(company_id: Optional[str] = None, product_type: Optional[str] = None):
    """List insurance products"""
    query = {"active": True}
    if company_id:
        query["company_id"] = company_id
    if product_type:
        query["product_type"] = product_type
    
    products = await DatabaseOperations.get_documents(Collections.PRODUCTS, query)
    # Convert ObjectIds to strings for JSON serialization
    products_clean = convert_objectid_to_string(products)
    return {"products": products_clean}


@app.post("/v1/policy/purchase")
async def purchase_policy(purchase_request: Dict[str, Any]):
    """Purchase a policy from a quote - simplified for demo"""
    try:
        # Extract required data
        plan_id = purchase_request.get("plan_id")
        user_id = purchase_request.get("user_id")
        quote_data = purchase_request.get("quote_data", {})
        
        if not plan_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing plan_id or user_id")
        
        # Generate policy IDs
        policy_id = f"POL{uuid.uuid4().hex[:8].upper()}"
        policy_number = f"PN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Create policy document
        policy_doc = {
            "policy_id": policy_id,
            "policy_number": policy_number,
            "user_id": user_id,  # Link to user account
            "plan_id": plan_id,
            
            # Copy quote data
            "company_name": quote_data.get("company_name", "Unknown"),
            "plan_name": quote_data.get("plan_name", "Unknown Plan"),
            "coverage_amount": quote_data.get("coverage_amount", 0),
            "monthly_premium": quote_data.get("monthly_premium", 0),
            "annual_premium": quote_data.get("annual_premium", 0),
            
            # Policy status
            "status": "active",
            "purchase_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "next_payment_date": datetime.utcnow(),
            
            # Demo data
            "payment_method": purchase_request.get("payment_method", "demo_card"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save policy to database
        await async_db[Collections.POLICIES].insert_one(policy_doc)
        
        # Update user's purchased policies list
        from backend.database import Collections as DbCollections
        await async_db[DbCollections.USERS].update_one(
            {"user_id": user_id},
            {"$addToSet": {"purchased_policies": policy_id}}
        )
        
        return {
            "success": True,
            "policy_id": policy_id,
            "policy_number": policy_number,
            "message": "Policy purchased successfully!",
            "policy_details": {
                "company_name": policy_doc["company_name"],
                "plan_name": policy_doc["plan_name"], 
                "coverage_amount": policy_doc["coverage_amount"],
                "monthly_premium": policy_doc["monthly_premium"],
                "status": "active"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Policy purchase error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to purchase policy: {str(e)}")

@app.get("/v1/user/{user_id}/policies")
async def get_user_policies(user_id: str):
    """Get all policies for a user"""
    try:
        print(f"🔍 Getting policies for user: {user_id}")
        policies = []
        policy_docs = async_db[Collections.POLICIES].find({"user_id": user_id})
        
        async for policy in policy_docs:
            print(f"📋 Found policy: {policy['policy_id']} for user {policy.get('user_id')}")
            policies.append({
                "policy_id": policy["policy_id"],
                "policy_number": policy["policy_number"],
                "company_name": policy.get("company_name", "Unknown"),
                "plan_name": policy.get("plan_name", "Unknown Plan"),
                "coverage_amount": policy.get("coverage_amount", 0),
                "monthly_premium": policy.get("monthly_premium", 0),
                "status": policy.get("status", "unknown"),
                "purchase_date": policy.get("purchase_date"),
                "effective_date": policy.get("effective_date"),
                "next_payment_date": policy.get("next_payment_date")
            })
        
        print(f"✅ Total policies found for {user_id}: {len(policies)}")
        return {
            "success": True,
            "user_id": user_id,
            "policies": policies,
            "total_policies": len(policies)
        }
        
    except Exception as e:
        print(f"❌ Get user policies error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user policies")

@app.post("/v1/claims/file")
async def file_claim(claim_request: Dict[str, Any]):
    """File a new insurance claim"""
    try:
        # Extract required data
        policy_id = claim_request.get("policy_id")
        user_id = claim_request.get("user_id")
        claim_type = claim_request.get("claim_type", "general")
        incident_description = claim_request.get("incident_description", "")
        claim_amount = claim_request.get("claim_amount", 0)
        
        if not policy_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing policy_id or user_id")
        
        # Verify user owns the policy
        policy = await async_db[Collections.POLICIES].find_one({
            "policy_id": policy_id, 
            "user_id": user_id
        })
        
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found or not owned by user")
        
        # Generate claim IDs
        claim_id = f"CLM{uuid.uuid4().hex[:8].upper()}"
        claim_number = f"CN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Create claim document
        claim_doc = {
            "claim_id": claim_id,
            "claim_number": claim_number,
            "policy_id": policy_id,
            "user_id": user_id,
            "company_name": policy.get("company_name", "Unknown"),
            
            # Claim details
            "claim_type": claim_type,
            "incident_description": incident_description,
            "claim_amount": float(claim_amount) if claim_amount else 0,
            
            # Status tracking
            "status": "submitted",
            "submission_date": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            
            # Processing info
            "estimated_processing_days": 5,  # Demo value
            "adjuster_assigned": None,
            "documents_required": ["incident_report", "supporting_evidence"],
            
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save claim to database
        await async_db[Collections.CLAIMS].insert_one(claim_doc)
        
        return {
            "success": True,
            "claim_id": claim_id,
            "claim_number": claim_number,
            "message": "Claim filed successfully!",
            "claim_details": {
                "claim_number": claim_number,
                "policy_id": policy_id,
                "claim_type": claim_type,
                "claim_amount": claim_amount,
                "status": "submitted",
                "estimated_processing_days": 5
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ File claim error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to file claim: {str(e)}")

@app.get("/v1/user/{user_id}/claims")
async def get_user_claims(user_id: str):
    """Get all claims for a user"""
    try:
        claims = []
        claim_docs = async_db[Collections.CLAIMS].find({"user_id": user_id})
        
        async for claim in claim_docs:
            claims.append({
                "claim_id": claim["claim_id"],
                "claim_number": claim["claim_number"],
                "policy_id": claim["policy_id"],
                "company_name": claim.get("company_name", "Unknown"),
                "claim_type": claim.get("claim_type", "general"),
                "claim_amount": claim.get("claim_amount", 0),
                "status": claim.get("status", "unknown"),
                "submission_date": claim.get("submission_date"),
                "last_updated": claim.get("last_updated"),
                "incident_description": claim.get("incident_description", ""),
                "estimated_processing_days": claim.get("estimated_processing_days", 0)
            })
        
        return {
            "success": True,
            "user_id": user_id,
            "claims": claims,
            "total_claims": len(claims)
        }
        
    except Exception as e:
        print(f"❌ Get user claims error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user claims")

@app.get("/v1/claims/{claim_id}")
async def get_claim_details(claim_id: str, user_id: str):
    """Get detailed information about a specific claim"""
    try:
        claim = await async_db[Collections.CLAIMS].find_one({
            "claim_id": claim_id,
            "user_id": user_id  # Ensure user owns the claim
        })
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        return {
            "success": True,
            "claim": {
                "claim_id": claim["claim_id"],
                "claim_number": claim["claim_number"],
                "policy_id": claim["policy_id"],
                "company_name": claim.get("company_name", "Unknown"),
                "claim_type": claim.get("claim_type", "general"),
                "claim_amount": claim.get("claim_amount", 0),
                "status": claim.get("status", "unknown"),
                "submission_date": claim.get("submission_date"),
                "last_updated": claim.get("last_updated"),
                "incident_description": claim.get("incident_description", ""),
                "estimated_processing_days": claim.get("estimated_processing_days", 0),
                "documents_required": claim.get("documents_required", []),
                "adjuster_assigned": claim.get("adjuster_assigned")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get claim details error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get claim details")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}