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
    
    # AI Chatbot Feature (pre-computed, not runtime)
    show_ai_help: bool = False   # Whether to show AI chatbot help button


class QuestionnaireResponse(BaseModel):
    """User's response to a question"""
    question_id: str
    answer: Any  # Could be string, list, number, etc.
    needs_help: bool = False
    help_description: Optional[str] = None
    ai_selected: bool = False  # If AI helper selected this answer


class QuestionnaireSession(BaseModel):
    """Complete questionnaire session with direct schema population"""
    session_id: str
    user_id: Optional[str] = None
    responses: List[QuestionnaireResponse] = []
    completed: bool = False
    current_question_index: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = {}  # For storing PDF extraction results, etc.
    
    # NEW: Direct schema population as user answers
    user_profile: Optional["UserProfile"] = None


# Insurance API Models (standardized)
class ApplicantProfile(BaseModel):
    """Enhanced applicant profile for insurance API with new questionnaire fields"""
    
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
    
    # Financial Information
    annual_income: Optional[float] = None
    occupation: Optional[str] = None
    
    # Health Information (enhanced)
    smoker: Optional[bool] = None
    smoking_vaping_habits: Optional[str] = None  # "never", "quit_over_year", "regular", etc.
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    
    # Medical History
    pre_existing_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    hospitalizations_last_5_years: Optional[int] = 0
    family_medical_history: Optional[List[str]] = []
    
    # Lifestyle Risk Factors (Phase 1)
    alcohol_consumption: Optional[str] = None  # "none", "light", "moderate", etc.
    exercise_frequency: Optional[str] = None  # "daily", "regular", "occasional", etc.
    dietary_habits: Optional[str] = None  # "very_healthy", "mostly_healthy", etc.
    high_risk_activities: Optional[List[str]] = []  # List of risky hobbies/activities
    travel_frequency: Optional[str] = None
    
    # Coverage Gaps & Transition Status (Phase 2)
    current_coverage_status: Optional[str] = None  # "parents_policy", "employer_current", etc.
    parents_policy_end_date: Optional[str] = None  # When parent coverage ends
    employer_coverage_expectation: Optional[str] = None  # Future employer coverage
    hospital_preference: Optional[str] = None  # "public_only", "private_preferred", etc.
    special_coverage_needs: Optional[List[str]] = []  # "maternity", "overseas", etc.
    
    # Preferences & Budget (Phase 3)
    coverage_vs_premium_priority: Optional[str] = None  # "lowest_premium", "balanced", etc.
    desired_add_ons: Optional[List[str]] = []  # "dental", "vision", "mental_health", etc.
    monthly_premium_budget: Optional[str] = None  # Budget range
    deductible_copay_preference: Optional[str] = None  # Willingness to pay deductibles
    
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
    deductible: float = 0  # Default to $0 deductible if not specified
    term_years: int = 1  # Default to 1 year term
    
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


# Base Schema Models - Foundation for direct questionnaire population
class UserProfile(BaseModel):
    """Base user profile schema - populated directly from questionnaire responses"""
    
    # Core Identity (required for API)
    age: int = Field(..., description="User's age")
    annual_income: float = Field(..., description="Annual income in USD")
    gender: Literal["M", "F", "OTHER"] = Field(default="OTHER")
    
    # Health Assessment (schema-enforced from MCQ)
    health_status: Literal["excellent", "good", "fair", "poor"]
    smoker_status: Literal["never", "former", "current"] = Field(default="never")
    bmi_category: Literal["underweight", "normal", "overweight", "obese"] = Field(default="normal")
    
    # Existing Coverage Analysis (direct MCQ mapping)
    existing_coverage_type: Literal["none", "employer_basic", "employer_comprehensive", "individual_basic", "individual_comprehensive", "parents"]
    existing_coverage_amount: Literal["none", "under_50k", "50k_100k", "100k_250k", "250k_500k", "over_500k"]
    current_monthly_premium: Optional[float] = None
    
    # Intent & Preferences (direct MCQ mapping)
    primary_need: Literal["save_money", "fill_gaps", "first_time", "life_change", "compare_options"]
    monthly_budget: Literal["under_100", "100_200", "200_400", "400_plus", "show_all"]
    coverage_priority: Literal["health_medical", "life_protection", "critical_illness", "comprehensive_all", "unsure"]
    urgency: Literal["immediately", "within_month", "within_3_months", "exploring"]
    
    # NEW: Enhanced Lifestyle & Risk Factors (v2.0)
    occupation: Optional[str] = Field(default="office_professional")
    smoking_status: Optional[str] = Field(default="never") 
    alcohol_consumption: Optional[str] = Field(default="social")
    exercise_frequency: Optional[str] = Field(default="weekly")
    high_risk_activities: Optional[List[str]] = Field(default=["none"])
    monthly_premium_budget: Optional[str] = Field(default="flexible")
    desired_add_ons: Optional[List[str]] = Field(default=["none"])
    
    # Derived/Calculated Fields (filled by agents or calculations)
    risk_score: Optional[int] = Field(default=None, description="0-100 risk assessment")
    affordability_ratio: Optional[float] = Field(default=None, description="% of income for insurance")
    
    def to_applicant_data(self) -> "ApplicantProfile":
        """Convert to API format - simple mapping, no agent needed"""
        from datetime import date
        
        # Calculate birth year
        current_year = date.today().year
        birth_year = current_year - self.age
        
        return ApplicantProfile(
            first_name="User",
            last_name="Person", 
            dob=f"{birth_year}-01-01",
            gender=self.gender,
            email="user@example.com",
            phone="000-000-0000",
            address_line1="123 Main St",
            city="Anytown", 
            state="CA",
            postal_code="12345",
            annual_income=self.annual_income,
            smoker=self.smoker_status == "current"
        )

# Agent Schemas - For intelligent analysis
class ExistingPolicyAssessment(BaseModel):
    """Schema for existing policy analysis agent output"""
    
    coverage_adequacy: Literal["under_insured", "adequately_insured", "over_insured", "no_coverage"]
    monthly_cost_assessment: Literal["very_cheap", "reasonable", "expensive", "very_expensive"]
    coverage_gaps: List[str] = Field(description="List of uncovered risks")
    over_coverage_areas: List[str] = Field(description="Areas of excessive coverage")
    
    # Actionable recommendations
    primary_action: Literal["no_action", "reduce_coverage", "add_supplemental", "switch_provider", "get_new_coverage"]
    potential_monthly_savings: float = Field(description="Estimated monthly savings in USD")
    confidence_score: int = Field(description="Confidence in recommendation 0-100")
    
    # Reasoning (LLM generated)
    analysis_reasoning: str = Field(description="Why this recommendation was made")
    specific_actions: List[str] = Field(description="3-5 specific action items")

class NeedsEvaluationSchema(BaseModel):
    """Schema for needs evaluation agent output"""
    
    should_get_quotes: bool = Field(description="Should we fetch new insurance quotes?")
    reasoning: str = Field(description="Why we should/shouldn't get quotes")
    recommended_coverage_amount: float = Field(description="Suggested coverage amount in USD")
    priority_product_type: Literal["HEALTH_BASIC", "HEALTH_PREMIUM", "LIFE_TERM", "CRITICAL_ILLNESS"]
    urgency_level: Literal["immediate", "soon", "can_wait", "no_rush"]
    
    # Key insights for user
    main_recommendation: str = Field(description="Primary recommendation for this user")
    action_items: List[str] = Field(max_items=4, description="Specific next steps")

class PolicyScore(BaseModel):
    """Schema for policy scoring agent output"""
    
    plan_id: str
    overall_score: int = Field(description="Overall score 0-100")
    
    # The 3 core metrics
    affordability_score: int = Field(description="0-100 based on income ratio") 
    ease_of_claims_score: int = Field(description="0-100 based on company data")
    coverage_ratio_score: int = Field(description="0-100 coverage per dollar")
    
    # User context
    fits_budget: bool
    matches_priorities: bool
    
    # LLM reasoning
    recommendation_reason: str = Field(description="Why this plan scored this way")
    best_for_user_because: str = Field(description="What makes this good for this specific user")


# Scoring Models (for Mission 3)
class PolicyScoreBreakdown(BaseModel):
    """Detailed breakdown of policy scoring"""
    affordability_score: float = Field(ge=0, le=100)
    ease_of_claims_score: float = Field(ge=0, le=100) 
    coverage_ratio_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    
    # Detailed metrics
    income_percentage: float  # Percentage of income used for insurance
    claims_processing_days: Optional[int] = None
    coverage_per_dollar: float  # Coverage amount per dollar of premium
    
    # Categories
    affordability_category: str  # "Excellent", "Good", etc.
    claims_ease_category: str
    coverage_value_category: str
    overall_category: str
    
    # User-specific insights
    value_proposition: str
    key_strengths: List[str] = []
    key_concerns: List[str] = []


class EnhancedInsuranceCard(BaseModel):
    """Insurance card with integrated scoring"""
    # Basic card info
    plan_id: str
    company_name: str
    plan_name: str
    
    # Pricing
    monthly_cost: str  # Formatted string like "$250/month"
    annual_cost: str
    coverage_amount: str  # Formatted string like "$500,000"
    
    # Features
    key_benefits: List[str]
    riders_included: List[str] = []
    
    # Status indicators  
    instant_approval: bool
    company_rating: float
    
    # Scoring integration (Mission 3)
    scores: PolicyScoreBreakdown
    
    # Visual indicators
    recommended: bool = False
    best_value: bool = False
    fastest_approval: bool = False
    badges: List[str] = []  # ["Great Value", "Easy Claims", etc.]
    
    # Additional details
    deductible: Optional[str] = None
    waiting_period: Optional[str] = None
    exclusions: List[str] = []