# auroraMart
IS2108 Project

# Set up virtual environment
To move out of aurora-mart and create virtual environment : cd ..
Rationale : prevent pushing of virtual environment onto github

Windows: venv\Scripts\Activate.ps1

# Install Dependencies
cd aurora-mart
pip install -r requirements.txt

# Create the aurora-mart django project
django-admin startproject aurora_mart_proj

# Creating the storefront, admin and AImodels app
python manage.py startapp storefront, admin AImodels

# Add project apps to installed app
add app to project level settings.py
