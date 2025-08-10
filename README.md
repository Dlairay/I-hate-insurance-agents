# Insurance API Backend with MongoDB

## Setup

1. **Install MongoDB**
   ```bash
   # macOS
   brew install mongodb-community
   brew services start mongodb-community
   
   # Ubuntu/Debian
   sudo apt-get install mongodb
   sudo systemctl start mongodb
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Populate database with fake data**
   ```bash
   python populate_db.py
   ```

4. **Run the API server**
   ```bash
   # MongoDB-backed version with multi-company support
   uvicorn insurance_backend_mongo:app --reload
   
   # Or original simple version
   uvicorn insurance_api:app --reload
   ```

## API Endpoints

### Quote Generation
- `POST /v1/quote` - Get quotes from multiple insurance companies
  - Queries all companies if `company_id` not specified
  - Returns aggregated quotes with recommendations
  - Calculates risk scores based on applicant data

### Policy Management
- `POST /v1/policy` - Issue a new policy
- `GET /v1/policy/{policy_id}` - Retrieve policy details

### Claims
- `POST /v1/claim` - Submit a claim

### Discovery
- `GET /v1/companies` - List all insurance companies
- `GET /v1/products` - List available products

## Database Structure

The MongoDB database contains:
- **5 Insurance Companies**: HealthGuard, LifeCare, ShieldPro, AmeriCare, TrustLife
- **20+ Products**: Various health, life, and critical illness plans
- **100 Customers**: With realistic health profiles and risk scores
- **Quotes & Policies**: Historical data with payment records
- **Claims**: Sample claims with various statuses
- **Rate Tables**: Pricing factors for each company/product

## Key Features

1. **Multi-Company Quotes**: Aggregates quotes from multiple providers
2. **Risk Assessment**: Dynamic risk scoring based on health data
3. **Realistic Pricing**: Uses rate tables with age, BMI, and health factors
4. **Complete Workflow**: Quote → Policy → Claims processing

## Testing

```bash
# Get quotes from all companies
curl -X POST http://localhost:8000/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "HEALTH_BASIC",
    "applicant": {
      "first_name": "John",
      "last_name": "Doe",
      "dob": "1985-01-15",
      "gender": "M",
      "email": "john@example.com",
      "phone": "555-0100",
      "address_line1": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "smoker": false,
      "height_cm": 180,
      "weight_kg": 75
    },
    "coverage_amount": 500000,
    "deductible": 1000
  }'
```