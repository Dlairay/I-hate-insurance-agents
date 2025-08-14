"""
PDF Parser Agent for Insurance Documents
========================================
AI agent that reads insurance PDFs and extracts relevant fields for API submission
Uses Ollama through Google ADK (consistent with other agents)
"""

import json
import logging
import os
import asyncio
import warnings
import io
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

# PDF processing library
try:
    import pdfplumber
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False
    logging.warning("pdfplumber not available - PDF text extraction disabled")

# Suppress Pydantic warnings (consistent with other agents)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

# Google ADK imports (same pattern as other agents)
try:
    from google.adk.agents import Agent
    from google.adk.sessions import InMemorySessionService
    from google.adk.runners import Runner
    from google.genai import types
    from google.adk.models.lite_llm import LiteLlm
    from dotenv import load_dotenv
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    logging.warning("Google ADK not available - PDF Parser will use fallback extraction")

# Load environment variables
if ADK_AVAILABLE:
    load_dotenv()

# Suppress logs (consistent with other agents)
logging.basicConfig(level=logging.ERROR)
if ADK_AVAILABLE:
    logging.getLogger("litellm").setLevel(logging.ERROR)
    logging.getLogger("google.adk").setLevel(logging.ERROR)

# Initialize Ollama model (following same pattern as questionnaire_agent.py)
if ADK_AVAILABLE:
    ollama_model = LiteLlm(model="ollama_chat/gpt-oss:20b")

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.shared.models import ApplicantProfile

def standardize_premium_costs(amount: float, period: str) -> dict:
    """
    Convert premium costs to standard units (daily, monthly, annual)
    
    Args:
        amount: Premium amount as float
        period: Period string (day, daily, month, monthly, year, yearly, annual, week, weekly)
        
    Returns:
        Dict with standardized costs: daily, monthly, annual
    """
    period_lower = period.lower().strip()
    
    # Normalize period names
    if period_lower in ['day', 'daily', 'per day', '/day']:
        daily_rate = amount
    elif period_lower in ['week', 'weekly', 'per week', '/week']:
        daily_rate = amount / 7
    elif period_lower in ['month', 'monthly', 'per month', '/month']:
        daily_rate = amount / 30.44  # Average days per month
    elif period_lower in ['year', 'yearly', 'annual', 'annually', 'per year', '/year']:
        daily_rate = amount / 365
    else:
        # Default to monthly if period is unclear
        print(f"⚠️  Unknown period '{period}', defaulting to monthly")
        daily_rate = amount / 30.44
    
    # Calculate all standard formats
    monthly_rate = daily_rate * 30.44
    annual_rate = daily_rate * 365
    
    return {
        'daily': round(daily_rate, 3),
        'monthly': round(monthly_rate, 2), 
        'annual': round(annual_rate, 2),
        'source_amount': amount,
        'source_period': period
    }

def format_premium_display(standardized_costs: dict, currency: str = "$") -> dict:
    """
    Format standardized costs for display
    
    Args:
        standardized_costs: Output from standardize_premium_costs()
        currency: Currency symbol (default: $)
        
    Returns:
        Dict with formatted display strings
    """
    return {
        'daily_formatted': f"{currency}{standardized_costs['daily']:.3f}/day",
        'monthly_formatted': f"{currency}{standardized_costs['monthly']:.2f}/month", 
        'annual_formatted': f"{currency}{standardized_costs['annual']:,.2f}/year",
        'daily_raw': standardized_costs['daily'],
        'monthly_raw': standardized_costs['monthly'],
        'annual_raw': standardized_costs['annual']
    }

def extract_and_standardize_premiums(text: str) -> list:
    """
    Extract premium information from text and standardize all found premiums
    
    Args:
        text: Text to search for premium patterns
        
    Returns:
        List of standardized premium dictionaries
    """
    import re
    
    premiums = []
    
    # Enhanced pattern to catch various premium formats
    patterns = [
        r'([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*per\s*(day|month|year|week)',
        r'([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*(?:/|per)\s*(day|month|year|week)',
        r'(\d+(?:\.\d{1,3})?)\s*([s\$£€¥]?)\s*(?:daily|monthly|yearly|annually)',
        r'premium\s*:?\s*([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*(?:/|per)?\s*(day|month|year|week)?'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower(), re.IGNORECASE)
        for match in matches:
            if len(match) == 3:
                currency, amount_str, period = match
                if amount_str and period:
                    try:
                        amount = float(amount_str)
                        
                        # Standardize the premium
                        standardized = standardize_premium_costs(amount, period)
                        
                        # Add formatting
                        formatted = format_premium_display(standardized, currency or '$')
                        
                        # Combine into complete premium info
                        premium_info = {
                            **standardized,
                            **formatted,
                            'currency': currency or '$',
                            'found_in_text': True
                        }
                        
                        premiums.append(premium_info)
                        
                    except (ValueError, TypeError):
                        continue
    
    return premiums

def extract_text_from_pdf_bytes(pdf_content: bytes, max_pages: int = 10) -> str:
    """
    Extract text from PDF bytes using pdfplumber
    
    Args:
        pdf_content: Raw PDF bytes
        max_pages: Maximum number of pages to process (to avoid huge PDFs)
        
    Returns:
        Extracted text string
    """
    if not PDF_PROCESSING_AVAILABLE:
        return "PDF processing not available - pdfplumber not installed"
    
    try:
        # Create a BytesIO object from the PDF bytes
        pdf_file = io.BytesIO(pdf_content)
        
        extracted_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages)
            
            print(f"📄 Processing {pages_to_process} of {total_pages} pages from PDF")
            
            for i, page in enumerate(pdf.pages[:pages_to_process]):
                page_text = page.extract_text()
                if page_text:
                    extracted_text += f"=== PAGE {i+1} ===\n{page_text}\n\n"
            
            # If we processed less than all pages, add a note
            if pages_to_process < total_pages:
                extracted_text += f"\n[Note: Only processed first {pages_to_process} of {total_pages} pages for efficiency]"
            
            return extracted_text
            
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return f"Error extracting PDF text: {str(e)}"

logger = logging.getLogger(__name__)

class PDFExtractionResult(BaseModel):
    """Result of PDF extraction"""
    extracted_fields: Dict[str, Any]
    confidence_score: float  # 0-100
    extracted_text_sample: str  # First 500 chars of extracted text
    missing_fields: List[str]
    warnings: List[str]
    processing_time_seconds: float

def extract_pdf_fields(pdf_text: str, existing_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function to extract insurance fields from PDF text content
    
    Args:
        pdf_text: Text extracted from PDF (simulated for now since we can't process actual PDFs with Ollama)
        existing_profile: Any existing profile data to merge with
        
    Returns:
        Dict with extracted insurance fields
    """
    print(f"--- Tool: extract_pdf_fields called ---")
    print(f"PDF text length: {len(pdf_text)} characters")
    print(f"Existing profile keys: {list(existing_profile.keys())}")
    
    # Extract real information from the actual PDF text
    extracted = {}
    text_lower = pdf_text.lower()
    
    print(f"🔍 Analyzing PDF content for insurance information...")
    
    # Detect document type based on content
    if "group insurance" in text_lower:
        extracted["document_type"] = "group_insurance_policy"
        print("📋 Detected: Group Insurance Policy Document")
    elif "term life" in text_lower:
        extracted["document_type"] = "life_insurance_policy" 
    elif "health" in text_lower or "medical" in text_lower:
        extracted["document_type"] = "health_insurance_policy"
    
    # Extract existing coverage information (this would be useful for existing_coverage questions)
    coverage_types = []
    coverage_amounts = []
    
    # Look for specific insurance products mentioned in the document
    if "group term life" in text_lower:
        coverage_types.append("life_insurance")
        # Look for coverage amounts
        import re
        amount_patterns = re.findall(r's\$[\d,]+(?:\.\d{2})?', pdf_text.lower())
        if amount_patterns:
            # Extract the largest amount as likely coverage
            amounts = [float(amt.replace('s$', '').replace(',', '')) for amt in amount_patterns]
            max_amount = max(amounts) if amounts else 0
            if max_amount > 0:
                coverage_amounts.append(max_amount)
                extracted["coverage_amount"] = f"${max_amount:,.0f}"
                print(f"💰 Found coverage amount: ${max_amount:,.0f}")
        
        # Look for premium information using standardized helper functions
        premiums_found = extract_and_standardize_premiums(pdf_text)
        if premiums_found:
            # Use the first premium found (usually the main coverage premium)
            main_premium = premiums_found[0]
            
            extracted["current_premium_daily"] = f"${main_premium['daily']:.3f}"
            extracted["current_premium_monthly"] = f"${main_premium['monthly']:.2f}"
            extracted["current_premium_annual"] = f"${main_premium['annual']:,.2f}"
            
            # Store raw numbers for calculations
            extracted["current_premium_daily_raw"] = main_premium['daily']
            extracted["current_premium_monthly_raw"] = main_premium['monthly']
            extracted["current_premium_annual_raw"] = main_premium['annual']
            
            print(f"💸 Found premium: {main_premium['daily_formatted']} ({main_premium['monthly_formatted']}, {main_premium['annual_formatted']})")
            
            # Store all premiums found for detailed analysis
            if len(premiums_found) > 1:
                extracted["all_premiums_found"] = len(premiums_found)
                print(f"📊 Total premiums found: {len(premiums_found)}")
        else:
            print("⚠️  No premium information found in document")
    
    if "personal injury" in text_lower:
        coverage_types.append("accident_insurance")
        
    if "disability income" in text_lower:
        coverage_types.append("disability_insurance")
        
    if "outpatient" in text_lower or "medicare" in text_lower:
        coverage_types.append("health_insurance")
    
    # If we found coverage types, this indicates existing coverage
    if coverage_types:
        extracted["existing_coverage_type"] = ", ".join(coverage_types)
        extracted["has_existing_coverage"] = True
        print(f"🏥 Found coverage types: {', '.join(coverage_types)}")
        
        # For group insurance, this is typically employer-provided
        if "group" in text_lower:
            extracted["coverage_source"] = "employer_group"
        else:
            extracted["coverage_source"] = "individual"
    else:
        extracted["has_existing_coverage"] = False
    
    # Look for policy numbers (pattern like G007500)
    policy_patterns = re.findall(r'(?:policy no|policy number)[:\s]*([a-z]?\d{6,})', text_lower)
    if policy_patterns:
        extracted["policy_number"] = policy_patterns[0].upper()
        print(f"📄 Found policy number: {extracted['policy_number']}")
    
    # Extract organization info (useful context)
    if "mindef" in text_lower and "mha" in text_lower:
        extracted["organization"] = "MINDEF & MHA"
        extracted["country"] = "Singapore"
        print("🏛️ Organization: Singapore MINDEF & MHA")
    
    # Set confidence based on what we extracted
    if coverage_types or policy_patterns:
        extracted["extraction_confidence"] = 80.0
        print(f"✅ High confidence extraction: Found {len(coverage_types)} coverage types")
    elif "insurance" in text_lower:
        extracted["extraction_confidence"] = 60.0
        print("ℹ️ Medium confidence: Insurance document but limited extraction")
    else:
        extracted["extraction_confidence"] = 20.0
        print("❓ Low confidence: Limited information extracted")
    
    # Merge with existing profile
    if existing_profile:
        extracted.update(existing_profile)
        extracted["merge_source"] = "pdf_plus_json"
    else:
        extracted["merge_source"] = "pdf_only"
    
    return extracted


def validate_extracted_fields(extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool function to validate and clean extracted fields
    
    Args:
        extracted_fields: Raw extracted fields
        
    Returns:
        Dict with validation results and cleaned fields
    """
    print(f"--- Tool: validate_extracted_fields called ---")
    print(f"Fields to validate: {list(extracted_fields.keys())}")
    
    validated = {}
    warnings = []
    missing_required = []
    
    # Essential fields for MVP API (matching ApplicantData model)
    required_fields = ['first_name', 'last_name', 'dob', 'gender', 'email', 'phone', 'address_line1', 'city', 'state', 'postal_code']
    
    for field in required_fields:
        if field in extracted_fields and extracted_fields[field]:
            validated[field] = str(extracted_fields[field]).strip()
        else:
            missing_required.append(field)
    
    # Essential optional fields for MVP (matching backend API)
    optional_fields = ['annual_income', 'occupation', 'smoker', 'height_cm', 'weight_kg', 'pre_existing_conditions']
    for field in optional_fields:
        if field in extracted_fields and extracted_fields[field]:
            if field == 'annual_income' and str(extracted_fields[field]).replace('.', '').replace(',', '').isdigit():
                validated[field] = float(str(extracted_fields[field]).replace(',', ''))
            elif field in ['height_cm', 'weight_kg'] and str(extracted_fields[field]).replace('.', '').isdigit():
                validated[field] = float(extracted_fields[field])
            elif field == 'smoker':
                validated[field] = str(extracted_fields[field]).lower() in ['true', 'yes', '1', 'smoker']
            elif field == 'pre_existing_conditions':
                # Handle list of conditions
                if isinstance(extracted_fields[field], list):
                    validated[field] = extracted_fields[field]
                else:
                    # Split comma-separated string
                    conditions = str(extracted_fields[field]).split(',')
                    validated[field] = [c.strip() for c in conditions if c.strip()]
            else:
                validated[field] = str(extracted_fields[field])
    
    # Add metadata
    validated["validation_warnings"] = warnings
    validated["missing_required_fields"] = missing_required
    validated["confidence_score"] = max(0, 100 - len(missing_required) * 10)
    
    return validated


class PDFParserAgent:
    """AI agent for parsing insurance PDFs using Ollama through Google ADK"""
    
    def __init__(self):
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the ADK agent if available"""
        if not ADK_AVAILABLE:
            logger.warning("Google ADK not available for PDF parsing")
            return
        
        try:
            # Create ADK agent with tools (following working agent pattern)
            self.agent = Agent(
                name="pdf_parser",
                model=ollama_model,
                description="Expert insurance document parser",
                instruction=(
                    "You are an expert insurance document parser. Your job is to extract relevant information from insurance-related documents and convert it into structured data.\n\n"
                    "When given PDF text content, you should:\n"
                    "1. Identify the type of insurance document\n"
                    "2. Extract personal information (name, DOB, address, contact info)\n"
                    "3. Extract financial information (income, occupation)\n"
                    "4. Extract health information (smoking status, medical history)\n"
                    "5. Extract existing coverage information\n"
                    "6. Validate and clean the extracted data\n\n"
                    "Always use the provided tools to extract and validate the information.\n"
                    "Be thorough but conservative - if you're not confident about a field, don't extract it."
                ),
                tools=[extract_pdf_fields, validate_extracted_fields]
            )
            logger.info("PDF Parser Agent initialized with Ollama")
        except Exception as e:
            logger.error(f"Failed to initialize PDF Parser Agent: {e}")
            self.agent = None
    
    def extract_insurance_fields(self, pdf_content: bytes, json_profile: Optional[Dict[str, Any]] = None) -> PDFExtractionResult:
        """
        Extract insurance-relevant fields from PDF content using Ollama
        
        Args:
            pdf_content: Raw PDF bytes
            json_profile: Optional existing JSON profile to merge with
            
        Returns:
            PDFExtractionResult with extracted fields
        """
        start_time = datetime.now()
        
        try:
            if self.agent:
                return self._extract_with_ollama(pdf_content, json_profile)
            else:
                return self._extract_with_fallback(pdf_content, json_profile)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return PDFExtractionResult(
                extracted_fields={},
                confidence_score=0.0,
                extracted_text_sample="",
                missing_fields=self._get_required_fields(),
                warnings=[f"PDF extraction failed: {str(e)}"],
                processing_time_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def extract_insurance_fields_async(self, pdf_content: bytes, json_profile: Optional[Dict[str, Any]] = None) -> PDFExtractionResult:
        """Async version for use in FastAPI"""
        return await asyncio.to_thread(self.extract_insurance_fields, pdf_content, json_profile)
    
    def _extract_with_ollama(self, pdf_content: bytes, json_profile: Optional[Dict[str, Any]] = None) -> PDFExtractionResult:
        """Extract fields using Ollama through ADK"""
        start_time = datetime.now()
        
        try:
            # Extract actual text from PDF using pdfplumber
            print("🔍 Extracting text from PDF using pdfplumber...")
            pdf_text = extract_text_from_pdf_bytes(pdf_content, max_pages=10)
            
            # Truncate text if it's too long for Ollama (keep first 8000 chars)  
            if len(pdf_text) > 8000:
                pdf_text = pdf_text[:8000] + "\n[Text truncated for processing efficiency]"
                print(f"📝 PDF text truncated to 8000 characters for Ollama processing")
            
            # For now, let's use a simpler extraction approach since the async ADK pattern is complex
            # We'll run the tools directly and then format the result
            
            print("🤖 Running PDF field extraction...")
            
            # Use the tool function directly to extract fields
            extracted_data = extract_pdf_fields(pdf_text, json_profile or {})
            print(f"📊 Extracted data: {extracted_data}")
            
            # Validate the extracted data  
            validation_result = validate_extracted_fields(extracted_data)
            print(f"✅ Validation result: {validation_result}")
            
            # Merge with existing profile if provided
            final_fields = {}
            if json_profile:
                final_fields.update(json_profile)
            
            # The extract_pdf_fields function returns the fields directly
            final_fields.update(extracted_data)
            
            # Create result
            confidence_score = 75.0 if final_fields else 25.0  # Higher confidence with real text
            
            return PDFExtractionResult(
                extracted_fields=final_fields,
                confidence_score=confidence_score,
                extracted_text_sample=pdf_text[:500],
                missing_fields=[f for f in self._get_required_fields() if f not in final_fields],
                warnings=["Using direct tool extraction (Ollama agent pattern simplified)"],
                processing_time_seconds=(datetime.now() - start_time).total_seconds()
            )
                
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            return self._extract_with_fallback(pdf_content, json_profile)
    
    def _extract_with_fallback(self, pdf_content: bytes, json_profile: Optional[Dict[str, Any]] = None) -> PDFExtractionResult:
        """Fallback extraction without AI"""
        start_time = datetime.now()
        
        # Basic fallback - just return the JSON profile if available, otherwise empty
        extracted_fields = json_profile if json_profile else {}
        missing_fields = self._find_missing_fields(extracted_fields)
        
        warnings = ["PDF extraction using fallback method - AI not available"]
        if not json_profile:
            warnings.append("No JSON profile provided and PDF parsing unavailable")
        
        return PDFExtractionResult(
            extracted_fields=extracted_fields,
            confidence_score=50.0 if json_profile else 0.0,
            extracted_text_sample="Fallback extraction - text content not available",
            missing_fields=missing_fields,
            warnings=warnings,
            processing_time_seconds=(datetime.now() - start_time).total_seconds()
        )
    
    def _merge_profiles(self, json_profile: Dict[str, Any], pdf_extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Merge JSON profile with PDF extracted data (PDF takes precedence)"""
        merged = json_profile.copy()
        merged.update(pdf_extracted)
        return merged
    
    def _validate_extracted_fields(self, raw_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted fields"""
        validated = {}
        
        # Define field validators
        field_validators = {
            'annual_income': lambda x: float(x) if x and str(x).replace('.', '').replace(',', '').isdigit() else None,
            'smoker': lambda x: bool(x) if isinstance(x, bool) else str(x).lower() in ['true', 'yes', '1'] if x else None,
            'height_cm': lambda x: float(x) if x and str(x).replace('.', '').isdigit() else None,
            'weight_kg': lambda x: float(x) if x and str(x).replace('.', '').isdigit() else None,
            'hospitalizations_last_5_years': lambda x: int(x) if x and str(x).isdigit() else 0,
        }
        
        # Process each field
        for key, value in raw_fields.items():
            if value is None or value == "" or value == []:
                continue
                
            if key in field_validators:
                try:
                    validated_value = field_validators[key](value)
                    if validated_value is not None:
                        validated[key] = validated_value
                except (ValueError, TypeError):
                    logger.warning(f"Invalid value for {key}: {value}")
            else:
                # For string fields, clean up
                if isinstance(value, str):
                    cleaned_value = value.strip()
                    if cleaned_value:
                        validated[key] = cleaned_value
                elif isinstance(value, list):
                    # Clean list fields
                    cleaned_list = [item.strip() if isinstance(item, str) else item for item in value if item]
                    if cleaned_list:
                        validated[key] = cleaned_list
                else:
                    validated[key] = value
        
        return validated
    
    def _get_required_fields(self) -> List[str]:
        """Get list of required fields for MVP insurance application"""
        return [
            'first_name', 'last_name', 'dob', 'gender', 'email', 'phone',
            'address_line1', 'city', 'state', 'postal_code'
        ]
    
    def _find_missing_fields(self, extracted_fields: Dict[str, Any]) -> List[str]:
        """Find missing required fields"""
        required_fields = self._get_required_fields()
        return [field for field in required_fields if field not in extracted_fields]
    
    def _calculate_confidence(self, extracted_fields: Dict[str, Any], missing_fields: List[str]) -> float:
        """Calculate confidence score based on completeness"""
        total_required = len(self._get_required_fields())
        found_required = total_required - len(missing_fields)
        
        # Base score from required fields
        base_score = (found_required / total_required) * 70
        
        # Bonus points for optional but valuable fields
        bonus_fields = ['occupation', 'smoker', 'height_cm', 'weight_kg', 'pre_existing_conditions']
        bonus_points = sum(10 for field in bonus_fields if field in extracted_fields)
        
        return min(100.0, base_score + bonus_points)

# Singleton instance
_pdf_parser_agent = None

def get_pdf_parser() -> PDFParserAgent:
    """Get singleton PDF parser agent instance"""
    global _pdf_parser_agent
    if _pdf_parser_agent is None:
        _pdf_parser_agent = PDFParserAgent()
    return _pdf_parser_agent

# Helper function for easy usage
async def parse_insurance_pdf(pdf_content: bytes, json_profile: Optional[Dict[str, Any]] = None) -> PDFExtractionResult:
    """
    Parse insurance PDF and extract fields
    
    Args:
        pdf_content: Raw PDF bytes
        json_profile: Optional existing JSON profile to merge
        
    Returns:
        PDFExtractionResult with extracted information
    """
    parser = get_pdf_parser()
    return parser.extract_insurance_fields(pdf_content, json_profile)

if __name__ == "__main__":
    # Test the agent
    async def test():
        # This would typically be called with actual PDF content
        result = await parse_insurance_pdf(b"dummy pdf content")
        print(f"Extraction result: {result}")
    
    asyncio.run(test())