from datetime import date


def status_for_expiry(expiry_date: date) -> str:
    today = date.today()
    if expiry_date < today:
        return "expired"
    days = (expiry_date - today).days
    if days <= 30:
        return "expiring"
    return "valid"
