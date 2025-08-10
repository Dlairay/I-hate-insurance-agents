"""
populate_db.py
==============
Script to populate MongoDB with fake insurance data for testing
"""

from faker import Faker
from datetime import datetime, timedelta, timezone
import random
import uuid
from typing import List, Dict, Any
from database import (
    sync_db, Collections,
    InsuranceCompany, InsuranceProduct, CustomerProfile,
    Quote, Policy, Claim, RateTable
)

fake = Faker()
Faker.seed(42)  # For reproducible fake data


def clear_database():
    """Clear all collections"""
    print("Clearing existing data...")
    collections = [
        Collections.COMPANIES,
        Collections.PRODUCTS,
        Collections.QUOTES,
        Collections.POLICIES,
        Collections.CLAIMS,
        Collections.CUSTOMERS,
        Collections.RATE_TABLES
    ]
    for collection in collections:
        sync_db[collection].delete_many({})
    print("Database cleared.")


def create_insurance_companies() -> List[Dict[str, Any]]:
    """Create fake insurance companies"""
    print("Creating insurance companies...")
    
    companies = [
        {
            "company_id": "HEALTHGUARD",
            "name": "HealthGuard Insurance Co.",
            "type": "health",
            "rating": 4.5,
            "established_year": 1985,
            "states_available": ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"],
            "products_offered": ["HEALTH_BASIC", "HEALTH_PREMIUM", "CRITICAL_ILLNESS"],
            "api_endpoint": "https://api.healthguard.com/v1",
            "api_key": "HG_" + uuid.uuid4().hex[:16],
            "risk_appetite": "moderate",
            "max_coverage_limits": {
                "HEALTH_BASIC": 1000000,
                "HEALTH_PREMIUM": 5000000,
                "CRITICAL_ILLNESS": 500000
            },
            "underwriting_turnaround_days": 2,
            "contact_email": "quotes@healthguard.com",
            "contact_phone": "1-800-HEALTH1",
            "website": "www.healthguard.com"
        },
        {
            "company_id": "LIFECARE",
            "name": "LifeCare Mutual",
            "type": "life",
            "rating": 4.7,
            "established_year": 1920,
            "states_available": ["CA", "NY", "TX", "FL", "IL", "WA", "MA", "VA", "AZ", "CO"],
            "products_offered": ["LIFE_TERM", "LIFE_WHOLE", "CRITICAL_ILLNESS"],
            "api_endpoint": "https://api.lifecare.com/v1",
            "api_key": "LC_" + uuid.uuid4().hex[:16],
            "risk_appetite": "conservative",
            "max_coverage_limits": {
                "LIFE_TERM": 10000000,
                "LIFE_WHOLE": 5000000,
                "CRITICAL_ILLNESS": 1000000
            },
            "underwriting_turnaround_days": 5,
            "contact_email": "newbusiness@lifecare.com",
            "contact_phone": "1-800-LIFE123",
            "website": "www.lifecare.com"
        },
        {
            "company_id": "SHIELDPRO",
            "name": "ShieldPro Insurance Group",
            "type": "multi-line",
            "rating": 4.3,
            "established_year": 1998,
            "states_available": ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"],
            "products_offered": ["HEALTH_BASIC", "HEALTH_PREMIUM", "LIFE_TERM", "CRITICAL_ILLNESS"],
            "api_endpoint": "https://api.shieldpro.com/v1",
            "api_key": "SP_" + uuid.uuid4().hex[:16],
            "risk_appetite": "aggressive",
            "max_coverage_limits": {
                "HEALTH_BASIC": 750000,
                "HEALTH_PREMIUM": 3000000,
                "LIFE_TERM": 5000000,
                "CRITICAL_ILLNESS": 750000
            },
            "underwriting_turnaround_days": 1,
            "contact_email": "quick-quote@shieldpro.com",
            "contact_phone": "1-888-SHIELD1",
            "website": "www.shieldpro.com"
        },
        {
            "company_id": "AMERICARE",
            "name": "AmeriCare National",
            "type": "health",
            "rating": 4.6,
            "established_year": 1975,
            "states_available": ["NY", "CA", "TX", "FL", "PA", "NJ", "MA", "CT", "MD", "VA"],
            "products_offered": ["HEALTH_BASIC", "HEALTH_PREMIUM", "CRITICAL_ILLNESS"],
            "api_endpoint": "https://api.americare.com/v1",
            "api_key": "AC_" + uuid.uuid4().hex[:16],
            "risk_appetite": "moderate",
            "max_coverage_limits": {
                "HEALTH_BASIC": 1500000,
                "HEALTH_PREMIUM": 7500000,
                "CRITICAL_ILLNESS": 1000000
            },
            "underwriting_turnaround_days": 3,
            "contact_email": "brokers@americare.com",
            "contact_phone": "1-800-AMCARE1",
            "website": "www.americare.com"
        },
        {
            "company_id": "TRUSTLIFE",
            "name": "TrustLife Insurance",
            "type": "life",
            "rating": 4.8,
            "established_year": 1910,
            "states_available": ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"],
            "products_offered": ["LIFE_TERM", "LIFE_WHOLE", "CRITICAL_ILLNESS"],
            "api_endpoint": "https://api.trustlife.com/v1",
            "api_key": "TL_" + uuid.uuid4().hex[:16],
            "risk_appetite": "conservative",
            "max_coverage_limits": {
                "LIFE_TERM": 15000000,
                "LIFE_WHOLE": 10000000,
                "CRITICAL_ILLNESS": 2000000
            },
            "underwriting_turnaround_days": 7,
            "contact_email": "newpolicies@trustlife.com",
            "contact_phone": "1-877-TRUST11",
            "website": "www.trustlife.com"
        }
    ]
    
    for company in companies:
        company["created_at"] = datetime.now(timezone.utc)
        company["updated_at"] = datetime.now(timezone.utc)
    
    result = sync_db[Collections.COMPANIES].insert_many(companies)
    print(f"Created {len(result.inserted_ids)} insurance companies")
    return companies


def create_insurance_products(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create insurance products for each company"""
    print("Creating insurance products...")
    products = []
    
    product_templates = {
        "HEALTH_BASIC": {
            "name_suffix": "Essential Health",
            "description": "Basic health coverage for individuals and families",
            "min_coverage": 100000,
            "max_coverage": 1000000,
            "coverage_types": ["hospitalization", "emergency", "preventive_care", "prescription_basic"],
            "min_age": 18,
            "max_age": 65,
            "base_rate": 200,
            "available_riders": [
                {"code": "DENTAL", "name": "Basic Dental", "rate": 25},
                {"code": "VISION", "name": "Vision Care", "rate": 15}
            ],
            "waiting_periods": {"general": 30, "pre_existing": 365},
            "exclusions": ["cosmetic_surgery", "experimental_treatment", "self_inflicted"]
        },
        "HEALTH_PREMIUM": {
            "name_suffix": "Premier Health",
            "description": "Comprehensive health coverage with enhanced benefits",
            "min_coverage": 500000,
            "max_coverage": 5000000,
            "coverage_types": ["hospitalization", "emergency", "preventive_care", "prescription_full", "specialist", "mental_health"],
            "min_age": 18,
            "max_age": 70,
            "base_rate": 500,
            "available_riders": [
                {"code": "DENTAL_PLUS", "name": "Premium Dental", "rate": 50},
                {"code": "VISION_PLUS", "name": "Premium Vision", "rate": 30},
                {"code": "WELLNESS", "name": "Wellness Benefits", "rate": 40}
            ],
            "waiting_periods": {"general": 15, "pre_existing": 180},
            "exclusions": ["cosmetic_surgery", "experimental_treatment"]
        },
        "LIFE_TERM": {
            "name_suffix": "Term Life",
            "description": "Affordable term life insurance protection",
            "min_coverage": 100000,
            "max_coverage": 10000000,
            "coverage_types": ["death_benefit", "terminal_illness"],
            "min_age": 18,
            "max_age": 65,
            "base_rate": 0.001,
            "available_riders": [
                {"code": "ACCIDENTAL_DEATH", "name": "Accidental Death Benefit", "rate": 0.0001},
                {"code": "WAIVER_PREMIUM", "name": "Waiver of Premium", "rate": 0.00005},
                {"code": "CHILD_RIDER", "name": "Child Term Rider", "rate": 5}
            ],
            "waiting_periods": {"general": 0, "suicide": 730},
            "exclusions": ["suicide_first_2_years", "war", "aviation_private"]
        },
        "LIFE_WHOLE": {
            "name_suffix": "Whole Life",
            "description": "Permanent life insurance with cash value",
            "min_coverage": 50000,
            "max_coverage": 5000000,
            "coverage_types": ["death_benefit", "cash_value", "dividends"],
            "min_age": 0,
            "max_age": 80,
            "base_rate": 0.003,
            "available_riders": [
                {"code": "PAID_UP", "name": "Paid-Up Additions", "rate": 0.0002},
                {"code": "LONG_TERM_CARE", "name": "Long-Term Care Rider", "rate": 0.0003}
            ],
            "waiting_periods": {"general": 0},
            "exclusions": ["suicide_first_2_years", "war"]
        },
        "CRITICAL_ILLNESS": {
            "name_suffix": "Critical Care",
            "description": "Lump-sum benefit for serious illness diagnosis",
            "min_coverage": 25000,
            "max_coverage": 1000000,
            "coverage_types": ["cancer", "heart_attack", "stroke", "organ_failure", "paralysis"],
            "min_age": 18,
            "max_age": 65,
            "base_rate": 0.002,
            "available_riders": [
                {"code": "RECURRENCE", "name": "Recurrence Benefit", "rate": 0.0001},
                {"code": "CHILD_CRITICAL", "name": "Child Critical Illness", "rate": 10}
            ],
            "waiting_periods": {"general": 90, "pre_existing": 730},
            "exclusions": ["pre_existing_conditions", "self_inflicted", "hiv_aids"]
        }
    }
    
    for company in companies:
        for product_type in company["products_offered"]:
            if product_type in product_templates:
                template = product_templates[product_type]
                
                # Adjust rates based on company's risk appetite
                rate_multiplier = {
                    "conservative": 1.2,
                    "moderate": 1.0,
                    "aggressive": 0.85
                }[company["risk_appetite"]]
                
                product = {
                    "product_id": f"{company['company_id']}_{product_type}",
                    "company_id": company["company_id"],
                    "product_type": product_type,
                    "product_name": f"{company['name']} {template['name_suffix']}",
                    "description": template["description"],
                    "min_coverage": template["min_coverage"],
                    "max_coverage": min(template["max_coverage"], company["max_coverage_limits"].get(product_type, template["max_coverage"])),
                    "coverage_types": template["coverage_types"],
                    "min_age": template["min_age"],
                    "max_age": template["max_age"],
                    "states_available": company["states_available"],
                    "available_riders": template["available_riders"],
                    "waiting_periods": template["waiting_periods"],
                    "exclusions": template["exclusions"],
                    "base_rate": template["base_rate"] * rate_multiplier,
                    "rating_factors": {
                        "age_per_year": 0.02,
                        "smoker": 1.5,
                        "bmi_over_30": 1.2,
                        "bmi_over_35": 1.4,
                        "pre_existing": 1.8,
                        "family_history": 1.1
                    },
                    "active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                products.append(product)
    
    if products:
        result = sync_db[Collections.PRODUCTS].insert_many(products)
        print(f"Created {len(result.inserted_ids)} insurance products")
    return products


def create_customers(num_customers: int = 100) -> List[Dict[str, Any]]:
    """Create fake customer profiles"""
    print(f"Creating {num_customers} customer profiles...")
    customers = []
    
    health_conditions = [
        "diabetes", "hypertension", "asthma", "arthritis", "depression",
        "anxiety", "thyroid", "migraine", "allergies", "none"
    ]
    
    occupations = [
        "teacher", "engineer", "nurse", "accountant", "sales", "manager",
        "developer", "designer", "doctor", "lawyer", "contractor", "retail"
    ]
    
    for i in range(num_customers):
        dob = fake.date_of_birth(minimum_age=18, maximum_age=75)
        age = (datetime.now().date() - dob).days // 365
        
        # Generate health profile based on age
        num_conditions = 0 if age < 30 else random.randint(0, min(3, (age - 30) // 15))
        conditions = random.sample(health_conditions[:-1], num_conditions) if num_conditions > 0 else ["none"]
        
        # BMI calculation
        height_cm = random.uniform(150, 200)
        # Generate weight with some correlation to age
        base_weight = random.uniform(50, 100)
        age_factor = max(0, (age - 25) * 0.2)  # Gain ~0.2kg per year after 25
        weight_kg = base_weight + age_factor + random.uniform(-10, 10)
        bmi = weight_kg / ((height_cm / 100) ** 2)
        
        # Risk scoring
        risk_score = 30  # Base
        risk_factors = []
        
        if age > 60:
            risk_score += 20
            risk_factors.append("Age over 60")
        elif age > 45:
            risk_score += 10
            risk_factors.append("Age 45-60")
        
        smoker = random.random() < 0.2  # 20% smokers
        if smoker:
            risk_score += 15
            risk_factors.append("Smoker")
        
        if bmi > 30:
            risk_score += 10
            risk_factors.append("BMI over 30")
        
        if len(conditions) > 0 and conditions[0] != "none":
            risk_score += len(conditions) * 5
            risk_factors.append(f"{len(conditions)} pre-existing conditions")
        
        customer = {
            "customer_id": f"CUST{str(i+1).zfill(6)}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "dob": dob.isoformat(),
            "gender": random.choice(["M", "F"]),
            "ssn_last_four": fake.ssn()[-4:],
            "address": {
                "line1": fake.street_address(),
                "line2": fake.secondary_address() if random.random() < 0.3 else None,
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postal_code": fake.postcode(),
                "country": "US"
            },
            "health_data": {
                "height_cm": round(height_cm, 1),
                "weight_kg": round(weight_kg, 1),
                "bmi": round(bmi, 1),
                "smoker": smoker,
                "pre_existing_conditions": conditions,
                "medications": [] if conditions[0] == "none" else random.sample(["metformin", "lisinopril", "atorvastatin", "levothyroxine"], min(2, len(conditions))),
                "hospitalizations_last_5_years": random.randint(0, 2) if age > 40 else 0,
                "family_history": random.choice(["heart_disease", "cancer", "diabetes", "none"]),
                "occupation": random.choice(occupations),
                "annual_income": random.randint(30000, 250000)
            },
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
            "quote_history": [],
            "policy_history": [],
            "claim_history": [],
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 730)),
            "updated_at": datetime.now(timezone.utc)
        }
        customers.append(customer)
    
    result = sync_db[Collections.CUSTOMERS].insert_many(customers)
    print(f"Created {len(result.inserted_ids)} customers")
    return customers


def create_quotes_and_policies(customers: List[Dict], products: List[Dict]) -> tuple:
    """Create quotes and convert some to policies"""
    print("Creating quotes and policies...")
    quotes = []
    policies = []
    
    # For each customer, create 1-3 quotes
    for customer in customers[:50]:  # First 50 customers get quotes
        num_quotes = random.randint(1, 3)
        customer_products = random.sample(products, min(num_quotes, len(products)))
        
        for product in customer_products:
            quote_id = f"Q{uuid.uuid4().hex[:8].upper()}"
            quote_date = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90))
            
            # Calculate premium based on customer risk
            base_premium = product["base_rate"]
            risk_multiplier = 1 + (customer["risk_score"] / 100)
            
            # Determine coverage amount
            coverage_amount = random.choice([250000, 500000, 750000, 1000000, 1500000])
            coverage_amount = min(coverage_amount, product["max_coverage"])
            coverage_amount = max(coverage_amount, product["min_coverage"])
            
            # Generate multiple plan options
            plans = []
            for tier, multiplier in [("Basic", 1.0), ("Standard", 1.2), ("Premium", 1.5)]:
                monthly_premium = (base_premium * risk_multiplier * multiplier * (coverage_amount / 100000))
                if product["product_type"] in ["LIFE_TERM", "LIFE_WHOLE"]:
                    monthly_premium = monthly_premium / 10  # Adjust for life insurance
                
                plan = {
                    "plan_id": f"P{uuid.uuid4().hex[:6].upper()}",
                    "plan_name": f"{tier} Plan",
                    "coverage_amount": coverage_amount,
                    "deductible": random.choice([500, 1000, 2500]) if "HEALTH" in product["product_type"] else None,
                    "base_premium": round(monthly_premium * 0.85, 2),
                    "taxes_fees": round(monthly_premium * 0.15, 2),
                    "total_monthly_premium": round(monthly_premium, 2),
                    "total_annual_premium": round(monthly_premium * 12, 2)
                }
                plans.append(plan)
            
            quote = {
                "quote_id": quote_id,
                "company_id": product["company_id"],
                "product_id": product["product_id"],
                "customer_id": customer["customer_id"],
                "quote_date": quote_date,
                "valid_until": quote_date + timedelta(days=30),
                "status": "quoted",
                "coverage_amount": coverage_amount,
                "deductible": plans[0]["deductible"],
                "term_years": random.choice([10, 20, 30]) if "TERM" in product["product_type"] else None,
                "riders": [],
                "base_premium": plans[0]["base_premium"],
                "rider_premiums": {},
                "discounts": {},
                "taxes_fees": plans[0]["taxes_fees"],
                "total_monthly_premium": plans[0]["total_monthly_premium"],
                "total_annual_premium": plans[0]["total_annual_premium"],
                "risk_score": customer["risk_score"],
                "risk_factors": customer["risk_factors"],
                "underwriting_requirements": [] if customer["risk_score"] < 70 else [{"type": "medical_exam", "reason": "High risk score"}],
                "plans": plans,
                "selected_plan_id": None,
                "created_at": quote_date,
                "updated_at": quote_date
            }
            quotes.append(quote)
            
            # Convert 60% of quotes to policies
            if random.random() < 0.6:
                selected_plan = random.choice(plans)
                policy_id = f"POL{uuid.uuid4().hex[:8].upper()}"
                policy_number = f"{datetime.now().year}{random.randint(100000, 999999)}"
                issue_date = quote_date + timedelta(days=random.randint(1, 7))
                effective_date = issue_date + timedelta(days=1)
                
                # Update quote with selected plan
                quote["selected_plan_id"] = selected_plan["plan_id"]
                quote["status"] = "converted"
                
                policy = {
                    "policy_id": policy_id,
                    "policy_number": policy_number,
                    "quote_id": quote_id,
                    "company_id": product["company_id"],
                    "product_id": product["product_id"],
                    "customer_id": customer["customer_id"],
                    "status": random.choice(["active", "active", "active", "lapsed"]),  # 75% active
                    "issue_date": issue_date,
                    "effective_date": effective_date,
                    "expiry_date": effective_date + timedelta(days=365 * (quote["term_years"] or 100)),
                    "last_renewed_date": None,
                    "coverage_amount": coverage_amount,
                    "deductible": selected_plan["deductible"],
                    "riders": [],
                    "beneficiaries": [
                        {
                            "name": fake.name(),
                            "relationship": random.choice(["spouse", "child", "parent", "sibling"]),
                            "percentage": 100
                        }
                    ],
                    "premium_amount": selected_plan["total_monthly_premium"],
                    "payment_frequency": random.choice(["monthly", "quarterly", "annual"]),
                    "payment_method": random.choice(["credit_card", "bank_account", "check"]),
                    "next_payment_date": effective_date + timedelta(days=30),
                    "payments": [],
                    "total_paid": 0,
                    "documents": [
                        {"type": "policy_document", "url": f"/documents/policies/{policy_id}.pdf"},
                        {"type": "id_card", "url": f"/documents/cards/{policy_id}.pdf"}
                    ],
                    "created_at": issue_date,
                    "updated_at": datetime.now(timezone.utc)
                }
                
                # Add payment history for active policies
                if policy["status"] == "active":
                    months_active = random.randint(1, 24)
                    for month in range(months_active):
                        payment_date = effective_date + timedelta(days=30 * month)
                        if payment_date < datetime.now(timezone.utc):
                            payment = {
                                "payment_id": f"PAY{uuid.uuid4().hex[:8].upper()}",
                                "amount": selected_plan["total_monthly_premium"],
                                "date": payment_date.isoformat(),
                                "method": policy["payment_method"],
                                "status": "completed"
                            }
                            policy["payments"].append(payment)
                            policy["total_paid"] += selected_plan["total_monthly_premium"]
                    
                    policy["next_payment_date"] = effective_date + timedelta(days=30 * (months_active + 1))
                
                policies.append(policy)
                
                # Update customer with policy reference
                customer["policy_history"].append(policy_id)
            
            # Update customer with quote reference
            customer["quote_history"].append(quote_id)
    
    if quotes:
        result = sync_db[Collections.QUOTES].insert_many(quotes)
        print(f"Created {len(result.inserted_ids)} quotes")
    
    if policies:
        result = sync_db[Collections.POLICIES].insert_many(policies)
        print(f"Created {len(result.inserted_ids)} policies")
    
    # Update customers with their quote and policy history
    for customer in customers:
        if customer["quote_history"] or customer["policy_history"]:
            sync_db[Collections.CUSTOMERS].update_one(
                {"customer_id": customer["customer_id"]},
                {"$set": {
                    "quote_history": customer["quote_history"],
                    "policy_history": customer["policy_history"]
                }}
            )
    
    return quotes, policies


def create_claims(policies: List[Dict]) -> List[Dict]:
    """Create fake claims for some policies"""
    print("Creating claims...")
    claims = []
    
    claim_types = {
        "HEALTH": ["hospitalization", "emergency_room", "surgery", "diagnostic", "prescription"],
        "LIFE": ["death_benefit", "terminal_illness"],
        "CRITICAL": ["cancer_diagnosis", "heart_attack", "stroke"]
    }
    
    # Create claims for 20% of active policies
    active_policies = [p for p in policies if p["status"] == "active"]
    policies_with_claims = random.sample(active_policies, min(len(active_policies) // 5, len(active_policies)))
    
    for policy in policies_with_claims:
        num_claims = random.randint(1, 3)
        
        for _ in range(num_claims):
            claim_id = f"CLM{uuid.uuid4().hex[:8].upper()}"
            claim_number = f"C{datetime.now().year}{random.randint(10000, 99999)}"
            
            # Determine claim type based on product
            product_type = policy["product_id"].split("_")[-1]
            if "HEALTH" in product_type:
                claim_type = random.choice(claim_types["HEALTH"])
            elif "LIFE" in product_type:
                claim_type = random.choice(claim_types["LIFE"])
            else:
                claim_type = random.choice(claim_types["CRITICAL"])
            
            submission_date = policy["effective_date"] + timedelta(days=random.randint(30, 365))
            if submission_date > datetime.now(timezone.utc):
                submission_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
            
            claim_amount = random.uniform(1000, min(50000, policy["coverage_amount"] * 0.1))
            
            # Determine claim status
            status_choices = ["approved", "approved", "approved", "under_review", "rejected"]
            status = random.choice(status_choices)
            
            claim = {
                "claim_id": claim_id,
                "claim_number": claim_number,
                "policy_id": policy["policy_id"],
                "company_id": policy["company_id"],
                "customer_id": policy["customer_id"],
                "claim_type": claim_type,
                "incident_date": (submission_date - timedelta(days=random.randint(1, 7))).isoformat(),
                "submission_date": submission_date,
                "description": fake.text(max_nb_chars=200),
                "status": status,
                "status_history": [
                    {"status": "submitted", "date": submission_date.isoformat(), "notes": "Claim received"},
                    {"status": "under_review", "date": (submission_date + timedelta(days=1)).isoformat(), "notes": "Under review by adjuster"}
                ],
                "claim_amount": round(claim_amount, 2),
                "approved_amount": round(claim_amount * 0.8, 2) if status == "approved" else None,
                "deductible_applied": policy.get("deductible", 0) if status == "approved" else None,
                "adjuster_name": fake.name(),
                "adjuster_notes": ["Initial review completed", "Documentation verified"],
                "investigation_notes": None if status == "approved" else "Pending additional documentation",
                "documents": [
                    {"type": "claim_form", "url": f"/documents/claims/{claim_id}_form.pdf"},
                    {"type": "medical_bills", "url": f"/documents/claims/{claim_id}_bills.pdf"}
                ],
                "payment_date": (submission_date + timedelta(days=random.randint(7, 30))).isoformat() if status == "approved" else None,
                "payment_method": "check" if status == "approved" else None,
                "payment_reference": f"CHK{random.randint(100000, 999999)}" if status == "approved" else None,
                "created_at": submission_date,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if status == "approved":
                claim["status_history"].append({
                    "status": "approved",
                    "date": (submission_date + timedelta(days=random.randint(2, 5))).isoformat(),
                    "notes": "Claim approved for payment"
                })
                claim["status_history"].append({
                    "status": "paid",
                    "date": claim["payment_date"],
                    "notes": f"Payment issued via {claim['payment_method']}"
                })
                claim["status"] = "paid"
            elif status == "rejected":
                claim["status_history"].append({
                    "status": "rejected",
                    "date": (submission_date + timedelta(days=random.randint(5, 10))).isoformat(),
                    "notes": "Claim denied - not covered under policy terms"
                })
            
            claims.append(claim)
    
    if claims:
        result = sync_db[Collections.CLAIMS].insert_many(claims)
        print(f"Created {len(result.inserted_ids)} claims")
    
    return claims


def create_rate_tables(companies: List[Dict]) -> List[Dict]:
    """Create rate tables for each company"""
    print("Creating rate tables...")
    rate_tables = []
    
    for company in companies:
        for product_type in company["products_offered"]:
            rate_table = {
                "table_id": f"RT_{company['company_id']}_{product_type}",
                "company_id": company["company_id"],
                "product_type": product_type,
                "effective_date": datetime.now(timezone.utc) - timedelta(days=365),
                "age_bands": [
                    {"min_age": 18, "max_age": 25, "factor": 0.8},
                    {"min_age": 26, "max_age": 35, "factor": 0.9},
                    {"min_age": 36, "max_age": 45, "factor": 1.0},
                    {"min_age": 46, "max_age": 55, "factor": 1.3},
                    {"min_age": 56, "max_age": 65, "factor": 1.7},
                    {"min_age": 66, "max_age": 75, "factor": 2.2},
                    {"min_age": 76, "max_age": 100, "factor": 3.0}
                ],
                "health_factors": {
                    "diabetes": 1.3,
                    "hypertension": 1.2,
                    "heart_disease": 1.5,
                    "cancer_history": 1.8,
                    "asthma": 1.1,
                    "mental_health": 1.15
                },
                "bmi_ranges": [
                    {"min_bmi": 0, "max_bmi": 18.5, "factor": 1.1},
                    {"min_bmi": 18.5, "max_bmi": 25, "factor": 1.0},
                    {"min_bmi": 25, "max_bmi": 30, "factor": 1.1},
                    {"min_bmi": 30, "max_bmi": 35, "factor": 1.3},
                    {"min_bmi": 35, "max_bmi": 100, "factor": 1.5}
                ],
                "smoker_factor": 1.5,
                "state_factors": {
                    "CA": 1.1, "NY": 1.15, "TX": 0.95, "FL": 1.05,
                    "IL": 1.0, "PA": 0.98, "OH": 0.96, "GA": 0.97,
                    "NC": 0.95, "MI": 0.99, "WA": 1.08, "MA": 1.12,
                    "VA": 1.0, "AZ": 1.02, "CO": 1.05, "NJ": 1.1,
                    "CT": 1.08, "MD": 1.06
                },
                "occupation_classes": {
                    "low_risk": 0.9,  # Office workers, teachers
                    "medium_risk": 1.0,  # Retail, healthcare
                    "high_risk": 1.3,  # Construction, mining
                    "very_high_risk": 1.6  # Logging, roofing
                },
                "discounts": {
                    "multi_policy": 0.1,
                    "annual_payment": 0.05,
                    "group": 0.15,
                    "loyalty_5_years": 0.08,
                    "healthy_lifestyle": 0.1
                },
                "rider_rates": {
                    "CRITICAL_ILLNESS": 0.002,
                    "DISABILITY": 0.003,
                    "ACCIDENTAL_DEATH": 0.001,
                    "DENTAL": 25,
                    "VISION": 15,
                    "WELLNESS": 40
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Adjust factors based on company risk appetite
            if company["risk_appetite"] == "conservative":
                for age_band in rate_table["age_bands"]:
                    age_band["factor"] *= 1.1
                rate_table["smoker_factor"] *= 1.1
            elif company["risk_appetite"] == "aggressive":
                for age_band in rate_table["age_bands"]:
                    age_band["factor"] *= 0.95
                rate_table["smoker_factor"] *= 0.95
            
            rate_tables.append(rate_table)
    
    if rate_tables:
        result = sync_db[Collections.RATE_TABLES].insert_many(rate_tables)
        print(f"Created {len(result.inserted_ids)} rate tables")
    
    return rate_tables


def main():
    """Main function to populate the database"""
    print("Starting database population...")
    print("=" * 50)
    
    # Clear existing data
    clear_database()
    
    # Create data in order
    companies = create_insurance_companies()
    products = create_insurance_products(companies)
    customers = create_customers(100)
    quotes, policies = create_quotes_and_policies(customers, products)
    claims = create_claims(policies)
    rate_tables = create_rate_tables(companies)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Database Population Summary:")
    print(f"✓ Companies: {len(companies)}")
    print(f"✓ Products: {len(products)}")
    print(f"✓ Customers: {len(customers)}")
    print(f"✓ Quotes: {len(quotes)}")
    print(f"✓ Policies: {len(policies)}")
    print(f"✓ Claims: {len(claims)}")
    print(f"✓ Rate Tables: {len(rate_tables)}")
    print("=" * 50)
    print("Database population completed successfully!")


if __name__ == "__main__":
    main()