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

        total = subtotal

        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'total': total
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = CartActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            sku = form.cleaned_data['sku_code']
            quantity = form.cleaned_data['quantity']
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
        else:
            return self.get(request, form=form)
        request.session['cart'] = cart
        return redirect('view_cart')