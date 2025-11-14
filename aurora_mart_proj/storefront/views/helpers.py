from ..models import *
import joblib
import os
from django.apps import apps
import pandas as pd

APP_PATH = apps.get_app_config('storefront').path

classifier_model_path = os.path.join(APP_PATH, 'mlmodels', 'b2c_customers_100.joblib')
rules_model_path = os.path.join(APP_PATH, 'mlmodels', 'b2c_products_500_transactions_50k.joblib')

try:
    CLASSIFIER_MODEL = joblib.load(classifier_model_path)
    ASSOCIATION_RULES_MODEL = joblib.load(rules_model_path)
    print("ML Models loaded successfully from storefront/mlmodels.")
except FileNotFoundError:
    print(f"ERROR: Could not find ML models. Check 'mlmodels' folder in '{APP_PATH}'")
    CLASSIFIER_MODEL = None
    ASSOCIATION_RULES_MODEL = None


def predict_preferred_category(model, customer_data):
    # This is the list of all columns the model was trained on
    columns = {
        'age':'int64', 'household_size':'int64', 'has_children':'int64', 'monthly_income_sgd':'float64',
        'gender_Female':'bool', 'gender_Male':'bool', 'employment_status_Full-time':'bool',
        'employment_status_Part-time':'bool', 'employment_status_Retired':'bool',
        'employment_status_Self-employed':'bool', 'employment_status_Student':'bool',
        'occupation_Admin':'bool', 'occupation_Education':'bool', 'occupation_Sales':'bool',
        'occupation_Service':'bool', 'occupation_Skilled Trades':'bool', 'occupation_Tech':'bool',
        'education_Bachelor':'bool', 'education_Diploma':'bool', 'education_Doctorate':'bool',
        'education_Master':'bool', 'education_Secondary':'bool'
    }
    
    # Create an empty DataFrame with the correct columns and types
    df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in columns.items()})
    
    # Convert new customer data to a DataFrame and encode it
    customer_df = pd.DataFrame([customer_data])
    customer_encoded = pd.get_dummies(customer_df, columns=['gender', 'employment_status', 'occupation', 'education'])    

    # Fill the empty DataFrame with the new customer's encoded data
    for col in df.columns:
        if col not in customer_encoded.columns:
            # Use False for bool columns, 0 for numeric
            if df[col].dtype == bool:
                df[col] = False
            else:
                df[col] = 0
        else:
            df[col] = customer_encoded[col]

    prediction = model.predict(df)    
    return prediction

def get_recommendations(loaded_rules, items, metric='confidence', top_n=6):
    recommendations = set()

    for item in items:
        # Find rules where the item is in the antecedents
        matched_rules = loaded_rules[loaded_rules['antecedents'].apply(lambda x: item in x)]
        # Sort by the specified metric and get the top N
        top_rules = matched_rules.sort_values(by=metric, ascending=False).head(top_n)

        for _, row in top_rules.iterrows():
            recommendations.update(row['consequents'])

    # Remove items that are already in the input list
    recommendations.difference_update(items)
    print(f"Recommendations after filtering out items already in cart: {recommendations}")
    return list(recommendations)[:top_n]