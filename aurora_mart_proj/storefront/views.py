from django.shortcuts import render, redirect
from django.db.models import Q
from .models import Product, Voucher
import joblib
import os
from django.apps import apps
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.views.generic import ListView, View
from .forms import CartActionForm
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile
import joblib
import pandas as pd
from django.apps import apps

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
    
    # Make the prediction
    prediction = model.predict(df)    
    return prediction


class StorefrontView(ListView):
    template_name = 'storefront.html'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '')
        user_clicked_category = request.GET.get('category')
        # active_category = request.GET.get('category')
        sort = request.GET.get('sort', 'name-asc')

        queryset = Product.objects.all()

        # Get the recommended category for the user
        recommended_category = "All"
        if CLASSIFIER_MODEL and request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                customer_data = {
                    'age': profile.age,
                    'household_size': profile.household_size,
                    'has_children': profile.has_children,
                    'monthly_income_sgd': float(profile.monthly_income_sgd),
                    'gender': profile.gender,
                    'employment_status': profile.employment_status,
                    'occupation': profile.occupation,
                    'education': profile.education
                }
                print(f"Customer data for prediction: {customer_data}")
                # Call the prediction function
                prediction = predict_preferred_category(CLASSIFIER_MODEL, customer_data)
                recommended_category = prediction[0]
                print(f"Predicted preferred category: {recommended_category}")
            except Exception as e:
                print(f"Prediction failed: {e}")
        
        if user_clicked_category:
            active_category = user_clicked_category
        else:
            active_category = recommended_category

        if active_category and active_category != 'All':
            queryset = queryset.filter(product_category=active_category)

        if query:
            queryset = queryset.filter(Q(product_name__icontains=query) | Q(product_category__icontains=query))

        if sort == 'name-asc':
            queryset = queryset.order_by('product_name')
        elif sort == 'name-desc':
            queryset = queryset.order_by('-product_name')
        elif sort == 'price-asc':
            queryset = queryset.order_by('unit_price')
        elif sort == 'price-desc':
            queryset = queryset.order_by('-unit_price')
        elif sort == 'rating-asc':
            queryset = queryset.order_by('product_rating')
        elif sort == 'rating-desc':
            queryset = queryset.order_by('-product_rating')

        categories = Product.objects.values_list('product_category', flat=True).distinct().order_by('product_category')
        cart = request.session.get('cart', {})
        cart_item_count = sum(cart.values())

        context = {
            'products': queryset,
            'categories': categories,
            'active_category': active_category,
            'query': query,
            'cart_item_count': cart_item_count,
            'sort': sort,
            'recommended_category': recommended_category,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = CartActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            sku = form.cleaned_data['sku_code']
            cart = request.session.get('cart', {})

            if action == 'add':
                cart[sku] = cart.get(sku, 0) + 1
                request.session['cart'] = cart
                messages.success(request, "Item added to cart!")
        else:
            return self.get(request, form=form)  # Re-render with errors; adjust if needed

        return redirect(request.META.get('HTTP_REFERER', 'storefront_home'))


class CartView(View):
    template_name = 'cart.html'

    def get(self, request, *args, **kwargs):
        # Handle displaying the cart (your existing get_context_data logic)
        cart = request.session.get('cart', {})
        cart_items = []
        subtotal = Decimal('0.00')

        products_in_cart = Product.objects.filter(sku_code__in=cart.keys())

        for product in products_in_cart:
            sku = product.sku_code
            quantity = cart.get(sku, 0)
            total_item_price = product.unit_price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total_price': total_item_price
            })
            subtotal += total_item_price
        
        applied_voucher, discount = self.get_voucher(request, subtotal)

        total = subtotal - discount

        current_voucher_code = (
            request.POST.get('voucher_code') or
            request.session.get('applied_voucher', '')
        )

        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'total': total,
            'applied_voucher': applied_voucher,
            'discount': discount,
            'current_voucher_code': current_voucher_code,
        }
        return render(request, self.template_name, context)
    
    def get_voucher(self, request, subtotal):
        discount = Decimal('0.00')
        applied_voucher = None
        voucher_code = request.session.get('applied_voucher')
        if voucher_code:
            try:
                voucher = Voucher.objects.get(code=voucher_code)
                if voucher.is_active and (not voucher.expiry_date or voucher.expiry_date >= date.today()):
                    applied_voucher = voucher
                    if voucher.discount_type == 'percent':
                        discount = subtotal * (voucher.discount_value / Decimal('100'))
                    else:  # 'amount'
                        discount = voucher.discount_value
                    # Cap discount at subtotal to avoid negative totals
                    discount = min(discount, subtotal)
                else:
                    # Invalid/expired: remove from session
                    del request.session['applied_voucher']
                    messages.error(request, "Applied voucher is no longer valid.")
            except Voucher.DoesNotExist:
                del request.session['applied_voucher']
                messages.error(request, "Applied voucher not found.")
        return applied_voucher, round(discount, 2)
        

    def post(self, request, *args, **kwargs):
        form = CartActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            sku = form.cleaned_data['sku_code']
            quantity = form.cleaned_data['quantity']
            cart = request.session.get('cart', {})
            voucher_code = form.cleaned_data['voucher_code']

            if action == 'update':
                sku = request.POST.get('sku_code')
                quantity = int(request.POST.get('quantity', 1))
                if sku in cart:
                    if quantity > 0:
                        cart[sku] = quantity
                    else:
                        del cart[sku]

            elif action == 'remove':
                sku = request.POST.get('sku_code')
                if sku in cart:
                    del cart[sku]
            elif action == 'apply_voucher':
                if voucher_code:
                    try:
                        # Check voucher validity
                        voucher = Voucher.objects.get(code=voucher_code)
                        if voucher.is_active and (not voucher.expiry_date or voucher.expiry_date >= date.today()):
                            request.session['applied_voucher'] = voucher.code
                            messages.success(request, f"Voucher '{voucher.code}' applied.")
                        elif not voucher.is_active:
                            messages.error(request, "Voucher is not active.")
                        else: # Expired
                            messages.error(request, "Voucher is expired.")
                    except Voucher.DoesNotExist:
                        messages.error(request, "Invalid voucher code.")
                else:
                    messages.error(request, "Please enter a voucher code.")
            elif action == 'remove_voucher':
                if 'applied_voucher' in request.session:
                    del request.session['applied_voucher']
                    messages.success(request, "Voucher removed.")

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        request.session['cart'] = cart
        return redirect('view_cart')


class ProfileView(LoginRequiredMixin, View):
    template_name = 'profile.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            profile = user.userprofile
        except UserProfile.DoesNotExist:
            profile = None

        # Try to fetch orders if an 'orders' app exists (adjust model name/fields to match your project)
        Order = None
        recent_orders = []
        total_orders = 0
        completed_orders = 0
        if apps.is_installed('orders'):
            try:
                Order = apps.get_model('orders', 'Order')
            except LookupError:
                Order = None

        if Order:
            qs = Order.objects.filter(user=user)
            total_orders = qs.count()
            completed_orders = qs.filter(status__iexact='completed').count()
            recent_orders = qs.order_by('-created_at')[:5]
        # Fallback placeholders if no Order model
        context = {
            'profile': profile,
            'user': user,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'recent_orders': recent_orders,
        }
        return render(request, self.template_name, context)