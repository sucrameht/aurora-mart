from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from ..models import *
from decimal import Decimal
from django.contrib import messages
from django.views.generic import ListView, View
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from authentication.models import UserProfile
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django import forms


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


class ManagePaymentMethodsView(LoginRequiredMixin, ListView):
    model = Card
    template_name = 'manage_payment_methods.html'
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

        return redirect('manage_payment_methods')


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
        return redirect('manage_payment_methods')


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