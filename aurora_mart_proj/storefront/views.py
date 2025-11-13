from django.shortcuts import render, redirect
from django.db.models import Q, Sum, F
from .models import *
import joblib
import os
from django.apps import apps
from decimal import Decimal
from django.contrib import messages
from django.views.generic import ListView, View, DetailView
from .forms import CartActionForm
from datetime import date, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile
import pandas as pd
from django.apps import apps
from django.db import transaction

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
                if profile.preferred_category != recommended_category:
                    profile.preferred_category = recommended_category
                    profile.save()
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
        if request.user.is_authenticated:
            cart_item_count = CartItem.objects.filter(user=request.user).aggregate(
                total_quantity=Sum('quantity')
            )['total_quantity'] or 0
        else:
            cart_item_count = request.session.get('cart_item_count', 0)

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

            if not request.user.is_authenticated:
                cart[sku] = cart.get(sku, 0) + 1
                request.session['cart'] = cart
                request.session['cart_item_count'] = sum(cart.values())
                messages.success(request, "Item added to cart! Please log in to save your cart.")
                return redirect('storefront_home')

            if action == 'add':
                try:
                    product = Product.objects.get(sku_code=sku)
                    # Get or create a cart item
                    cart_item, created = CartItem.objects.get_or_create(
                        user=request.user, 
                        product=product,
                        quantity=1
                    )
                    if not created:
                        # If it already exists, just increment the quantity
                        cart_item.quantity += 1
                    
                    cart_item.save()
                    messages.success(request, "Item added to cart!")
                
                except Product.DoesNotExist:
                    messages.error(request, "Product not found.")
        else:
            return self.get(request, form=form)  # Re-render with errors; adjust if needed
        return redirect(request.META.get('HTTP_REFERER', 'storefront_home'))


class CartView(View):
    template_name = 'cart.html'

    def get(self, request, *args, **kwargs):
        # Handle displaying the cart (your existing get_context_data logic)
        if not request.user.is_authenticated:
            cart = request.session.get('cart', {})
            cart_items = []
            subtotal = Decimal('0.00')
            cart_skus = list(cart.keys())

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
        else:
            cart_items = CartItem.objects.filter(user=request.user).select_related('product')
            subtotal = sum(item.total_price for item in cart_items)
            cart_skus = [item.product.sku_code for item in cart_items]
    
        recommended_products = []

        if cart_skus and ASSOCIATION_RULES_MODEL is not None:
            # Call your new function
            recommended_skus = get_recommendations(
                ASSOCIATION_RULES_MODEL, 
                cart_skus, 
                metric='lift',  # 'lift' is often good for recommendations
                top_n=6
            )
            # Get the full Product objects for the recommended SKUs
            recommended_products = Product.objects.filter(sku_code__in=recommended_skus)
        print(f"Recommended products based on cart: {[p.sku_code for p in recommended_products]}")

        
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
            'recommended_products': recommended_products,
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
                    discount = min(discount, subtotal)
                else:
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
            voucher_code = form.cleaned_data['voucher_code']

            if request.user.is_authenticated:
                if action == 'update':
                    sku = request.POST.get('sku_code')
                    quantity = int(request.POST.get('quantity', 1))
                    try:
                        cart_item = CartItem.objects.get(user=request.user, product__sku_code=sku)
                        if quantity > 0:
                            cart_item.quantity = quantity
                            cart_item.save()
                        else:
                            cart_item.delete() # Remove if quantity is 0
                    except CartItem.DoesNotExist:
                        messages.error(request, "Item not in cart.")
                
                elif action == 'remove':
                    sku = request.POST.get('sku_code')
                    CartItem.objects.filter(user=request.user, product__sku_code=sku).delete()
            
            else:
                cart = request.session.get('cart', {})
                
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
                
                request.session['cart'] = cart
                request.session['cart_item_count'] = sum(cart.values())

            if action == 'apply_voucher':
                if not request.user.is_authenticated:
                    return redirect('login')
                if voucher_code:
                    try:
                        profile = UserProfile.objects.get(user=request.user)
                        voucher = Voucher.objects.get(code=voucher_code)
                        if not profile.vouchers.filter(code=voucher_code).exists():
                            messages.error(request, "This voucher is not valid for your account.")
                            return redirect('view_cart')
                        if voucher.is_active and (not voucher.expiry_date or voucher.expiry_date >= date.today()):
                            request.session['applied_voucher'] = voucher.code
                            messages.success(request, f"Voucher '{voucher.code}' applied.")
                        elif not voucher.is_active:
                            messages.error(request, "Voucher is not active.")
                        else:
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

        return redirect('view_cart')


class ProfileView(LoginRequiredMixin, View):
    template_name = 'profile.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        active_tab = request.GET.get('tab', 'active')
        
        try:
            profile = user.userprofile
        except UserProfile.DoesNotExist:
            profile = None

        user_transactions = Transactions.objects.filter(user=user)
        
        completed_orders_list = user_transactions.filter(
            status='Delivery Completed'
        ).order_by('-transaction_datetime')

        active_orders_list = user_transactions.exclude(
            status='Delivery Completed'
        ).order_by('-transaction_datetime')
        
        total_orders = user_transactions.count()
        completed_orders_count = completed_orders_list.count() 
        
        if request.user.is_authenticated:
            cart_items_db = CartItem.objects.filter(user=request.user).select_related('product')
            cart_item_count = sum(item.quantity for item in cart_items_db)

        context = {
            'profile': profile,
            'user': user,
            'total_orders': total_orders,
            'completed_orders': completed_orders_count,
            'active_orders_list': active_orders_list,
            'completed_orders_list': completed_orders_list,
            'cart_item_count': cart_item_count,
            'active_tab': active_tab,  # --- ADD THIS ---
        }
        return render(request, self.template_name, context)

class CheckoutView(LoginRequiredMixin, View):
    template_name = 'checkout.html'

    def get(self, request, *args, **kwargs):
        cart_items_db = CartItem.objects.filter(user=request.user).select_related('product')
        
        if not cart_items_db.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('view_cart')

        cart_items = []
        subtotal = Decimal('0.00')

        for item in cart_items_db:
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'total_price': item.total_price  # Use the model property
            })
            subtotal += item.total_price # Use the model property

        # (This logic is from CartView's get_voucher method)
        discount = Decimal('0.00')
        voucher_code = request.session.get('applied_voucher')
        if voucher_code:
            try:
                voucher = Voucher.objects.get(code=voucher_code, is_active=True)
                if not voucher.expiry_date or voucher.expiry_date >= date.today():
                    if voucher.discount_type == 'percent':
                        discount = subtotal * (voucher.discount_value / Decimal('100'))
                    else:
                        discount = voucher.discount_value
                    discount = min(discount, subtotal)
                else:
                    del request.session['applied_voucher']
            except Voucher.DoesNotExist:
                del request.session['applied_voucher']

        total = subtotal - discount

        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = None

        saved_addresses = ShippingAddress.objects.filter(user=request.user)

        selected_address = None
        load_address_id = request.GET.get('load_address_id')

        if load_address_id:
            try:
                selected_address = ShippingAddress.objects.get(id=load_address_id, user=request.user)
            except ShippingAddress.DoesNotExist:
                pass
        
        selected_payment_method = request.GET.get('payment_method', 'card')

        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount': discount,
            'total': total,
            'profile': profile,
            'user': request.user,
            'saved_addresses': saved_addresses,
            'selected_address': selected_address,
            'selected_payment_method': selected_payment_method,
        }
        return render(request, self.template_name, context)

    @transaction.atomic # all or nothing
    def post(self, request, *args, **kwargs):
        
        cart_items_db = CartItem.objects.filter(user=request.user).select_related('product')
        subtotal = Decimal('0.00')

        if not cart_items_db.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('view_cart')

        for item in cart_items_db:
            subtotal += item.total_price
        
        discount = Decimal('0.00')
        voucher_code = request.session.get('applied_voucher')
        voucher_obj = None # Will store the voucher object if found
        
        if voucher_code:
            try:
                voucher_obj = Voucher.objects.get(code=voucher_code, is_active=True)
                if not voucher_obj.expiry_date or voucher_obj.expiry_date >= date.today():
                    if voucher_obj.discount_type == 'percent':
                        discount = subtotal * (voucher_obj.discount_value / Decimal('100'))
                    else:
                        discount = voucher_obj.discount_value
                    discount = min(discount, subtotal)
                else:
                    del request.session['applied_voucher']
                    voucher_obj = None # Voucher expired
            except Voucher.DoesNotExist:
                del request.session['applied_voucher']
                voucher_obj = None # Voucher not found
        
        total = subtotal - discount

        payment_method = request.POST.get('payment_method')
        shipping_first_name = request.POST.get('first_name')
        shipping_last_name = request.POST.get('last_name')
        shipping_phone = request.POST.get('phone')
        shipping_address = request.POST.get('address')
        shipping_city = request.POST.get('city')
        shipping_state = request.POST.get('state')
        shipping_postal_code = request.POST.get('postal_code')

        if not all([payment_method, shipping_first_name, shipping_address, shipping_city, shipping_postal_code]):
            messages.error(request, "Please fill out all required shipping and payment fields.")
            return self.get(request)
        
        try:
            profile = UserProfile.objects.get(user=request.user)
            if payment_method == 'wallet':
                if profile.wallet_balance < total:
                    messages.error(request, f"Insufficient wallet balance. You need ${total}, but only have ${profile.wallet_balance}.")
                    return self.get(request)
                profile.wallet_balance -= total
                profile.save()
            elif payment_method == 'card':
                print("Processing credit card (simulation)...")
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found.")
            return self.get(request)
        except Exception as e:
            messages.error(request, f"An error occurred during payment: {e}")
            return self.get(request)

        # --- Create the Transaction ---
        new_transaction = Transactions.objects.create(
            user=request.user,
            transaction_datetime=datetime.now(),
            shipping_first_name=shipping_first_name,
            shipping_last_name=shipping_last_name,
            shipping_phone=shipping_phone,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_postal_code=shipping_postal_code,
            status='Payment Made',
            voucher_value=discount,
            payment_method=payment_method,
        )

        items_to_create = []
        for item in cart_items_db:
            items_to_create.append(
                OrderItem(
                    transactions=new_transaction,
                    product=item.product,
                    quantity_purchased=item.quantity,
                    price_at_purchase=item.product.unit_price, 
                )
            )
            product = item.product
            product.num_sold = F('num_sold') + item.quantity
            product.quantity_on_hand = F('quantity_on_hand') - item.quantity
            product.save()

        OrderItem.objects.bulk_create(items_to_create)

        if voucher_obj:
            voucher_obj.used_count = F('used_count') + 1
            voucher_obj.save()
            del request.session['applied_voucher']

        cart_items_db.delete()
        messages.success(request, f"Your order #{new_transaction.id} has been placed!")
        return redirect('profile')

    
class AddShippingAddressView(LoginRequiredMixin, View):
    template_name = 'add_shipping_address.html'
    
    def get(self, request, *args, **kwargs):
        # Just show the blank form
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # 1. Get the form data
        nickname = request.POST.get('nickname')
        
        # 2. Check for a nickname (it's required for this to work)
        if not nickname:
            messages.error(request, "You must provide a nickname (e.g., 'Home' or 'Work').")
            return render(request, self.template_name)
            
        # 3. Create and save the new address object
        try:
            ShippingAddress.objects.create(
                user=request.user,
                nickname=nickname,
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                phone=request.POST.get('phone'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                postal_code=request.POST.get('postal_code'),
            )
            messages.success(request, f"Address '{nickname}' saved!")
        
        except Exception as e:
            # Handle error, e.g., if nickname is not unique for this user
            messages.error(request, f"Could not save address: {e}")
            return render(request, self.template_name)

        # 4. Redirect back to the checkout page
        #    We check the 'next' parameter to be safe.
        next_url = request.GET.get('next')
        if next_url == 'checkout':
            return redirect('checkout')
        
        # Default fallback
        return redirect('profile')

class EditProfileView(LoginRequiredMixin, View):
    template_name = 'edit_profile.html'

    def get(self, request, *args, **kwargs):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('profile')
        
        context = {
            'user': request.user,
            'profile': profile
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        # We can safely assume the profile exists now because of the get method
        profile = UserProfile.objects.get(user=request.user)
        
        # Get data from the POST form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Get profile-specific data (add any other fields you have)
        phone_number = request.POST.get('phone_number') # Assumes 'phone_number' on UserProfile
        
        # Update the User model
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        # Update the UserProfile model
        profile.phone_number = phone_number
        # profile.age = request.POST.get('age') # Example
        # profile.household_size = request.POST.get('household_size') # Example
        profile.save()
        
        messages.success(request, "Your profile has been updated.")
        return redirect('profile') # Redirect back to the profile page

class WalletView(LoginRequiredMixin, View):
    template_name = 'wallet.html'
    
    def get(self, request, *args, **kwargs):
        # Get profile, or create it if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        context = {
            'profile': profile
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile = UserProfile.objects.get(user=request.user)
        try:
            # Get the amount from the form
            top_up_amount = Decimal(request.POST.get('top_up_amount'))
            
            if top_up_amount <= 0:
                messages.error(request, "Top-up amount must be positive.")
            else:
                profile.wallet_balance += top_up_amount
                profile.save()
                messages.success(request, f"Successfully added ${top_up_amount} to your wallet.")
        
        except:
            messages.error(request, "Invalid amount entered. Please enter a number.")
            
        return redirect('wallet') # Redirect back to the same page

class CustomerTransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transactions
    template_name = 'transaction_detail.html'
    context_object_name = 'transaction'
    login_url ='/login'

    def get_queryset(self):
        """Ensure user can only see their own transactions."""
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Order Details'
        return context