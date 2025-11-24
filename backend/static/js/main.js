// Main JavaScript for Readify Library Management System

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Confirm delete actions
    $('.btn-delete').on('click', function(e) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });

    // Book search with autocomplete
    $('#search-input').on('keyup', function() {
        var query = $(this).val();
        if (query.length >= 2) {
            $.ajax({
                url: '/api/search/',
                data: { 'q': query },
                dataType: 'json',
                success: function(data) {
                    displaySearchResults(data.books);
                }
            });
        } else {
            $('#search-results').empty();
        }
    });

    // Form validation
    $('form').on('submit', function() {
        var $form = $(this);
        var isValid = true;

        // Check required fields
        $form.find('[required]').each(function() {
            if ($(this).val().trim() === '') {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });

        // Email validation
        $form.find('input[type="email"]').each(function() {
            var email = $(this).val();
            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (email && !emailRegex.test(email)) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });

        if (!isValid) {
            showAlert('Please fill in all required fields correctly.', 'danger');
            return false;
        }
    });

    // ISBN validation
    $('input[name="isbn"]').on('blur', function() {
        var isbn = $(this).val();
        if (isbn && !/^\d{13}$/.test(isbn)) {
            $(this).addClass('is-invalid');
            showAlert('ISBN must be exactly 13 digits.', 'warning');
        } else {
            $(this).removeClass('is-invalid');
        }
    });

    // Phone number formatting
    $('input[name="phone"]').on('input', function() {
        var phone = $(this).val().replace(/\D/g, '');
        if (phone.length >= 10) {
            phone = phone.substring(0, 10);
            phone = phone.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
            $(this).val(phone);
        }
    });

    // Loading states for buttons
    $('form').on('submit', function() {
        var $submitBtn = $(this).find('button[type="submit"]');
        $submitBtn.prop('disabled', true);
        $submitBtn.html('<span class="loading"></span> Processing...');
    });

    // Book availability check
    $('.btn-borrow').on('click', function(e) {
        var $btn = $(this);
        var bookId = $btn.data('book-id');
        
        $.ajax({
            url: '/api/check-availability/',
            data: { 'book_id': bookId },
            dataType: 'json',
            success: function(data) {
                if (!data.available) {
                    e.preventDefault();
                    showAlert('This book is no longer available for borrowing.', 'warning');
                    $btn.prop('disabled', true).text('Not Available');
                }
            }
        });
    });

    // Fine calculation
    function calculateFine(dueDate) {
        var today = new Date();
        var due = new Date(dueDate);
        var diffTime = today - due;
        var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays > 0) {
            var dailyRate = 5.0; // From settings
            var maxDays = 30;
            var daysToCharge = Math.min(diffDays, maxDays);
            return daysToCharge * dailyRate;
        }
        return 0;
    }

    // Update fine amounts
    $('.fine-amount').each(function() {
        var dueDate = $(this).data('due-date');
        var fine = calculateFine(dueDate);
        if (fine > 0) {
            $(this).text('$' + fine.toFixed(2));
            $(this).addClass('text-danger');
        }
    });

    // Table sorting
    $('.sortable').on('click', 'th[data-sort]', function() {
        var $th = $(this);
        var column = $th.data('sort');
        var direction = $th.hasClass('asc') ? 'desc' : 'asc';
        
        $('.sortable th').removeClass('asc desc');
        $th.addClass(direction);
        
        // Sort table rows
        var $tbody = $('.sortable tbody');
        var $rows = $tbody.find('tr').toArray();
        
        $rows.sort(function(a, b) {
            var aVal = $(a).find('td[data-sort="' + column + '"]').text();
            var bVal = $(b).find('td[data-sort="' + column + '"]').text();
            
            if (direction === 'asc') {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });
        
        $.each($rows, function(index, row) {
            $tbody.append(row);
        });
    });

    // Print functionality
    $('.btn-print').on('click', function() {
        window.print();
    });

    // Export functionality
    $('.btn-export').on('click', function() {
        var format = $(this).data('format');
        var tableId = $(this).data('table');
        
        if (format === 'csv') {
            exportToCSV(tableId);
        } else if (format === 'pdf') {
            exportToPDF(tableId);
        }
    });

    // Dark mode toggle (if implemented)
    $('#dark-mode-toggle').on('click', function() {
        $('body').toggleClass('dark-mode');
        localStorage.setItem('darkMode', $('body').hasClass('dark-mode'));
    });

    // Load dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        $('body').addClass('dark-mode');
    }
});

// Utility functions
function showAlert(message, type) {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('.container').first().prepend(alertHtml);
    
    setTimeout(function() {
        $('.alert').first().fadeOut('slow');
    }, 5000);
}

function getAlertIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

function displaySearchResults(books) {
    var $results = $('#search-results');
    $results.empty();
    
    if (books.length === 0) {
        $results.html('<div class="text-muted">No books found</div>');
        return;
    }
    
    books.forEach(function(book) {
        var bookHtml = `
            <div class="search-result-item">
                <a href="${book.url}" class="text-decoration-none">
                    <div class="d-flex align-items-center p-2 border-bottom">
                        <div class="me-3">
                            <i class="fas fa-book fa-2x text-muted"></i>
                        </div>
                        <div>
                            <h6 class="mb-0">${book.title}</h6>
                            <small class="text-muted">${book.authors.join(', ')}</small>
                            <br>
                            <small class="text-muted">ISBN: ${book.isbn}</small>
                        </div>
                        <div class="ms-auto">
                            <span class="badge bg-${book.available ? 'success' : 'secondary'}">
                                ${book.available ? 'Available' : 'Unavailable'}
                            </span>
                        </div>
                    </div>
                </a>
            </div>
        `;
        $results.append(bookHtml);
    });
}

function exportToCSV(tableId) {
    var table = document.getElementById(tableId);
    var csv = [];
    var rows = table.querySelectorAll('tr');
    
    for (var i = 0; i < rows.length; i++) {
        var row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (var j = 0; j < cols.length; j++) {
            row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
        }
        
        csv.push(row.join(','));
    }
    
    var csvContent = csv.join('\n');
    var blob = new Blob([csvContent], { type: 'text/csv' });
    var url = window.URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'library_data.csv';
    a.click();
    window.URL.revokeObjectURL(url);
}

function exportToPDF(tableId) {
    // This would require a PDF library like jsPDF
    showAlert('PDF export functionality requires additional setup.', 'info');
}

// AJAX error handling
$(document).ajaxError(function(event, xhr, settings, thrownError) {
    console.error('AJAX Error:', thrownError);
    showAlert('An error occurred. Please try again.', 'danger');
});

// Form reset
function resetForm(formId) {
    document.getElementById(formId).reset();
    $('#' + formId + ' .is-invalid').removeClass('is-invalid');
}

// Date formatting
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Number formatting
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Apply debounced search
$('#search-input').on('keyup', debounce(function() {
    var query = $(this).val();
    if (query.length >= 2) {
        // Perform search
    }
}, 300));
