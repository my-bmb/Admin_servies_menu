// Admin Dashboard JavaScript

$(document).ready(function() {
    // Auto-calculate final price
    $('input[name="price"], input[name="discount"]').on('input', function() {
        const price = parseFloat($('input[name="price"]').val()) || 0;
        const discount = parseFloat($('input[name="discount"]').val()) || 0;
        const finalPrice = price - (price * discount / 100);
        $('#final_price').val(finalPrice.toFixed(2));
    });
    
    // Image preview for file inputs
    $('input[type="file"]').on('change', function(e) {
        const input = $(this);
        const preview = input.siblings('img');
        
        if (preview.length && e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                preview.attr('src', e.target.result);
            };
            
            reader.readAsDataURL(e.target.files[0]);
        }
    });
    
    // Confirm before delete
    $('form[action*="delete"]').submit(function(e) {
        if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
            e.preventDefault();
        }
    });
    
    // Toast notifications
    function showToast(message, type = 'success') {
        const toast = $(`
            <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 11">
                <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(toast);
        const bsToast = new bootstrap.Toast(toast.find('.toast')[0]);
        bsToast.show();
        
        // Remove toast after hiding
        toast.find('.toast').on('hidden.bs.toast', function() {
            $(this).closest('.position-fixed').remove();
        });
    }
    
    // Flash messages to toast
    $('.alert').each(function() {
        const alert = $(this);
        const message = alert.text().trim();
        const type = alert.hasClass('alert-success') ? 'success' : 
                    alert.hasClass('alert-danger') ? 'danger' :
                    alert.hasClass('alert-warning') ? 'warning' :
                    alert.hasClass('alert-info') ? 'info' : 'success';
        
        if (message) {
            showToast(message, type);
        }
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
});
