from django.shortcuts import render, redirect, get_object_or_404
from ..models import *
from django.contrib import messages
from django.views.generic import View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction

class CustomerTransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transactions
    template_name = 'transaction_detail.html'
    context_object_name = 'transaction'

    def get_queryset(self):
        """Ensure user can only see their own transactions."""
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transaction = context.get('transaction')

        total = transaction.total_spent
        voucher_value = transaction.voucher_value
        grand_total = total - voucher_value

        context['page_title'] = f'Order Details'
        context['total'] = total
        context['grand_total'] = grand_total
        context['voucher_value'] = voucher_value
        return context

class RateOrderView(LoginRequiredMixin, View):
    template_name = 'reviews.html'

    def get(self, request, *args, **kwargs):
        order_pk = self.kwargs.get('pk')
        order = get_object_or_404(Transactions, pk=order_pk, user=request.user)

        if order.status != 'Delivery Completed':
            messages.error(request, "You can only review completed orders.")
            return redirect('profile')

        order_items = OrderItem.objects.filter(transactions=order).select_related('product')
        context = {
            'order': order,
            'order_items': order_items
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        order_pk = self.kwargs.get('pk')
        order = get_object_or_404(Transactions, pk=order_pk, user=request.user)

        if order.status != 'Delivery Completed':
            messages.error(request, "You can only review completed orders.")
            return redirect('profile')

        for item in order.items.all():
            rating_key = f'rating_{item.pk}'
            review_key = f'review_{item.pk}'

            if rating_key in request.POST and request.POST[rating_key]:
                item.rating = request.POST[rating_key]
            
            if review_key in request.POST:
                item.text_review = request.POST[review_key]
            
            item.save()

        messages.success(request, "Your review has been submitted successfully!")
        return redirect('profile')

class CancelOrderView(LoginRequiredMixin, View):
    template_name = 'cancel_order_form.html'

    def get(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transactions, pk=self.kwargs.get('pk'), user=request.user)
        if transaction.status != 'Payment Made':
            messages.error(request, "This order cannot be cancelled at its current stage.")
            return redirect('profile')
        return render(request, self.template_name, {'transaction': transaction})

    def post(self, request, *args, **kwargs):
        transaction_obj = get_object_or_404(Transactions, pk=self.kwargs.get('pk'), user=request.user)
        if transaction_obj.status == 'Payment Made':
            try:
                with db_transaction.atomic():
                    transaction_obj.status = 'Cancelled'
                    transaction_obj.notes = request.POST.get('reason', '')

                    # Restock items
                    for item in transaction_obj.items.all():
                        product = item.product
                        product.quantity_on_hand += item.quantity_purchased
                        product.save()
                    
                    transaction_obj.save()
                
                messages.success(request, "Your order has been successfully cancelled and items have been restocked.")
            except Exception as e:
                messages.error(request, f"An error occurred while cancelling your order: {e}")
        else:
            messages.error(request, "This order cannot be cancelled at its current stage.")
        return redirect('profile')

class RequestRefundView(LoginRequiredMixin, View):
    template_name = 'request_refund_form.html'

    def get(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transactions, pk=self.kwargs.get('pk'), user=request.user)
        if transaction.status != 'Delivery Completed':
            messages.error(request, "A refund can only be requested for completed orders.")
            return redirect('profile')
        return render(request, self.template_name, {'transaction': transaction})

    def post(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transactions, pk=self.kwargs.get('pk'), user=request.user)
        if transaction.status == 'Delivery Completed':
            transaction.status = 'Request for Refund'
            transaction.notes = request.POST.get('reason', '')
            transaction.save()
            messages.success(request, "Your refund request has been submitted.")
        else:
            messages.error(request, "A refund can only be requested for completed orders.")
        return redirect('profile')