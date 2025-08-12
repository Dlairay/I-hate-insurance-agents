"""
questionnaire/questions.py
==========================
Enhanced MVP Insurance Questionnaire - 15 essential questions
"""

from backend.shared.models import Question, QuestionOption, QuestionType

# Enhanced MVP Questionnaire - 15 Essential Questions
INSURANCE_QUESTIONS = [
    # Question 1: Basic Identity (Combined age/income for quick profile)
    Question(
        id="basic_info",
        question_text="Let's start with the basics - what's your age and annual income?",
        question_type=QuestionType.TEXT,
        required=True,
        help_text="Format: Age (e.g., 28) and Income (e.g., 75000). This helps calculate affordability.",
        category="essential",
        show_ai_help=True
    ),
    
    # Question 2: Occupation (NEW - Risk factor)
    Question(
        id="occupation",
        question_text="What's your occupation?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="office_professional", label="Office/Professional (low risk)"),
            QuestionOption(value="healthcare", label="Healthcare worker"),
            QuestionOption(value="education", label="Teacher/Education"),
            QuestionOption(value="retail_service", label="Retail/Service industry"),
            QuestionOption(value="transportation", label="Driver/Transportation"),
            QuestionOption(value="construction", label="Construction/Manual labor (higher risk)"),
            QuestionOption(value="law_enforcement", label="Law enforcement/Security"),
            QuestionOption(value="self_employed", label="Self-employed/Business owner"),
            QuestionOption(value="other", label="Other")
        ],
        required=True,
        help_text="Your occupation affects risk assessment and premium calculation",
        category="essential",
        show_ai_help=False
    ),
    
    # Question 3: Existing Coverage
    Question(
        id="existing_coverage",
        question_text="What insurance do you currently have?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="none", label="No insurance - I need coverage"),
            QuestionOption(value="employer_only", label="Basic employer insurance only"),
            QuestionOption(value="employer_comprehensive", label="Comprehensive employer coverage"),
            QuestionOption(value="individual_basic", label="Individual policy - basic coverage"),
            QuestionOption(value="individual_comprehensive", label="Individual policy - comprehensive"),
            QuestionOption(value="parents", label="Still on parents' policy (ending soon)")
        ],
        required=True,
        help_text="We'll analyze if you need supplemental coverage or can save money",
        category="essential",
        show_ai_help=False
    ),
    
    # Question 4: Coverage Amount if Existing
    Question(
        id="current_coverage_amount",
        question_text="If you have existing coverage, what's the total coverage amount?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="none", label="No existing coverage"),
            QuestionOption(value="under_50k", label="Under $50,000"),
            QuestionOption(value="50k_100k", label="$50,000 - $100,000"),
            QuestionOption(value="100k_250k", label="$100,000 - $250,000"),
            QuestionOption(value="250k_500k", label="$250,000 - $500,000"),
            QuestionOption(value="over_500k", label="Over $500,000")
        ],
        required=True,
        help_text="We'll check if you're over-insured or have coverage gaps",
        category="essential",
        show_ai_help=False
    ),
    
    # Question 5: Health Status
    Question(
        id="health_status",
        question_text="How would you describe your overall health?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="excellent", label="Excellent - no issues, active lifestyle"),
            QuestionOption(value="good", label="Good - minor issues, generally healthy"),
            QuestionOption(value="fair", label="Fair - some managed conditions"),
            QuestionOption(value="poor", label="Poor - multiple health concerns")
        ],
        required=True,
        help_text="Honesty ensures accurate quotes and recommendations",
        category="essential",
        show_ai_help=True
    ),
    
    # Question 6: Smoking/Vaping (NEW - Critical risk factor)
    Question(
        id="smoking_vaping_habits",
        question_text="Do you smoke or vape?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="never", label="Never smoked/vaped"),
            QuestionOption(value="quit_over_year", label="Quit over a year ago"),
            QuestionOption(value="quit_under_year", label="Quit less than a year ago"),
            QuestionOption(value="occasional", label="Occasional/Social (less than weekly)"),
            QuestionOption(value="regular", label="Regular (weekly)"),
            QuestionOption(value="daily", label="Daily smoker/vaper")
        ],
        required=True,
        help_text="Smoking status significantly affects premiums - be honest for accurate quotes",
        category="lifestyle",
        show_ai_help=True
    ),
    
    # Question 7: Alcohol Consumption (NEW)
    Question(
        id="alcohol_consumption",
        question_text="How often do you consume alcohol?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="never", label="Never/Non-drinker"),
            QuestionOption(value="rare", label="Rarely (special occasions only)"),
            QuestionOption(value="social", label="Social (1-2 times per week)"),
            QuestionOption(value="moderate", label="Moderate (3-4 times per week)"),
            QuestionOption(value="daily", label="Daily")
        ],
        required=True,
        help_text="Alcohol consumption affects health risk assessment",
        category="lifestyle",
        show_ai_help=True
    ),
    
    # Question 8: Exercise Frequency (NEW)
    Question(
        id="exercise_frequency",
        question_text="How often do you exercise?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="daily", label="Daily (5-7 times per week)"),
            QuestionOption(value="regular", label="Regular (3-4 times per week)"),
            QuestionOption(value="weekly", label="Weekly (1-2 times per week)"),
            QuestionOption(value="monthly", label="Occasionally (few times a month)"),
            QuestionOption(value="rarely", label="Rarely or never")
        ],
        required=True,
        help_text="Regular exercise indicates lower health risk",
        category="lifestyle",
        show_ai_help=True
    ),
    
    # Question 9: High-Risk Activities (NEW)
    Question(
        id="high_risk_activities",
        question_text="Do you participate in any high-risk activities? (Select all that apply)",
        question_type=QuestionType.MCQ_MULTIPLE,
        options=[
            QuestionOption(value="none", label="None - I avoid risky activities"),
            QuestionOption(value="scuba", label="Scuba diving"),
            QuestionOption(value="skydiving", label="Skydiving/Parachuting"),
            QuestionOption(value="racing", label="Motor racing/Motorcycling"),
            QuestionOption(value="climbing", label="Rock climbing/Mountaineering"),
            QuestionOption(value="martial_arts", label="Combat sports/Martial arts"),
            QuestionOption(value="flying", label="Private aviation/Flying"),
            QuestionOption(value="extreme_sports", label="Other extreme sports")
        ],
        required=True,
        help_text="High-risk activities may affect life insurance premiums",
        category="lifestyle",
        show_ai_help=True
    ),
    
    # Question 10: Primary Insurance Need
    Question(
        id="primary_need",
        question_text="What's your main reason for looking at insurance?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="save_money", label="Save money on existing coverage"),
            QuestionOption(value="fill_gaps", label="Fill gaps in current coverage"),
            QuestionOption(value="first_time", label="First-time buyer - need guidance"),
            QuestionOption(value="life_change", label="Life change (marriage, baby, new job)"),
            QuestionOption(value="compare_options", label="Just comparing what's available")
        ],
        required=True,
        help_text="This helps us focus on what matters most to you",
        category="essential",
        show_ai_help=True
    ),
    
    # Question 11: Monthly Budget (NEW - Specific amount)
    Question(
        id="monthly_premium_budget",
        question_text="What's your comfortable monthly budget for insurance premiums?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="under_50", label="Under $50/month"),
            QuestionOption(value="50_100", label="$50-100/month"),
            QuestionOption(value="100_150", label="$100-150/month"),
            QuestionOption(value="150_200", label="$150-200/month"),
            QuestionOption(value="200_300", label="$200-300/month"),
            QuestionOption(value="300_400", label="$300-400/month"),
            QuestionOption(value="400_500", label="$400-500/month"),
            QuestionOption(value="over_500", label="Over $500/month"),
            QuestionOption(value="flexible", label="Flexible - show me options")
        ],
        required=True,
        help_text="We'll prioritize plans within your budget",
        category="budget",
        show_ai_help=True
    ),
    
    # Question 12: Budget Range (kept for compatibility)
    Question(
        id="budget",
        question_text="Confirm your budget range for filtering:",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="under_100", label="Under $100/month"),
            QuestionOption(value="100_200", label="$100-200/month"),
            QuestionOption(value="200_400", label="$200-400/month"),
            QuestionOption(value="400_plus", label="$400+/month"),
            QuestionOption(value="show_all", label="Show me everything")
        ],
        required=True,
        help_text="We'll only show plans within your budget",
        category="budget",
        show_ai_help=True
    ),
    
    # Question 13: Coverage Priority
    Question(
        id="coverage_priority",
        question_text="What type of coverage is most important?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="health_medical", label="Health/Medical coverage"),
            QuestionOption(value="life_protection", label="Life insurance protection"),
            QuestionOption(value="critical_illness", label="Critical illness coverage"),
            QuestionOption(value="comprehensive_all", label="Comprehensive (all types)"),
            QuestionOption(value="unsure", label="Not sure - need recommendations")
        ],
        required=True,
        help_text="We'll prioritize plans that match your needs",
        category="essential",
        show_ai_help=True
    ),
    
    # Question 14: Desired Add-ons (NEW)
    Question(
        id="desired_add_ons",
        question_text="Which additional coverages interest you? (Select all that apply)",
        question_type=QuestionType.MCQ_MULTIPLE,
        options=[
            QuestionOption(value="none", label="Basic coverage only"),
            QuestionOption(value="dental", label="Dental coverage"),
            QuestionOption(value="vision", label="Vision/Eye care"),
            QuestionOption(value="mental_health", label="Mental health support"),
            QuestionOption(value="maternity", label="Maternity benefits"),
            QuestionOption(value="alternative", label="Alternative medicine (TCM, chiropractic)"),
            QuestionOption(value="outpatient", label="Outpatient specialist visits"),
            QuestionOption(value="wellness", label="Wellness programs/Preventive care")
        ],
        required=True,
        help_text="Additional coverages may increase premiums but provide more comprehensive protection",
        category="preferences",
        show_ai_help=True
    ),
    
    # Question 15: Timeline
    Question(
        id="timeline",
        question_text="When do you need coverage to start?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="immediately", label="Immediately (gap in coverage)"),
            QuestionOption(value="within_month", label="Within 30 days"),
            QuestionOption(value="within_3_months", label="Within 3 months"),
            QuestionOption(value="exploring", label="Just exploring options")
        ],
        required=True,
        help_text="Urgent needs get priority recommendations",
        category="essential",
        show_ai_help=False
    )
]

def should_show_question(question, responses):
    """Determine if a question should be shown based on previous responses"""
    # Skip budget confirmation if monthly budget was already specific
    if question.id == "budget" and "monthly_premium_budget" in responses:
        monthly_budget = responses["monthly_premium_budget"]
        if monthly_budget != "flexible":
            # Auto-fill budget based on monthly_premium_budget
            return False
    
    # Always show all other questions
    return True