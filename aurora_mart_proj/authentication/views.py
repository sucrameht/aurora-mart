from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from .models import UserProfile
from .forms import RegistrationForm, onboardingForm, ChangePasswordForm
from django.urls import reverse_lazy
import os
from joblib import load
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# note that in CBVs, FormView helps to handle rendering via template_name
# to make use of isStaff for redirection, change_password requirements
class customLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = False

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        try:
            user_profile =  UserProfile.objects.get(user=user)
            if user_profile.is_initial_password:
                return reverse_lazy("change_password") # dynamically builds the url and returns the string URL lazily 
        
        except UserProfile.DoesNotExist:
            # create the user to redirect to onboarding
            return reverse_lazy("onboarding")
        
        if user.is_staff:
            return reverse_lazy("auroraadmin:admin_dashboard") # for admins - yet to create
        
        return reverse_lazy("storefront_home") # for customers - yet to create

# comes here from the login page    
class RegisterView(FormView):
    template_name = "authentication/register.html"
    form_class = RegistrationForm
    # for navigation -> to the next page (onboarding)
    # reverse_lazy is used instead of reverse to avoid circular imports, reverse_lazy delays resolution until the view is instantiated
    success_url = reverse_lazy('onboarding')

    def form_valid(self, form):
        user = form.save()  # Save the new user in the Django User model records
        login(self.request, user) # starts a session, prevents the user from having to re log in from the log in page - Django login function
        return super().form_valid(form)

class OnboardingView(LoginRequiredMixin, FormView):
    template_name = "authentication/onboarding.html"
    form_class = onboardingForm
    success_url = reverse_lazy('storefront_home')

    # modify the FormView form instantiation process to ensure that the onboarding form uses the specific instance (which contains the UserProfile if previously inputted)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        try:
            # might lead to a not null constraint we were to force feed into the instance attribute
            user_profile = UserProfile.objects.get(user=user)
            kwargs['instance'] = user_profile
        except UserProfile.DoesNotExist:
            pass
        return kwargs
    
    # validate all the fields in the form and generate preferred category using ai model
    def form_valid(self, form):
        form.save(commit=True, user=self.request.user)
        profile = UserProfile.objects.get(user=self.request.user)
        profile.preferred_category = "General"
        profile.save()
        return super().form_valid(form)
    
class ChangePasswordView(LoginRequiredMixin, FormView):
    template_name = "authentication/changepassword.html"
    form_class = ChangePasswordForm     
    success_url = reverse_lazy('storefront_home')

    # inititalise the form with request data, returns a changepasswordform instance with a POST req or empty form w GET
    def get_form(self, form_class=None):
        if form_class==None:
            form_class = self.get_form_class()
        return form_class(self.request.POST or None)

    def form_valid(self, form):
        # save the new password
        self.request.user.set_password(form.cleaned_data['new_password'])
        self.request.user.save()
        profile = UserProfile.objects.get(user=self.request.user)
        if profile.is_initial_password:
            profile.is_initial_password = False
            profile.save()
        # update the user's session data, prevents the user from getting logged out immediately after the pw update
        update_session_auth_hash(self.request, self.request.user)
        # check if the user is a staff, redirect to the admin page
        if self.request.user.is_staff:
            return_url = reverse_lazy("auroraadmin:admin_dashboard")
            return redirect(return_url)
        return super().form_valid(form)