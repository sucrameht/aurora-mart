from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from ..models import *
from decimal import Decimal
from django.contrib import messages
from django.views.generic import ListView, View
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile, WalletHistory
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django import forms
from ..forms import CardForm
from django.db import transaction


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

        active_statuses = ['Payment Made', 'Delivered to Warehouse']
        active_orders_list = user_transactions.filter(status__in=active_statuses).order_by('-transaction_datetime')

        completed_orders_list = user_transactions.filter(status='Delivery Completed').order_by('-transaction_datetime')

        other_statuses = ['Cancelled', 'Request for Refund', 'Refund Approved', 'Refund Rejected']
        other_orders_list = user_transactions.filter(status__in=other_statuses).order_by('-transaction_datetime')
        
        total_orders = user_transactions.count()
        completed_orders_count = completed_orders_list.count() 

        context = {
            'profile': profile,
            'user': user,
            'total_orders': total_orders,
            'completed_orders': completed_orders_count,
            'active_orders_list': active_orders_list,
            'completed_orders_list': completed_orders_list,
            'other_orders_list': other_orders_list,
            'active_tab': active_tab,
        }
        return render(request, self.template_name, context)

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
        profile = UserProfile.objects.get(user=request.user)
        
        # Update User model
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        
        # Update UserProfile model
        profile.phone_number = request.POST.get('phone_number')
        profile.age = request.POST.get('age')
        profile.household_size = request.POST.get('household_size')
        profile.gender = request.POST.get('gender')
        profile.has_children = request.POST.get('has_children') == 'true'
        profile.employment_status = request.POST.get('employment_status')
        profile.occupation = request.POST.get('occupation')
        profile.education = request.POST.get('education')
        profile.monthly_income_sgd = request.POST.get('monthly_income_sgd')
        profile.save()
        
        messages.success(request, "Your profile has been updated successfully.")
        return redirect('profile')

class WalletView(LoginRequiredMixin, View):
    template_name = 'wallet.html'
    
    def get(self, request, *args, **kwargs):
        # Get profile, or create it if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        history = profile.wallet_history.all().order_by('-timestamp')

        saved_cards = Card.objects.filter(user=request.user)
        selected_card = None
        selected_card_id = request.GET.get('selected_card') 

        if selected_card_id:
            try:
                selected_card = Card.objects.get(id=selected_card_id, user=request.user)
            except Card.DoesNotExist:
                pass
        
        context = {
            'profile': profile,
            'history': history,
            'saved_cards': saved_cards,
            'selected_card': selected_card,
        }
        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        profile = UserProfile.objects.get(user=request.user)
        
        try:
            top_up_amount = Decimal(request.POST.get('top_up_amount'))
            if top_up_amount <= 0:
                messages.error(request, "Top-up amount must be positive.")
                return redirect('wallet')
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount entered. Please enter a number.")
            return redirect('wallet')

        selected_card_id = request.POST.get('selected_card')
        
        # Logic for handling payment
        if selected_card_id:
            # Using a saved card
            try:
                card = Card.objects.get(id=selected_card_id, user=request.user)
                # In a real scenario, you'd process payment with the card token.
                # For this simulation, we just approve it.
                print(f"Processing top-up with saved card: {card.nickname}")
            except Card.DoesNotExist:
                messages.error(request, "The selected card was not found.")
                return redirect('wallet')
        else:
            # Using a new card
            card_form = CardForm(request.POST)
            if card_form.is_valid():
                # In a real app, you would NOT save the full card number.
                # You'd send it to a payment gateway and get a token.
                # For this project, we save the last 4 digits.
                new_card = Card.objects.create(
                    user=request.user,
                    nickname=card_form.cleaned_data.get('nickname') or f"Card ending in {card_form.cleaned_data['card_number'][-4:]}",
                    cardholder_name=card_form.cleaned_data['cardholder_name'],
                    last_four=card_form.cleaned_data['card_number'][-4:],
                    expiry_month=card_form.cleaned_data['expiry_month'],
                    expiry_year=card_form.cleaned_data['expiry_year'],
                )
                print(f"Processing top-up with new card: {new_card.nickname}")
            else:
                # Re-render the page with the form errors
                messages.error(request, "There was an error with your card details. Please check and try again.")
                
                history = profile.wallet_history.all().order_by('-timestamp')
                saved_cards = Card.objects.filter(user=request.user)
                context = {
                    'profile': profile,
                    'history': history,
                    'saved_cards': saved_cards,
                    'selected_card': None, # Don't pre-select a card on error
                    'card_form': card_form, # Pass the invalid form back to the template
                }
                return render(request, self.template_name, context)

        # If payment is successful, update wallet
        profile.wallet_balance += top_up_amount
        profile.save()
        
        WalletHistory.objects.create(
            user_profile=profile,
            transaction_type='TOPUP',
            amount=top_up_amount
        )
        
        messages.success(request, f"Successfully added ${top_up_amount} to your wallet.")
        return redirect('wallet')

class ProfileSettingsView(LoginRequiredMixin, View):
    template_name = 'profile_settings.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class ManageAddressesView(LoginRequiredMixin, ListView):
    model = ShippingAddress
    template_name = 'manage_addresses.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user).order_by('nickname')


class ManageCardsView(LoginRequiredMixin, ListView):
    model = Card
    template_name = 'manage_cards.html'
    context_object_name = 'cards'

    def get_queryset(self):
        return Card.objects.filter(user=self.request.user).order_by('nickname')


class EditShippingAddressView(LoginRequiredMixin, View):
    template_name = 'edit_shipping_address.html'

    def get(self, request, *args, **kwargs):
        address = get_object_or_404(ShippingAddress, pk=self.kwargs['pk'], user=request.user)
        return render(request, self.template_name, {'address': address})

    def post(self, request, *args, **kwargs):
        address = get_object_or_404(ShippingAddress, pk=self.kwargs['pk'], user=request.user)
        
        address.nickname = request.POST.get('nickname')
        address.first_name = request.POST.get('first_name')
        address.last_name = request.POST.get('last_name')
        address.phone = request.POST.get('phone')
        address.address = request.POST.get('address')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        
        try:
            address.save()
            messages.success(request, f"Address '{address.nickname}' updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating address: {e}")

        return redirect('manage_addresses')


class EditCardView(LoginRequiredMixin, View):
    template_name = 'edit_card.html'

    def get(self, request, *args, **kwargs):
        card = get_object_or_404(Card, pk=self.kwargs['pk'], user=request.user)
        return render(request, self.template_name, {'card': card})

    def post(self, request, *args, **kwargs):
        card = get_object_or_404(Card, pk=self.kwargs['pk'], user=request.user)
        
        card.nickname = request.POST.get('nickname')
        card.cardholder_name = request.POST.get('cardholder_name')
        card.expiry_month = request.POST.get('expiry_month')
        card.expiry_year = request.POST.get('expiry_year')
        
        try:
            card.save()
            messages.success(request, f"Card '{card.nickname}' updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating card: {e}")

        return redirect('manage_cards')


class DeleteShippingAddressView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        address = get_object_or_404(ShippingAddress, pk=self.kwargs['pk'], user=request.user)
        try:
            address.delete()
            messages.success(request, "Address deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting address: {e}")
        return redirect('manage_addresses')


class DeleteCardView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        card = get_object_or_404(Card, pk=self.kwargs['pk'], user=request.user)
        try:
            card.delete()
            messages.success(request, "Card deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting card: {e}")
        return redirect('manage_cards')


class ChangePasswordView(LoginRequiredMixin, View):
    template_name = 'change_password.html'
    form_class = PasswordChangeForm

    def get(self, request, *args, **kwargs):
        form = self.form_class(user=request.user)
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Important to keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile_settings')
        else:
            # The form will contain the error messages
            messages.error(request, 'Please correct the errors below.')
        
        context = {'form': form}
        return render(request, self.template_name, context)


class MyVouchersView(LoginRequiredMixin, ListView):
    model = Voucher
    template_name = 'my_vouchers.html'
    context_object_name = 'vouchers'

    def get_queryset(self):
        """
        Returns the vouchers associated with the current user's profile.
        Orders them so that active vouchers appear before expired ones.
        """
        profile = get_object_or_404(UserProfile, user=self.request.user)
        
        # Annotate with an 'is_expired' field to sort by
        today = date.today()
        return profile.vouchers.annotate(
            is_expired=Q(expiry_date__lt=today) | Q(is_active=False)
        ).order_by('is_expired', '-expiry_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = date.today()
        return context

class DeleteAccountView(LoginRequiredMixin, View):
    template_name = 'delete_account.html'
    
    class PasswordConfirmationForm(forms.Form):
        password = forms.CharField(widget=forms.PasswordInput, label="Confirm Your Password")

    def get(self, request, *args, **kwargs):
        form = self.PasswordConfirmationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.PasswordConfirmationForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['password']):
                # Log the user out before deleting
                logout(request)
                # Delete the user
                user.delete()
                messages.success(request, "Your account has been permanently deleted.")
                return redirect('storefront_home')
            else:
                messages.error(request, "Incorrect password. Account deletion failed.")
        
        return render(request, self.template_name, {'form': form})