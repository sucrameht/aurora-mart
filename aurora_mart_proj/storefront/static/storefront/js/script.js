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
});

            