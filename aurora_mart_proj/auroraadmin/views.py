from django.shortcuts import render, get_object_or_404, redirect
from storefront.models import Product
from django.db.models import Q
from django.views import View
from .forms import ProductCreateForm
from django.urls import reverse
from django.contrib import messages
from django import forms

# Create your views here.
def analytics_view(request):
    return render(request, 'auroraadmin/analytics.html')

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