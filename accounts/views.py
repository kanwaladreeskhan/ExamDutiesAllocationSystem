from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect


def post_login_redirect(request):
    if request.user.role == "COORDINATOR":
        return redirect("coordinator")
    return redirect("dashboard")