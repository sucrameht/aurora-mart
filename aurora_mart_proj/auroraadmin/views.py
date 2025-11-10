from django.shortcuts import render, get_object_or_404, redirect
from storefront.models import Product, Voucher
from django.db.models import Q
from django.views import View
from .forms import ProductCreateForm, VoucherForm
from django.urls import reverse
from django.contrib import messages
from django import forms
from storefront.models import Transactions
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.db.models import Sum, F, DecimalField
from decimal import Decimal
from django.core.paginator import Paginator
from authentication.models import UserProfile
from django.contrib.auth.models import User

# helper function for decorator functions
def is_staff(user):
    return user.is_staff

def analytics_view(request):
    return render(request, 'auroraadmin/analytics.html')

# dispatch is the method that redirects to the right functions after all the checks have been cleared
@method_decorator(login_required(login_url='/authentication/login/'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/authentication/login/'), name='dispatch')
class ProductInventoryView(View):
    template_name = 'auroraadmin/product.html'
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

        # prepare context
        context = {
            'products': productsSet,
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
        
@method_decorator(login_required(login_url='/authentication/login/'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/authentication/login/'), name='dispatch')
class AddProductView(View):
    template_name = 'auroraadmin/add_product.html'

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
    
@method_decorator(login_required(login_url='/authentication/login/'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/authentication/login/'), name='dispatch')
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
    
class TransactionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Transactions
    template_name = 'auroraadmin/transactions_list.html'
    context_object_name = 'transactions'

    login_url ='/authentication/login/'
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff
    
    # optimisation (avoid slow load time by loading the dataset only once instead on multiple calls)
    def get_queryset(self):
        queryset = super().get_queryset()

        # join the user table
        queryset = queryset.select_related('user')

        # use the annotate func to calc the num of products and total spent in the view
        queryset = queryset.annotate(
            viewcal_num_of_products = Sum('items__quantity_purchased', default=0),
            viewcal_total_spent = Sum(F('items__quantity_purchased') * F('items__product__unit_price'), default=Decimal(0.0), output_field=DecimalField())
        )

        # implementing the search logic
        search_query = self.request.GET.get('q')
        if search_query:
            search_filters = Q(user__username__icontains=search_query)
            if search_query.isdigit():
                # adds the user_id that matches to the search
                search_filters |= Q(user_id=int(search_query))
            queryset = queryset.filter(search_filters)

        # implementing the sorting logic
        sort_by = self.request.GET.get('sort', '-transaction_datetime')

        # defining the fields that are sortable
        valid_sort_fields = [
            'user__id', '-user__id',
            'transaction_datetime', '-transaction_datetime',
            'viewcal_num_of_products', '-viewcal_num_of_products',
            'viewcal_total_spent', '-viewcal_total_spent'
        ]

        # apply valid sort_key if any, order by will clear default
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Transactions'

        # pass search and sort state from the tmplate
        context['search_query'] = self.request.GET.get('q', '')
        context['current_sort'] = self.request.GET.get('sort', '-transaction_datetime')
        
        return context
    
class TransactionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Transactions
    template_name = 'auroraadmin/transaction_detail.html'
    context_object_name = 'transaction'
    login_url ='/authentication/login/'

    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Transaction {self.object.id}'
        return context

@method_decorator(login_required(login_url='/authentication/login/'), name='dispatch')
@method_decorator(user_passes_test(is_staff, login_url='/authentication/login/'), name='dispatch')
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
    
    # for both create and delete (KIV) new voucher
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

            messages.success(request, f'Voucher assigned to {count} users successfully.')
        
        return redirect('auroraadmin:voucher_list')