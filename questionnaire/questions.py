"""
questionnaire/questions.py
==========================
Conversational insurance questionnaire for first-time buyers
"""

from shared.models import Question, QuestionOption, QuestionType

# Conversational Insurance Questionnaire for First-Time Buyers
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
        question_text="What's your email address?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),
    
    Question(
        id="personal_phone",
        question_text="And your phone number?",
        question_type=QuestionType.TEXT,
        required=True,
        category="personal"
    ),

    # Address
    Question(
        id="address_line1",
        question_text="What's your home address?",
        question_type=QuestionType.TEXT,
        required=True,
        category="address"
    ),
    
    Question(
        id="address_city",
        question_text="Which city?",
        question_type=QuestionType.TEXT,
        required=True,
        category="address"
    ),
    
    Question(
        id="address_state", 
        question_text="Which state?",
        question_type=QuestionType.TEXT,
        required=True,
        category="address"
    ),
    
    Question(
        id="address_postal_code",
        question_text="And your ZIP code?",
        question_type=QuestionType.TEXT,
        required=True,
        category="address"
    ),

    # Life Stage & Priorities - What first-time buyers understand
    Question(
        id="life_stage",
        question_text="What best describes your current life stage?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="young_single", label="Young adult, single, starting career"),
            QuestionOption(value="young_couple", label="Young couple, no kids yet"),
            QuestionOption(value="new_parents", label="New parents with young children"),
            QuestionOption(value="growing_family", label="Growing family with school-age kids"),
            QuestionOption(value="established_family", label="Established family with teens"),
            QuestionOption(value="empty_nesters", label="Kids are grown and independent"),
            QuestionOption(value="pre_retirement", label="Planning for retirement soon"),
            QuestionOption(value="other", label="Something else")
        ],
        required=True,
        help_text="This helps us understand what kind of protection you need most",
        category="lifestyle"
    ),

    Question(
        id="main_concern",
        question_text="What's your biggest worry if something happened to you?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="income_replacement", label="My family couldn't pay bills without my income"),
            QuestionOption(value="mortgage_debt", label="My family couldn't pay the mortgage or other debts"),
            QuestionOption(value="children_future", label="My kids' education and future would suffer"),
            QuestionOption(value="medical_bills", label="Medical bills would be overwhelming"),
            QuestionOption(value="burial_costs", label="Funeral and final expenses"),
            QuestionOption(value="business_protection", label="My business or employees would struggle"),
            QuestionOption(value="not_sure", label="I'm not sure what I should worry about")
        ],
        required=True,
        help_text="Understanding your priorities helps us recommend the right coverage",
        category="priorities"
    ),

    Question(
        id="financial_dependents",
        question_text="Who depends on your income?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="none", label="Just me - no one depends on my income"),
            QuestionOption(value="spouse", label="My spouse/partner"),
            QuestionOption(value="spouse_kids", label="My spouse and children"),
            QuestionOption(value="children_only", label="My children (single parent)"),
            QuestionOption(value="parents", label="My aging parents"),
            QuestionOption(value="extended", label="Extended family members"),
            QuestionOption(value="multiple", label="Several people depend on me")
        ],
        required=True,
        help_text="This is key to determining how much coverage you might need",
        category="priorities"
    ),

    Question(
        id="monthly_budget",
        question_text="What can you comfortably afford to spend monthly on insurance?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="25", label="Around $25/month - keeping it minimal"),
            QuestionOption(value="50", label="About $50/month - reasonable protection"),
            QuestionOption(value="100", label="Around $100/month - good coverage"),
            QuestionOption(value="200", label="About $200/month - comprehensive protection"),
            QuestionOption(value="flexible", label="I want to see options and decide"),
            QuestionOption(value="unsure", label="I honestly don't know what's reasonable")
        ],
        required=True,
        help_text="Be honest - there are good options at every budget level",
        category="budget"
    ),

    Question(
        id="health_overall",
        question_text="How would you describe your overall health?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="excellent", label="Excellent - I'm very healthy and active"),
            QuestionOption(value="good", label="Good - generally healthy with minor issues"),
            QuestionOption(value="fair", label="Fair - some health concerns but manageable"),
            QuestionOption(value="poor", label="Poor - significant health challenges"),
            QuestionOption(value="improving", label="Getting better - recovering from health issues")
        ],
        required=True,
        help_text="This affects your rates, but everyone can find coverage",
        category="health"
    ),

    Question(
        id="smoking_habits",
        question_text="Do you smoke or use tobacco?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="never", label="I've never been a smoker"),
            QuestionOption(value="quit", label="I quit smoking (over 12 months ago)"),
            QuestionOption(value="recent_quit", label="I recently quit (within the last year)"),
            QuestionOption(value="occasional", label="Only occasionally or socially"),
            QuestionOption(value="regular", label="I'm a regular smoker")
        ],
        required=True,
        help_text="Smoking significantly affects rates, but being honest helps us find the right fit",
        category="health"
    ),

    Question(
        id="health_conditions",
        question_text="Do you currently have any ongoing health conditions?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="none", label="No ongoing health issues"),
            QuestionOption(value="minor", label="Minor conditions (allergies, mild asthma, etc.)"),
            QuestionOption(value="managed", label="Well-controlled conditions (diabetes, high BP, etc.)"),
            QuestionOption(value="serious", label="More serious conditions"),
            QuestionOption(value="prefer_discuss", label="I'd prefer to discuss this privately")
        ],
        required=True,
        help_text="Even with health conditions, there are coverage options available",
        category="health"
    ),

    Question(
        id="lifestyle_risk",
        question_text="Any hobbies or activities that might be considered risky?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="low_risk", label="Pretty standard lifestyle - nothing risky"),
            QuestionOption(value="some_adventure", label="Some adventure sports occasionally"),
            QuestionOption(value="regular_risk", label="Regular risky hobbies (motorcycles, climbing, etc.)"),
            QuestionOption(value="high_risk", label="High-risk activities are a big part of my life"),
            QuestionOption(value="travel", label="I travel frequently to various countries")
        ],
        required=True,
        help_text="Just helps us understand what coverage might work best",
        category="lifestyle"
    ),

    Question(
        id="insurance_timeline",
        question_text="When are you looking to have coverage start?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="immediately", label="As soon as possible"),
            QuestionOption(value="month", label="Within the next month"),
            QuestionOption(value="few_months", label="In the next few months"),
            QuestionOption(value="planning", label="Just planning ahead for now"),
            QuestionOption(value="specific_date", label="By a specific date (wedding, baby, etc.)")
        ],
        required=True,
        help_text="This helps us prioritize your options",
        category="timeline"
    ),

    Question(
        id="insurance_knowledge",
        question_text="How familiar are you with life insurance?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="beginner", label="Complete beginner - this is all new to me"),
            QuestionOption(value="some_research", label="I've done some research online"),
            QuestionOption(value="basic_understanding", label="I understand the basics"),
            QuestionOption(value="experienced", label="I've had insurance before"),
            QuestionOption(value="very_knowledgeable", label="I know quite a bit about insurance")
        ],
        required=True,
        help_text="This helps us explain things at the right level for you",
        category="preferences"
    ),

    Question(
        id="decision_factors",
        question_text="What matters most to you in choosing insurance?",
        question_type=QuestionType.MCQ_SINGLE,
        options=[
            QuestionOption(value="lowest_cost", label="Lowest monthly cost - I need to keep it affordable"),
            QuestionOption(value="best_value", label="Best value - good balance of cost and coverage"),
            QuestionOption(value="most_coverage", label="Maximum coverage - cost is less important"),
            QuestionOption(value="company_reputation", label="Trusted company with good reputation"),
            QuestionOption(value="simple_process", label="Simple, easy process with quick approval"),
            QuestionOption(value="not_sure", label="I need help figuring out what should matter most")
        ],
        required=True,
        help_text="This helps us rank the options we show you",
        category="preferences"
    )
]

def should_show_question(question, responses):
    """Determine if a question should be shown based on previous responses"""
    # Always show all questions for now - can add conditional logic later
    return True