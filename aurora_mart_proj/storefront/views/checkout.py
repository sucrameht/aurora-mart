from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F
from ..models import *
from decimal import Decimal
from django.contrib import messages
from django.views.generic import View
from datetime import date, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile
from django.db import transaction

class CheckoutView(LoginRequiredMixin, View):
    template_name = 'checkout.html'

    def get(self, request, *args, **kwargs):
        buy_now_item_session = request.session.get('buy_now_item')

        if buy_now_item_session:
            product = get_object_or_404(Product, sku_code=buy_now_item_session['sku_code'])
            cart_items = [{
                'product': product,
                'quantity': 1,
                'total_price': product.unit_price
            }]
            subtotal = product.unit_price
            discount = Decimal('0.00') # No vouchers for buy now
            total = subtotal

        else:
            # --- REGULAR CART CHECKOUT LOGIC ---
            cart_items_db = CartItem.objects.filter(user=request.user, is_selected=True).select_related('product')
            
            if not cart_items_db.exists():
                messages.warning(request, "You have no items selected for checkout.")
                return redirect('view_cart')

            cart_items = []
            subtotal = Decimal('0.00')

            for item in cart_items_db:
                item_total = item.quantity * item.product.unit_price
                cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'total_price': item_total
                })
                subtotal += item_total

            # (This logic is from CartView's get_voucher method)
            discount = Decimal('0.00')
            voucher_code = request.session.get('applied_voucher')
            if voucher_code:
                try:
                    voucher = Voucher.objects.get(code=voucher_code, is_active=True)
                    if voucher.discount_type == 'percent':
                        discount = (subtotal * (voucher.discount_value / 100)).quantize(Decimal('0.01'))
                    else: # amount
                        discount = voucher.discount_value
                    
                    if discount > subtotal:
                        discount = subtotal

                except Voucher.DoesNotExist:
                    messages.error(request, "The applied voucher is no longer valid.")
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
        buy_now_item_session = request.session.get('buy_now_item')
        user = request.user
        profile = None # Define profile in the outer scope
        
        # --- Common data from form ---
        shipping_data = {
            'shipping_first_name': request.POST.get('first_name'),
            'shipping_last_name': request.POST.get('last_name'),
            'shipping_phone': request.POST.get('phone'),
            'shipping_address': request.POST.get('address'),
            'shipping_city': request.POST.get('city'),
            'shipping_state': request.POST.get('state'),
            'shipping_postal_code': request.POST.get('postal_code'),
        }
        payment_method = request.POST.get('payment_method')

        if not all([shipping_data['shipping_first_name'], shipping_data['shipping_address'], 
                    shipping_data['shipping_city'], shipping_data['shipping_postal_code']]):
            messages.error(request, "Please fill in all required shipping details.")
            return redirect(request.META.get('HTTP_REFERER', 'checkout'))

        items_to_process = []
        total = Decimal('0.00')
        discount = Decimal('0.00')
        voucher_obj = None

        if buy_now_item_session:
            # --- Handle "Buy Now" ---
            product = get_object_or_404(Product, sku_code=buy_now_item_session['sku_code'])
            
            # Stock Check
            if product.quantity_on_hand < 1:
                messages.error(request, f"Sorry, {product.product_name} is out of stock.")
                del request.session['buy_now_item']
                return redirect('storefront_home')
            
            items_to_process.append({'product': product, 'quantity': 1})
            total = product.unit_price
            # No vouchers, so discount remains 0 and voucher_obj remains None

        else:
            # --- Handle "Regular Cart" ---
            cart_items_db = CartItem.objects.filter(user=request.user, is_selected=True).select_related('product')
            if not cart_items_db.exists():
                messages.error(request, "Your cart is empty or no items are selected.")
                return redirect('view_cart')

            subtotal = Decimal('0.00')
            for item in cart_items_db:
                # Stock Check (This was missing from your original cart logic)
                if item.product.quantity_on_hand < item.quantity:
                    messages.error(request, f"Sorry, {item.product.product_name} is low on stock ({item.product.quantity_on_hand} left). Please update your cart.")
                    return redirect('view_cart')
                
                items_to_process.append({'product': item.product, 'quantity': item.quantity})
                subtotal += item.total_price
            
            # Voucher Logic (copied from your original 'else' block)
            voucher_code = request.session.get('applied_voucher')
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

        try:
            profile = UserProfile.objects.get(user=request.user)
            if payment_method == 'wallet':
                if profile.wallet_balance < total:
                    messages.error(request, f"Insufficient wallet balance. You need ${total}, but only have ${profile.wallet_balance}.")
                    return redirect('checkout')
                profile.wallet_balance -= total
                profile.save()
            elif payment_method == 'card':
                print("Processing credit card (simulation)...")
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found.")
            return redirect('checkout')
        except Exception as e:
            messages.error(request, f"An error occurred during payment: {e}")
            return redirect('checkout')

        new_transaction = Transactions.objects.create(
            user=request.user,
            transaction_datetime=datetime.now(),
            **shipping_data, # Unpack the shipping data dict
            status='Payment Made',
            voucher_value=discount,
            payment_method=payment_method,
        )

        items_to_create = []
        for item_data in items_to_process:
            product = item_data['product']
            quantity = item_data['quantity']
            
            items_to_create.append(
                OrderItem(
                    transactions=new_transaction,
                    product=product,
                    quantity_purchased=quantity,
                    price_at_purchase=product.unit_price, 
                )
            )

            product.num_sold = F('num_sold') + quantity
            product.quantity_on_hand = F('quantity_on_hand') - quantity
            product.save()

        OrderItem.objects.bulk_create(items_to_create)

        if voucher_obj:
            voucher_obj.used_count = F('used_count') + 1
            voucher_obj.save()
            if 'applied_voucher' in request.session:
                del request.session['applied_voucher']
            if profile:
                profile.vouchers.remove(voucher_obj)

        # Clean up the correct source
        if buy_now_item_session:
            del request.session['buy_now_item']
        else:
            CartItem.objects.filter(user=request.user, is_selected=True).delete()

        messages.success(request, f"Your order has been placed!")
        return redirect('profile')