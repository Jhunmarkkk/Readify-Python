from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .models import (
    Book, Borrower, Borrowing, Fine, Category, Author, Reservation
)
from .forms import (
    BookForm, BorrowerForm, BorrowingForm, ReturnBookForm,
    SearchForm, ReservationForm, CustomUserCreationForm, FineForm
)
from django.views.generic import DeleteView
from django.contrib.auth.decorators import user_passes_test


class CustomLoginView(BaseLoginView):
    """Custom login view that redirects admin users to dashboard"""
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        """Redirect admin users to dashboard, others to home or next parameter"""
        # Check if there's a 'next' parameter in the URL
        redirect_to = self.request.GET.get('next', '')
        
        # If there's a next parameter, use it (unless it's the login page)
        if redirect_to and redirect_to != reverse('library:login'):
            return redirect_to
        
        # If user is staff and no specific redirect, go to dashboard
        if self.request.user.is_staff:
            return reverse('library:dashboard')
        
        # Otherwise use default redirect (home page)
        return super().get_success_url()


def home(request):
    """Home page with library statistics"""
    context = {
        'total_books': Book.objects.count(),
        'total_borrowers': Borrower.objects.filter(is_active=True).count(),
        'currently_borrowed': Borrowing.objects.filter(return_date__isnull=True).count(),
        'overdue_books': Borrowing.objects.filter(
            return_date__isnull=True,
            due_date__lt=timezone.now()
        ).count(),
        'total_fines': Fine.objects.filter(status='pending').aggregate(
            total=Sum('amount')
        )['total'] or 0,
        'recent_books': Book.objects.order_by('-created_at')[:5],
        'recent_borrowings': Borrowing.objects.order_by('-borrow_date')[:5],
    }
    return render(request, 'library/home.html', context)


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to Readify.')
            return redirect('library:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'library/register.html', {'form': form})


@login_required
def profile_view(request):
    """User profile view"""
    try:
        borrower = request.user.borrower
    except Borrower.DoesNotExist:
        messages.error(request, 'You need a borrower profile to access this page.')
        return redirect('library:home')

    if request.method == 'POST':
        form = BorrowerForm(request.POST, instance=borrower)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('library:profile')
    else:
        form = BorrowerForm(instance=borrower)
    
    return render(request, 'library/profile.html', {'form': form, 'borrower': borrower})


class BookListView(ListView):
    """Display all books with search and filtering"""
    model = Book
    template_name = 'library/books.html'
    context_object_name = 'books'
    paginate_by = 12

    def get_queryset(self):
        queryset = Book.objects.select_related('category').prefetch_related('authors')
        search_query = self.request.GET.get('search', '')
        category_filter = self.request.GET.get('category', '')
        status_filter = self.request.GET.get('status', '')

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(isbn__icontains=search_query) |
                Q(authors__first_name__icontains=search_query) |
                Q(authors__last_name__icontains=search_query) |
                Q(publisher__icontains=search_query)
            ).distinct()

        if category_filter:
            queryset = queryset.filter(category_id=category_filter)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_form'] = SearchForm(self.request.GET)
        context['status_choices'] = Book.STATUS_CHOICES
        return context


class BookDetailView(DetailView):
    """Display book details"""
    model = Book
    template_name = 'library/book_detail.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        
        # Check if current user can borrow this book
        can_borrow = False
        if self.request.user.is_authenticated:
            try:
                borrower = self.request.user.borrower
                can_borrow = (
                    borrower.can_borrow_more and 
                    book.is_available and 
                    borrower.is_active
                )
            except Borrower.DoesNotExist:
                pass

        context.update({
            'can_borrow': can_borrow,
            'recent_borrowings': book.borrowings.order_by('-borrow_date')[:5],
            'has_reservation': False,
        })

        # Check if user has a pending reservation for this book
        if self.request.user.is_authenticated:
            try:
                borrower = self.request.user.borrower
                context['has_reservation'] = borrower.reservations.filter(
                    book=book, status='pending'
                ).exists()
            except Borrower.DoesNotExist:
                pass

        return context


@login_required
def borrow_book(request, book_id):
    """Handle book borrowing"""
    book = get_object_or_404(Book, id=book_id)
    
    try:
        borrower = request.user.borrower
    except Borrower.DoesNotExist:
        messages.error(request, 'You need a borrower profile to borrow books.')
        return redirect('library:home')

    if request.method == 'POST':
        form = BorrowingForm(request.POST)
        if form.is_valid():
            # Check if borrower can borrow more books
            if not borrower.can_borrow_more:
                messages.error(request, 'You have reached the maximum number of books you can borrow.')
                return redirect('library:book_detail', book_id=book.id)

            # Check if book is available
            if not book.is_available:
                messages.error(request, 'This book is not available for borrowing.')
                return redirect('library:book_detail', book_id=book.id)

            # Create borrowing record
            borrowing = form.save(commit=False)
            borrowing.borrower = borrower
            borrowing.book = book
            borrowing.save()

            messages.success(request, f'Successfully borrowed "{book.title}". Due date: {borrowing.due_date.strftime("%Y-%m-%d")}')
            return redirect('library:my_borrowings')

    else:
        form = BorrowingForm()

    return render(request, 'library/borrow_book.html', {
        'form': form,
        'book': book,
        'borrower': borrower
    })


@login_required
def my_borrowings(request):
    """Display current user's borrowings"""
    try:
        borrower = request.user.borrower
        borrowings = borrower.borrowings.select_related('book').order_by('-borrow_date')
        
        # Separate current and past borrowings
        current_borrowings = borrowings.filter(return_date__isnull=True)
        past_borrowings = borrowings.filter(return_date__isnull=False)
        
        # Check for overdue books and create fines
        for borrowing in current_borrowings:
            if borrowing.is_overdue and not hasattr(borrowing, 'fine'):
                fine_amount = borrowing.fine_amount
                if fine_amount > 0:
                    Fine.objects.create(
                        borrowing=borrowing,
                        amount=fine_amount
                    )

        paginator = Paginator(current_borrowings, 10)
        page_number = request.GET.get('page')
        current_page = paginator.get_page(page_number)

    except Borrower.DoesNotExist:
        current_borrowings = Borrowing.objects.none()
        past_borrowings = Borrowing.objects.none()
        current_page = None

    return render(request, 'library/my_borrowings.html', {
        'current_borrowings': current_page,
        'past_borrowings': past_borrowings[:10],  # Show only recent 10
    })


@login_required
def return_book(request, borrowing_id):
    """Handle book return"""
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    # Check if user owns this borrowing or is staff
    if not (request.user == borrowing.borrower.user or request.user.is_staff):
        messages.error(request, 'You can only return your own books.')
        return redirect('library:my_borrowings')

    if request.method == 'POST':
        form = ReturnBookForm(request.POST, instance=borrowing)
        if form.is_valid():
            borrowing = form.save(commit=False)
            borrowing.return_date = timezone.now()
            borrowing.status = 'returned'
            borrowing.save()

            # Update book availability
            book = borrowing.book
            book.available_copies += 1
            if book.status == 'borrowed':
                book.status = 'available'
            book.save()

            messages.success(request, f'Successfully returned "{book.title}".')
            return redirect('library:my_borrowings')

    else:
        form = ReturnBookForm(instance=borrowing)

    return render(request, 'library/return_book.html', {
        'form': form,
        'borrowing': borrowing,
        'fine_amount': borrowing.fine_amount if borrowing.is_overdue else 0
    })


@login_required
def reserve_book(request, book_id):
    """Handle book reservation"""
    book = get_object_or_404(Book, id=book_id)
    
    try:
        borrower = request.user.borrower
    except Borrower.DoesNotExist:
        messages.error(request, 'You need a borrower profile to reserve books.')
        return redirect('library:book_detail', book_id=book.id)

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            # Check if user already has a pending reservation for this book
            if borrower.reservations.filter(book=book, status='pending').exists():
                messages.error(request, 'You already have a pending reservation for this book.')
                return redirect('library:book_detail', book_id=book.id)

            # Create reservation
            reservation = form.save(commit=False)
            reservation.borrower = borrower
            reservation.book = book
            reservation.save()

            messages.success(request, f'Successfully reserved "{book.title}". You will be notified when it becomes available.')
            return redirect('library:my_reservations')

    else:
        form = ReservationForm()

    return render(request, 'library/reserve_book.html', {
        'form': form,
        'book': book,
        'borrower': borrower
    })


@login_required
def my_reservations(request):
    """Display current user's reservations"""
    try:
        borrower = request.user.borrower
        reservations = borrower.reservations.select_related('book').order_by('-request_date')
    except Borrower.DoesNotExist:
        reservations = Reservation.objects.none()

    return render(request, 'library/my_reservations.html', {
        'reservations': reservations
    })


@login_required
def cancel_reservation(request, reservation_id):
    """Cancel a book reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Check if user owns this reservation
    if request.user != reservation.borrower.user:
        messages.error(request, 'You can only cancel your own reservations.')
        return redirect('library:my_reservations')

    if reservation.status == 'pending':
        reservation.status = 'cancelled'
        reservation.save()
        messages.success(request, f'Reservation for "{reservation.book.title}" has been cancelled.')
    else:
        messages.error(request, 'This reservation cannot be cancelled.')

    return redirect('library:my_reservations')


@login_required
def my_fines(request):
    """Display current user's fines"""
    try:
        borrower = request.user.borrower
        fines = Fine.objects.filter(
            borrowing__borrower=borrower
        ).select_related('borrowing__book').order_by('-created_at')
        
        total_fines = fines.aggregate(total=Sum('amount'))['total'] or 0
        pending_fines = fines.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        
    except Borrower.DoesNotExist:
        fines = Fine.objects.none()
        total_fines = 0
        pending_fines = 0

    return render(request, 'library/my_fines.html', {
        'fines': fines,
        'total_fines': total_fines,
        'pending_fines': pending_fines,
    })


def search_books(request):
    """Advanced book search"""
    form = SearchForm(request.GET)
    books = Book.objects.none()
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search', '')
        category = form.cleaned_data.get('category')
        author = form.cleaned_data.get('author')
        
        books = Book.objects.select_related('category').prefetch_related('authors')
        
        if search_query:
            books = books.filter(
                Q(title__icontains=search_query) |
                Q(isbn__icontains=search_query) |
                Q(publisher__icontains=search_query)
            )
        
        if category:
            books = books.filter(category=category)
            
        if author:
            books = books.filter(authors=author)

    # Paginate results
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'library/search.html', {
        'form': form,
        'books': page_obj,
        'results_count': books.count() if form.is_valid() else 0,
    })


# Staff-only views
@login_required
def dashboard(request):
    """Staff dashboard with library statistics"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('library:home')

    # Calculate statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    context = {
        # Basic statistics
        'total_books': Book.objects.count(),
        'total_borrowers': Borrower.objects.filter(is_active=True).count(),
        'active_borrowings': Borrowing.objects.filter(return_date__isnull=True).count(),
        'overdue_borrowings_count': Borrowing.objects.filter(
            return_date__isnull=True,
            due_date__lt=timezone.now()
        ).count(),
        
        # Recent activity
        'recent_borrowings': Borrowing.objects.filter(
            borrow_date__gte=week_ago
        ).count(),
        'recent_returns': Borrowing.objects.filter(
            return_date__gte=week_ago
        ).count(),
        
        # Fines
        'total_fines': Fine.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'pending_fines': Fine.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
        
        # Popular books
        'popular_books': Book.objects.annotate(
            borrow_count=Count('borrowings')
        ).order_by('-borrow_count')[:10],
        
        # Overdue books (QuerySet for detailed list)
        'overdue_borrowings': Borrowing.objects.filter(
            return_date__isnull=True,
            due_date__lt=timezone.now()
        ).select_related('borrower__user', 'book').order_by('due_date'),
        
        # Recent activity
        'recent_activity': Borrowing.objects.select_related(
            'borrower__user', 'book'
        ).order_by('-borrow_date')[:10],
    }

    return render(request, 'library/dashboard.html', context)


def api_book_search(request):
    """API endpoint for AJAX book search"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'books': []})

    books = Book.objects.filter(
        Q(title__icontains=query) |
        Q(isbn__icontains=query)
    )[:10]

    results = []
    for book in books:
        results.append({
            'id': book.id,
            'title': book.title,
            'isbn': book.isbn,
            'authors': [author.full_name for author in book.authors.all()],
            'available': book.is_available,
            'url': reverse('library:book_detail', args=[book.id])
        })

    return JsonResponse({'books': results})


# Admin Management Views - Custom admin interface matching Library Dashboard design
def is_staff_check(user):
    """Check if user is staff"""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_staff_check)
def admin_manage(request, model_name):
    """Unified admin management view for all models"""
    model_map = {
        'books': {'model': Book, 'title': 'Books', 'icon': 'fa-book'},
        'authors': {'model': Author, 'title': 'Authors', 'icon': 'fa-user-pen'},
        'categories': {'model': Category, 'title': 'Categories', 'icon': 'fa-tags'},
        'borrowers': {'model': Borrower, 'title': 'Borrowers', 'icon': 'fa-users'},
        'borrowings': {'model': Borrowing, 'title': 'Borrowings', 'icon': 'fa-book-reader'},
        'fines': {'model': Fine, 'title': 'Fines', 'icon': 'fa-dollar-sign'},
        'reservations': {'model': Reservation, 'title': 'Reservations', 'icon': 'fa-bookmark'},
        'users': {'model': User, 'title': 'Users', 'icon': 'fa-user'},
    }
    
    if model_name not in model_map:
        messages.error(request, 'Invalid model name.')
        return redirect('library:dashboard')
    
    model_info = model_map[model_name]
    model = model_info['model']
    
    # Get search query
    search_query = request.GET.get('search', '')
    queryset = model.objects.all()
    
    # Apply search based on model
    if search_query:
        if model_name == 'books':
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(isbn__icontains=search_query) |
                Q(publisher__icontains=search_query)
            )
        elif model_name == 'authors':
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        elif model_name == 'categories':
            queryset = queryset.filter(name__icontains=search_query)
        elif model_name == 'borrowers':
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(library_id__icontains=search_query)
            )
        elif model_name == 'borrowings':
            queryset = queryset.filter(
                Q(book__title__icontains=search_query) |
                Q(borrower__user__username__icontains=search_query)
            )
        elif model_name == 'fines':
            queryset = queryset.filter(
                Q(borrowing__book__title__icontains=search_query) |
                Q(borrowing__borrower__user__username__icontains=search_query)
            )
        elif model_name == 'reservations':
            queryset = queryset.filter(
                Q(book__title__icontains=search_query) |
                Q(borrower__user__username__icontains=search_query)
            )
        elif model_name == 'users':
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'model_name': model_name,
        'model_title': model_info['title'],
        'model_icon': model_info['icon'],
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': queryset.count(),
    }
    
    return render(request, 'library/admin/manage.html', context)


@login_required
@user_passes_test(is_staff_check)
def admin_add(request, model_name):
    """Add new item for any model"""
    model_map = {
        'books': {'model': Book, 'form': BookForm, 'title': 'Add Book'},
        'authors': {'model': Author, 'form': None, 'title': 'Add Author'},
        'categories': {'model': Category, 'form': None, 'title': 'Add Category'},
    }
    
    if model_name not in model_map:
        messages.error(request, 'Invalid model name.')
        return redirect('library:admin_manage', model_name=model_name)
    
    model_info = model_map[model_name]
    
    if request.method == 'POST':
        if model_name == 'books':
            form = BookForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, f'{model_info["title"]} added successfully!')
                return redirect('library:admin_manage', model_name=model_name)
        elif model_name == 'authors':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            bio = request.POST.get('bio', '')
            birth_date = request.POST.get('birth_date') or None
            if first_name and last_name:
                Author.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    bio=bio,
                    birth_date=birth_date
                )
                messages.success(request, 'Author added successfully!')
                return redirect('library:admin_manage', model_name=model_name)
        elif model_name == 'categories':
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            if name:
                Category.objects.create(name=name, description=description)
                messages.success(request, 'Category added successfully!')
                return redirect('library:admin_manage', model_name=model_name)
    else:
        if model_name == 'books':
            form = BookForm()
        else:
            form = None
    
    # Use special template for books
    template_name = 'library/admin/edit_book.html' if model_name == 'books' else 'library/admin/add.html'
    
    context = {
        'model_name': model_name,
        'title': model_info['title'],
        'form': form,
        'object': None,  # For add page
    }
    
    return render(request, template_name, context)


@login_required
@user_passes_test(is_staff_check)
def admin_edit(request, model_name, pk):
    """Edit existing item for any model"""
    model_map = {
        'books': {'model': Book, 'form': BookForm, 'title': 'Edit Book'},
        'authors': {'model': Author, 'form': None, 'title': 'Edit Author'},
        'categories': {'model': Category, 'form': None, 'title': 'Edit Category'},
        'borrowers': {'model': Borrower, 'form': BorrowerForm, 'title': 'Edit Borrower'},
        'borrowings': {'model': Borrowing, 'form': BorrowingForm, 'title': 'Edit Borrowing'},
        'fines': {'model': Fine, 'form': FineForm, 'title': 'Edit Fine'},
        'reservations': {'model': Reservation, 'form': ReservationForm, 'title': 'Edit Reservation'},
    }
    
    if model_name not in model_map:
        messages.error(request, 'Invalid model name.')
        return redirect('library:admin_manage', model_name=model_name)
    
    model_info = model_map[model_name]
    obj = get_object_or_404(model_info['model'], pk=pk)
    
    if request.method == 'POST':
        if model_name in ['books', 'borrowers', 'borrowings', 'fines', 'reservations']:
            if model_name == 'books':
                form = BookForm(request.POST, request.FILES, instance=obj)
            elif model_name == 'borrowers':
                form = BorrowerForm(request.POST, instance=obj)
            elif model_name == 'borrowings':
                form = BorrowingForm(request.POST, instance=obj)
            elif model_name == 'fines':
                form = FineForm(request.POST, instance=obj)
            elif model_name == 'reservations':
                form = ReservationForm(request.POST, instance=obj)
            
            if form.is_valid():
                form.save()
                messages.success(request, f'{model_info["title"]} updated successfully!')
                return redirect('library:admin_manage', model_name=model_name)
        elif model_name == 'authors':
            obj.first_name = request.POST.get('first_name')
            obj.last_name = request.POST.get('last_name')
            obj.bio = request.POST.get('bio', '')
            birth_date = request.POST.get('birth_date') or None
            obj.birth_date = birth_date
            obj.save()
            messages.success(request, 'Author updated successfully!')
            return redirect('library:admin_manage', model_name=model_name)
        elif model_name == 'categories':
            obj.name = request.POST.get('name')
            obj.description = request.POST.get('description', '')
            obj.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('library:admin_manage', model_name=model_name)
    else:
        if model_name in ['books', 'borrowers', 'borrowings', 'fines', 'reservations']:
            if model_name == 'books':
                form = BookForm(instance=obj)
            elif model_name == 'borrowers':
                form = BorrowerForm(instance=obj)
            elif model_name == 'borrowings':
                form = BorrowingForm(instance=obj)
            elif model_name == 'fines':
                form = FineForm(instance=obj)
            elif model_name == 'reservations':
                form = ReservationForm(instance=obj)
        else:
            form = None
    
    # Use special template for books
    template_name = 'library/admin/edit_book.html' if model_name == 'books' else 'library/admin/edit.html'
    
    context = {
        'model_name': model_name,
        'title': model_info['title'],
        'form': form,
        'object': obj,
    }
    
    return render(request, template_name, context)


@login_required
@user_passes_test(is_staff_check)
def admin_delete(request, model_name, pk):
    """Delete item for any model"""
    model_map = {
        'books': {'model': Book, 'title': 'Book'},
        'authors': {'model': Author, 'title': 'Author'},
        'categories': {'model': Category, 'title': 'Category'},
        'borrowers': {'model': Borrower, 'title': 'Borrower'},
        'borrowings': {'model': Borrowing, 'title': 'Borrowing'},
        'fines': {'model': Fine, 'title': 'Fine'},
        'reservations': {'model': Reservation, 'title': 'Reservation'},
    }
    
    if model_name not in model_map:
        messages.error(request, 'Invalid model name.')
        return redirect('library:admin_manage', model_name=model_name)
    
    model_info = model_map[model_name]
    obj = get_object_or_404(model_info['model'], pk=pk)
    
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'{model_info["title"]} deleted successfully!')
        return redirect('library:admin_manage', model_name=model_name)
    
    context = {
        'model_name': model_name,
        'title': model_info['title'],
        'object': obj,
    }
    
    return render(request, 'library/admin/delete.html', context)
