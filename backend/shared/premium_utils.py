"""
Premium Standardization Utilities
=================================
Helper functions to standardize insurance premium costs across different time periods
"""

def standardize_premium_costs(amount: float, period: str) -> dict:
    """
    Convert premium costs to standard units (daily, monthly, annual)
    
    Args:
        amount: Premium amount as float
        period: Period string (day, daily, month, monthly, year, yearly, annual, week, weekly)
        
    Returns:
        Dict with standardized costs: daily, monthly, annual
        
    Examples:
        >>> standardize_premium_costs(0.831, "day")
        {'daily': 0.831, 'monthly': 25.3, 'annual': 303.31, ...}
        
        >>> standardize_premium_costs(25, "month") 
        {'daily': 0.822, 'monthly': 25.0, 'annual': 300.08, ...}
    """
    period_lower = period.lower().strip()
    
    # Normalize period names
    if period_lower in ['day', 'daily', 'per day', '/day', 'd']:
        daily_rate = amount
    elif period_lower in ['week', 'weekly', 'per week', '/week', 'w']:
        daily_rate = amount / 7
    elif period_lower in ['month', 'monthly', 'per month', '/month', 'm']:
        daily_rate = amount / 30.44  # Average days per month
    elif period_lower in ['year', 'yearly', 'annual', 'annually', 'per year', '/year', 'y']:
        daily_rate = amount / 365
    elif period_lower in ['quarter', 'quarterly', 'per quarter', '/quarter', 'q']:
        daily_rate = amount / (365 / 4)
    elif period_lower in ['semi-annual', 'semi-annually', 'twice yearly']:
        daily_rate = amount / (365 / 2)
    else:
        # Default to monthly if period is unclear
        print(f"⚠️  Unknown period '{period}', defaulting to monthly")
        daily_rate = amount / 30.44
    
    # Calculate all standard formats
    weekly_rate = daily_rate * 7
    monthly_rate = daily_rate * 30.44
    quarterly_rate = daily_rate * (365 / 4)
    annual_rate = daily_rate * 365
    
    return {
        'daily': round(daily_rate, 3),
        'weekly': round(weekly_rate, 2),
        'monthly': round(monthly_rate, 2), 
        'quarterly': round(quarterly_rate, 2),
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
        'weekly_formatted': f"{currency}{standardized_costs['weekly']:.2f}/week",
        'monthly_formatted': f"{currency}{standardized_costs['monthly']:.2f}/month", 
        'quarterly_formatted': f"{currency}{standardized_costs['quarterly']:,.2f}/quarter",
        'annual_formatted': f"{currency}{standardized_costs['annual']:,.2f}/year",
        'daily_raw': standardized_costs['daily'],
        'weekly_raw': standardized_costs['weekly'],
        'monthly_raw': standardized_costs['monthly'],
        'quarterly_raw': standardized_costs['quarterly'],
        'annual_raw': standardized_costs['annual']
    }

def compare_premiums(premium1: dict, premium2: dict, comparison_period: str = "annual") -> dict:
    """
    Compare two standardized premiums
    
    Args:
        premium1: First premium (from standardize_premium_costs)
        premium2: Second premium (from standardize_premium_costs)
        comparison_period: Period to use for comparison (daily, weekly, monthly, annual)
        
    Returns:
        Dict with comparison results
    """
    if comparison_period not in premium1 or comparison_period not in premium2:
        raise ValueError(f"Invalid comparison period: {comparison_period}")
    
    cost1 = premium1[comparison_period]
    cost2 = premium2[comparison_period]
    
    difference = cost2 - cost1
    percentage_diff = (difference / cost1) * 100 if cost1 != 0 else 0
    
    if difference > 0:
        comparison_text = f"Premium 2 costs ${abs(difference):.2f} more per {comparison_period} ({percentage_diff:+.1f}%)"
        cheaper_option = "premium1"
    elif difference < 0:
        comparison_text = f"Premium 2 costs ${abs(difference):.2f} less per {comparison_period} ({percentage_diff:+.1f}%)"
        cheaper_option = "premium2"
    else:
        comparison_text = f"Both premiums cost the same per {comparison_period}"
        cheaper_option = "equal"
    
    return {
        'premium1_cost': cost1,
        'premium2_cost': cost2,
        'difference': difference,
        'percentage_difference': percentage_diff,
        'cheaper_option': cheaper_option,
        'comparison_text': comparison_text,
        'comparison_period': comparison_period
    }

def calculate_coverage_value_ratio(coverage_amount: float, premium_annual: float) -> dict:
    """
    Calculate coverage value ratio (coverage per dollar of premium)
    
    Args:
        coverage_amount: Total coverage amount
        premium_annual: Annual premium cost
        
    Returns:
        Dict with value ratio calculations
    """
    if premium_annual <= 0:
        return {
            'coverage_per_dollar': 0,
            'cost_per_1000_coverage': 0,
            'value_rating': 'undefined',
            'error': 'Premium must be greater than 0'
        }
    
    coverage_per_dollar = coverage_amount / premium_annual
    cost_per_1000_coverage = (premium_annual / coverage_amount) * 1000
    
    # Value rating based on coverage per dollar
    if coverage_per_dollar >= 3000:
        value_rating = 'excellent'
    elif coverage_per_dollar >= 2000:
        value_rating = 'very_good'
    elif coverage_per_dollar >= 1500:
        value_rating = 'good'
    elif coverage_per_dollar >= 1000:
        value_rating = 'fair'
    else:
        value_rating = 'poor'
    
    return {
        'coverage_per_dollar': round(coverage_per_dollar, 2),
        'cost_per_1000_coverage': round(cost_per_1000_coverage, 2),
        'value_rating': value_rating,
        'coverage_amount': coverage_amount,
        'annual_premium': premium_annual
    }

def extract_premium_from_text(text: str) -> list:
    """
    Extract and standardize all premium information found in text
    
    Args:
        text: Text to search for premium patterns
        
    Returns:
        List of standardized premium dictionaries
    """
    import re
    
    premiums = []
    
    # Enhanced patterns to catch various premium formats
    patterns = [
        r'([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*per\s*(day|week|month|quarter|year)',
        r'([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*(?:/|per)\s*(day|week|month|quarter|year)',
        r'(\d+(?:\.\d{1,3})?)\s*([s\$£€¥]?)\s*(?:daily|weekly|monthly|quarterly|yearly|annually)',
        r'premium\s*:?\s*([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*(?:/|per)?\s*(day|week|month|quarter|year)?',
        r'rate\s*:?\s*([s\$£€¥]?)(\d+(?:\.\d{1,3})?)\s*(?:/|per)?\s*(day|week|month|quarter|year)?'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower(), re.IGNORECASE)
        for match in matches:
            if len(match) >= 3:
                currency = match[0] if match[0] else '$'
                try:
                    amount = float(match[1])
                    period = match[2] if len(match) > 2 and match[2] else 'month'
                    
                    # Standardize the premium
                    standardized = standardize_premium_costs(amount, period)
                    
                    # Add formatting
                    formatted = format_premium_display(standardized, currency)
                    
                    # Combine into complete premium info
                    premium_info = {
                        **standardized,
                        **formatted,
                        'currency': currency,
                        'found_in_text': True,
                        'original_text_match': match
                    }
                    
                    premiums.append(premium_info)
                    
                except (ValueError, TypeError):
                    continue
    
    # Remove duplicates (same daily rate)
    unique_premiums = []
    seen_rates = set()
    
    for premium in premiums:
        daily_rate = premium['daily']
        if daily_rate not in seen_rates:
            unique_premiums.append(premium)
            seen_rates.add(daily_rate)
    
    return unique_premiums

# Test function
if __name__ == "__main__":
    # Test the functions
    print("🔧 Testing Premium Standardization Utils")
    print("=" * 50)
    
    # Test standardization
    test_premium = standardize_premium_costs(0.831, "day")
    formatted = format_premium_display(test_premium)
    
    print("Original: $0.831/day")
    print(f"Standardized: {formatted['annual_formatted']}")
    
    # Test comparison
    premium1 = standardize_premium_costs(25, "month")
    premium2 = standardize_premium_costs(350, "year")
    comparison = compare_premiums(premium1, premium2, "annual")
    print(f"\nComparison: {comparison['comparison_text']}")
    
    # Test value ratio
    value_ratio = calculate_coverage_value_ratio(1000000, 303.31)
    print(f"Value Ratio: {value_ratio['coverage_per_dollar']:.0f} coverage per $1 premium ({value_ratio['value_rating']})")