from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
import csv
from authentication.models import UserProfile

class Command(BaseCommand):
    help = "Importing user profile data from CSV file."

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        with open(kwargs['csv_file'], 'r') as file:
            # headers to id columns
            reader = csv.DictReader(file)
            # get all the customers, do not include the superuser
            customers = User.objects.filter(is_staff=False).order_by('id')
            users = {user.username : user for user in customers}
            username = list(users.keys())
            
            for index, row in enumerate(reader):
                user = users[username[index]]
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'age': int(row['age']),
                        'gender' : row['gender'],
                        'employment_status' : row['employment_status'],
                        'occupation' : row['occupation'],
                        'education' : row['education'],
                        'household_size' : int(row['household_size']),
                        'has_children' : bool(row['has_children']),
                        'monthly_income_sgd' : float(row['monthly_income_sgd']),
                        'preferred_category' : row['preferred_category'],
                        'is_initial_password' : False
                    }
            )
        self.stdout.write(self.style.SUCCESS('Successfully imported user profiles from excel file.'))