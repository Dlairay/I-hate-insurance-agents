# AI Insurance Broker System

An AI-powered insurance broker platform that automates the insurance shopping process with personalized recommendations, policy management, and claims processing.

## 🚀 Features

- **AI-Powered Questionnaire**: 3-phase intelligent questionnaire system
- **Multi-Company Quotes**: Get quotes from 5+ insurance companies
- **Smart Scoring System**: User-relative scoring based on affordability, claims ease, and coverage ratio
- **Policy Management**: Purchase and manage insurance policies
- **Claims Processing**: Submit and track insurance claims
- **Shopping Cart**: Add multiple policies to cart before checkout
- **User Dashboard**: View active policies and recent claims

## 📋 Prerequisites

- Python 3.8+
- MongoDB (local or cloud instance)
- Ollama (for AI features, optional)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd insuretech
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install and Start MongoDB
```bash
# macOS
brew install mongodb-community
brew services start mongodb-community

# Ubuntu/Debian
sudo apt-get install mongodb
sudo systemctl start mongodb

# Windows
# Download and install from https://www.mongodb.com/try/download/community
```

### 5. Install Ollama (Optional - for AI features)
```bash
# macOS
brew install ollama
ollama serve

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve

# Pull the required model
ollama pull llama3
```

## 🚦 Running the Application

### Option 1: Run Everything with One Command
```bash
python run_insurance_demo.py
```
This will:
- Check MongoDB connection
- Populate database with sample data
- Start both backend servers
- Open the application in your browser

### Option 2: Run Servers Individually

**Terminal 1 - Insurance Backend API (Port 8000):**
```bash
python -m uvicorn insurance_backend.insurance_backend_mongo:app --port 8000 --reload
```

**Terminal 2 - Questionnaire Server (Port 8001):**
```bash
python -m uvicorn backend.questionnaire_server:app --port 8001 --reload
```

Then open your browser to: `http://localhost:8001`

## 📁 Project Structure

```
insuretech/
├── backend/                     # Backend services
│   ├── questionnaire_server.py  # Main questionnaire server (Port 8001)
│   ├── questions.py             # Question definitions
│   ├── agents/                  # AI agents
│   │   ├── scoring_agent.py    # Policy scoring system
│   │   ├── response_parser_agent.py  # Response parsing
│   │   └── recommendation_agent.py   # AI recommendations
│   └── shared/
│       └── models.py            # Pydantic data models
│
├── insurance_backend/           # Insurance API backend
│   └── insurance_backend_mongo.py  # Main API server (Port 8000)
│
├── database/                    # Database utilities
│   ├── database.py             # MongoDB connection
│   └── populate_db.py          # Database seeder
│
├── frontend/                    # Frontend files
│   ├── templates/              # HTML pages
│   │   ├── index.html         # Landing page
│   │   ├── login.html         # Login/Signup
│   │   ├── questionnaire.html # Insurance questionnaire
│   │   ├── insurance_recommendations.html  # Recommendations
│   │   ├── checkout.html      # Cart checkout
│   │   ├── payment.html       # Payment processing
│   │   ├── dashboard.html     # User dashboard
│   │   ├── claims.html        # Claims submission
│   │   └── faq.html          # FAQ page
│   └── static/                # Static assets
│       ├── css/              # Stylesheets
│       ├── js/               # JavaScript files
│       └── images/           # Images and icons
│
├── requirements.txt            # Python dependencies
└── run_insurance_demo.py      # Main launcher script
```

## 🔧 Configuration

### MongoDB Connection
The system uses a local MongoDB instance by default. To use a different MongoDB URL:
1. Edit `database/database.py`
2. Update the `MONGO_URL` variable

### Port Configuration
- Insurance Backend API: Port 8000
- Questionnaire Server: Port 8001

To change ports, update the uvicorn commands accordingly.

## 💻 Usage

### 1. Sign Up / Login
- Navigate to `http://localhost:8001`
- Click "Get Insured!" or "Log In"
- Create a new account or login

### 2. Complete Questionnaire
- Answer the 3-phase questionnaire (25 questions)
- Get personalized insurance recommendations
- View scoring metrics for each plan

### 3. Purchase Policies
- Add policies to cart
- Proceed to checkout
- Complete payment (demo mode)
- View policies in dashboard

### 4. Submit Claims
- Go to Claims page
- Select your policy
- Enter claim amount
- Submit and track in dashboard

## 🧪 Test Accounts

The system works with any email/password combination in demo mode. Sample test account:
- Email: `test@example.com`
- Password: `password` (any password works in demo)

## 📝 API Documentation

### Insurance Backend (Port 8000)
- `POST /v1/register` - Register new user
- `POST /v1/quote` - Get insurance quotes
- `POST /v1/policy/purchase` - Purchase policy
- `GET /v1/user/{user_id}/policies` - Get user policies
- `POST /v1/claim` - Submit claim

### Questionnaire Server (Port 8001)
- `POST /api/start-session` - Start questionnaire
- `POST /api/session/{id}/answer` - Submit answer
- `GET /api/recommendations/{session_id}` - Get recommendations

## 🐛 Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
brew services list  # macOS
sudo systemctl status mongodb  # Linux

# Start MongoDB if not running
brew services start mongodb-community  # macOS
sudo systemctl start mongodb  # Linux
```

### Port Already in Use
```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
```

### Missing Dependencies
```bash
pip install fastapi uvicorn motor pydantic pymongo
```

### Ollama Not Working
The system works without Ollama. AI features will use fallback methods if Ollama is not available.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues or questions:
- Check the FAQ page in the application
- Open an issue on GitHub
- Contact the development team

## 🚀 Quick Start Commands

```bash
# Clone and setup
git clone <repository-url>
cd insuretech
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start MongoDB
brew services start mongodb-community  # macOS

# Run the application
python run_insurance_demo.py

# Access at http://localhost:8001
```

---

**Note**: This is a demo application. In production, ensure proper security measures including:
- Password hashing
- Secure API keys
- HTTPS configuration
- Production MongoDB setup
- Environment variables for sensitive data