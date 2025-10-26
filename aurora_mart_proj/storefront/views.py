from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    # simple placeholder response — swap for a real template later
    return HttpResponse("<h1>AuroraMart Storefront (placeholder)</h1><p>Replace with real storefront.</p>")