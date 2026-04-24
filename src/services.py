def calculate_credit(user, years, amount):
    salary = float(user.salary)

    expense = 2500000 if user.is_married else 2000000

    available = salary - expense

    if available <= 0:
        return False, "Daromad yetarli emas"

    max_credit = available * (years * 12)

    if amount > max_credit:
        return False, "Sizning sorovingiz rad etildi"

    monthly_payment = amount / (years * 12)

    return True, monthly_payment