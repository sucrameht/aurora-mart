from django.shortcuts import render
from django.db.models import Q
from .models import Product
import joblib
import os
from django.apps import apps

# Create your views here.
def storefront(request):
    # return HttpResponse("Welcome to Aurora Mart Storefront!")
    query = request.GET.get('query', '')
    active_category = request.GET.get('category')
    categories = Product.objects.values_list('product_category', flat=True).distinct().order_by('product_category')

    products = Product.objects.all()

    if active_category and active_category != 'All':
        products = products.filter(product_category=active_category)

    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(product_category__icontains=query))
    
    context = {
        'products': products,
        'categories': categories,
        'active_category': active_category,
        'query': query
    }
    return render(request, 'storefront.html', context)


app_path = apps.get_app_config('storefront').path
model_path = os.path.join(app_path, 'mlmodels', 'b2c_customers_100.joblib')
loaded_model = joblib.load(model_path)
model_path = os.path.join(app_path, 'mlmodels', 'b2c_products_500_transactions_50k.joblib')
loaded_rules = joblib.load(model_path)

