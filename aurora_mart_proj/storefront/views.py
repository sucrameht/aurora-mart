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


class StorefrontView(ListView):
    template_name = 'storefront.html'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '')
        active_category = request.GET.get('category')
        sort = request.GET.get('sort', 'name-asc')

        queryset = Product.objects.all()

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