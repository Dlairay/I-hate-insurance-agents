"""
questionnaire/questions.py
==========================
Conversational insurance questionnaire - like talking to a human agent
"""

from shared.models import Question, QuestionOption, QuestionType

# Conversational Insurance Questionnaire
INSURANCE_QUESTIONS = [
    # Personal Information (can be skipped with JSON upload)
    Question(
        id="personal_first_name",
        question_text="What's your first name?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="personal_last_name", 
        question_text="And your last name?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="personal_dob",
        question_text="When were you born?",
        question_type=QuestionType.DATE,
        required=True,
        help_text="This helps us find age-appropriate coverage options",
        category="personal"
    ),
    
    Question(
        id="personal_gender",
        question_text="Gender (for insurance rates)?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="M", label="Male"),
            QuestionOption(value="F", label="Female"),
            QuestionOption(value="OTHER", label="Prefer not to say")
        ],
        required=True,
        category="personal"
    ),
    
    Question(
        id="personal_email",
        question_text="What is your email address?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="personal_phone",
        question_text="What is your phone number?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    # Address Information
    Question(
        id="address_line1",
        question_text="What is your street address?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="address_city",
        question_text="What city do you live in?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="address_state",
        question_text="Which state do you live in?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="CA", label="California"),
            QuestionOption(value="NY", label="New York"),
            QuestionOption(value="TX", label="Texas"),
            QuestionOption(value="FL", label="Florida"),
            QuestionOption(value="IL", label="Illinois"),
            QuestionOption(value="PA", label="Pennsylvania"),
            QuestionOption(value="OH", label="Ohio"),
            QuestionOption(value="GA", label="Georgia"),
            QuestionOption(value="NC", label="North Carolina"),
            QuestionOption(value="MI", label="Michigan"),
            # Add more states as needed
        ],
        required=True,
        category="personal"
    ),
    
    Question(
        id="address_postal_code",
        question_text="What is your ZIP/postal code?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    # Health Information
    Question(
        id="health_smoker",
        question_text="Do you currently smoke or use tobacco products?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="false", label="No, I don't smoke"),
            QuestionOption(value="true", label="Yes, I smoke cigarettes"),
            QuestionOption(value="true", label="Yes, I use other tobacco products"),
            QuestionOption(value="former", label="I'm a former smoker (quit over 12 months ago)")
        ],
        required=True,
        help_text="This affects insurance rates as smoking increases health risks",
        category="health"
    ),
    
    Question(
        id="health_height",
        question_text="What is your height?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="152", label="5'0\" (152 cm)"),
            QuestionOption(value="155", label="5'1\" (155 cm)"),
            QuestionOption(value="157", label="5'2\" (157 cm)"),
            QuestionOption(value="160", label="5'3\" (160 cm)"),
            QuestionOption(value="163", label="5'4\" (163 cm)"),
            QuestionOption(value="165", label="5'5\" (165 cm)"),
            QuestionOption(value="168", label="5'6\" (168 cm)"),
            QuestionOption(value="170", label="5'7\" (170 cm)"),
            QuestionOption(value="173", label="5'8\" (173 cm)"),
            QuestionOption(value="175", label="5'9\" (175 cm)"),
            QuestionOption(value="178", label="5'10\" (178 cm)"),
            QuestionOption(value="180", label="5'11\" (180 cm)"),
            QuestionOption(value="183", label="6'0\" (183 cm)"),
            QuestionOption(value="185", label="6'1\" (185 cm)"),
            QuestionOption(value="188", label="6'2\" (188 cm)"),
            QuestionOption(value="191", label="6'3\" (191 cm)"),
            QuestionOption(value="193", label="6'4\" (193 cm)"),
            QuestionOption(value="196", label="6'5\" (196 cm)"),
            QuestionOption(value="custom", label="Other (please specify in help)")
        ],
        required=True,
        help_text="Height is used to calculate BMI for health assessment",
        category="health"
    ),
    
    Question(
        id="health_weight",
        question_text="What is your approximate weight?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="45", label="Under 100 lbs (45 kg)"),
            QuestionOption(value="50", label="100-110 lbs (45-50 kg)"),
            QuestionOption(value="55", label="110-120 lbs (50-55 kg)"),
            QuestionOption(value="60", label="120-135 lbs (55-60 kg)"),
            QuestionOption(value="65", label="135-145 lbs (60-65 kg)"),
            QuestionOption(value="70", label="145-155 lbs (65-70 kg)"),
            QuestionOption(value="75", label="155-165 lbs (70-75 kg)"),
            QuestionOption(value="80", label="165-175 lbs (75-80 kg)"),
            QuestionOption(value="85", label="175-190 lbs (80-85 kg)"),
            QuestionOption(value="90", label="190-200 lbs (85-90 kg)"),
            QuestionOption(value="95", label="200-210 lbs (90-95 kg)"),
            QuestionOption(value="100", label="210-220 lbs (95-100 kg)"),
            QuestionOption(value="110", label="220-240 lbs (100-110 kg)"),
            QuestionOption(value="120", label="240-265 lbs (110-120 kg)"),
            QuestionOption(value="130", label="Over 265 lbs (120+ kg)")
        ],
        required=True,
        help_text="Weight ranges help us calculate your BMI for health assessment",
        category="health"
    ),
    
    Question(
        id="health_conditions",
        question_text="Do you have any of the following medical conditions?",
        question_type=QuestionType.MCQ_MULTIPLE,
        options=[
            QuestionOption(value="none", label="None of the above"),
            QuestionOption(value="diabetes", label="Diabetes (Type 1 or 2)"),
            QuestionOption(value="hypertension", label="High blood pressure"),
            QuestionOption(value="heart_disease", label="Heart disease or heart attack"),
            QuestionOption(value="cancer", label="Cancer (any type)"),
            QuestionOption(value="asthma", label="Asthma"),
            QuestionOption(value="depression", label="Depression or anxiety"),
            QuestionOption(value="thyroid", label="Thyroid disorders"),
            QuestionOption(value="arthritis", label="Arthritis"),
            QuestionOption(value="kidney", label="Kidney disease"),
            QuestionOption(value="liver", label="Liver disease"),
            QuestionOption(value="other", label="Other condition (please describe in help)")
        ],
        required=True,
        help_text="Pre-existing conditions affect coverage and rates",
        category="health"
    ),
    
    Question(
        id="health_medications",
        question_text="Are you currently taking any prescription medications?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="none", label="No medications"),
            QuestionOption(value="1-2", label="1-2 medications"),
            QuestionOption(value="3-4", label="3-4 medications"),
            QuestionOption(value="5+", label="5 or more medications"),
            QuestionOption(value="describe", label="I need help describing my medications")
        ],
        required=True,
        help_text="Medications can indicate underlying health conditions",
        category="health"
    ),
    
    Question(
        id="health_hospitalizations",
        question_text="How many times have you been hospitalized in the past 5 years?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="0", label="Never"),
            QuestionOption(value="1", label="Once"),
            QuestionOption(value="2", label="Twice"),
            QuestionOption(value="3", label="3 times"),
            QuestionOption(value="4+", label="4 or more times")
        ],
        required=True,
        help_text="Recent hospitalizations indicate current health status",
        category="health"
    ),
    
    Question(
        id="health_family_history",
        question_text="Do you have a family history of any serious medical conditions?",
        question_type=QuestionType.MCQ_MULTIPLE,
        options=[
            QuestionOption(value="none", label="No significant family history"),
            QuestionOption(value="heart_disease", label="Heart disease"),
            QuestionOption(value="cancer", label="Cancer"),
            QuestionOption(value="diabetes", label="Diabetes"),
            QuestionOption(value="stroke", label="Stroke"),
            QuestionOption(value="alzheimers", label="Alzheimer's disease"),
            QuestionOption(value="mental_health", label="Mental health conditions"),
            QuestionOption(value="kidney", label="Kidney disease"),
            QuestionOption(value="unknown", label="I don't know my family history")
        ],
        required=True,
        help_text="Family history can indicate genetic predisposition to conditions",
        category="health"
    ),
    
    # Lifestyle Information
    Question(
        id="lifestyle_occupation",
        question_text="What is your occupation?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="office_worker", label="Office/desk worker"),
            QuestionOption(value="teacher", label="Teacher/educator"),
            QuestionOption(value="healthcare", label="Healthcare worker"),
            QuestionOption(value="retail", label="Retail/customer service"),
            QuestionOption(value="engineer", label="Engineer/technical"),
            QuestionOption(value="manager", label="Manager/executive"),
            QuestionOption(value="sales", label="Sales professional"),
            QuestionOption(value="construction", label="Construction worker"),
            QuestionOption(value="driver", label="Driver/transportation"),
            QuestionOption(value="artist", label="Artist/creative"),
            QuestionOption(value="student", label="Student"),
            QuestionOption(value="retired", label="Retired"),
            QuestionOption(value="unemployed", label="Currently unemployed"),
            QuestionOption(value="other", label="Other (please describe in help)")
        ],
        required=True,
        help_text="Occupation affects risk assessment for insurance",
        category="lifestyle"
    ),
    
    Question(
        id="lifestyle_income",
        question_text="What is your approximate annual household income?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="25000", label="Under $25,000"),
            QuestionOption(value="40000", label="$25,000 - $40,000"),
            QuestionOption(value="60000", label="$40,000 - $60,000"),
            QuestionOption(value="80000", label="$60,000 - $80,000"),
            QuestionOption(value="100000", label="$80,000 - $100,000"),
            QuestionOption(value="150000", label="$100,000 - $150,000"),
            QuestionOption(value="200000", label="$150,000 - $200,000"),
            QuestionOption(value="250000", label="$200,000 - $250,000"),
            QuestionOption(value="300000", label="Over $250,000"),
            QuestionOption(value="prefer_not_to_say", label="Prefer not to say")
        ],
        required=False,
        help_text="Income helps determine appropriate coverage amounts",
        category="financial"
    ),
    
    Question(
        id="lifestyle_exercise",
        question_text="How often do you exercise or engage in physical activity?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="daily", label="Daily or almost daily"),
            QuestionOption(value="several_times_week", label="Several times per week"),
            QuestionOption(value="weekly", label="About once a week"),
            QuestionOption(value="monthly", label="A few times per month"),
            QuestionOption(value="rarely", label="Rarely or never")
        ],
        required=True,
        help_text="Exercise frequency indicates overall health and lifestyle",
        category="lifestyle"
    ),
    
    Question(
        id="lifestyle_alcohol",
        question_text="How often do you consume alcohol?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="never", label="I don't drink alcohol"),
            QuestionOption(value="social", label="Socially/occasionally (1-2 drinks per week)"),
            QuestionOption(value="moderate", label="Moderate (3-7 drinks per week)"),
            QuestionOption(value="frequent", label="Frequent (8-14 drinks per week)"),
            QuestionOption(value="heavy", label="More than 14 drinks per week"),
            QuestionOption(value="recovering", label="I'm in recovery from alcohol")
        ],
        required=True,
        help_text="Alcohol consumption affects health risk assessment",
        category="lifestyle"
    ),
    
    # Product-specific questions
    Question(
        id="product_type",
        question_text="What type of insurance are you looking for?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="HEALTH_BASIC", label="Basic Health Insurance", 
                         description="Essential health coverage for medical expenses"),
            QuestionOption(value="HEALTH_PREMIUM", label="Premium Health Insurance",
                         description="Comprehensive health coverage with enhanced benefits"),
            QuestionOption(value="LIFE_TERM", label="Term Life Insurance",
                         description="Temporary life coverage for a specific period"),
            QuestionOption(value="LIFE_WHOLE", label="Whole Life Insurance",
                         description="Permanent life coverage with cash value"),
            QuestionOption(value="CRITICAL_ILLNESS", label="Critical Illness Insurance",
                         description="Lump sum payment if diagnosed with serious illness")
        ],
        required=True,
        help_text="Different insurance types have different requirements and benefits",
        category="product"
    ),
    
    Question(
        id="product_coverage_amount",
        question_text="How much coverage do you need?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="100000", label="$100,000"),
            QuestionOption(value="250000", label="$250,000"),
            QuestionOption(value="500000", label="$500,000"),
            QuestionOption(value="750000", label="$750,000"),
            QuestionOption(value="1000000", label="$1,000,000"),
            QuestionOption(value="1500000", label="$1,500,000"),
            QuestionOption(value="2000000", label="$2,000,000"),
            QuestionOption(value="custom", label="Other amount (please specify in help)")
        ],
        required=True,
        help_text="Coverage amount should reflect your financial needs and obligations",
        category="product"
    ),
    
    Question(
        id="product_deductible",
        question_text="What deductible would you prefer? (For health insurance)",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="500", label="$500 (higher premium, lower out-of-pocket)"),
            QuestionOption(value="1000", label="$1,000 (balanced option)"),
            QuestionOption(value="2500", label="$2,500 (lower premium, higher out-of-pocket)"),
            QuestionOption(value="5000", label="$5,000 (lowest premium)"),
            QuestionOption(value="unsure", label="I'm not sure what's best for me")
        ],
        required=False,
        depends_on={"product_type": ["HEALTH_BASIC", "HEALTH_PREMIUM"]},
        help_text="Deductible is what you pay before insurance coverage kicks in",
        category="product"
    ),
    
    Question(
        id="product_term_years",
        question_text="For how many years do you want term life coverage?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="10", label="10 years"),
            QuestionOption(value="15", label="15 years"),
            QuestionOption(value="20", label="20 years"),
            QuestionOption(value="25", label="25 years"),
            QuestionOption(value="30", label="30 years"),
            QuestionOption(value="unsure", label="I'm not sure what's appropriate")
        ],
        required=False,
        depends_on={"product_type": ["LIFE_TERM"]},
        help_text="Term length should cover your financial obligations period",
        category="product"
    ),
    
    # Preferences and priorities
    Question(
        id="preferences_budget",
        question_text="What's your monthly budget for insurance premiums?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="50", label="Under $50/month"),
            QuestionOption(value="100", label="$50-100/month"),
            QuestionOption(value="200", label="$100-200/month"),
            QuestionOption(value="300", label="$200-300/month"),
            QuestionOption(value="500", label="$300-500/month"),
            QuestionOption(value="500+", label="Over $500/month"),
            QuestionOption(value="flexible", label="I'm flexible on budget")
        ],
        required=True,
        help_text="Budget helps us recommend appropriate plans",
        category="preferences"
    ),
    
    Question(
        id="preferences_priority",
        question_text="What's most important to you in choosing insurance?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="lowest_cost", label="Lowest monthly cost"),
            QuestionOption(value="best_coverage", label="Most comprehensive coverage"),
            QuestionOption(value="company_reputation", label="Insurance company reputation"),
            QuestionOption(value="fast_approval", label="Quick approval process"),
            QuestionOption(value="low_deductible", label="Low deductible/out-of-pocket costs"),
            QuestionOption(value="flexible_payments", label="Flexible payment options")
        ],
        required=True,
        help_text="Your priorities help us rank the best options for you",
        category="preferences"
    ),
    
    Question(
        id="preferences_approval_speed",
        question_text="How quickly do you need insurance coverage?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="immediate", label="Immediately (instant approval preferred)"),
            QuestionOption(value="week", label="Within a week"),
            QuestionOption(value="month", label="Within a month"),
            QuestionOption(value="flexible", label="I can wait for the best deal")
        ],
        required=True,
        help_text="Timeline affects which insurance options are suitable",
        category="preferences"
    )
]

# Helper function to get questions by category
def get_questions_by_category(category: str) -> list[Question]:
    """Get all questions for a specific category"""
    return [q for q in INSURANCE_QUESTIONS if q.category == category]

# Helper function to check if question should be shown based on dependencies
def should_show_question(question: Question, responses: dict) -> bool:
    """Check if a question should be shown based on previous responses"""
    if not question.depends_on:
        return True
    
    for response_id, required_values in question.depends_on.items():
        user_response = responses.get(response_id)
        if not user_response or user_response not in required_values:
            return False
    
    return True