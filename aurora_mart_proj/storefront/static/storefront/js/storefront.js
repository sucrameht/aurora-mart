const modal = document.getElementById('modal');
        const modalTitle = document.getElementById('modal-title');
        const modalImage = document.getElementById('modal-image');
        const modalDescription = document.getElementById('modal-description');
        const modalPrice = document.getElementById('modal-price');
        const modalRating = document.getElementById('modal-rating');
        const modalStock = document.getElementById('modal-stock');

function openModal(element) {
    const name = element.getAttribute('data-name');
    const imageUrl = element.getAttribute('data-image-url');
    const description = element.getAttribute('data-description');
    const price = element.getAttribute('data-price');
    const rating = element.getAttribute('data-rating');
    const stock = element.getAttribute('data-stock');

    modalTitle.textContent = name;
    modalImage.src = imageUrl;
    modalImage.alt = name;
    modalDescription.textContent = description;
    modalPrice.textContent = '$' + price;
    modalRating.innerHTML = '★ ' + rating;
    modalStock.textContent = stock + ' left';
    
    modal.style.display = 'flex';
}

function closeModal() {
    modal.style.display = 'none';
}

window.onclick = function(event) {
    if (event.target === modal) {
        closeModal();
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.querySelector(".search-bar");
    const tabs = document.querySelectorAll(".tab");
    const productCards = document.querySelectorAll(".product-card");
    let activeCategory = "All";

    tabs.forEach(tab => {
        tab.addEventListener("click", function() {
            activeCategory = this.getAttribute("data-category");

            tabs.forEach(t => t.classList.remove("active"));
            this.classList.add("active");

            filterProducts();
        });
    });

    const sortSelect = document.getElementById('sort-options');

    sortSelect.addEventListener('change', function() {
        sortProducts(this.value);
    });

    function sortProducts(sortValue) {
        const productGrid = document.querySelector('.product-grid');
        const products = Array.from(productGrid.querySelectorAll('.product-card'));
    
        let sortedProducts = [...products];
    
        switch (sortValue) {
            case 'name-asc':
                sortedProducts.sort((a, b) =>
                    a.dataset.name.localeCompare(b.dataset.name)
                );
                break;
    
            case 'name-desc':
                sortedProducts.sort((a, b) =>
                    b.dataset.name.localeCompare(a.dataset.name)
                );
                break;
    
            case 'price-asc':
                sortedProducts.sort((a, b) =>
                    parseFloat(a.dataset.price) - parseFloat(b.dataset.price)
                );
                break;
    
            case 'price-desc':
                sortedProducts.sort((a, b) =>
                    parseFloat(b.dataset.price) - parseFloat(a.dataset.price)
                );
                break;
    
            case 'rating-asc':
                sortedProducts.sort((a, b) =>
                    parseFloat(a.dataset.rating) - parseFloat(b.dataset.rating)
                );
                break;
    
            case 'rating-desc':
                sortedProducts.sort((a, b) =>
                    parseFloat(b.dataset.rating) - parseFloat(a.dataset.rating)
                );
                break;
    
            default:
                sortedProducts = products; // keep original order
        }
    
        // Clear and re-render sorted cards
        productGrid.innerHTML = '';
        sortedProducts.forEach(card => productGrid.appendChild(card));
    }

    searchInput.addEventListener("input", function() { filterProducts(); });

    function filterProducts() {
        const query = searchInput.value.toLowerCase();

        productCards.forEach(card => {
            const category = card.getAttribute("data-category");
            const name = card.getAttribute("data-name").toLowerCase();

            const matchesSearch = name.includes(query)
            const matchesCategory = (activeCategory === "All" || category === activeCategory);

            if (matchesSearch && matchesCategory) {
                card.style.display = "flex";
            } else {
                card.style.display = "none";
                
            }
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    const productGrid = document.querySelector('.product-grid');
    const addCartUrl = productGrid.dataset.addCartUrl;

    function showToast(message) {
        const toast = document.getElementById('toast-notification');
        toast.textContent = message;
        toast.className = "show";
        setTimeout(function() { 
            toast.className = toast.className.replace("show", ""); 
        }, 5000);
    }

    document.querySelectorAll('.add-cart').forEach(button => {
        button.addEventListener('click', function(event) {
            const sku = this.getAttribute('data-sku');
            
            const formData = new FormData();
            formData.append('sku_code', sku);

            fetch(addCartUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('cart-count').textContent = data.cart_item_count;
                    showToast(data.message);
                } else {
                    showToast(data.message || 'Error adding to cart');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('An error occurred.');
            });
        });
    });
});

            