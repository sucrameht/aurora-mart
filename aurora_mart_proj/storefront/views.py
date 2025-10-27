from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Product
import joblib
import os
from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal

# Create your views here.
def storefront(request):
    # return HttpResponse("Welcome to Aurora Mart Storefront!")
    query = request.GET.get('query', '')
    active_category = request.GET.get('category')
    categories = Product.objects.values_list('product_category', flat=True).distinct().order_by('product_category')
    cart = request.session.get('cart', {})
    cart_item_count = sum(cart.values())

    products = Product.objects.all()

    if active_category and active_category != 'All':
        products = products.filter(product_category=active_category)

    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(product_category__icontains=query))
    
    context = {
        'products': products,
        'categories': categories,
        'active_category': active_category,
        'query': query,
        'cart_item_count': cart_item_count
    }
    return render(request, 'storefront.html', context)

@require_POST
def add_to_cart(request):
    sku = request.POST.get('sku_code')
    product = get_object_or_404(Product, sku_code=sku)
    
    # Get the cart from the session, or create an empty one
    cart = request.session.get('cart', {})
    
    # Get current quantity, default to 0, then add 1
    quantity = cart.get(sku, 0) + 1
    
    # Basic check against stock
    if quantity > product.quantity_on_hand:
        return JsonResponse({'status': 'error', 'message': 'Not enough stock'}, status=400)
        
    cart[sku] = quantity
    request.session['cart'] = cart
    
    # Return success and new total item count
    cart_item_count = sum(cart.values())
    return JsonResponse({
        'status': 'success',
        'message': f'Added {product.product_name} to cart.',
        'cart_item_count': cart_item_count
    })

def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    subtotal = Decimal('0.00')

    # Get product objects for SKUs in cart
    products_in_cart = Product.objects.filter(sku_code__in=cart.keys())

    for product in products_in_cart:
        sku = product.sku_code
        quantity = cart[sku]
        total_item_price = product.unit_price * quantity
        
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total_price': total_item_price
        })
        subtotal += total_item_price
    
    # For now, total is the same as subtotal
    total = subtotal 

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': total
    }
    return render(request, 'cart.html', context)

@require_POST
def update_cart(request):
    sku = request.POST.get('sku_code')
    quantity = int(request.POST.get('quantity', 1))
    cart = request.session.get('cart', {})
    
    if sku in cart:
        if quantity > 0:
            # Optional: Check stock levels again
            # product = Product.objects.get(sku_code=sku)
            # if quantity > product.quantity_on_hand: ...
            cart[sku] = quantity
        else:
            # Remove if quantity is 0 or less
            del cart[sku]
    
    request.session['cart'] = cart
    return redirect('view_cart') # Redirect back to the cart page

@require_POST
def remove_from_cart(request):
    sku = request.POST.get('sku_code')
    cart = request.session.get('cart', {})
    
    if sku in cart:
        del cart[sku]
        
    request.session['cart'] = cart
    return redirect('view_cart')

