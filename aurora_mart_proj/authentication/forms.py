from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    # redefine the save condition
    def save(self, commit=True):
        user = super().save(commit=False) # get the original object
        user.is_staff = False # all need onboarding users are not considered to be stuff
        if commit:
            user.save()
        return user
    
class onboardingForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ["age", "gender","employment_status", "phone_number", "occupation", "education", "household_size", "has_children", "monthly_income_sgd"]

        GENDER = [
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Others', 'Others'),
        ]

        EMPLOYMENT_STATUS = [ 
            ('Full-time', 'Full-time'),
            ('Part-time', 'Part-time'),
            ('Self-employed', 'Self-employed'),
            ('Unemployed', 'Unemployed'),
            ('Student', 'Student'),
            ('Retired', 'Retired'),
            ('Others', 'Others')
        ]

        EDUCATION = [
            ('No Formal Education', 'No Formal Education'),
            ('High School', 'High School'),
            ('Diploma', 'Diploma'),
            ('Bachelor', 'Bachelor'),
            ('Master', 'Master'),
            ('Doctorate', 'Doctorate'),
            ('Others', 'Others')
        ]

        widgets = {
            'gender': forms.Select(choices=GENDER),
            'employment_status': forms.Select(choices=EMPLOYMENT_STATUS),
            'education': forms.Select(choices=EDUCATION),
        }

    def save(self, commit = True, user=None):
        user_profile = super().save(commit=False)
        if user:
            user_profile.user = user
        if commit:
            user_profile.save()
        return user_profile

class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Old Password", required=True)
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="New Password", required=True)
    # need re-confirm password?