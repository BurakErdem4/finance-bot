import pandas as pd

def calculate_rebalance(new_investment_tl, current_values, target_percentages):
    """
    Calculates how to distribute new investment to reach target allocation.
    
    Args:
        new_investment_tl (float): Amount of new money to invest.
        current_values (dict): Current asset values {Category: Value}.
        target_percentages (dict): Target percentages {Category: Percentage (0-100)}.
        
    Returns:
        dict: Suggestions {Category: Amount to Invest}.
    """
    # 1. Total portfolio value after investment
    current_total = sum(current_values.values())
    future_total = current_total + new_investment_tl
    
    # 2. Calculate target values for each category
    targets = {cat: (pct / 100) * future_total for cat, pct in target_percentages.items()}
    
    # 3. Calculate the gaps (Target - Current)
    gaps = {cat: targets[cat] - current_values.get(cat, 0) for cat in target_percentages}
    
    # 4. Filter only positive gaps (where we need to buy)
    # If a gap is negative, it means we are already over target, we won't buy more.
    positive_gaps = {cat: max(0, gap) for cat, gap in gaps.items()}
    total_positive_gap = sum(positive_gaps.values())
    
    # 5. Distribute the new investment proportionally based on the gaps
    # If total_positive_gap is 0 (all categories over target somehow), distribute by target percentages
    suggestions = {}
    if total_positive_gap > 0:
        for cat, gap in positive_gaps.items():
            # Amount to allocate is safe to be up to the gap or scaled down to fit investment
            allocation = (gap / total_positive_gap) * new_investment_tl
            suggestions[cat] = round(allocation, 2)
    else:
        # Fallback to target percentages if no clear gaps (unlikely with new money)
        for cat, pct in target_percentages.items():
            suggestions[cat] = round((pct / 100) * new_investment_tl, 2)
            
    return suggestions

def get_rebalance_summary(suggestions):
    """
    Formats suggestions into a human readable text.
    """
    lines = []
    for cat, amount in suggestions.items():
        if amount > 0:
            lines.append(f"{amount:,.0f} TL ile **{cat}** almalısın.")
    
    if not lines:
        return "Mevcut yatırım tutarı ile yapılacak bir işlem önerilmiyor."
    
    return "Hedefine ulaşmak için: " + ", ".join(lines)
