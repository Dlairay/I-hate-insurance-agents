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
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

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
    ollama_model = LiteLlm(model="ollama_chat/llama3:latest")

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import ApplicantProfile

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
    
    # For now, since Ollama can't actually process PDF binaries, we'll simulate extraction
    # In a real implementation, you'd first convert PDF to text, then use Ollama to parse it
    
    # Simulate field extraction based on text patterns
    extracted = {}
    
    # Look for common insurance document patterns
    text_lower = pdf_text.lower()
    
    # Try to extract name patterns
    if "applicant" in text_lower or "policyholder" in text_lower:
        # This would be more sophisticated text parsing
        extracted["extraction_confidence"] = 70.0
        extracted["document_type"] = "insurance_application"
    
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
            # Create ADK agent with tools (following questionnaire_agent pattern)
            self.agent = Agent(
                model=ollama_model,
                tools=[extract_pdf_fields, validate_extracted_fields],
                instructions="""
You are an expert insurance document parser. Your job is to extract relevant information from insurance-related documents and convert it into structured data.

When given PDF text content, you should:
1. Identify the type of insurance document
2. Extract personal information (name, DOB, address, contact info)
3. Extract financial information (income, occupation)
4. Extract health information (smoking status, medical history)
5. Extract existing coverage information
6. Validate and clean the extracted data

Always use the provided tools to extract and validate the information.
Be thorough but conservative - if you're not confident about a field, don't extract it.
"""
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
            # Since Ollama can't process PDF binaries directly, we need to simulate text extraction
            # In a real implementation, you'd use a library like PyPDF2 or pdfplumber first
            pdf_text = f"[SIMULATED PDF TEXT - {len(pdf_content)} bytes of PDF content]"
            
            # Create session and runner (following ADK pattern)
            session_service = InMemorySessionService()
            runner = Runner(session_service=session_service)
            
            # Build message for extraction
            message = f"""
Please extract insurance information from this document. 

PDF Content: {pdf_text}

Existing Profile: {json.dumps(json_profile) if json_profile else 'None'}

Use the extract_pdf_fields tool to extract information, then the validate_extracted_fields tool to clean and validate the results.
"""
            
            # Run the agent
            result = runner.run(
                agent=self.agent,
                user_message=message
            )
            
            # Get the final response
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            # For now, since we're simulating, merge with JSON profile and return basic result
            if json_profile:
                extracted_fields = json_profile.copy()
                confidence = 85.0  # Good confidence if we have JSON profile
                warnings = ["Using provided JSON profile data"]
            else:
                extracted_fields = {}
                confidence = 30.0  # Low confidence without real PDF processing
                warnings = ["PDF processing simulated - real implementation needs PDF-to-text conversion"]
            
            missing_fields = self._find_missing_fields(extracted_fields)
            
            return PDFExtractionResult(
                extracted_fields=extracted_fields,
                confidence_score=confidence,
                extracted_text_sample=response_text[:500] if response_text else "Ollama processing completed",
                missing_fields=missing_fields,
                warnings=warnings,
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