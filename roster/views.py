from django.shortcuts import render


def home(request):
    """Simple home page."""
    return render(request, "home.html")
