from django.shortcuts import render
from django.views.generic import View

class LandingPageView(View):
    template_name = 'landingpage.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
