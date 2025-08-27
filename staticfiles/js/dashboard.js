// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add loading state to submit buttons
            const submitButtons = form.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-spinner fa-spin';
                }
            });
        });
    });

    // Initialize any Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}); 