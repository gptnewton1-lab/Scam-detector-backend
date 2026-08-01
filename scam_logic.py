from typing import List, Tuple

def analyze_text(text: str) -> Tuple[int, str, List[str]]:
    text_lower = text.lower()
    score = 0
    reasons: List[str] = []

    urgent_words = [
        "urgent", "immediately", "act now", "limited time", 
        "offer expires", "do not miss out", "last chance", 
        "sign up now", "limited slot available", "register now"
    ]

    payment_words = [
        "send money", "credit card", "bank account", "momo", 
        "paypal", "orange money", "gift card", "bitcoin", 
        "pay", "enter now", "connect with ur bankaccount", "win prizes"
    ]

    scam_words = [
        "claim", "bonus", "prize", "verify account", 
        "click to recieve", "first $5000"
    ]

    # Count actual matches to allow scalable, dynamic scoring
    urgent_matches = [w for w in urgent_words if w in text_lower]
    payment_matches = [w for w in payment_words if w in text_lower]
    scam_matches = [w for w in scam_words if w in text_lower]

    # Accumulate scores based on density of triggers
    if urgent_matches:
        # Base points + extra points per additional match
        score += 15 + (len(urgent_matches) - 1) * 5
        reasons.append(f"Urgency language detected ({len(urgent_matches)} flags)")

    if payment_matches:
        score += 20 + (len(payment_matches) - 1) * 10
        reasons.append(f"Payment request detected ({len(payment_matches)} flags)")

    if scam_matches:
        score += 10 + (len(scam_matches) - 1) * 5
        reasons.append(f"Scam language detected ({len(scam_matches)} flags)")

    # Enforce strict maximum bounds
    if score > 100:
        score = 100

    # Classify structural risk labels
    if score >= 60:
        label = "dangerous, potential scam"
    elif score >= 40:
        label = "likely scam"
    elif score >= 20:
        label = "suspicious"
    else:
        label = "safe"

    return score, label, reasons
