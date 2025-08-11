"""
questionnaire/questions.py
==========================
MVP Insurance Questionnaire - Simplified to 8 essential questions
"""

from shared.models import Question, QuestionOption, QuestionType

# MVP Simplified Questionnaire - 8 Essential Questions
INSURANCE_QUESTIONS = [
    # Question 1: Basic Identity (Combined name/DOB/income for quick profile)
    Question(
        id="basic_info",
        question_text="Let's start with the basics - what's your age and annual income?",
        question_type=QuestionType.TEXT,
        required=True,
        help_text="Format: Age (e.g., 28) and Income (e.g., 75000). This helps calculate affordability.",
        category="essential"
    ),
    
    # Question 2: Existing Coverage (Critical for gap analysis)
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
        category="essential"
    ),
    
    # Question 3: Coverage Amount if Existing (For gap analysis)
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
        category="essential"
    ),
    
    # Question 4: Health Risk (Single most important factor)
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
        category="essential"
    ),
    
    # Question 5: Primary Insurance Need
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
        category="essential"
    ),
    
    # Question 6: Budget Range (Critical for recommendations)
    Question(
        id="budget",
        question_text="What's your monthly budget for insurance?",
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
        category="essential"
    ),
    
    # Question 7: Coverage Priority
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
        category="essential"
    ),
    
    # Question 8: Decision Timeline
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
        category="essential"
    )
]

def should_show_question(question, responses):
    """Determine if a question should be shown based on previous responses"""
    # Always show all questions for now - can add conditional logic later
    return True