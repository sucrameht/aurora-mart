from .models import CartItem
from django.db.models import Sum

def cart_context(request):
    """
    Provides the cart item count to the context of all templates.
    """
    cart_item_count = 0
    if request.user.is_authenticated:
        # For logged-in users, count items from the database
        cart_item_count = CartItem.objects.filter(user=request.user).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
    else:
        # For anonymous users, count items from the session
        cart = request.session.get('cart', {})
        cart_item_count = sum(cart.values())
        
    return {'cart_item_count': cart_item_count}
