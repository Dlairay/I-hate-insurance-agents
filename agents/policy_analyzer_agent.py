"""
Policy Analyzer Agent
=====================
Analyzes existing insurance policies to detect over-coverage, gaps, and savings opportunities
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class CoverageAnalysis(str, Enum):
    OVER_INSURED = "over_insured"
    ADEQUATELY_INSURED = "adequately_insured"
    UNDER_INSURED = "under_insured"
    NO_COVERAGE = "no_coverage"

class PolicyRecommendation(str, Enum):
    NO_ACTION_NEEDED = "no_action_needed"
    REDUCE_COVERAGE = "reduce_coverage"
    ADD_SUPPLEMENTAL = "add_supplemental"
    SWITCH_PROVIDER = "switch_provider"
    GET_NEW_COVERAGE = "get_new_coverage"

class ExistingPolicyAnalysis(BaseModel):
    """Results of analyzing existing insurance policies"""
    
    # Coverage Analysis
    coverage_status: CoverageAnalysis
    coverage_gaps: List[str]
    over_coverage_areas: List[str]
    
    # Financial Analysis
    current_monthly_cost: float
    potential_monthly_savings: float
    coverage_to_income_ratio: float
    
    # Recommendations
    primary_recommendation: PolicyRecommendation
    recommendation_reason: str
    specific_actions: List[str]
    
    # Risk Assessment
    uncovered_risks: List[str]
    adequately_covered_risks: List[str]
    
    # Savings Opportunities
    can_save_money: bool
    savings_explanation: str
    recommended_coverage_amount: float

class PolicyAnalyzerAgent:
    """Agent that analyzes existing policies for gaps and over-coverage"""
    
    def __init__(self):
        # Industry benchmarks for coverage analysis
        self.coverage_benchmarks = {
            "health": {
                "min_coverage": 50000,
                "adequate_coverage": 100000,
                "max_reasonable": 500000
            },
            "life": {
                "min_multiplier": 5,  # 5x annual income minimum
                "adequate_multiplier": 10,  # 10x annual income adequate
                "max_multiplier": 20  # 20x annual income maximum
            },
            "critical_illness": {
                "min_coverage": 25000,
                "adequate_coverage": 50000,
                "max_reasonable": 200000
            }
        }
        
        # Cost benchmarks as % of income
        self.cost_benchmarks = {
            "optimal_range": (2, 6),  # 2-6% of income
            "warning_threshold": 8,  # Above 8% is concerning
            "over_insured_threshold": 10  # Above 10% likely over-insured
        }
    
    def analyze_existing_policy(
        self,
        existing_coverage_type: str,
        existing_coverage_amount: float,
        existing_monthly_premium: float,
        annual_income: float,
        age: int,
        health_status: str,
        primary_need: str
    ) -> ExistingPolicyAnalysis:
        """
        Analyze existing insurance policy for optimization opportunities
        
        Args:
            existing_coverage_type: Type of existing coverage (employer, individual, etc.)
            existing_coverage_amount: Current total coverage amount
            existing_monthly_premium: Current monthly premium
            annual_income: User's annual income
            age: User's age
            health_status: Self-reported health status
            primary_need: User's primary insurance need
            
        Returns:
            ExistingPolicyAnalysis with recommendations
        """
        
        # Calculate key metrics
        coverage_to_income_ratio = existing_coverage_amount / annual_income
        premium_to_income_ratio = (existing_monthly_premium * 12) / annual_income * 100
        
        # Analyze coverage adequacy
        coverage_status = self._determine_coverage_status(
            existing_coverage_amount, annual_income, age, health_status
        )
        
        # Identify gaps and over-coverage
        coverage_gaps = self._identify_coverage_gaps(
            existing_coverage_type, existing_coverage_amount, age, health_status
        )
        
        over_coverage_areas = self._identify_over_coverage(
            existing_coverage_amount, annual_income, age, existing_coverage_type
        )
        
        # Calculate potential savings
        potential_savings = self._calculate_potential_savings(
            existing_monthly_premium, existing_coverage_amount, annual_income, age
        )
        
        # Generate recommendation
        recommendation, reason = self._generate_recommendation(
            coverage_status, primary_need, premium_to_income_ratio, coverage_gaps
        )
        
        # Specific actions
        specific_actions = self._generate_specific_actions(
            recommendation, coverage_gaps, over_coverage_areas, primary_need
        )
        
        # Risk assessment
        uncovered_risks = self._identify_uncovered_risks(existing_coverage_type, age, health_status)
        covered_risks = self._identify_covered_risks(existing_coverage_type)
        
        # Recommended coverage amount
        recommended_coverage = self._calculate_recommended_coverage(
            annual_income, age, health_status, existing_coverage_type
        )
        
        return ExistingPolicyAnalysis(
            coverage_status=coverage_status,
            coverage_gaps=coverage_gaps,
            over_coverage_areas=over_coverage_areas,
            current_monthly_cost=existing_monthly_premium,
            potential_monthly_savings=potential_savings,
            coverage_to_income_ratio=coverage_to_income_ratio,
            primary_recommendation=recommendation,
            recommendation_reason=reason,
            specific_actions=specific_actions,
            uncovered_risks=uncovered_risks,
            adequately_covered_risks=covered_risks,
            can_save_money=potential_savings > 0,
            savings_explanation=self._explain_savings(potential_savings, coverage_status),
            recommended_coverage_amount=recommended_coverage
        )
    
    def _determine_coverage_status(
        self, coverage_amount: float, annual_income: float, age: int, health_status: str
    ) -> CoverageAnalysis:
        """Determine if user is over/under/adequately insured"""
        
        if coverage_amount == 0:
            return CoverageAnalysis.NO_COVERAGE
        
        # Calculate ideal coverage based on income and age
        ideal_multiplier = self._get_ideal_multiplier(age, health_status)
        ideal_coverage = annual_income * ideal_multiplier
        
        coverage_ratio = coverage_amount / ideal_coverage
        
        if coverage_ratio < 0.5:
            return CoverageAnalysis.UNDER_INSURED
        elif coverage_ratio > 1.5:
            return CoverageAnalysis.OVER_INSURED
        else:
            return CoverageAnalysis.ADEQUATELY_INSURED
    
    def _get_ideal_multiplier(self, age: int, health_status: str) -> float:
        """Get ideal coverage multiplier based on age and health"""
        
        # Base multiplier
        if age < 30:
            base_multiplier = 8
        elif age < 40:
            base_multiplier = 10
        elif age < 50:
            base_multiplier = 12
        else:
            base_multiplier = 8
        
        # Adjust for health
        health_adjustments = {
            "excellent": -1,
            "good": 0,
            "fair": 1,
            "poor": 2
        }
        
        health_adjustment = health_adjustments.get(health_status, 0)
        
        return max(5, base_multiplier + health_adjustment)
    
    def _identify_coverage_gaps(
        self, coverage_type: str, coverage_amount: float, age: int, health_status: str
    ) -> List[str]:
        """Identify gaps in current coverage"""
        
        gaps = []
        
        # Check for basic gaps based on coverage type
        if coverage_type == "employer_only":
            gaps.append("Limited provider network")
            gaps.append("No coverage if you leave job")
            if coverage_amount < 100000:
                gaps.append("Low coverage amount for serious illness")
        
        elif coverage_type == "individual_basic":
            gaps.append("May lack comprehensive prescription coverage")
            gaps.append("Limited specialist access")
        
        # Age-specific gaps
        if age > 40 and coverage_amount < 200000:
            gaps.append("Insufficient coverage for age-related health risks")
        
        if age < 30 and coverage_type != "none":
            if "critical_illness" not in coverage_type.lower():
                gaps.append("No critical illness coverage (important for young adults)")
        
        # Health-specific gaps
        if health_status in ["fair", "poor"]:
            if coverage_amount < 250000:
                gaps.append("Coverage may be insufficient for chronic conditions")
        
        return gaps
    
    def _identify_over_coverage(
        self, coverage_amount: float, annual_income: float, age: int, coverage_type: str
    ) -> List[str]:
        """Identify areas of over-coverage"""
        
        over_coverage = []
        
        # Check if coverage exceeds reasonable multiples
        coverage_ratio = coverage_amount / annual_income
        
        if coverage_ratio > 15:
            over_coverage.append(f"Coverage is {coverage_ratio:.1f}x income (10-12x usually sufficient)")
        
        # Age-specific over-coverage
        if age < 30 and coverage_amount > 500000:
            over_coverage.append("Very high coverage for young age (unless specific health concerns)")
        
        # Coverage type specific
        if "comprehensive" in coverage_type and coverage_amount > 300000:
            if age < 40:
                over_coverage.append("Comprehensive coverage may include unnecessary riders")
        
        return over_coverage
    
    def _calculate_potential_savings(
        self, current_premium: float, coverage_amount: float, annual_income: float, age: int
    ) -> float:
        """Calculate potential monthly savings by optimizing coverage"""
        
        # Estimate optimal premium based on benchmarks
        optimal_premium_ratio = 0.04  # 4% of income is reasonable
        optimal_monthly_premium = (annual_income * optimal_premium_ratio) / 12
        
        # If paying more than optimal, calculate savings
        if current_premium > optimal_monthly_premium:
            # Could save 20-30% by switching or optimizing
            potential_savings = current_premium * 0.25
        else:
            potential_savings = 0
        
        # Additional savings for over-insurance
        if coverage_amount > annual_income * 15:
            # Over-insured, could reduce coverage
            potential_savings += current_premium * 0.15
        
        return round(potential_savings, 2)
    
    def _generate_recommendation(
        self, coverage_status: CoverageAnalysis, primary_need: str, 
        premium_ratio: float, coverage_gaps: List[str]
    ) -> Tuple[PolicyRecommendation, str]:
        """Generate primary recommendation and reason"""
        
        # Check primary need first
        if primary_need == "save_money" and premium_ratio > 6:
            return (
                PolicyRecommendation.SWITCH_PROVIDER,
                "Your premiums are high relative to income - switching could save money"
            )
        
        if primary_need == "fill_gaps" and coverage_gaps:
            return (
                PolicyRecommendation.ADD_SUPPLEMENTAL,
                f"You have {len(coverage_gaps)} coverage gaps that need addressing"
            )
        
        # Based on coverage status
        if coverage_status == CoverageAnalysis.OVER_INSURED:
            return (
                PolicyRecommendation.REDUCE_COVERAGE,
                "You're paying for more coverage than typically needed"
            )
        
        elif coverage_status == CoverageAnalysis.UNDER_INSURED:
            return (
                PolicyRecommendation.ADD_SUPPLEMENTAL,
                "Your current coverage may not be sufficient for major medical events"
            )
        
        elif coverage_status == CoverageAnalysis.NO_COVERAGE:
            return (
                PolicyRecommendation.GET_NEW_COVERAGE,
                "You need insurance coverage to protect against medical costs"
            )
        
        else:  # Adequately insured
            if premium_ratio > 8:
                return (
                    PolicyRecommendation.SWITCH_PROVIDER,
                    "Your coverage is good but you're paying too much"
                )
            else:
                return (
                    PolicyRecommendation.NO_ACTION_NEEDED,
                    "Your current coverage and pricing are appropriate"
                )
    
    def _generate_specific_actions(
        self, recommendation: PolicyRecommendation, gaps: List[str], 
        over_coverage: List[str], primary_need: str
    ) -> List[str]:
        """Generate specific action items"""
        
        actions = []
        
        if recommendation == PolicyRecommendation.REDUCE_COVERAGE:
            actions.append("Review and remove unnecessary riders")
            actions.append("Consider increasing deductible to lower premium")
            if over_coverage:
                actions.append(f"Reduce coverage amount (currently {over_coverage[0]})")
        
        elif recommendation == PolicyRecommendation.ADD_SUPPLEMENTAL:
            for gap in gaps[:3]:  # Top 3 gaps
                actions.append(f"Add coverage for: {gap}")
        
        elif recommendation == PolicyRecommendation.SWITCH_PROVIDER:
            actions.append("Get quotes from 3-5 different insurers")
            actions.append("Compare coverage levels carefully")
            actions.append("Check for bundle discounts")
        
        elif recommendation == PolicyRecommendation.GET_NEW_COVERAGE:
            actions.append("Start with basic health insurance")
            actions.append("Consider term life insurance if you have dependents")
            actions.append("Look into critical illness coverage")
        
        return actions
    
    def _identify_uncovered_risks(self, coverage_type: str, age: int, health_status: str) -> List[str]:
        """Identify risks not covered by current policy"""
        
        risks = []
        
        # Universal gaps
        if "employer" in coverage_type:
            risks.append("Job loss or career change")
        
        # Age-specific risks
        if age > 40:
            risks.append("Age-related chronic conditions")
            risks.append("Long-term care needs")
        
        if age < 35:
            risks.append("Sports or accident injuries")
        
        # Health-specific risks
        if health_status in ["fair", "poor"]:
            risks.append("Expensive specialist treatments")
            risks.append("Experimental treatments")
        
        return risks
    
    def _identify_covered_risks(self, coverage_type: str) -> List[str]:
        """Identify what's well covered"""
        
        covered = []
        
        if "comprehensive" in coverage_type:
            covered.extend([
                "Hospitalization",
                "Emergency care",
                "Preventive care",
                "Prescription drugs"
            ])
        elif "employer" in coverage_type:
            covered.extend([
                "Basic medical care",
                "In-network treatments",
                "Routine checkups"
            ])
        elif "individual" in coverage_type:
            covered.extend([
                "Major medical events",
                "Choice of providers"
            ])
        
        return covered
    
    def _calculate_recommended_coverage(
        self, annual_income: float, age: int, health_status: str, coverage_type: str
    ) -> float:
        """Calculate recommended coverage amount"""
        
        # Get ideal multiplier
        multiplier = self._get_ideal_multiplier(age, health_status)
        
        # Base recommendation
        recommended = annual_income * multiplier
        
        # Adjust for specific situations
        if "employer" in coverage_type:
            # Employer coverage typically needs supplementing
            recommended *= 1.2
        
        # Round to nearest 50k
        return round(recommended / 50000) * 50000
    
    def _explain_savings(self, savings: float, coverage_status: CoverageAnalysis) -> str:
        """Explain how savings can be achieved"""
        
        if savings == 0:
            return "Your current premiums are already optimized"
        
        if coverage_status == CoverageAnalysis.OVER_INSURED:
            return f"You could save ${savings:.0f}/month by reducing coverage to recommended levels"
        
        elif savings > 0:
            return f"Shopping for better rates could save you ${savings:.0f}/month"
        
        return "Optimizing your coverage could reduce costs"

# Helper function for easy usage
def analyze_existing_policy(
    existing_coverage: str,
    coverage_amount: str,
    monthly_premium: float,
    annual_income: float,
    age: int,
    health_status: str,
    primary_need: str
) -> ExistingPolicyAnalysis:
    """
    Analyze existing insurance policy
    
    Args:
        existing_coverage: Type from questionnaire (none, employer_only, etc.)
        coverage_amount: Range from questionnaire (under_50k, 50k_100k, etc.)
        monthly_premium: Current monthly payment
        annual_income: User's annual income
        age: User's age
        health_status: From questionnaire
        primary_need: User's primary goal
        
    Returns:
        Complete policy analysis with recommendations
    """
    
    # Convert coverage amount range to number
    coverage_mapping = {
        "none": 0,
        "under_50k": 25000,
        "50k_100k": 75000,
        "100k_250k": 175000,
        "250k_500k": 375000,
        "over_500k": 750000
    }
    
    coverage_amount_num = coverage_mapping.get(coverage_amount, 0)
    
    # Estimate monthly premium if not provided
    if monthly_premium == 0 and existing_coverage != "none":
        # Rough estimates based on coverage type
        premium_estimates = {
            "employer_only": annual_income * 0.02 / 12,
            "employer_comprehensive": annual_income * 0.04 / 12,
            "individual_basic": annual_income * 0.03 / 12,
            "individual_comprehensive": annual_income * 0.05 / 12,
            "parents": 50  # Nominal amount
        }
        monthly_premium = premium_estimates.get(existing_coverage, 100)
    
    analyzer = PolicyAnalyzerAgent()
    return analyzer.analyze_existing_policy(
        existing_coverage_type=existing_coverage,
        existing_coverage_amount=coverage_amount_num,
        existing_monthly_premium=monthly_premium,
        annual_income=annual_income,
        age=age,
        health_status=health_status,
        primary_need=primary_need
    )

if __name__ == "__main__":
    # Test the analyzer
    result = analyze_existing_policy(
        existing_coverage="employer_comprehensive",
        coverage_amount="250k_500k",
        monthly_premium=450,
        annual_income=75000,
        age=35,
        health_status="good",
        primary_need="save_money"
    )
    
    print(f"Coverage Status: {result.coverage_status.value}")
    print(f"Recommendation: {result.primary_recommendation.value}")
    print(f"Potential Savings: ${result.potential_monthly_savings}/month")
    print(f"Reason: {result.recommendation_reason}")