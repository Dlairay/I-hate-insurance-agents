# AI Insurance Broker - Complete System

## Project Description
This is a fully operational AI-powered independent insurance broker that automates the complete insurance shopping process. The system works like a human insurance agent by collecting customer information through an intelligent conversational questionnaire, getting quotes from multiple insurance companies, and providing personalized AI-driven recommendations.

## Target Insurance Products
- Health Insurance (Basic and Premium plans)
- Critical Illness Insurance  
- Life Insurance (Term and Whole Life)
- Supplementary coverage (Disability, Accidental Death, etc.)

## System Architecture

### ✅ **Completed Components**

#### 1. **AI-Powered Conversational Questionnaire System** (Port 8001)
- **Conversational Questions**: 21 human-friendly questions designed for first-time insurance buyers
- **Two Questionnaire Flows**:
  - **Manual Flow**: 21 questions (personal info + address + insurance questions)
  - **JSON Upload Flow**: 11 questions (skips personal/address, auto-filled from uploaded profile)
- **QuestionnaireHelper**: Ollama/LLaMA3-based AI that helps users answer questions by interpreting natural language descriptions
- **Real-time AI Help**: Users can click "Need Help?" and describe their situation - AI provides suggestions and explanations
- **Smart Question Flow**: Questions like "What's your biggest worry?" instead of technical insurance terms
- **Intelligent Translation**: Converts user-friendly responses to technical insurance requirements
- **Progress Tracking**: Accurate progress bars that account for skipped questions
- **Session Management**: Proper handling of both manual and JSON upload sessions

#### 2. **Insurance Backend API** (Port 8000)
- **MongoDB Database**: 5 insurance companies with 16 different products
- **Quote Engine**: Aggregates quotes from multiple companies simultaneously
- **Risk Assessment**: Sophisticated scoring based on health, lifestyle, and demographics
- **Policy Management**: Complete policy lifecycle from quote to issuance
- **Claims Processing**: Submit and track insurance claims
- **100+ Sample Customers**: Realistic test data for development and testing

#### 3. **AI Response Parser**
- **ResponseParser**: Ollama/LLaMA3-based AI that converts raw insurance API responses into user-friendly cards
- **Standardized Cards**: Consistent format showing cost, coverage, benefits, and ratings
- **Value Scoring**: AI calculates value scores based on multiple factors
- **Smart Labeling**: Automatically assigns labels like "Best Value", "Fastest Approval", "Recommended"

#### 4. **AI Recommendation Engine**  
- **RecommendationEngine**: Ollama/LLaMA3-based AI that generates personalized recommendations
- **Profile Matching**: Analyzes user's age, health, budget, and priorities
- **Confidence Scoring**: Provides confidence scores for how well each plan matches user needs
- **Detailed Explanations**: Clear reasons why each plan is recommended with pros/cons
- **Smart Ranking**: Orders recommendations by best match to user profile

#### 5. **Interactive Web Frontend**
- **Responsive Design**: Bootstrap-based interface that works on all devices
- **Two-Path Entry**: Users can either start questionnaire manually or upload JSON profile
- **Real-time AI Help**: Integrated help system with AI suggestions throughout the questionnaire
- **Profile Upload**: Drag-and-drop JSON file upload with validation and progress feedback
- **Results Display**: Insurance cards with detailed information and AI recommendations
- **Debug Console**: Comprehensive logging for troubleshooting

## Complete File Structure & Architecture

```
insuretech/
├── run_insurance_demo.py           # Main launcher script for complete system
│
├── backend/                         # Insurance Backend API (Port 8000)
│   ├── insurance_backend_mongo.py  # Main API server with quote aggregation
│   ├── database.py                 # MongoDB connection and initialization
│   └── populate_db.py              # Database seeder with sample data
│
├── questionnaire/                   # Questionnaire Server (Port 8001)
│   ├── server.py                   # FastAPI server for questionnaire flow
│   ├── questions.py                # 21 conversational questions definition
│   └── questions_old.py            # [DEPRECATED] Original 28 technical questions
│
├── agents/                          # AI Agents (Ollama/LLaMA3 powered)
│   ├── questionnaire_agent.py      # AI helper for answering questions
│   ├── response_parser_agent.py    # Converts API responses to cards
│   └── recommendation_agent.py     # Generates personalized recommendations
│
├── frontend/                        # Web Interface
│   ├── templates/
│   │   └── questionnaire.html      # Main HTML template
│   └── static/
│       ├── css/
│       │   └── style.css           # Custom styling
│       └── js/
│           └── questionnaire.js    # Frontend logic and interactions
│
├── shared/                          # Shared Components
│   └── models.py                   # Pydantic models used across system
│
└── CLAUDE.md                       # This documentation
```

## Detailed File Roles & Relationships

### 🚀 **Entry Point**

#### `run_insurance_demo.py`
- **Role**: System launcher and orchestrator
- **Functions**:
  - Checks if Ollama is running (for AI agents)
  - Verifies MongoDB is running
  - Populates database if empty (calls `backend/populate_db.py`)
  - Starts backend API server (port 8000)
  - Starts questionnaire server (port 8001)
  - Manages graceful shutdown
- **Dependencies**: All backend and questionnaire modules
- **Used by**: User to start the complete system

### 📊 **Backend API Layer (Port 8000)**

#### `backend/insurance_backend_mongo.py`
- **Role**: Main insurance API server
- **Functions**:
  - `/v1/quote` - Receives insurance requests, calculates quotes from multiple companies
  - `/v1/policy` - Creates and manages policies
  - `/v1/claim` - Handles insurance claims
  - Risk assessment and pricing calculation
  - Quote aggregation from 5 insurance companies
- **Dependencies**: 
  - `backend/database.py` - MongoDB connection
  - `shared/models.py` - Data models (InsuranceRequest, Quote, Policy)
- **Used by**: `questionnaire/server.py` (calls `/v1/quote` after questionnaire completion)

#### `backend/database.py`
- **Role**: MongoDB connection manager
- **Functions**:
  - Initializes MongoDB client
  - Creates database and collections
  - Provides database instance to other modules
- **Used by**: 
  - `backend/insurance_backend_mongo.py` - For all database operations
  - `backend/populate_db.py` - For seeding data

#### `backend/populate_db.py`
- **Role**: Database seeder
- **Functions**:
  - Creates 5 insurance companies
  - Creates 16 insurance products
  - Generates 100+ sample customers
  - Creates sample quotes, policies, and claims
- **Dependencies**: `backend/database.py`, `shared/models.py`
- **Used by**: `run_insurance_demo.py` (on first run)

### 📝 **Questionnaire Layer (Port 8001)**

#### `questionnaire/server.py`
- **Role**: Questionnaire API server and flow controller
- **Key Functions**:
  - `start_session()` - Begins manual questionnaire (21 questions)
  - `start_session_with_profile()` - Begins with JSON upload (11 questions)
  - `submit_answer()` - Processes answers and manages flow
  - `get_question_help()` - Provides AI assistance
  - `process_completed_questionnaire()` - Sends to backend for quotes
  - `calculate_progress()` - Handles dual-flow progress tracking
  - `determine_coverage_amount()` - Converts life situations to coverage
  - `convert_responses_to_applicant()` - Translates conversational to technical
- **Dependencies**:
  - `questionnaire/questions.py` - Question definitions
  - `agents/questionnaire_agent.py` - AI help (lazy loaded)
  - `agents/response_parser_agent.py` - Parse insurance responses (lazy loaded)
  - `agents/recommendation_agent.py` - Generate recommendations (lazy loaded)
  - `shared/models.py` - Data models
  - `frontend/templates/questionnaire.html` - Serves UI
- **Used by**: Frontend JavaScript via API calls
- **Calls**: `backend/insurance_backend_mongo.py` (`/v1/quote` endpoint)

#### `questionnaire/questions.py`
- **Role**: Defines 21 conversational questions
- **Structure**:
  - 6 Personal questions (name, DOB, gender, email, phone)
  - 4 Address questions
  - 11 Insurance questions (lifestyle, health, priorities, budget)
- **Question Types**: TEXT, MCQ_SINGLE, MCQ_MULTIPLE, DATE, NUMBER
- **Used by**: `questionnaire/server.py` (INSURANCE_QUESTIONS array)

### 🤖 **AI Agent Layer**

#### `agents/questionnaire_agent.py`
- **Role**: AI helper for questionnaire assistance
- **Key Components**:
  - `QuestionnaireHelper` class - Main wrapper
  - `QuestionnaireHelperAgent` - Async agent implementation
  - Uses Google ADK with Ollama/LLaMA3
- **Functions**:
  - `help_select_answer()` - Interprets user description, suggests answer
  - `explain_answer_choice()` - Explains why answer was chosen
  - `_fallback_selection()` - Rule-based backup when AI unavailable
- **Used by**: `questionnaire/server.py` (via lazy loading in `get_questionnaire_helper()`)

#### `agents/response_parser_agent.py`
- **Role**: Converts raw insurance API responses to user-friendly cards
- **Functions**:
  - `parse_insurance_response()` - Main parsing function
  - Creates standardized insurance cards
  - Calculates value scores
  - Assigns labels (Best Value, Recommended, etc.)
- **Used by**: `questionnaire/server.py` (in `process_completed_questionnaire()`)

#### `agents/recommendation_agent.py`
- **Role**: Generates personalized recommendations
- **Functions**:
  - `generate_recommendations()` - Creates ranked recommendations
  - Analyzes user profile and preferences
  - Provides confidence scores
  - Generates pros/cons for each plan
- **Used by**: `questionnaire/server.py` (in `process_completed_questionnaire()`)

### 🎨 **Frontend Layer**

#### `frontend/templates/questionnaire.html`
- **Role**: Main UI template
- **Features**:
  - Welcome screen with dual entry (manual vs JSON upload)
  - Question display with multiple input types
  - Progress bar
  - Help section with AI integration
  - Results display with insurance cards
- **Used by**: `questionnaire/server.py` (served at root `/`)

#### `frontend/static/js/questionnaire.js`
- **Role**: Frontend interaction logic
- **Key Classes/Functions**:
  - `QuestionnaireApp` - Main application class
  - `startQuestionnaire()` - Begins manual flow
  - `handleProfileUpload()` - Handles JSON file upload
  - `displayQuestion()` - Renders questions based on type
  - `getAIHelp()` - Requests AI assistance
  - `showAISuggestion()` - Displays AI help
  - `submitAnswer()` - Sends answers to backend
  - `showResults()` - Displays insurance quotes
- **API Calls**:
  - `POST /api/start-session` - Start manual questionnaire
  - `POST /api/start-session-with-profile` - Start with JSON
  - `POST /api/session/{id}/answer` - Submit answers
  - `POST /api/session/{id}/get-help` - Get AI help
- **Used by**: Browser (loaded by questionnaire.html)

#### `frontend/static/css/style.css`
- **Role**: Custom styling for the application
- **Features**:
  - Card designs for insurance quotes
  - Progress bar styling
  - Responsive design adjustments
  - Help section styling
- **Used by**: `frontend/templates/questionnaire.html`

### 📦 **Shared Components**

#### `shared/models.py`
- **Role**: Central data model definitions (Pydantic)
- **Key Models**:
  - `Question`, `QuestionOption` - Question structure
  - `QuestionnaireSession`, `QuestionnaireResponse` - Session management
  - `ApplicantProfile` - User information
  - `InsuranceRequest` - Request to insurance companies
  - `Quote`, `Policy`, `Claim` - Insurance entities
  - `InsuranceCard`, `Recommendation` - Display models
- **Used by**: ALL Python modules for type safety and validation

## Data Flow Sequence

### Manual Questionnaire Flow
```
1. User → Browser → questionnaire.js → POST /api/start-session
2. server.py → Creates session → Returns first question
3. User answers → questionnaire.js → POST /api/session/{id}/answer
4. server.py → Stores answer → Returns next question
5. [Optional] User needs help → POST /api/session/{id}/get-help
6. server.py → questionnaire_agent.py → Returns AI suggestion
7. After 21 questions → server.py → process_completed_questionnaire()
8. server.py → POST backend:8000/v1/quote → Gets raw quotes
9. server.py → response_parser_agent.py → Standardized cards
10. server.py → recommendation_agent.py → Personalized recommendations
11. Results → questionnaire.js → Display cards and recommendations
```

### JSON Upload Flow
```
1. User uploads JSON → questionnaire.js → handleProfileUpload()
2. questionnaire.js → POST /api/start-session-with-profile
3. server.py → Pre-fills 10 personal/address answers
4. server.py → Skips to question 11 (lifestyle questions)
5. [Continue from step 3 of manual flow, but only 11 questions]
```

## API Communication Map

```
Frontend (8001)                    Questionnaire Server (8001)
     │                                      │
     ├─[REST API]──────────────────────────┤
     │                                      │
     │                                      ├─[AI Agents]
     │                                      │  ├─ questionnaire_agent.py
     │                                      │  ├─ response_parser_agent.py
     │                                      │  └─ recommendation_agent.py
     │                                      │
     │                                      └─[HTTP]──> Backend API (8000)
     │                                                          │
     └─[Static Files]                                          └─[MongoDB]
        ├─ questionnaire.html
        ├─ questionnaire.js
        └─ style.css
```

## Module Dependencies

### Import Hierarchy
```
run_insurance_demo.py
├── backend/populate_db.py
│   ├── backend/database.py
│   └── shared/models.py
│
├── backend/insurance_backend_mongo.py
│   ├── backend/database.py
│   └── shared/models.py
│
└── questionnaire/server.py
    ├── questionnaire/questions.py
    │   └── shared/models.py
    ├── agents/questionnaire_agent.py
    │   └── shared/models.py
    ├── agents/response_parser_agent.py
    │   └── shared/models.py
    └── agents/recommendation_agent.py
        └── shared/models.py
```

## Key Integration Points

### 1. **Questionnaire → Backend API**
- **When**: After questionnaire completion
- **Endpoint**: `POST http://localhost:8000/v1/quote`
- **Data**: `InsuranceRequest` object with applicant profile and requirements
- **Response**: Raw quotes from multiple insurance companies

### 2. **Server → AI Agents**
- **Lazy Loading**: Agents initialized only when needed
- **Functions**: `get_questionnaire_helper()`, `get_response_parser()`, `get_recommendation_engine()`
- **Purpose**: Avoid startup delays from Ollama initialization

### 3. **Frontend → Questionnaire Server**
- **REST API**: All communication via JSON
- **Session-based**: Each user gets unique session ID
- **Real-time**: Immediate responses for help requests

### 4. **Database Integration**
- **MongoDB**: Central data store
- **Collections**: companies, products, customers, quotes, policies, claims
- **Seeding**: Automatic population on first run

## Testing & Development

### Running Individual Components
```bash
# Backend only
python -m uvicorn backend.insurance_backend_mongo:app --port 8000 --reload

# Questionnaire only  
python -m uvicorn questionnaire.server:app --port 8001 --reload

# Populate database
python backend/populate_db.py

# Test AI agents
python -c "from agents.questionnaire_agent import QuestionnaireHelper; print('AI ready')"
```

### Key Files for Modifications
- **Add new questions**: `questionnaire/questions.py`
- **Change UI**: `frontend/templates/questionnaire.html` and `frontend/static/js/questionnaire.js`
- **Modify AI behavior**: `agents/questionnaire_agent.py`
- **Add insurance companies**: `backend/populate_db.py`
- **Change quote logic**: `backend/insurance_backend_mongo.py`

## Success Metrics & Performance
- **Questionnaire Completion**: < 5 minutes with JSON upload, < 10 minutes manual
- **AI Help Response**: < 3 seconds with Ollama, instant with fallback
- **Quote Generation**: Multiple providers in < 30 seconds
- **System Reliability**: 100% uptime with proper error handling
- **User Experience**: Intuitive interface with real-time assistance

## Recent Fixes Applied
- ✅ Fixed JavaScript syntax errors in questionnaire.js
- ✅ Resolved Google ADK type annotation conflicts  
- ✅ Fixed Question model vs dictionary conversion issues
- ✅ Implemented proper JSON upload flow with question skipping
- ✅ Corrected progress calculation for both questionnaire flows
- ✅ Added comprehensive debug logging throughout system

## Future Enhancements
- Real-time chat support during questionnaire
- Advanced document upload with OCR
- Integration with health tracking devices
- Automated renewal optimization
- Claims assistance workflow
- Family/group policy management
- Mobile app development