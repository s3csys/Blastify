document.addEventListener('DOMContentLoaded', function() {
    // Find all pagination elements
    const paginationElements = document.querySelectorAll('.pagination');
    
    // Remove flex-column class from all pagination elements
    paginationElements.forEach(function(pagination) {
        pagination.classList.remove('flex-column');
    });
});