from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class Category(models.Model):
    """Book categories for better organization"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Author(models.Model):
    """Book authors"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Book(models.Model):
    """Library books"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
    ]

    title = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True, help_text="13-character ISBN")
    authors = models.ManyToManyField(Author, related_name='books')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='books')
    publisher = models.CharField(max_length=200)
    publication_year = models.IntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(2024)]
    )
    pages = models.IntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    total_copies = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    available_copies = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Ensure available_copies doesn't exceed total_copies
        if self.available_copies > self.total_copies:
            self.available_copies = self.total_copies
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        return self.available_copies > 0 and self.status == 'available'


class Borrower(models.Model):
    """Extended user model for library borrowers"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='borrower')
    library_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    membership_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    max_books_allowed = models.IntegerField(default=5, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.library_id})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def current_borrowed_books(self):
        return self.borrowings.filter(return_date__isnull=True).count()

    @property
    def can_borrow_more(self):
        return self.current_borrowed_books < self.max_books_allowed


class Borrowing(models.Model):
    """Book borrowing transactions"""
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('borrowed', 'Borrowed'),
            ('returned', 'Returned'),
            ('overdue', 'Overdue'),
        ],
        default='borrowed'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-borrow_date']
        unique_together = ['borrower', 'book', 'borrow_date']

    def __str__(self):
        return f"{self.borrower.full_name} - {self.book.title}"

    def save(self, *args, **kwargs):
        # Set due date to 14 days from borrow date if not set
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=14)
        
        # Update book availability
        if self.pk is None:  # New borrowing
            self.book.available_copies -= 1
            if self.book.available_copies == 0:
                self.book.status = 'borrowed'
            self.book.save()
        elif self.return_date and not self._state.adding:  # Book returned
            if self.status == 'borrowed':
                self.book.available_copies += 1
                if self.book.status == 'borrowed':
                    self.book.status = 'available'
                self.book.save()
                self.status = 'returned'

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return timezone.now() > self.due_date and self.return_date is None

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (timezone.now() - self.due_date).days
        return 0

    @property
    def fine_amount(self):
        if self.is_overdue:
            days = self.days_overdue
            daily_rate = getattr(settings, 'DAILY_FINE_RATE', 5.0)
            max_days = getattr(settings, 'MAX_FINE_DAYS', 30)
            days_to_charge = min(days, max_days)
            return days_to_charge * daily_rate
        return 0


class Fine(models.Model):
    """Fine records for overdue books"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ]

    borrowing = models.OneToOneField(Borrowing, on_delete=models.CASCADE, related_name='fine')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Fine: ${self.amount} - {self.borrowing}"

    def pay_fine(self, notes=""):
        """Mark fine as paid"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.notes = notes
        self.save()

    def waive_fine(self, notes=""):
        """Waive the fine"""
        self.status = 'waived'
        self.notes = notes
        self.save()


class Reservation(models.Model):
    """Book reservations by borrowers"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE, related_name='reservations')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    request_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['request_date']
        unique_together = ['borrower', 'book', 'request_date']

    def __str__(self):
        return f"{self.borrower.full_name} - {self.book.title}"

    def save(self, *args, **kwargs):
        # Set expiry date to 7 days from request date if not set
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_date and self.status == 'pending'
