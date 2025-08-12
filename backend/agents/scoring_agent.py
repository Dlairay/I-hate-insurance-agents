"""
Insurance Policy Scoring Agent
==============================
Calculates three key metrics for insurance policies relative to the user
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum

from backend.shared.models import ApplicantProfile

# Import the actual QuotePlan model from the backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from insurance_backend.insurance_backend_mongo import QuotePlan
except ImportError:
    # Fallback definition if import fails
    from pydantic import BaseModel
    from typing import Dict, Any, List, Optional
    
    class QuotePlan(BaseModel):
        """Fallback QuotePlan model"""
        plan_id: str
        plan_name: str
        company_id: str
        company_name: str
        company_rating: float
        coverage_amount: float
        deductible: Optional[float]
        base_premium: float
        rider_premiums: Dict[str, float] = {}
        taxes_fees: float
        total_monthly_premium: float
        total_annual_premium: float
        coverage_details: Dict[str, Any] = {}
        exclusions: List[str] = []
        waiting_periods: Dict[str, int] = {}

logger = logging.getLogger(__name__)

class ScoreCategory(str, Enum):
    EXCELLENT = "excellent"  # 90-100
    VERY_GOOD = "very_good"  # 80-89
    GOOD = "good"           # 70-79
    FAIR = "fair"          # 60-69
    POOR = "poor"          # 0-59

class PolicyScore(BaseModel):
    """Individual policy score with all metrics"""
    plan_id: str
    plan_name: str
    company_name: str
    
    # The 3 core metrics (0-100 scale)
    affordability_score: float
    ease_of_claims_score: float
    coverage_ratio_score: float
    
    # Overall composite score
    overall_score: float
    overall_category: ScoreCategory
    
    # Detailed breakdowns
    affordability_details: Dict[str, Any]
    claims_ease_details: Dict[str, Any]
    coverage_ratio_details: Dict[str, Any]
    
    # User-specific insights
    income_percentage: float  # % of income used for insurance
    annual_cost_breakdown: Dict[str, float]
    value_proposition: str

class ScoringAgent:
    """Agent for scoring insurance policies on 3 key metrics"""
    
    def __init__(self):
        self.weights = {
            "affordability": 0.4,     # 40% weight
            "ease_of_claims": 0.25,   # 25% weight  
            "coverage_ratio": 0.35    # 35% weight
        }
        
        # Claims ease scoring database (could be moved to external data source)
        self.company_claims_ratings = {
            "LifeSecure Corp": {"ease_score": 85, "avg_processing_days": 12, "approval_rate": 0.94},
            "HealthGuard Insurance": {"ease_score": 78, "avg_processing_days": 18, "approval_rate": 0.89},
            "PrimeCare Solutions": {"ease_score": 92, "avg_processing_days": 8, "approval_rate": 0.97},
            "SecureLife Partners": {"ease_score": 73, "avg_processing_days": 22, "approval_rate": 0.86},
            "Guardian Health": {"ease_score": 88, "avg_processing_days": 10, "approval_rate": 0.95},
        }
    
    def score_policy(self, plan: QuotePlan, applicant: ApplicantProfile) -> PolicyScore:
        """Score a single policy on all three metrics"""
        
        # Calculate individual scores
        affordability_score, affordability_details = self._calculate_affordability_score(plan, applicant)
        claims_score, claims_details = self._calculate_claims_ease_score(plan)
        coverage_score, coverage_details = self._calculate_coverage_ratio_score(plan, applicant)
        
        # Calculate composite score
        overall_score = (
            affordability_score * self.weights["affordability"] +
            claims_score * self.weights["ease_of_claims"] +
            coverage_score * self.weights["coverage_ratio"]
        )
        
        # Determine overall category
        overall_category = self._score_to_category(overall_score)
        
        # Calculate income percentage
        income_percentage = self._calculate_income_percentage(plan, applicant)
        
        # Annual cost breakdown
        annual_breakdown = self._calculate_annual_costs(plan)
        
        # Generate value proposition
        value_prop = self._generate_value_proposition(
            plan, overall_score, affordability_score, claims_score, coverage_score
        )
        
        return PolicyScore(
            plan_id=plan.plan_id,
            plan_name=plan.plan_name,
            company_name=plan.company_name,
            affordability_score=affordability_score,
            ease_of_claims_score=claims_score,
            coverage_ratio_score=coverage_score,
            overall_score=overall_score,
            overall_category=overall_category,
            affordability_details=affordability_details,
            claims_ease_details=claims_details,
            coverage_ratio_details=coverage_details,
            income_percentage=income_percentage,
            annual_cost_breakdown=annual_breakdown,
            value_proposition=value_prop
        )
    
    def score_multiple_policies(self, plans: List[QuotePlan], applicant: ApplicantProfile) -> List[PolicyScore]:
        """Score multiple policies and return sorted by overall score"""
        scores = []
        
        for plan in plans:
            try:
                score = self.score_policy(plan, applicant)
                scores.append(score)
            except Exception as e:
                logger.error(f"Failed to score plan {plan.plan_id}: {e}")
        
        # Sort by overall score (descending)
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        return scores
    
    def _calculate_affordability_score(self, plan: QuotePlan, applicant: ApplicantProfile) -> tuple[float, Dict[str, Any]]:
        """
        Calculate affordability score (0-100) based on income percentage
        
        Scoring logic:
        - 0-2% of income = 100 points (Excellent)
        - 2-4% of income = 85 points (Very Good)  
        - 4-6% of income = 70 points (Good)
        - 6-8% of income = 55 points (Fair)
        - 8%+ of income = 40 points (Poor)
        """
        annual_income = applicant.annual_income or 50000  # Default fallback
        annual_premium = plan.total_annual_premium
        
        income_percentage = (annual_premium / annual_income) * 100
        
        # Score based on income percentage
        if income_percentage <= 2:
            score = 100
            category = "Excellent - Very affordable"
        elif income_percentage <= 4:
            score = 85
            category = "Very Good - Quite affordable"
        elif income_percentage <= 6:
            score = 70
            category = "Good - Reasonably affordable"
        elif income_percentage <= 8:
            score = 55
            category = "Fair - Somewhat expensive"
        else:
            score = 40
            category = "Poor - Very expensive relative to income"
        
        # Adjust score based on taxes and fees
        total_first_year_cost = annual_premium + (plan.taxes_fees * 12)
        if plan.taxes_fees * 12 > annual_premium * 0.1:  # Taxes/fees > 10% of premium
            score -= 5
        
        # Deductible impact on affordability
        if plan.deductible:
            deductible_impact = min(plan.deductible / annual_income * 100, 10)  # Max 10 point reduction
            score -= deductible_impact
        
        score = max(0, min(100, score))  # Clamp to 0-100
        
        details = {
            "income_percentage": income_percentage,
            "annual_premium": annual_premium,
            "annual_income": annual_income,
            "category": category,
            "taxes_fees_annual": plan.taxes_fees * 12,
            "deductible": plan.deductible,
            "total_first_year_cost": total_first_year_cost
        }
        
        return score, details
    
    def _calculate_claims_ease_score(self, plan: QuotePlan) -> tuple[float, Dict[str, Any]]:
        """
        Calculate ease of claims score based on company performance data
        
        This could be enhanced with real-time data from insurance regulators,
        customer reviews, industry reports, etc.
        """
        company_name = plan.company_name
        
        # Get company data or use default
        company_data = self.company_claims_ratings.get(company_name, {
            "ease_score": 75,  # Default average score
            "avg_processing_days": 15,
            "approval_rate": 0.90
        })
        
        base_score = company_data["ease_score"]
        
        # Adjust score based on plan features
        score_adjustments = 0
        
        # For QuotePlan, we don't have approval info, so base on company rating
        if plan.company_rating >= 4.5:
            score_adjustments += 5
        elif plan.company_rating <= 3.0:
            score_adjustments -= 5
        
        # Higher deductibles may indicate more complex claims
        if plan.deductible and plan.deductible > 2500:
            score_adjustments -= 3
        elif plan.deductible and plan.deductible == 0:
            score_adjustments += 2
        
        final_score = max(0, min(100, base_score + score_adjustments))
        
        details = {
            "company_base_score": company_data["ease_score"],
            "avg_processing_days": company_data["avg_processing_days"],
            "approval_rate": company_data["approval_rate"],
            "company_rating": plan.company_rating,
            "deductible": plan.deductible,
            "score_adjustments": score_adjustments,
            "category": self._score_to_category(final_score).value
        }
        
        return final_score, details
    
    def _calculate_coverage_ratio_score(self, plan: QuotePlan, applicant: ApplicantProfile) -> tuple[float, Dict[str, Any]]:
        """
        Calculate coverage-to-payment ratio score
        
        This measures how much coverage you get per dollar spent
        Higher coverage amounts and more benefits = higher score
        """
        annual_premium = plan.total_annual_premium
        coverage_amount = plan.coverage_amount
        
        # Base ratio: coverage amount per dollar of premium
        coverage_per_dollar = coverage_amount / annual_premium
        
        # Normalize the ratio to a 0-100 score
        # These benchmarks could be calibrated based on market data
        if coverage_per_dollar >= 200:  # $200+ coverage per $1 premium
            base_score = 95
        elif coverage_per_dollar >= 150:
            base_score = 85
        elif coverage_per_dollar >= 100:
            base_score = 75
        elif coverage_per_dollar >= 75:
            base_score = 65
        elif coverage_per_dollar >= 50:
            base_score = 55
        else:
            base_score = 45
        
        # Adjust for benefits and features
        feature_bonus = 0
        # QuotePlan doesn't have key_features, so use coverage_details and rider_premiums
        feature_count = len(plan.coverage_details) + len(plan.rider_premiums)
        feature_bonus += min(feature_count * 2, 15)  # Max 15 bonus points
        
        # Penalty for high deductibles (reduces effective coverage)
        deductible_penalty = 0
        if plan.deductible:
            deductible_ratio = plan.deductible / coverage_amount
            if deductible_ratio > 0.1:  # Deductible > 10% of coverage
                deductible_penalty = min(deductible_ratio * 50, 20)  # Max 20 point penalty
        
        # Waiting periods reduce value
        waiting_penalty = 0
        if plan.waiting_periods:
            avg_waiting_days = sum(plan.waiting_periods.values()) / len(plan.waiting_periods) if plan.waiting_periods else 0
            if avg_waiting_days > 90:  # More than 3 months waiting
                waiting_penalty = min((avg_waiting_days - 90) / 30 * 2, 10)  # Max 10 point penalty
        
        final_score = max(0, min(100, base_score + feature_bonus - deductible_penalty - waiting_penalty))
        
        details = {
            "coverage_per_dollar": coverage_per_dollar,
            "coverage_amount": coverage_amount,
            "annual_premium": annual_premium,
            "base_score": base_score,
            "feature_bonus": feature_bonus,
            "feature_count": feature_count,
            "deductible_penalty": deductible_penalty,
            "waiting_penalty": waiting_penalty,
            "coverage_details": plan.coverage_details,
            "rider_premiums": plan.rider_premiums,
            "waiting_periods": plan.waiting_periods,
            "category": self._score_to_category(final_score).value
        }
        
        return final_score, details
    
    def _calculate_income_percentage(self, plan: QuotePlan, applicant: ApplicantProfile) -> float:
        """Calculate what percentage of income goes to this insurance"""
        annual_income = applicant.annual_income or 50000
        return (plan.total_annual_premium / annual_income) * 100
    
    def _calculate_annual_costs(self, plan: QuotePlan) -> Dict[str, float]:
        """Break down all annual costs"""
        return {
            "base_premium": plan.base_premium * 12,
            "rider_premiums": sum(plan.rider_premiums.values()) * 12,
            "taxes_fees": plan.taxes_fees * 12,
            "estimated_deductible": plan.deductible or 0,
            "total_annual_premium": plan.total_annual_premium,
            "total_with_deductible": plan.total_annual_premium + (plan.deductible or 0)
        }
    
    def _generate_value_proposition(self, plan: QuotePlan, overall_score: float, 
                                   affordability: float, claims: float, coverage: float) -> str:
        """Generate a value proposition summary"""
        
        strengths = []
        if affordability >= 80:
            strengths.append("very affordable")
        if claims >= 85:
            strengths.append("easy claims process")
        if coverage >= 80:
            strengths.append("excellent coverage value")
        
        weaknesses = []
        if affordability < 60:
            weaknesses.append("expensive relative to income")
        if claims < 65:
            weaknesses.append("complex claims process")
        if coverage < 65:
            weaknesses.append("limited coverage value")
        
        if overall_score >= 85:
            opening = "Excellent choice"
        elif overall_score >= 75:
            opening = "Very good option"
        elif overall_score >= 65:
            opening = "Solid choice"
        else:
            opening = "Consider alternatives"
        
        if strengths:
            value_prop = f"{opening} with {', '.join(strengths)}."
        else:
            value_prop = f"{opening} for your situation."
        
        if weaknesses:
            value_prop += f" Note: {', '.join(weaknesses)}."
        
        return value_prop
    
    def _score_to_category(self, score: float) -> ScoreCategory:
        """Convert numeric score to category"""
        if score >= 90:
            return ScoreCategory.EXCELLENT
        elif score >= 80:
            return ScoreCategory.VERY_GOOD
        elif score >= 70:
            return ScoreCategory.GOOD
        elif score >= 60:
            return ScoreCategory.FAIR
        else:
            return ScoreCategory.POOR

# Singleton instance
_scoring_agent = None

def get_scoring_agent() -> ScoringAgent:
    """Get singleton scoring agent instance"""
    global _scoring_agent
    if _scoring_agent is None:
        _scoring_agent = ScoringAgent()
    return _scoring_agent

# Helper functions
def score_insurance_policies(plans: List[QuotePlan], applicant: ApplicantProfile) -> List[PolicyScore]:
    """Score multiple insurance policies"""
    agent = get_scoring_agent()
    return agent.score_multiple_policies(plans, applicant)

def score_single_policy(plan: QuotePlan, applicant: ApplicantProfile) -> PolicyScore:
    """Score a single insurance policy"""
    agent = get_scoring_agent()
    return agent.score_policy(plan, applicant)

if __name__ == "__main__":
    # Test the scoring system
    print("Insurance Scoring Agent loaded successfully")