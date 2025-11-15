from django.shortcuts import render, get_object_or_404, redirect
from storefront.models import Product, Voucher, Transactions, OrderItem
from django.db.models import Q
from django.views import View
from .forms import ProductCreateForm, VoucherForm, CustomerVoucherAssignForm, SuperUserCreationForm, DeliveryAdminCreationForm, BulkStatusUpdateForm
from django.urls import reverse
from django.contrib import messages
from django import forms
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.db.models import Sum, F, DecimalField, Max, Count, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncQuarter
from decimal import Decimal
from django.core.paginator import Paginator
from authentication.models import UserProfile, WalletHistory
from django.contrib.auth.models import User
import secrets, string
from django.http import HttpResponseForbidden, HttpResponse
from django.utils import timezone
from datetime import timedelta
import matplotlib
matplotlib.use('Agg')  # Setting non-GUI backend before importing pyplot
import matplotlib.pyplot as plt
from io import BytesIO

from storefront.models import ChatThread, ChatMessage
from django.http import HttpResponseForbidden, HttpResponse
from django.utils import timezone
from datetime import timedelta
import matplotlib
matplotlib.use('Agg')  # Setting non-GUI backend before importing pyplot
import matplotlib.pyplot as plt
from io import BytesIO

SKU_MAPPINGS = {
    'Automotive': {
        'initial': 'A',
        'subcats': {
            'Car Care': 'CC',
            'Tools & Equipment': 'T&',
            'Exterior Accessories': 'EA',
            'Interior Accessories': 'IA',
            'Oils & Fluids': 'O&',
        }
    },
    'Beauty & Personal Care': {
        'initial': 'BP',
        'subcats': {
            'Fragrances': 'F',
            'Hair Care': 'HC',
            'Makeup': 'M',
            'Grooming Tools': 'GT',
            'Skincare': 'S',
        }
    },
    'Books': {
        'initial': 'B',
        'subcats': {
            'Children': 'C',
            'Comics & Manga': 'C&',
            'Fiction':"F",
            'Non?Fiction': 'N',
            'Textbooks': 'T',
        }
    },
    'Electronics': {
        'initial': 'E',
        'subcats': {
            'Cameras': 'C',
            'Headphones': 'H',
            'Laptops': 'L',
            'Monitors': 'M',
            'Printers': 'P',
            'Smartphones': 'S',
            'Smart Home': 'SH',
            'Smartwatches': 'S',
            'Tablets': 'T',
        }
    },
    'Fashion - Men': {
        'initial': 'F-',
        'subcats': {
            'Accessories': 'A',
            'Bottoms': 'B',
            'Footwear': 'F',
            'Outerwear': 'O',
            'Tops': 'T',
        }
    },
    'Fashion - Women': {
        'initial': 'F-',
        'subcats': {
            'Accessories': 'A',
            'Bottoms': 'B',
            'Dresses': 'D',
            'Handbags': 'H',
            'Footwear': 'F',
            'Outerwear': 'O',
            'Tops': 'T',
        }
    },
    'Groceries & Gourmet': {
        'initial': 'GG',
        'subcats': {
            'Beverages': 'B',
            'Breakfast': 'BF',
            'Health Foods': 'HF',
            'Pantry Staples': 'PS',
            'Snacks': 'S',
        }
    },
    'Health': {
        'initial': 'H',
        'subcats': {
            'Supplements': 'S',
            'First Aid': 'FA',
            'Medical Devices': 'MD',
            'Personal Care':'PC'
        }
    },
    'Home & Kitchen': {
        'initial': 'HK',
        'subcats': {
            'Small Appliances': 'SA',
            'Bedding': 'B',
            'Cookware': 'C',
            'Vacuum & Cleaning': 'C&',
            'Home Decor': 'HD',
            'Storage & Organization': 'S&',
        }
    },
    'Pet Supplies': {
        'initial': 'PS',
        'subcats': {
            'Accessories': 'A',
            'Aquatic':'A',
            'Cat': 'C',
            'Dog': 'D',
            'Small Pets': 'SP',
        }
    },
    'Sports & Outdoors': {
        'initial': 'SO',
        'subcats': {
            'Camping & Hiking': 'C&',
            'Cycling': 'C',
            'Fitness Equipment': 'FE',
            'Team Sports': 'TS',
            'Yoga & Wellness': 'Y&',
        }
    },
    'Toys & Games': {
        'initial': 'TG',
        'subcats': {
            'Action Figures': 'AF',
            'Board Games': 'BG',
            'Building Sets':'BS',
            'Puzzles': 'P',
            'STEM Toys': 'ST',
        }
    },
}

# helper function for decorator functions
def is_staff(user):
    return user.is_staff

def is_delivery_admin(user):
    """Check if user is a delivery admin"""
    if not user.is_staff:
        return False
    try:
        return user.userprofile.is_delivery_admin
    except:
        return False

def is_not_delivery_admin(user):
    """Check if user is staff but NOT a delivery admin (regular admin/superuser)"""
    if not user.is_staff:
        return False
    try:
        return not user.userprofile.is_delivery_admin
    except:
        return True  # If no profile, assume they're regular admin

def analytics_view(request):
    return render(request, 'auroraadmin/analytics.html')

def _create_empty_chart(title):
    """
    Creates a placeholder chart image with a "No Data" message.
    """
    plt.close('all')  # Clear any existing matplotlib state
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, "No data available", 
             ha='center', va='center', fontsize=14, color='gray', fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

# dispatch is the method that redirects to the right functions after all the checks have been cleared
@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_not_delivery_admin, login_url='/login'), name='dispatch')
class ProductInventoryView(View):
    template_name = 'auroraadmin/product.html'
    paginate_by = 20
   
    def get(self, request, *args, **kwargs):
        # query and filter set up
        productsSet = Product.objects.all().order_by('sku_code')

        # search parameters (received from URL)
        search_query = request.GET.get('q')
        category_filter = request.GET.get('category')
        itemChange_pk = request.GET.get('edit')

        # filtering logic
        if category_filter and category_filter != 'All':
            productsSet = productsSet.filter(product_category=category_filter)

        if search_query:
            # search by Name or Code
            productsSet = productsSet.filter(
                Q(product_name__icontains=search_query) |
                Q(sku_code__icontains=search_query)
            )

        # all unique categories for the filter dropdown
        categories = Product.objects.values_list('product_category', flat=True).distinct().order_by('product_category')

        # Pagination
        paginator = Paginator(productsSet, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # prepare context
        context = {
            'products': page_obj,
            'page_obj': page_obj,
            'categories': categories,
            'search_query': search_query,
            'category_filter': category_filter,
            'selected_category': category_filter,
            'itemChange_pk': itemChange_pk,
        }

        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        pk = request.POST.get('pk')
        action = request.POST.get('action')

        # preserve the filter/search for redirect
        search_query = request.POST.get('q', '').strip()
        category_filter = request.POST.get('category', '').strip()
        redirect_url = reverse('auroraadmin:product')

        # to update the different search parameters
        params = []
        if search_query:
            params.append(f'q={search_query}')
        if category_filter:
            params.append(f'category={category_filter}')
        if params:
            redirect_url += '?' + '&'.join(params)

        # run the action (reorder)
        if action == "reorder":
            if pk == None:
                return redirect(redirect_url)
            product = get_object_or_404(Product, sku_code=pk)
            try:
                product.quantity_on_hand += product.reorder_quantity
                product.save()
                messages.success(request, f'Order Successful: Reordered {product.reorder_quantity} units of {product.product_name}.')
            except Exception as e:
                print(e)
                messages.error(request, f'Order Failed: {e}')
                pass
            return redirect(redirect_url)
        
@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class AddProductView(View):
    template_name = 'auroraadmin/add_product.html'

    def generate_unique_sku(category, subcategory):
        if category not in SKU_MAPPINGS or subcategory not in SKU_MAPPINGS[category]['subcats']:
            raise ValueError(f"Invalid category/subcategory: {category}/{subcategory}")
        prefix = SKU_MAPPINGS[category]['initial'] + SKU_MAPPINGS[category]['subcats'][subcategory] + '-'
        chars = string.ascii_uppercase +  string.digits
        for _ in range(100):
            random_part = ''.join(secrets.choice(chars) for _ in range(8))
            sku = prefix + random_part
            if not Product.objects.filter(sku_code=sku).exists():
                return sku
        raise ValueError("Could not generate a unique SKU")

    # build the dropdown list for form inputting
    def _build_category_mapper(self):
        catSubcatPairs = Product.objects.values('product_category', 'product_subcategory').distinct()
        mapping = {}
        categories = set()

        for pair in catSubcatPairs:
            category = pair['product_category']
            subcategory = pair['product_subcategory']
            categories.add(category)
            if category not in mapping:
                mapping[category] = set()
            mapping[category].add(subcategory)

        # sort the sets for template use
        for category in mapping:
            mapping[category] = sorted(mapping[category])
        
        return mapping, sorted(categories)


    def get(self, request, *args, **kwargs):
        selected_cat = request.GET.get('load_category', '').strip()
        # prepopulate the form if there is data
        form = ProductCreateForm(request.GET or None)
        categoryToSubCategoryMapping, categories = self._build_category_mapper()

        if selected_cat:
            sub_choices = [(s, s) for s in categoryToSubCategoryMapping.get(selected_cat, [])]
            form.fields['product_subcategory'] = forms.ChoiceField(choices=[('', '---')] + sub_choices, required=True)
            form.initial['product_category'] = selected_cat
        
        context = {
            'form': form,
            'categories': categories,
            'selected_category': selected_cat
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        # for the purpose of error handling, etching the prod cat to shortlist the subcats when returning the form page for the user to check
        selected_cat = request.POST.get('product_category','').strip()
        form = ProductCreateForm(request.POST)
        categoryToSubCategoryMapping, categories = self._build_category_mapper()

        if selected_cat:
            sub_choices = [(s, s) for s in categoryToSubCategoryMapping.get(selected_cat, [])]
            form.fields['product_subcategory'] = forms.ChoiceField(choices=[('', '---')] + sub_choices, required=True)

        if form.is_valid():
            # such that we can create an instance without commiting, such that we can set user defined fields
            product = form.save(commit=False)
            if hasattr(product, "product_rating"):
                product.product_rating = 0.0
            try:
                product.sku_code = AddProductView.generate_unique_sku(product.product_category, product.product_subcategory)
            except ValueError as e:
                messages.error(request, f'Error generating SKU: {e}')
                context = {
                    'form': form,
                    'categories': categories,
                    'selected_category': selected_cat
                }
                return render(request, self.template_name, context)
            product.save()
            messages.success(request, 'Product added successfully.')
            return redirect(reverse('auroraadmin:product'))
        
        context = {
            'form': form,
            'categories': categories,
            'selected_category': selected_cat
        }
        # if there are errors
        return render(request, self.template_name, context)
    
@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class ProductActionsView(View):
    template_name = 'auroraadmin/product_actions.html'

    def get(self, request, sku_code, *args, **kwargs):
        product = get_object_or_404(Product, sku_code=sku_code)
        # Preserve filters for redirect
        search_query = request.GET.get('q', '').strip()
        category_filter = request.GET.get('category', '').strip()
        context = {
            'product': product,
            'search_query': search_query,
            'category_filter': category_filter,
        }
        return render(request, self.template_name, context)

    def post(self, request, sku_code, *args, **kwargs):
        product = get_object_or_404(Product, sku_code=sku_code)
        action = request.POST.get('action')
        search_query = request.POST.get('q', '').strip()
        category_filter = request.POST.get('category', '').strip()
        redirect_url = reverse('auroraadmin:product_actions',kwargs={'sku_code':sku_code})
        params = []
        if search_query:
            params.append(f'q={search_query}')
        if category_filter:
            params.append(f'category={category_filter}')
        if params:
            redirect_url += '?' + '&'.join(params)

        if action == "reorder":
            try:
                product.quantity_on_hand += product.reorder_quantity
                product.save()
                messages.success(request, f'Order Successful: Reordered {product.reorder_quantity} units of {product.product_name}.')
            except Exception as e:
                messages.error(request, f'Order Failed: {e}')
        
        elif action == "change_price":
            new_price = request.POST.get('new_price')
            try:
                product.unit_price = float(new_price)
                product.save()
                messages.success(request, f'Price updated successfully for {product.product_name} to ${product.unit_price:.2f}.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid price value.')
        
        return redirect(redirect_url)

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class DeleteProductView(View):
    template_name = 'auroraadmin/product_confirm_del.html'

    def get(self, request, sku_code, *args, **kwargs):
        product = get_object_or_404(Product,sku_code=sku_code)
        context = {
            'product': product
        }
        return render(request, self.template_name, context)
    
    def post(self, request, sku_code, *args, **kwargs):
        product = get_object_or_404(Product,sku_code=sku_code)
        product_name = product.product_name
        product.delete()
        return redirect(reverse('auroraadmin:product'))

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')    
class TransactionListView(View):
    template_name = 'auroraadmin/transactions_list.html'
    
    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('q', '').strip()
        sort_by = request.GET.get('sort', '-transaction_datetime')
        user_id = request.GET.get('user_id', '').strip()

        # Define valid sort fields (same as before)
        valid_sort_fields = [
            'user__id', '-user__id',
            'transaction_datetime', '-transaction_datetime',
            'viewcal_num_of_products', '-viewcal_num_of_products',
            'viewcal_total_spent', '-viewcal_total_spent'
        ]

        if sort_by not in valid_sort_fields:
            sort_by = '-transaction_datetime'

        # Helper function to get filtered, sorted, and paginated queryset for a status
        def get_paginated_transactions(status, page_param):
            queryset = Transactions.objects.filter(status=status).select_related('user').annotate(
                viewcal_num_of_products=Sum('items__quantity_purchased', default=0),
                viewcal_total_spent=Sum(
                    F('items__quantity_purchased') * F('items__price_at_purchase'),
                    default=Decimal(0.0),
                    output_field=DecimalField()
                ) + F('voucher_value')
            )

            if user_id:
                queryset = queryset.filter(user__id=user_id)


            if search_query:
                queryset = queryset.filter(user__username=search_query)

            queryset = queryset.order_by(sort_by)

            paginator = Paginator(queryset, 30)
            page_number = request.GET.get(page_param)
            return paginator.get_page(page_number)

        # paginated data for each status
        payment_page = get_paginated_transactions('Payment Made', 'payment_page')
        delivered_page = get_paginated_transactions('Delivered to Warehouse', 'delivered_page')
        completed_page = get_paginated_transactions('Delivery Completed', 'completed_page')

        context = {
            'page_title': 'Transactions',
            'search_query': search_query,
            'current_sort': sort_by,
            'user_id': user_id,
            'payment_page': payment_page,
            'delivered_page': delivered_page,
            'completed_page': completed_page,
        }
        return render(request, self.template_name, context)
    
class TransactionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Transactions
    template_name = 'auroraadmin/transaction_detail.html'
    context_object_name = 'transaction'
    login_url ='/login'

    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Transaction {self.object.id}'

        grand_total = sum(item.quantity_purchased * item.price_at_purchase for item in self.object.items.all())
        voucher_value = self.object.voucher_value
        final_total = grand_total + voucher_value
        context['grand_total'] = grand_total        
        context['voucher_value'] = voucher_value
        context['final_total'] = final_total
        return context

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_delivery_admin, login_url='/login'), name='dispatch')
class BulkStatusUpdateView(View):
    template_name = 'auroraadmin/bulk_status_update.html'
    
    def get(self, request, *args, **kwargs):
        # Get all transactions grouped by status
        payment_made = Transactions.objects.filter(status='Payment Made').select_related('user').annotate(
            viewcal_num_of_products=Sum('items__quantity_purchased', default=0),
            viewcal_total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase'),
                default=Decimal(0.0),
                output_field=DecimalField()
            ) + F('voucher_value')
        ).order_by('-transaction_datetime')
        
        delivered_warehouse = Transactions.objects.filter(status='Delivered to Warehouse').select_related('user').annotate(
            viewcal_num_of_products=Sum('items__quantity_purchased', default=0),
            viewcal_total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase'),
                default=Decimal(0.0),
                output_field=DecimalField()
            ) + F('voucher_value')
        ).order_by('-transaction_datetime')
        
        form = BulkStatusUpdateForm()
        
        context = {
            'page_title': 'Bulk Status Update',
            'payment_made': payment_made,
            'delivered_warehouse': delivered_warehouse,
            'form': form,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        form = BulkStatusUpdateForm(request.POST)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            transaction_ids_str = form.cleaned_data['transaction_ids']
            
            # Parse the comma-separated transaction IDs
            try:
                transaction_ids = [int(id.strip()) for id in transaction_ids_str.split(',') if id.strip()]
            except ValueError:
                messages.error(request, 'Invalid transaction IDs.')
                return redirect('auroraadmin:bulk_status_update')
            
            if not transaction_ids:
                messages.error(request, 'No transactions selected.')
                return redirect('auroraadmin:bulk_status_update')
            
            # Perform the status update
            if action == 'to_warehouse':
                transactions = Transactions.objects.filter(
                    id__in=transaction_ids, 
                    status='Payment Made'
                )
                updated_count = transactions.update(status='Delivered to Warehouse')
                messages.success(
                    request, 
                    f'Successfully updated {updated_count} transaction(s) to "Delivered to Warehouse".'
                )
            
            elif action == 'to_completed':
                transactions = Transactions.objects.filter(
                    id__in=transaction_ids, 
                    status='Delivered to Warehouse'
                )
                updated_count = transactions.update(status='Delivery Completed')
                messages.success(
                    request, 
                    f'Successfully updated {updated_count} transaction(s) to "Delivery Completed".'
                )
            
            return redirect('auroraadmin:bulk_status_update')
        
        # If form is invalid, re-render with errors
        payment_made = Transactions.objects.filter(status='Payment Made').select_related('user').annotate(
            viewcal_num_of_products=Sum('items__quantity_purchased', default=0),
            viewcal_total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase'),
                default=Decimal(0.0),
                output_field=DecimalField()
            ) + F('voucher_value')
        ).order_by('-transaction_datetime')
        
        delivered_warehouse = Transactions.objects.filter(status='Delivered to Warehouse').select_related('user').annotate(
            viewcal_num_of_products=Sum('items__quantity_purchased', default=0),
            viewcal_total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase'),
                default=Decimal(0.0),
                output_field=DecimalField()
            ) + F('voucher_value')
        ).order_by('-transaction_datetime')
        
        context = {
            'page_title': 'Bulk Status Update',
            'payment_made': payment_made,
            'delivered_warehouse': delivered_warehouse,
            'form': form,
        }
        return render(request, self.template_name, context)

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_not_delivery_admin, login_url='/login'), name='dispatch')
class VoucherManagementView(View):
    template_name = 'auroraadmin/vouchers.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        form = VoucherForm()
        voucher_list = Voucher.objects.all().order_by('code')

        paginator = Paginator(voucher_list, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'form': form,
            'vouchers': page_obj, # for rendering the list
            'page_obj': page_obj,  # for pagination controls, allows for better differentiation
        }

        return render(request, self.template_name, context)
    
    # for both creating new voucher and activate/deactivate
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == "create":
            form = VoucherForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Voucher created successfully.')
            else:
                voucher_list = Voucher.objects.all().order_by('code')
                paginator = Paginator(voucher_list, self.paginate_by)
                page_number = request.GET.get('page')
                page_obj = paginator.get_page(page_number)
                context = {
                    'form': form,
                    'vouchers': page_obj, # for rendering the list
                    'page_obj': page_obj,  # for pagination controls, allows for better differentiation
                }
                messages.error(request, 'Failed to save form, please correct the errors.')
                return render(request, self.template_name, context)
        
        elif action == 'toggle_status':
            voucher_pk = request.POST.get('voucher_pk')
            voucher = get_object_or_404(Voucher, id=voucher_pk)
            voucher.is_active = not voucher.is_active
            voucher.save()
            status = 'activated' if voucher.is_active else 'deactivated'
            messages.success(request, f'Voucher {voucher.code} has been successfully {status}')

        elif action == 'mass_assign':
            voucher_pk = request.POST.get('voucher_pk')
            voucher = get_object_or_404(Voucher, id=voucher_pk)

            # find all non-staff users who do not have the given voucher
            user_to_add_voucher = User.objects.filter(is_staff=False).exclude(userprofile__vouchers=voucher)

            count = 0
            for user in user_to_add_voucher:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.vouchers.add(voucher)
                count += 1
            
            voucher.issued_count += count
            voucher.save()

            messages.success(request, f'Voucher assigned to {count} users successfully.')
        
        return redirect('auroraadmin:voucher_list')

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_not_delivery_admin, login_url='/login'), name='dispatch')
class CustomerListView(View):
    template_name = 'auroraadmin/customer.html'
    paginate_by = 40

    def get(self, request, *args, **kwargs):
        # list of none-staff users
        customer_list = User.objects.filter(is_staff=False)

        # searching logic
        search_query = request.GET.get('q', '')
        if search_query:
            # check if only digits present
            if search_query.isdigit():
                search_filters = Q(id=int(search_query))
            else: # check for username
                search_filters = (
                    Q(username__icontains=search_query)
                )
            customer_list = customer_list.filter(search_filters)

        # join userprofile and fetch the vouchers
        customer_list = customer_list.select_related('userprofile').prefetch_related('userprofile__vouchers')

        # use annotation to improve the speed of rendering (calculated fields)
        customer_list = customer_list.annotate(
            total_transactions=Count('transactions', distinct=True),
            total_spent=Sum(
                F('transactions__items__quantity_purchased') * F('transactions__items__price_at_purchase'),
                default=Decimal('0.0'),
                output_field=DecimalField()
            ) + Sum('transactions__voucher_value', default=Decimal('0.0'), output_field=DecimalField()),
            last_transaction_date=Max('transactions__transaction_datetime')
        )

        # sorting
        sort_by = request.GET.get('sort', 'id') # default is id, if sort is not defined
        valid_sort_fields = [
            'username', '-username',
            'id', '-id',
            'email', '-email',
            'userprofile__preferred_category', '-userprofile__preferred_category',
            'total_transactions', '-total_transactions',
            'total_spent', '-total_spent',
            'last_transaction_date', '-last_transaction_date',
        ]

        if sort_by in valid_sort_fields:
            customer_list = customer_list.order_by(sort_by)

        paginator = Paginator(customer_list, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'customers': page_obj, # for looping to view the list
            'page_obj': page_obj, # for page control
            'search_query': search_query,
            'current_sort': sort_by,
        }
        return render(request, self.template_name, context)
    
@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class CustomerVoucherAssignView(View):
    template_name  = 'auroraadmin/customer_add_vouchers.html'

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id, is_staff=False)
        form = CustomerVoucherAssignForm(user=user)
        current_vouchers = user.userprofile.vouchers.all().order_by('code')

        context = {
            'title': f'Assign Vouchers to {user.username}',
            'form': form,
            'customer': user,
            'current_vouchers': current_vouchers,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id, is_staff=False)
        form = CustomerVoucherAssignForm(request.POST, user=user)
        current_vouchers = user.userprofile.vouchers.all().order_by('code')

        if form.is_valid():
            num_assigned = form.save()
            messages.success(request, f'Successfully assigned {num_assigned} vouchers to {user.username}.')
            return redirect('auroraadmin:customers_list')
        
        context = {
            'title': f'Assign Vouchers to {user.username}',
            'form': form,
            'customer': user,
            'current_vouchers': current_vouchers,
        }
        return render(request, self.template_name, context)

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_superuser, login_url='/login'), name='dispatch')
class AdminUserView(View):
    template_name = 'auroraadmin/admin_users.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.username != 'admin':
            return HttpResponseForbidden("Only the main admin user can access this page!")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        admins = User.objects.filter(is_superuser=True).exclude(id=request.user.id)
        
        # Get delivery admins (staff but not superuser, with is_delivery_admin=True)
        delivery_admins = User.objects.filter(
            is_staff=True, 
            is_superuser=False,
            userprofile__is_delivery_admin=True
        ).select_related('userprofile')
        
        superuser_form = SuperUserCreationForm()
        delivery_admin_form = DeliveryAdminCreationForm()
        
        context = {
            'superuser_form': superuser_form,
            'delivery_admin_form': delivery_admin_form,
            'admins': admins,
            'delivery_admins': delivery_admins,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        if 'add_superuser' in request.POST:
            form = SuperUserCreationForm(request.POST)
            
            if form.is_valid():
                form.save()
                messages.success(request, 'New admin user created successfully.')
                return redirect('auroraadmin:admin_users')
            else:
                admins = User.objects.filter(is_superuser=True).exclude(username='admin')
                delivery_admins = User.objects.filter(
                    is_staff=True, 
                    is_superuser=False,
                    userprofile__is_delivery_admin=True
                ).select_related('userprofile')
                delivery_admin_form = DeliveryAdminCreationForm()
                context = {
                    'superuser_form': form,
                    'delivery_admin_form': delivery_admin_form,
                    'admins': admins,
                    'delivery_admins': delivery_admins,
                }
                return render(request, self.template_name, context)
        
        elif 'add_delivery_admin' in request.POST:
            form = DeliveryAdminCreationForm(request.POST)
            
            if form.is_valid():
                form.save()
                messages.success(request, 'New delivery admin user created successfully.')
                return redirect('auroraadmin:admin_users')
            else:
                admins = User.objects.filter(is_superuser=True).exclude(username='admin')
                delivery_admins = User.objects.filter(
                    is_staff=True, 
                    is_superuser=False,
                    userprofile__is_delivery_admin=True
                ).select_related('userprofile')
                superuser_form = SuperUserCreationForm()
                context = {
                    'superuser_form': superuser_form,
                    'delivery_admin_form': form,
                    'admins': admins,
                    'delivery_admins': delivery_admins,
                }
                return render(request, self.template_name, context)
        
        elif 'delete' in request.POST:
            admin_id = request.POST.get('pk')
            admin_user = get_object_or_404(User, id=admin_id, is_superuser=True)
            admin_user.delete()
            messages.success(request, 'Admin user deleted successfully.')
            return redirect('auroraadmin:admin_users')
        
        elif 'delete_delivery_admin' in request.POST:
            admin_id = request.POST.get('pk')
            delivery_user = get_object_or_404(
                User, 
                id=admin_id, 
                is_staff=True, 
                is_superuser=False
            )
            delivery_user.delete()
            messages.success(request, 'Delivery admin user deleted successfully.')
            return redirect('auroraadmin:admin_users')
        
        return self.get(request)

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_not_delivery_admin, login_url='/login'), name='dispatch')
class DashboardView(View):
    template_name = 'auroraadmin/dashboard.html'
    def get(self, request):
        time_frame = request.GET.get('time_frame', '1m') # default 1 month
        selected_category = request.GET.get('category', 'all') # default all categories
        now = timezone.now()

        # company current status
        total_customers = User.objects.filter(is_staff=False).count()
        total_delivery_admins = User.objects.filter(is_staff=True, userprofile__is_delivery_admin=True).count()
        total_staff_count = User.objects.filter(is_staff=True).count()
        # "Employees" are all staff members who are NOT delivery admins
        total_employees = total_staff_count - total_delivery_admins
        global_pending_orders = Transactions.objects.filter(status='Payment Made').count()

        # determine start-current frame
        if time_frame == '1w':
            start_date = now - timedelta(weeks=1)
            period_label = 'Last 1 Week'
        elif time_frame == '1m':
            start_date = now - timedelta(days=30)
            period_label = 'Last 1 Month'
        elif time_frame == '3m':
            start_date = now - timedelta(days=90)
            period_label = 'Last 3 Months'
        elif time_frame == '6m':
            start_date = now - timedelta(days=180)
            period_label = 'Last 6 Months'
        elif time_frame == '1y':
            start_date = now - timedelta(days=365)
            period_label = 'Last 1 Year'
        elif time_frame == 'all':
            start_date = None
            period_label = 'All Time'
        else: # stick to the default
            start_date = now - timedelta(days=30)
            period_label = 'Last 1 Month'

        # filtering the transactions and adding total spent for each transaction
        filtered_transactions = Transactions.objects.all()
        if start_date: # gte (>= start date)
            filtered_transactions = filtered_transactions.filter(transaction_datetime__gte=start_date)

        completed_transactions = filtered_transactions.filter(status='Delivery Completed')

        completed_transactions = completed_transactions.annotate(
            total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase'),
                default=Decimal('0.0'),
                output_field=DecimalField()
            ) + F('voucher_value')
        )

        # Filter by category if selected
        product_quantity_by_period = OrderItem.objects.filter(transactions__in=completed_transactions)
        if selected_category != 'all':
            product_quantity_by_period = product_quantity_by_period.filter(product__product_category=selected_category)
        
        product_quantity_by_period = product_quantity_by_period.values(
            'product__product_name', 'product__sku_code', 'product__product_category'
        ).annotate(
            total_sold=Sum('quantity_purchased')
        )

        total_revenue = completed_transactions.aggregate(total=Sum('total_spent'))['total'] or 0
        total_completed_transactions = completed_transactions.count()
        avg_order_value = total_revenue / total_completed_transactions if total_completed_transactions > 0 else 0
        voucher_savings = completed_transactions.aggregate(savings=Sum('voucher_value'))['savings'] or 0

        top_products = product_quantity_by_period.order_by('-total_sold')[:5]
        bottom_products = product_quantity_by_period.order_by('total_sold')[:5]
        
        # Get all available categories for filter dropdown
        all_categories = Product.objects.values_list('product_category', flat=True).distinct().order_by('product_category')
        
        context = {
            # NEW Current Status KPIs
            'total_customers': total_customers,
            'total_employees': total_employees,
            'total_delivery_admins': total_delivery_admins,
            'global_pending_orders': global_pending_orders,

            # Time-Filtered KPIs
            'total_revenue': total_revenue,
            'total_transactions': total_completed_transactions, # Use this corrected value
            'avg_order_value': avg_order_value,
            'voucher_savings': -voucher_savings, # Keeping the negation from your original code
            
            # Page state
            'top_products': top_products,
            'bottom_products': bottom_products,
            'time_frame': time_frame,
            'period_label': period_label,
            'selected_category': selected_category,
            'all_categories': all_categories,
        }

        return render(request, self.template_name, context)

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class GenderChartView(View):
    def get(self, request, time_frame):
        now = timezone.now()
        start_date = None

        # Determine start date (same logic as DashboardView)
        if time_frame == '1w':
            start_date = now - timedelta(weeks=1)
        elif time_frame == '1m':
            start_date = now - timedelta(days=30)
        elif time_frame == '3m':
            start_date = now - timedelta(days=90)
        elif time_frame == '6m':
            start_date = now - timedelta(days=180)
        elif time_frame == '1y':
            start_date = now - timedelta(days=365)

        transactions = Transactions.objects.filter(status='Delivery Completed')
        if start_date:
            transactions = transactions.filter(transaction_datetime__gte=start_date)

        gender_data = UserProfile.objects.filter(
            user__transactions__in=transactions
        ).values('gender').annotate(count=Count('gender')).order_by('gender')

        if not gender_data.exists():
            return _create_empty_chart(f"Customer Gender Distribution ({time_frame})")

        labels = [item['gender'] for item in gender_data]
        sizes = [item['count'] for item in gender_data]
        
        # Clear any existing matplotlib state
        plt.close('all')
        
        fig, ax = plt.subplots(num=1, figsize=(9, 6), dpi=100, clear=True)
        # Set transparent background
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        # Add counts to pie chart labels
        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct*total/100.0))
                return f'{pct:.1f}%\n({val})'
            return my_autopct
        
        ax.pie(sizes, labels=labels, autopct=make_autopct(sizes), startangle=90, 
               colors=['#007ca5', '#28a745', '#ffc107'], textprops={'fontsize': 11, 'color': 'white'})
        plt.tight_layout(pad=0.5)
        
        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100, pad_inches=0.05, 
                   facecolor='none', edgecolor='none', transparent=True)
        plt.close(fig)
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
class AdminChatListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ChatThread
    template_name = 'auroraadmin/chat_list.html'
    context_object_name = 'threads'
    login_url = '/login'

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return ChatThread.objects.all().order_by('-updated_at')

class AdminChatThreadView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'auroraadmin/chat_thread.html'
    login_url = '/login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        thread_id = self.kwargs.get('thread_id')
        thread = get_object_or_404(ChatThread, pk=thread_id)
        messages = thread.messages.all()
        context = {
            'thread': thread,
            'messages': messages
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        thread_id = self.kwargs.get('thread_id')
        thread = get_object_or_404(ChatThread, pk=thread_id)
        
        message = request.POST.get('message')
        if message:
            ChatMessage.objects.create(
                thread=thread,
                sender=request.user,
                message=message
            )
        
        return redirect('auroraadmin:admin_chat_thread', thread_id=thread.pk)

@method_decorator(login_required(login_url='/login/'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login/'), name='dispatch')
class SalesTrendChartView(View):
    def get(self, request, time_frame):
        selected_category = request.GET.get('category', 'all')
        now = timezone.now()
        start_date = None

        if time_frame == '1w':
            start_date = now - timedelta(weeks=1)
            trunc_func = TruncDay
            date_format = '%Y-%m-%d'
        elif time_frame == '1m':
            start_date = now - timedelta(days=30)
            trunc_func = TruncWeek
            date_format = '%Y-%U'
        elif time_frame == '3m':
            start_date = now - timedelta(days=90)
            trunc_func = TruncWeek
            date_format = '%Y-%U'
        elif time_frame == '6m':
            start_date = now - timedelta(days=180)
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        elif time_frame == '1y':
            start_date = now - timedelta(days=365)
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        elif time_frame == 'all':
            trunc_func = TruncQuarter
            date_format = None  # Custom formatting below

        filtered_transactions = Transactions.objects.filter(status='Delivery Completed')
        if start_date:
            filtered_transactions = filtered_transactions.filter(transaction_datetime__gte=start_date)
        
        # Filter by category if selected
        if selected_category != 'all':
            filtered_transactions = filtered_transactions.filter(
                items__product__product_category=selected_category
            ).distinct()

        filtered_transactions = filtered_transactions.annotate(
            final_total=Sum(F('items__quantity_purchased') * F('items__price_at_purchase')) + F('voucher_value')
        )

        sales_trend = filtered_transactions.annotate(
            date=trunc_func('transaction_datetime')
        ).values('date').annotate(
            revenue=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase') + F('voucher_value'),
                default=Decimal('0.0'),
                output_field=DecimalField()
            )
        ).order_by('date')
        
        if not sales_trend:
            return _create_empty_chart("Sales Trend Chart")

        dates = []
        for item in sales_trend:
            if date_format:
                dates.append(item['date'].strftime(date_format))
            else:
                # For 'all', format as Year-Quarter
                year = item['date'].year
                month = item['date'].month
                quarter = (month - 1) // 3 + 1
                dates.append(f"{year}-Q{quarter}")
        revenues = [float(item['revenue']) for item in sales_trend]

        # Clear any existing matplotlib state
        plt.close('all')
        
        fig, ax = plt.subplots(num=2, figsize=(10, 6), dpi=100, clear=True)
        # Set transparent background
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        ax.plot(dates, revenues, marker='o', linewidth=2, markersize=6, color='#4299e1')
        
        # Add value labels next to each point
        for i, revenue in enumerate(revenues):
            ax.text(i, revenue, f'${revenue:.0f}', 
                   ha='left', va='bottom', fontsize=9, fontweight='bold', color='white')
        
        ax.set_xlabel('Period', labelpad=10, fontsize=11, color='white')
        ax.set_ylabel('Revenue (S$)', labelpad=10, fontsize=11, color='white')
        ax.tick_params(axis='x', labelsize=10, colors='white')
        ax.tick_params(axis='y', labelsize=10, colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout(pad=0.5)

        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100, pad_inches=0.05,
                   facecolor='none', edgecolor='none', transparent=True)
        plt.close(fig)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

class RevenueByCategoryChartView(View):
    def get(self, request, time_frame):
        now = timezone.now()
        start_date = None
        selected_category = request.GET.get('category', 'all')

        # Determine start date (same logic as DashboardView)
        if time_frame == '1w':
            start_date = now - timedelta(weeks=1)
        elif time_frame == '1m':
            start_date = now - timedelta(days=30)
        elif time_frame == '3m':
            start_date = now - timedelta(days=90)
        elif time_frame == '6m':
            start_date = now - timedelta(days=180)
        elif time_frame == '1y':
            start_date = now - timedelta(days=365)

        # Filter transactions
        filtered_transactions = Transactions.objects.filter(status='Delivery Completed')
        if start_date:
            filtered_transactions = filtered_transactions.filter(transaction_datetime__gte=start_date)

        # If category is selected, show subcategories; otherwise show categories
        order_items = OrderItem.objects.filter(transactions__in=filtered_transactions)
        
        if selected_category != 'all':
            # Filter by category and group by subcategory
            order_items = order_items.filter(product__product_category=selected_category)
            revenue_data = order_items.values(
                'product__product_subcategory'
            ).annotate(
                total_revenue=Sum(
                    F('quantity_purchased') * F('price_at_purchase') + F('transactions__voucher_value'),
                    default=Decimal('0.0'),
                    output_field=DecimalField()
                )
            ).order_by('-total_revenue')[:10]
            
            if not revenue_data:
                return _create_empty_chart(f"Revenue by Subcategory in {selected_category} ({time_frame})")
            
            labels = [item['product__product_subcategory'] or 'Uncategorized' for item in revenue_data]
        else:
            # Group by category
            revenue_data = order_items.values(
                'product__product_category'
            ).annotate(
                total_revenue=Sum(
                    F('quantity_purchased') * F('price_at_purchase') + F('transactions__voucher_value'),
                    default=Decimal('0.0'),
                    output_field=DecimalField()
                )
            ).order_by('-total_revenue')[:10]
            
            if not revenue_data:
                return _create_empty_chart(f"Revenue by Category ({time_frame})")
            
            labels = [item['product__product_category'] or 'Uncategorized' for item in revenue_data]

        revenues = [float(item['total_revenue']) for item in revenue_data]

        # Clear any existing matplotlib state
        plt.close('all')
        
        # Create vertical bar chart - wider for better readability
        fig, ax = plt.subplots(num=3, figsize=(12, 8), dpi=100, clear=True)
        # Set transparent background
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        bars = ax.bar(labels, revenues, color='#28a745')  # Vertical bars
        
        # Add value labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.0f}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='white')
        
        ax.set_xlabel('Subcategory' if selected_category != 'all' else 'Category', labelpad=12, fontsize=11, color='white')
        ax.set_ylabel('Revenue (S$)', labelpad=12, fontsize=11, color='white')
        ax.tick_params(axis='x', labelsize=10, colors='white')
        ax.tick_params(axis='y', labelsize=10, colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout(pad=0.5)

        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100, pad_inches=0.05,
                   facecolor='none', edgecolor='none', transparent=True)
        plt.close(fig)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

class TopBuyersChartView(View):
    """Horizontal bar chart showing top 5 buyers by total transaction amount for the time frame."""
    def get(self, request, time_frame):
        now = timezone.now()
        start_date = None

        # Determine start date (same logic as DashboardView)
        if time_frame == '1w':
            start_date = now - timedelta(weeks=1)
        elif time_frame == '1m':
            start_date = now - timedelta(days=30)
        elif time_frame == '3m':
            start_date = now - timedelta(days=90)
        elif time_frame == '6m':
            start_date = now - timedelta(days=180)
        elif time_frame == '1y':
            start_date = now - timedelta(days=365)

        # Filter transactions for the period
        filtered_transactions = Transactions.objects.filter(status='Delivery Completed')
        if start_date:
            filtered_transactions = filtered_transactions.filter(transaction_datetime__gte=start_date)

        # Aggregate total spent per user (only users with at least one transaction will be present)
        buyers = filtered_transactions.values('user__username').annotate(
            total_spent=Sum(
                F('items__quantity_purchased') * F('items__price_at_purchase') + F('voucher_value'),
                default=Decimal('0.0'),
                output_field=DecimalField()
            )
        ).order_by('-total_spent')[:5]

        if not buyers:
            return _create_empty_chart(f"Top Buyers ({time_frame})")

        labels = [b['user__username'] or 'Unknown' for b in buyers]
        amounts = [float(b['total_spent']) for b in buyers]

        # reverse so the largest appears at the top in a horizontal bar chart
        labels = labels[::-1]
        amounts = amounts[::-1]

        plt.close('all')
        fig, ax = plt.subplots(num=10, figsize=(12, 7), dpi=100, clear=True)
        # Set transparent background
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        bars = ax.barh(labels, amounts, color='#667eea')
        
        # Add value labels beside each bar
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'${width:.2f}',
                   ha='left', va='center', fontsize=10, fontweight='bold', color='white')
        
        ax.set_xlabel('Total Spent (S$)', labelpad=12, fontsize=11, color='white')
        ax.set_ylabel('Customer', labelpad=12, fontsize=11, color='white')
        ax.tick_params(axis='x', labelsize=10, colors='white')
        ax.tick_params(axis='y', labelsize=10, colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        plt.tight_layout(pad=0.5)

        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100, pad_inches=0.05,
                   facecolor='none', edgecolor='none', transparent=True)
        plt.close(fig)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class CancelledTransactionsView(ListView):
    model = Transactions
    template_name = 'auroraadmin/cancelled_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transactions.objects.filter(status='Cancelled')
        search_query = self.request.GET.get('q', '').strip()
        sort_by = self.request.GET.get('sort', '-transaction_datetime')

        if search_query:
            queryset = queryset.filter(user__username__icontains=search_query)

        valid_sort_fields = ['transaction_datetime', '-transaction_datetime', 'total_spent', '-total_spent']
        if sort_by in valid_sort_fields:
            if 'total_spent' in sort_by:
                queryset = queryset.annotate(
                    total_spent_calc=Sum(F('items__quantity_purchased') * F('items__price_at_purchase'))
                ).order_by(sort_by.replace('total_spent', 'total_spent_calc'))
            else:
                queryset = queryset.order_by(sort_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_sort'] = self.request.GET.get('sort', '-transaction_datetime')
        return context

@method_decorator(login_required(login_url='/login'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/login'), name='dispatch')
class RefundRequestsView(View):
    template_name = 'auroraadmin/refund_requests.html'

    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('q', '').strip()
        sort_by = request.GET.get('sort', '-transaction_datetime')

        valid_sort_fields = ['transaction_datetime', '-transaction_datetime', 'total_spent', '-total_spent']
        if sort_by not in valid_sort_fields:
            sort_by = '-transaction_datetime'

        def get_paginated_transactions(status, page_param):
            queryset = Transactions.objects.filter(status=status)
            if search_query:
                queryset = queryset.filter(user__username__icontains=search_query)

            if 'total_spent' in sort_by:
                queryset = queryset.annotate(
                    total_spent_calc=Sum(F('items__quantity_purchased') * F('items__price_at_purchase'))
                ).order_by(sort_by.replace('total_spent', 'total_spent_calc'))
            else:
                queryset = queryset.order_by(sort_by)

            paginator = Paginator(queryset, 10) # Adjust page size if needed
            page_number = request.GET.get(page_param)
            return paginator.get_page(page_number)

        pending_page = get_paginated_transactions('Request for Refund', 'pending_page')
        approved_page = get_paginated_transactions('Refund Approved', 'approved_page')
        rejected_page = get_paginated_transactions('Refund Rejected', 'rejected_page')

        context = {
            'pending_page': pending_page,
            'approved_page': approved_page,
            'rejected_page': rejected_page,
            'search_query': search_query,
            'current_sort': sort_by,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        transaction_id = request.POST.get('transaction_id')
        action = request.POST.get('action')
        transaction = get_object_or_404(Transactions, pk=transaction_id)

        if action == 'approve':
            # Calculate the total amount to be refunded
            total_refund = sum(item.quantity_purchased * item.price_at_purchase for item in transaction.items.all())
            
            # The voucher value is stored as a positive number, so we subtract it
            final_refund_amount = total_refund - transaction.voucher_value

            # Get the user and their profile
            user = transaction.user
            if user:
                try:
                    profile = user.userprofile
                    profile.wallet_balance += final_refund_amount
                    profile.save()
                    
                    # Create a history record for the refund
                    WalletHistory.objects.create(
                        user_profile=profile,
                        transaction_type='REFUND',
                        amount=final_refund_amount,
                        related_transaction=transaction
                    )
                    
                    transaction.status = 'Refund Approved'
                    transaction.save()
                    messages.success(request, f"Refund for order #{transaction.pk} has been approved. ${final_refund_amount} was credited to {user.username}'s wallet.")
                
                except UserProfile.DoesNotExist:
                    messages.error(request, f"Could not process refund. User profile for {user.username} not found.")
                except Exception as e:
                    messages.error(request, f"An unexpected error occurred: {e}")
            else:
                messages.error(request, f"Could not process refund. The user for this transaction no longer exists.")

        elif action == 'reject':
            transaction.status = 'Refund Rejected'
            transaction.save()
            messages.error(request, f"Refund for order #{transaction.pk} has been rejected.")
        
        return redirect('auroraadmin:refund_requests')