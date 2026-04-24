from django.shortcuts import render


def landing_page(request):
    """
    Renders the beautiful landing page for QueueLess.
    Satisfies US-11 requirements.
    """
    return render(request, "landing.html")
