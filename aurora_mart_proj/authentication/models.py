from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    gender =  models.CharField(max_length=20)
    employment_status = models.CharField(max_length=200)
    occupation = models.CharField(max_length=200)
    education = models.CharField()
    household_size = models.IntegerField()
    has_children = models.BooleanField(default=False)
    monthly_income_sgd = models.DecimalField(max_digits=20, decimal_places=11) # no restrictions on the decimal places due to the formatting type of the data inputs
    preferred_category = models.CharField(max_length=200, blank=True, null=True)
    is_initial_password = models.BooleanField(default=True) # for setting of initial password