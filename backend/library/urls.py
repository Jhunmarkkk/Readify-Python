from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'library'

urlpatterns = [
    # Home and general pages
    path('', views.home, name='home'),
    path('search/', views.search_books, name='search'),
    path('api/search/', views.api_book_search, name='api_search'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Book-related views
    path('books/', views.BookListView.as_view(), name='book_list'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('books/<int:book_id>/borrow/', views.borrow_book, name='borrow_book'),
    path('books/<int:book_id>/reserve/', views.reserve_book, name='reserve_book'),
    
    # User account views
    path('profile/', views.profile_view, name='profile'),
    path('my-borrowings/', views.my_borrowings, name='my_borrowings'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('my-fines/', views.my_fines, name='my_fines'),
    
    # Borrowing actions
    path('return/<int:borrowing_id>/', views.return_book, name='return_book'),
    path('cancel-reservation/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    
    # Staff views
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin management views (custom admin interface)
    path('manage/<str:model_name>/', views.admin_manage, name='admin_manage'),
    path('manage/<str:model_name>/add/', views.admin_add, name='admin_add'),
    path('manage/<str:model_name>/<int:pk>/edit/', views.admin_edit, name='admin_edit'),
    path('manage/<str:model_name>/<int:pk>/delete/', views.admin_delete, name='admin_delete'),
]
