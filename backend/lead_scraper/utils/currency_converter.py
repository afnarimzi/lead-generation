"""Currency conversion utility for normalizing budgets to USD."""

import re
from typing import Optional, Tuple
from decimal import Decimal


# Exchange rates (approximate, update periodically)
EXCHANGE_RATES = {
    'USD': 1.0,
    'GBP': 1.27,  # 1 GBP = 1.27 USD
    'EUR': 1.09,  # 1 EUR = 1.09 USD
    'INR': 0.012, # 1 INR = 0.012 USD
    'AUD': 0.65,  # 1 AUD = 0.65 USD
    'CAD': 0.74,  # 1 CAD = 0.74 USD
}


def extract_currency_and_amount(budget_str: str) -> Optional[Tuple[str, float]]:
    """
    Extract currency code and amount from budget string.
    
    Examples:
        "₹50000" → ("INR", 50000)
        "$1000" → ("USD", 1000)
        "£500" → ("GBP", 500)
        "€800" → ("EUR", 800)
        "1000 USD" → ("USD", 1000)
        "500-1000" → ("USD", 750)  # average
    
    Args:
        budget_str: Budget string with currency symbol or code
        
    Returns:
        Tuple of (currency_code, amount) or None if parsing fails
    """
    if not budget_str:
        return None
    
    budget_str = str(budget_str).strip()
    
    # Currency symbols to codes
    symbol_map = {
        '$': 'USD',
        '£': 'GBP',
        '€': 'EUR',
        '₹': 'INR',
        'A$': 'AUD',
        'C$': 'CAD',
    }
    
    # Try to find currency symbol
    currency = 'USD'  # default
    for symbol, code in symbol_map.items():
        if symbol in budget_str:
            currency = code
            budget_str = budget_str.replace(symbol, '').strip()
            break
    
    # Try to find currency code (USD, GBP, EUR, INR, etc.)
    currency_match = re.search(r'\b(USD|GBP|EUR|INR|AUD|CAD)\b', budget_str, re.IGNORECASE)
    if currency_match:
        currency = currency_match.group(1).upper()
        budget_str = re.sub(r'\b(USD|GBP|EUR|INR|AUD|CAD)\b', '', budget_str, flags=re.IGNORECASE).strip()
    
    # Remove commas and other non-numeric characters except dots, hyphens, and spaces
    budget_str = re.sub(r'[^\d.\-\s]', '', budget_str)
    
    # Handle range (e.g., "500-1000" or "500 - 1000")
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', budget_str)
    if range_match:
        min_amount = float(range_match.group(1))
        max_amount = float(range_match.group(2))
        amount = (min_amount + max_amount) / 2  # Take average
        return (currency, amount)
    
    # Extract single number
    number_match = re.search(r'(\d+(?:\.\d+)?)', budget_str)
    if number_match:
        amount = float(number_match.group(1))
        return (currency, amount)
    
    return None


def convert_to_usd(amount: float, from_currency: str) -> float:
    """
    Convert amount from given currency to USD.
    
    Args:
        amount: Amount in source currency
        from_currency: Source currency code (USD, GBP, EUR, INR, etc.)
        
    Returns:
        Amount in USD
    """
    from_currency = from_currency.upper()
    
    if from_currency not in EXCHANGE_RATES:
        # Unknown currency, assume USD
        return amount
    
    rate = EXCHANGE_RATES[from_currency]
    return amount * rate


def normalize_budget_to_usd(budget_value: any) -> Optional[float]:
    """
    Normalize budget value to USD.
    
    Handles:
    - Numeric values (assumed USD)
    - String values with currency symbols/codes
    - Decimal types from database
    - Range values (takes average)
    
    Args:
        budget_value: Budget value (str, int, float, Decimal, or None)
        
    Returns:
        Budget in USD or None if parsing fails
    """
    if budget_value is None:
        return None
    
    # Handle Decimal from database
    if isinstance(budget_value, Decimal):
        return float(budget_value)
    
    # Handle numeric types (assume USD)
    if isinstance(budget_value, (int, float)):
        return float(budget_value)
    
    # Handle string with currency
    if isinstance(budget_value, str):
        result = extract_currency_and_amount(budget_value)
        if result:
            currency, amount = result
            return convert_to_usd(amount, currency)
    
    return None


def format_budget_usd(amount: Optional[float]) -> str:
    """
    Format budget amount as USD string.
    
    Args:
        amount: Amount in USD
        
    Returns:
        Formatted string like "$1,234" or "N/A"
    """
    if amount is None:
        return "N/A"
    
    return f"${amount:,.0f}"
