from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

from ..models.credit import Credit
from ..services import calculate_credit

User = get_user_model()


@csrf_exempt
def credit_request_api(request):

    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Faqat POST ishlaydi"
        })

    username = request.POST.get("username")
    amount = request.POST.get("amount")
    years = request.POST.get("years")

    # 🔥 USER CHECK
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Bunday user mavjud emas"
        })

    if not amount or not years:
        return JsonResponse({
            "status": "error",
            "message": "amount va years kerak"
        })

    amount = float(amount)
    years = int(years)

    # 🔥 CALC
    ok, result = calculate_credit(user, years, amount)

    credit = Credit.objects.create(
        user=user,
        amount=amount,
        years=years,
        monthly_payment=result if ok else 0,
        is_approved=ok,
        reason="Tasdiqlandi" if ok else result
    )

    if ok:
        return JsonResponse({
            "status": "ok",
            "message": "Tasdiqlandi",
            "monthly_payment": result
        })

    return JsonResponse({
        "status": "error",
        "message": result
    })