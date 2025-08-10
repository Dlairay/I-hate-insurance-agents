"""
shared/models.py
================
Shared data models used across the application
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, date
from enum import Enum


class ProductType(str, Enum):
    LIFE_TERM = "LIFE_TERM"
    LIFE_WHOLE = "LIFE_WHOLE"
    HEALTH_BASIC = "HEALTH_BASIC"
    HEALTH_PREMIUM = "HEALTH_PREMIUM"
    CRITICAL_ILLNESS = "CRITICAL_ILLNESS"


class QuestionType(str, Enum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTIPLE = "mcq_multiple" 
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"


# Questionnaire Models
class QuestionOption(BaseModel):
    """Individual option for MCQ questions"""
    value: str
    label: str
    description: Optional[str] = None


class Question(BaseModel):
    """Single questionnaire question"""
    id: str
    question_text: str
    question_type: QuestionType
    options: Optional[List[QuestionOption]] = None
    required: bool = True
    help_text: Optional[str] = None
    depends_on: Optional[Dict[str, Any]] = None  # Conditional logic
    category: str  # "personal", "health", "financial", "product"


class QuestionnaireResponse(BaseModel):
    """User's response to a question"""
    question_id: str
    answer: Any  # Could be string, list, number, etc.
    needs_help: bool = False
    help_description: Optional[str] = None
    ai_selected: bool = False  # If AI helper selected this answer


class QuestionnaireSession(BaseModel):
    """Complete questionnaire session"""
    session_id: str
    user_id: Optional[str] = None
    responses: List[QuestionnaireResponse] = []
    completed: bool = False
    current_question_index: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Insurance API Models (standardized)
class ApplicantProfile(BaseModel):
    """Standardized applicant profile for insurance API"""
    
    # Personal Information
    first_name: str
    last_name: str
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: Literal["M", "F", "OTHER"]
    email: str
    phone: str
    
    # Address
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    
    # Health Information
    smoker: Optional[bool] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    
    # Medical History
    pre_existing_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    hospitalizations_last_5_years: Optional[int] = 0
    family_medical_history: Optional[List[str]] = []
    
    # Lifestyle
    exercise_frequency: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    travel_frequency: Optional[str] = None
    
    @validator("dob")
    def validate_dob(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except Exception as exc:
            raise ValueError(f"dob must be in YYYY-MM-DD format: {v}") from exc
        return v
    
    def age(self) -> int:
        birth = date.fromisoformat(self.dob)
        today = date.today()
        years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return years


class InsuranceRequest(BaseModel):
    """Request to insurance API"""
    product_type: ProductType
    applicant: ApplicantProfile
    coverage_amount: float = Field(..., gt=0)
    deductible: Optional[float] = None
    term_years: Optional[int] = None
    riders: Optional[List[str]] = []
    beneficiaries: Optional[List[Dict[str, Any]]] = []


class InsurancePlan(BaseModel):
    """Standardized insurance plan response"""
    plan_id: str
    plan_name: str
    company_id: str
    company_name: str
    company_rating: float
    
    # Coverage
    coverage_amount: float
    deductible: Optional[float]
    term_years: Optional[int]
    
    # Pricing
    monthly_premium: float
    annual_premium: float
    setup_fees: float = 0
    
    # Features
    key_features: List[str] = []
    riders_included: List[str] = []
    waiting_periods: Dict[str, int] = {}
    exclusions: List[str] = []
    
    # Additional info
    instant_approval: bool = False
    underwriting_required: bool = False
    estimated_approval_days: int = 0


class InsuranceQuoteResponse(BaseModel):
    """Response from insurance API"""
    session_id: str
    request_date: datetime
    valid_until: datetime
    
    # Applicant info
    applicant_id: str
    risk_assessment: Dict[str, Any]
    
    # Available plans
    plans: List[InsurancePlan]
    
    # Metadata
    total_quotes: int
    companies_queried: int
    instant_approvals: int


# AI Agent Response Models
class InsuranceCard(BaseModel):
    """Standardized insurance card for display"""
    plan_id: str
    company_name: str
    plan_name: str
    
    # Key highlights
    monthly_cost: str  # Formatted string like "$250/month"
    coverage_amount: str  # Formatted string like "$500,000"
    key_benefits: List[str]  # Top 3-4 benefits
    
    # Status indicators
    instant_approval: bool
    company_rating: float
    value_score: float  # AI-calculated value score 0-100
    
    # Quick facts
    deductible: Optional[str] = None
    waiting_period: Optional[str] = None
    
    # Visual indicators
    recommended: bool = False
    best_value: bool = False
    fastest_approval: bool = False


class RecommendationReason(BaseModel):
    """Reason for recommending a plan"""
    factor: str  # "cost", "coverage", "company_rating", "features"
    weight: float  # 0-1, how important this factor was
    description: str  # Human readable explanation


class InsuranceRecommendation(BaseModel):
    """AI recommendation for insurance plans"""
    plan_id: str
    rank: int  # 1 = top recommendation
    confidence_score: float  # 0-100
    
    # Why this plan was recommended
    reasons: List[RecommendationReason]
    
    # Comparison with user profile
    profile_match_score: float  # 0-100
    cost_effectiveness: float  # 0-100
    
    # Summary
    recommendation_summary: str  # AI-generated summary
    pros: List[str]
    cons: List[str]


class UserProfile(BaseModel):
    """AI-analyzed user profile"""
    age_group: str  # "young", "middle_aged", "senior"
    risk_level: str  # "low", "medium", "high"
    financial_capacity: str  # "budget", "moderate", "premium"
    health_status: str  # "excellent", "good", "fair", "poor"
    
    # Priorities (inferred from questionnaire)
    priorities: Dict[str, float]  # {"cost": 0.8, "coverage": 0.6, "speed": 0.3}
    
    # Constraints
    max_monthly_budget: Optional[float] = None
    preferred_companies: List[str] = []
    must_have_features: List[str] = []