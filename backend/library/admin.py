from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Author, Book, Borrower, Borrowing, Fine, Reservation
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'book_count', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    ordering = ['name']

    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books Count'


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'birth_date', 'book_count', 'created_at']
    search_fields = ['first_name', 'last_name']
    list_filter = ['birth_date', 'created_at']
    ordering = ['last_name', 'first_name']

    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books Count'


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        'cover_image_preview', 'title', 'isbn', 'authors_list', 'category', 'status', 
        'available_copies', 'total_copies', 'publication_year'
    ]
    list_filter = ['status', 'category', 'publication_year', 'created_at']
    search_fields = ['title', 'isbn', 'publisher']
    filter_horizontal = ['authors']
    readonly_fields = ['created_at', 'updated_at', 'cover_image_preview']
    ordering = ['title']

    def authors_list(self, obj):
        return ", ".join([author.full_name for author in obj.authors.all()])
    authors_list.short_description = 'Authors'

    def cover_image_preview(self, obj):
        """Display a thumbnail preview of the book cover image"""
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.cover_image.url
            )
        return format_html('<span style="color: #999;">No image</span>')
    cover_image_preview.short_description = 'Cover Image'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'isbn', 'authors', 'category')
        }),
        ('Book Cover Image', {
            'fields': ('cover_image', 'cover_image_preview'),
            'description': 'Upload a cover image for this book. Recommended size: 300x400px or similar aspect ratio.'
        }),
        ('Publication Details', {
            'fields': ('publisher', 'publication_year', 'pages', 'price')
        }),
        ('Availability', {
            'fields': ('status', 'total_copies', 'available_copies')
        }),
        ('Additional Information', {
            'fields': ('description', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BorrowerInline(admin.StackedInline):
    model = Borrower
    can_delete = False
    verbose_name_plural = 'Borrower Profile'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = (BorrowerInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'borrower_status')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')

    def borrower_status(self, obj):
        if hasattr(obj, 'borrower'):
            return format_html(
                '<span style="color: green;">Active Borrower</span>'
            )
        return format_html('<span style="color: red;">No Borrower Profile</span>')
    borrower_status.short_description = 'Borrower Status'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = [
        'library_id', 'full_name', 'email', 'phone', 'membership_date', 
        'is_active', 'current_borrowed_books', 'max_books_allowed'
    ]
    list_filter = ['is_active', 'membership_date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'library_id']
    readonly_fields = ['membership_date']
    ordering = ['user__last_name', 'user__first_name']

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'library_id')
        }),
        ('Contact Information', {
            'fields': ('phone', 'address', 'date_of_birth')
        }),
        ('Membership Settings', {
            'fields': ('is_active', 'max_books_allowed', 'membership_date')
        }),
    )


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = [
        'borrower', 'book', 'borrow_date', 'due_date', 'return_date', 
        'status', 'days_overdue_display', 'fine_amount_display'
    ]
    list_filter = ['status', 'borrow_date', 'due_date', 'return_date']
    search_fields = ['borrower__user__username', 'book__title']
    readonly_fields = ['borrow_date', 'fine_amount_display']
    date_hierarchy = 'borrow_date'
    ordering = ['-borrow_date']

    def days_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red;">{} days</span>',
                obj.days_overdue
            )
        return "0"
    days_overdue_display.short_description = 'Days Overdue'

    def fine_amount_display(self, obj):
        amount = obj.fine_amount
        if amount > 0:
            return format_html('<span style="color: red;">${:.2f}</span>', amount)
        return "$0.00"
    fine_amount_display.short_description = 'Fine Amount'

    fieldsets = (
        ('Borrowing Information', {
            'fields': ('borrower', 'book', 'borrow_date', 'due_date')
        }),
        ('Return Information', {
            'fields': ('return_date', 'status', 'notes')
        }),
        ('Fine Information', {
            'fields': ('fine_amount_display',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = [
        'borrowing', 'amount', 'status', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['borrowing__borrower__user__username', 'borrowing__book__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Fine Information', {
            'fields': ('borrowing', 'amount', 'status')
        }),
        ('Payment Information', {
            'fields': ('paid_at', 'notes')
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_paid', 'waive_fines']

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='paid',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} fines marked as paid.')
    mark_as_paid.short_description = "Mark selected fines as paid"

    def waive_fines(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='waived')
        self.message_user(request, f'{updated} fines waived.')
    waive_fines.short_description = "Waive selected fines"


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'borrower', 'book', 'request_date', 'expiry_date', 'status'
    ]
    list_filter = ['status', 'request_date', 'expiry_date']
    search_fields = ['borrower__user__username', 'book__title']
    readonly_fields = ['request_date']
    date_hierarchy = 'request_date'
    ordering = ['-request_date']

    fieldsets = (
        ('Reservation Information', {
            'fields': ('borrower', 'book', 'request_date', 'expiry_date')
        }),
        ('Status Information', {
            'fields': ('status', 'notes')
        }),
    )

    actions = ['fulfill_reservations', 'cancel_reservations']

    def fulfill_reservations(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='fulfilled')
        self.message_user(request, f'{updated} reservations fulfilled.')
    fulfill_reservations.short_description = "Fulfill selected reservations"

    def cancel_reservations(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{updated} reservations cancelled.')
    cancel_reservations.short_description = "Cancel selected reservations"
