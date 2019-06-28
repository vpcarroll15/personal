from django.shortcuts import render
from django.http import HttpResponse


# Create your views here.
def aboutme(request):
    """Displays the page that explains my ratings philosophy."""
    return HttpResponse("Hello, world. You're at the polls index.")
