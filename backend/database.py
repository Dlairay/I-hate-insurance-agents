"""
database.py
===========
MongoDB connection and models for insurance data
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import os
from bson import ObjectId


# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "insurance_db")

# Async client for FastAPI
async_client = AsyncIOMotorClient(MONGODB_URL)
async_db = async_client[DATABASE_NAME]

# Sync client for data population scripts
sync_client = MongoClient(MONGODB_URL)
sync_db = sync_client[DATABASE_NAME]


# Collections
class Collections:
    """MongoDB collection names"""
    COMPANIES = "insurance_companies"
    PRODUCTS = "insurance_products"
    QUOTES = "quotes"
    POLICIES = "policies"
    CLAIMS = "claims"
    CUSTOMERS = "customers"
    RATE_TABLES = "rate_tables"
    QUESTIONNAIRE_SESSIONS = "questionnaire_sessions"  # Store completed questionnaires
    PDF_EXTRACTIONS = "pdf_extractions"  # Store PDF processing results
    POLICY_SCORES = "policy_scores"  # Store scoring results


# Helper class for ObjectId handling
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


# MongoDB Models
class MongoBaseModel(BaseModel):
    """Base model with MongoDB ObjectId support"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class InsuranceCompany(MongoBaseModel):
    """Insurance company/provider model"""
    company_id: str = Field(..., unique=True)
    name: str
    type: str  # "health", "life", "multi-line"
    rating: float = Field(ge=0, le=5)
    established_year: int
    states_available: List[str]
    products_offered: List[str]
    
    # API configuration (for multi-provider simulation)
    api_endpoint: str
    api_key: str
    
    # Business rules
    risk_appetite: str  # "conservative", "moderate", "aggressive"
    max_coverage_limits: Dict[str, float]
    underwriting_turnaround_days: int
    
    # Contact info
    contact_email: str
    contact_phone: str
    website: str


class InsuranceProduct(MongoBaseModel):
    """Insurance product offered by a company"""
    product_id: str = Field(..., unique=True)
    company_id: str
    product_type: str  # matches ProductType enum
    product_name: str
    description: str
    
    # Coverage details
    min_coverage: float
    max_coverage: float
    coverage_types: List[str]
    
    # Eligibility
    min_age: int
    max_age: int
    states_available: List[str]
    
    # Features
    available_riders: List[Dict[str, Any]]
    waiting_periods: Dict[str, int]
    exclusions: List[str]
    
    # Pricing factors
    base_rate: float
    rating_factors: Dict[str, float]
    
    active: bool = True


class CustomerProfile(MongoBaseModel):
    """Customer/applicant profile"""
    customer_id: str = Field(..., unique=True)
    
    # Personal info
    first_name: str
    last_name: str
    email: str
    phone: str
    dob: str
    gender: str
    ssn_last_four: str
    
    # Address
    address: Dict[str, str]
    
    # Health profile
    health_data: Dict[str, Any]
    
    # Risk profile
    risk_score: float
    risk_factors: List[str]
    
    # History
    quote_history: List[str] = []
    policy_history: List[str] = []
    claim_history: List[str] = []


class Quote(MongoBaseModel):
    """Insurance quote record"""
    quote_id: str = Field(..., unique=True)
    company_id: str
    product_id: str
    customer_id: str
    
    # Quote details
    quote_date: datetime
    valid_until: datetime
    status: str
    
    # Coverage
    coverage_amount: float
    deductible: Optional[float]
    term_years: Optional[int]
    riders: List[str]
    
    # Pricing
    base_premium: float
    rider_premiums: Dict[str, float]
    discounts: Dict[str, float]
    taxes_fees: float
    total_monthly_premium: float
    total_annual_premium: float
    
    # Risk assessment
    risk_score: float
    risk_factors: List[str]
    underwriting_requirements: List[Dict[str, str]]
    
    # Plans offered
    plans: List[Dict[str, Any]]
    selected_plan_id: Optional[str]


class Policy(MongoBaseModel):
    """Active insurance policy"""
    policy_id: str = Field(..., unique=True)
    policy_number: str = Field(..., unique=True)
    quote_id: str
    company_id: str
    product_id: str
    customer_id: str
    
    # Status
    status: str  # "active", "lapsed", "cancelled", "expired"
    
    # Dates
    issue_date: datetime
    effective_date: datetime
    expiry_date: Optional[datetime]
    last_renewed_date: Optional[datetime]
    
    # Coverage
    coverage_amount: float
    deductible: Optional[float]
    riders: List[str]
    beneficiaries: List[Dict[str, Any]]
    
    # Premium
    premium_amount: float
    payment_frequency: str
    payment_method: str
    next_payment_date: datetime
    
    # Payment history
    payments: List[Dict[str, Any]] = []
    total_paid: float = 0
    
    # Documents
    documents: List[Dict[str, str]] = []


class QuestionnaireSessionRecord(MongoBaseModel):
    """Completed questionnaire session stored in database"""
    session_id: str = Field(..., unique=True)
    user_id: Optional[str] = None
    
    # Questionnaire responses mapped to profile fields
    applicant_profile: Dict[str, Any]
    
    # Session metadata
    completion_date: datetime = Field(default_factory=datetime.utcnow)
    questionnaire_version: str = "3-phase-v1"
    source: str  # "manual", "json_upload", "pdf_upload"
    
    # PDF processing info (if applicable)
    pdf_filename: Optional[str] = None
    pdf_extraction_confidence: Optional[float] = None
    
    # Generated quotes and scores
    quote_request_id: Optional[str] = None
    policy_scores: List[Dict[str, Any]] = []


class PDFExtractionRecord(MongoBaseModel):
    """PDF document processing results"""
    extraction_id: str = Field(..., unique=True)
    session_id: str
    
    # File info
    filename: str
    file_size_bytes: int
    file_hash: str  # For duplicate detection
    
    # Extraction results
    extracted_fields: Dict[str, Any]
    confidence_score: float
    processing_time_seconds: float
    
    # Quality metrics
    missing_required_fields: List[str]
    warnings: List[str]
    
    # AI model info
    extraction_method: str  # "gemini", "fallback"
    model_version: Optional[str] = None


class PolicyScoreRecord(MongoBaseModel):
    """Policy scoring results for analytics"""
    score_id: str = Field(..., unique=True)
    session_id: str
    plan_id: str
    
    # Scores
    overall_score: float
    affordability_score: float
    ease_of_claims_score: float
    coverage_ratio_score: float
    
    # User context
    user_annual_income: float
    income_percentage: float
    
    # Plan details for analysis
    company_name: str
    plan_name: str
    monthly_premium: float
    coverage_amount: float
    
    # Scoring metadata
    scoring_version: str = "v1"
    scoring_weights: Dict[str, float]


class Claim(MongoBaseModel):
    """Insurance claim record"""
    claim_id: str = Field(..., unique=True)
    claim_number: str = Field(..., unique=True)
    policy_id: str
    company_id: str
    customer_id: str
    
    # Claim details
    claim_type: str
    incident_date: datetime
    submission_date: datetime
    description: str
    
    # Status tracking
    status: str
    status_history: List[Dict[str, Any]]
    
    # Assessment
    claim_amount: float
    approved_amount: Optional[float]
    deductible_applied: Optional[float]
    
    # Processing
    adjuster_name: Optional[str]
    adjuster_notes: List[str]
    investigation_notes: Optional[str]
    
    # Documents
    documents: List[Dict[str, Any]]
    
    # Payment
    payment_date: Optional[datetime]
    payment_method: Optional[str]
    payment_reference: Optional[str]


class RateTable(MongoBaseModel):
    """Rating tables for premium calculation"""
    table_id: str = Field(..., unique=True)
    company_id: str
    product_type: str
    effective_date: datetime
    
    # Age-based rates
    age_bands: List[Dict[str, Any]]  # [{min_age, max_age, factor}]
    
    # Health factors
    health_factors: Dict[str, float]
    bmi_ranges: List[Dict[str, Any]]  # [{min_bmi, max_bmi, factor}]
    smoker_factor: float
    
    # Geographic factors
    state_factors: Dict[str, float]
    
    # Occupation factors
    occupation_classes: Dict[str, float]
    
    # Discount factors
    discounts: Dict[str, float]
    
    # Rider rates
    rider_rates: Dict[str, float]


# Database initialization
async def init_db():
    """Initialize database with indexes"""
    # Create indexes for better query performance
    await async_db[Collections.COMPANIES].create_index("company_id", unique=True)
    await async_db[Collections.PRODUCTS].create_index("product_id", unique=True)
    await async_db[Collections.PRODUCTS].create_index("company_id")
    await async_db[Collections.QUOTES].create_index("quote_id", unique=True)
    await async_db[Collections.QUOTES].create_index("customer_id")
    await async_db[Collections.POLICIES].create_index("policy_id", unique=True)
    await async_db[Collections.POLICIES].create_index("policy_number", unique=True)
    await async_db[Collections.POLICIES].create_index("customer_id")
    await async_db[Collections.CLAIMS].create_index("claim_id", unique=True)
    await async_db[Collections.CLAIMS].create_index("policy_id")
    await async_db[Collections.CUSTOMERS].create_index("customer_id", unique=True)
    await async_db[Collections.CUSTOMERS].create_index("email", unique=True)
    await async_db[Collections.RATE_TABLES].create_index("table_id", unique=True)
    await async_db[Collections.RATE_TABLES].create_index(["company_id", "product_type"])


# CRUD operations
class DatabaseOperations:
    """Database operations wrapper"""
    
    @staticmethod
    async def create_document(collection: str, document: dict) -> str:
        """Create a new document"""
        document["created_at"] = datetime.utcnow()
        document["updated_at"] = datetime.utcnow()
        result = await async_db[collection].insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    async def get_document(collection: str, query: dict) -> Optional[dict]:
        """Get a single document"""
        return await async_db[collection].find_one(query)
    
    @staticmethod
    async def get_documents(collection: str, query: dict = None, limit: int = 100) -> List[dict]:
        """Get multiple documents"""
        query = query or {}
        cursor = async_db[collection].find(query).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def update_document(collection: str, query: dict, update: dict) -> bool:
        """Update a document"""
        update["updated_at"] = datetime.utcnow()
        result = await async_db[collection].update_one(query, {"$set": update})
        return result.modified_count > 0
    
    @staticmethod
    async def delete_document(collection: str, query: dict) -> bool:
        """Delete a document"""
        result = await async_db[collection].delete_one(query)
        return result.deleted_count > 0


# Helper functions for common queries
async def get_company_products(company_id: str) -> List[dict]:
    """Get all products for a company"""
    return await DatabaseOperations.get_documents(
        Collections.PRODUCTS,
        {"company_id": company_id, "active": True}
    )


async def get_customer_policies(customer_id: str, status: str = "active") -> List[dict]:
    """Get all policies for a customer"""
    return await DatabaseOperations.get_documents(
        Collections.POLICIES,
        {"customer_id": customer_id, "status": status}
    )


async def get_policy_claims(policy_id: str) -> List[dict]:
    """Get all claims for a policy"""
    return await DatabaseOperations.get_documents(
        Collections.CLAIMS,
        {"policy_id": policy_id}
    )