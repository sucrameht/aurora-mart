from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
import pandas as pd

class Command(BaseCommand):
    # explanation of what this class does
    help = "Importing User sensitive information from a CSV file"
    
    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help="The path to the CSV file containing user data.",
        )
    
    def handle(self, *args, **kwargs):
        df = pd.read_excel(kwargs['excel_file'], header=0)

        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        for index, row in df.iterrows():
            username = row['username']
            email = row['email']
            password = row['password']
                
            User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                is_staff=False
            )
        self.stdout.write(self.style.SUCCESS('Successfully imported users from CSV file.'))