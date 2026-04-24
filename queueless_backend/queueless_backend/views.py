from django.shortcuts import redirect


def landing_page(request):
    """
    Redirects the user to the landing page.
    """
    return redirect("https://queue-less-phi.vercel.app")
