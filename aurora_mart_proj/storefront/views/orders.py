from django.shortcuts import render, redirect, get_object_or_404
from ..models import *
from django.contrib import messages
from django.views.generic import View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

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