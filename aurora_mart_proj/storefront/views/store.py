from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from ..models import *
from decimal import Decimal
from django.contrib import messages
from django.views.generic import ListView, View, DetailView
from ..forms import CartActionForm
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile
from .helpers import (
    CLASSIFIER_MODEL, 
    ASSOCIATION_RULES_MODEL, 
    predict_preferred_category, 
    get_recommendations
)



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

        context = {
            'products': queryset,
            'categories': categories,
            'active_category': active_category,
            'query': query,
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
                    cart_item, created = CartItem.objects.get_or_create(
                        user=request.user, 
                        product=product,
                        defaults={'quantity': 1}  # Use 'defaults'
                    )
                    
                    if not created:
                        cart_item.quantity += 1
                        cart_item.save() #
                    
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

class BuyNowView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        sku_code = self.kwargs.get('sku_code')
        product = get_object_or_404(Product, sku_code=sku_code)
        
        # Store the single item in the session for checkout
        request.session['buy_now_item'] = {
            'sku_code': product.sku_code,
            'quantity': 1,
            'price': str(product.unit_price) 
        }
        
        # Clear any previous cart-based checkout session data
        if 'applied_voucher' in request.session:
            del request.session['applied_voucher']

        return redirect('checkout')

class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'sku_code'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        context['reviews'] = OrderItem.objects.filter(
            product=product
        ).filter(
            # Find items where EITHER the rating is > 0
            Q(rating__gt=0) | 
            # OR the text_review is not null AND not an empty string
            (Q(text_review__isnull=False) & ~Q(text_review=''))
        ).select_related('transactions__user').order_by('-transactions__transaction_datetime')

        # Get product recommendations
        recommended_products = []
        if ASSOCIATION_RULES_MODEL is not None:
            recommended_skus = get_recommendations(
                ASSOCIATION_RULES_MODEL, 
                [product.sku_code], 
                metric='lift',
                top_n=5
            )
            recommended_products = Product.objects.filter(sku_code__in=recommended_skus)
        
        context['recommended_products'] = recommended_products
            
        return context