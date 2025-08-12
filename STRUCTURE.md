# Codebase Structure

## 📁 Project Organization

The codebase is organized into 4 main folders for clear separation of concerns:

```
insuretech/
├── 📁 frontend/                # All frontend assets
│   ├── static/                 # Static files
│   │   ├── css/               # Stylesheets
│   │   ├── images/            # Images and icons
│   │   └── js/                # JavaScript files
│   └── templates/             # HTML templates
│       ├── login.html         # Authentication page
│       ├── dashboard.html     # User dashboard
│       ├── claims.html        # Claims management
│       └── questionnaire.html # Main questionnaire
│
├── 📁 backend/                 # Application backend
│   ├── questionnaire_server.py # Questionnaire API (port 8001)
│   ├── questions.py           # Question definitions
│   ├── agents/                # AI agents
│   │   ├── questionnaire_agent.py      # AI questionnaire helper
│   │   ├── response_parser_agent.py    # Response parser
│   │   ├── recommendation_agent.py     # Recommendations AI
│   │   ├── pdf_parser_agent.py        # PDF document parser
│   │   ├── scoring_agent.py           # Policy scoring
│   │   ├── policy_analyzer_agent.py   # Policy analysis
│   │   ├── needs_evaluation_agent.py  # Needs evaluation
│   │   └── option_selector_agent.py   # Option selection
│   └── shared/                # Shared utilities
│       ├── models.py          # Data models
│       └── premium_utils.py   # Premium calculations
│
├── 📁 database/                # Database layer
│   ├── database.py            # MongoDB models & connection
│   └── populate_db.py         # Database seeder
│
├── 📁 insurance_backend/       # Insurance API
│   └── insurance_backend_mongo.py  # Main insurance API (port 8000)
│
└── 📄 run_insurance_demo.py    # System launcher
```

## 🚀 Quick Start

```bash
# Run the complete system
python run_insurance_demo.py
```

This will:
1. Check and start MongoDB
2. Populate database with test data
3. Start Insurance Backend API on port 8000
4. Start Questionnaire Server on port 8001
5. Serve the web interface

## 🏗️ Architecture

### Frontend Layer
- **Templates**: HTML pages for UI (login, dashboard, claims, questionnaire)
- **Static Assets**: CSS, JavaScript, and images
- **JavaScript**: Main application logic in `app.js`

### Backend Layer
- **Questionnaire Server**: FastAPI server handling user sessions and questionnaire flow
- **AI Agents**: Intelligent processing using Ollama/LLaMA3
- **Shared Models**: Pydantic models for data validation

### Database Layer
- **MongoDB Models**: Insurance companies, products, policies, claims, users
- **Database Seeder**: Populates test data for development

### Insurance Backend Layer
- **API Server**: Core insurance operations (quotes, policies, claims)
- **Business Logic**: Risk assessment, pricing, policy management

## 📡 API Endpoints

### Questionnaire Server (Port 8001)
- `/` - Main questionnaire interface
- `/login` - User authentication
- `/dashboard` - User dashboard
- `/claims` - Claims management
- `/api/start-session` - Start questionnaire
- `/api/auth/*` - Authentication endpoints

### Insurance Backend (Port 8000)
- `/v1/quote` - Get insurance quotes
- `/v1/policy/purchase` - Purchase policy
- `/v1/user/{id}/policies` - Get user policies
- `/v1/claims/*` - Claims operations

## 🔧 Configuration

Environment variables in `.env`:
- `MONGODB_URL` - MongoDB connection (default: mongodb://localhost:27017)
- `DATABASE_NAME` - Database name (default: insurance_db)

## 🧪 Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run individual components
python -m uvicorn insurance_backend.insurance_backend_mongo:app --port 8000
python -m uvicorn backend.questionnaire_server:app --port 8001

# Populate database
python database/populate_db.py
```

## 🤖 AI Components

The system uses Ollama with LLaMA3 for:
- Natural language questionnaire assistance
- Insurance document parsing (PDFs)
- Personalized recommendations
- Policy analysis and scoring

Make sure Ollama is running:
```bash
ollama serve
ollama pull llama3:latest
```