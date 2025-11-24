from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from library.models import Category, Author, Book, Borrower, Borrowing, Fine


class Command(BaseCommand):
    help = 'Populate the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create categories
        categories_data = [
            {'name': 'Fiction', 'description': 'Novels, short stories, and other fictional works'},
            {'name': 'Non-Fiction', 'description': 'Biographies, history, science, and other factual works'},
            {'name': 'Science Fiction', 'description': 'Science fiction and fantasy novels'},
            {'name': 'Mystery', 'description': 'Mystery and thriller novels'},
            {'name': 'Romance', 'description': 'Romance novels and love stories'},
            {'name': 'Biography', 'description': 'Biographical works and memoirs'},
            {'name': 'History', 'description': 'Historical works and accounts'},
            {'name': 'Science', 'description': 'Scientific works and textbooks'},
            {'name': 'Technology', 'description': 'Computer science and technology books'},
            {'name': 'Philosophy', 'description': 'Philosophical works and theories'},
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create authors
        authors_data = [
            {'first_name': 'George', 'last_name': 'Orwell', 'bio': 'English novelist and essayist'},
            {'first_name': 'Harper', 'last_name': 'Lee', 'bio': 'American novelist'},
            {'first_name': 'F. Scott', 'last_name': 'Fitzgerald', 'bio': 'American novelist and short story writer'},
            {'first_name': 'Jane', 'last_name': 'Austen', 'bio': 'English novelist'},
            {'first_name': 'Mark', 'last_name': 'Twain', 'bio': 'American writer and humorist'},
            {'first_name': 'Charles', 'last_name': 'Dickens', 'bio': 'English writer and social critic'},
            {'first_name': 'J.K.', 'last_name': 'Rowling', 'bio': 'British author, best known for Harry Potter series'},
            {'first_name': 'Stephen', 'last_name': 'King', 'bio': 'American author of horror, supernatural fiction'},
            {'first_name': 'Isaac', 'last_name': 'Asimov', 'bio': 'American writer and professor of biochemistry'},
            {'first_name': 'Arthur C.', 'last_name': 'Clarke', 'bio': 'British science fiction writer'},
        ]

        authors = {}
        for author_data in authors_data:
            author, created = Author.objects.get_or_create(
                first_name=author_data['first_name'],
                last_name=author_data['last_name'],
                defaults={'bio': author_data['bio']}
            )
            authors[f"{author_data['first_name']} {author_data['last_name']}"] = author
            if created:
                self.stdout.write(f'Created author: {author.full_name}')

        # Create books
        books_data = [
            {
                'title': '1984',
                'isbn': '9780451524935',
                'authors': ['George Orwell'],
                'category': 'Fiction',
                'publisher': 'Signet Classics',
                'publication_year': 1949,
                'pages': 328,
                'description': 'A dystopian social science fiction novel about totalitarian control.',
                'total_copies': 3,
                'available_copies': 2,
            },
            {
                'title': 'To Kill a Mockingbird',
                'isbn': '9780061120084',
                'authors': ['Harper Lee'],
                'category': 'Fiction',
                'publisher': 'Harper Perennial',
                'publication_year': 1960,
                'pages': 376,
                'description': 'A novel about racial injustice and childhood innocence.',
                'total_copies': 2,
                'available_copies': 1,
            },
            {
                'title': 'The Great Gatsby',
                'isbn': '9780743273565',
                'authors': ['F. Scott Fitzgerald'],
                'category': 'Fiction',
                'publisher': 'Scribner',
                'publication_year': 1925,
                'pages': 180,
                'description': 'A novel about the American Dream and social class.',
                'total_copies': 4,
                'available_copies': 3,
            },
            {
                'title': 'Pride and Prejudice',
                'isbn': '9780141439518',
                'authors': ['Jane Austen'],
                'category': 'Romance',
                'publisher': 'Penguin Classics',
                'publication_year': 1813,
                'pages': 432,
                'description': 'A romantic novel about Elizabeth Bennet and Mr. Darcy.',
                'total_copies': 3,
                'available_copies': 2,
            },
            {
                'title': 'The Adventures of Tom Sawyer',
                'isbn': '9780486400778',
                'authors': ['Mark Twain'],
                'category': 'Fiction',
                'publisher': 'Dover Publications',
                'publication_year': 1876,
                'pages': 224,
                'description': 'A novel about a young boy growing up along the Mississippi River.',
                'total_copies': 2,
                'available_copies': 1,
            },
            {
                'title': 'A Tale of Two Cities',
                'isbn': '9780486406510',
                'authors': ['Charles Dickens'],
                'category': 'Fiction',
                'publisher': 'Dover Publications',
                'publication_year': 1859,
                'pages': 304,
                'description': 'A novel set during the French Revolution.',
                'total_copies': 2,
                'available_copies': 2,
            },
            {
                'title': 'Harry Potter and the Philosopher\'s Stone',
                'isbn': '9780747532699',
                'authors': ['J.K. Rowling'],
                'category': 'Fiction',
                'publisher': 'Bloomsbury',
                'publication_year': 1997,
                'pages': 223,
                'description': 'The first book in the Harry Potter series.',
                'total_copies': 5,
                'available_copies': 3,
            },
            {
                'title': 'The Shining',
                'isbn': '9780307743657',
                'authors': ['Stephen King'],
                'category': 'Mystery',
                'publisher': 'Anchor',
                'publication_year': 1977,
                'pages': 688,
                'description': 'A horror novel about a haunted hotel.',
                'total_copies': 3,
                'available_copies': 2,
            },
            {
                'title': 'Foundation',
                'isbn': '9780553293357',
                'authors': ['Isaac Asimov'],
                'category': 'Science Fiction',
                'publisher': 'Spectra',
                'publication_year': 1951,
                'pages': 244,
                'description': 'The first book in the Foundation series.',
                'total_copies': 2,
                'available_copies': 1,
            },
            {
                'title': '2001: A Space Odyssey',
                'isbn': '9780451457998',
                'authors': ['Arthur C. Clarke'],
                'category': 'Science Fiction',
                'publisher': 'Ace',
                'publication_year': 1968,
                'pages': 221,
                'description': 'A science fiction novel about human evolution and space exploration.',
                'total_copies': 3,
                'available_copies': 2,
            },
        ]

        books = {}
        for book_data in books_data:
            book, created = Book.objects.get_or_create(
                isbn=book_data['isbn'],
                defaults={
                    'title': book_data['title'],
                    'category': categories[book_data['category']],
                    'publisher': book_data['publisher'],
                    'publication_year': book_data['publication_year'],
                    'pages': book_data['pages'],
                    'description': book_data['description'],
                    'total_copies': book_data['total_copies'],
                    'available_copies': book_data['available_copies'],
                }
            )
            if created:
                # Add authors
                for author_name in book_data['authors']:
                    if author_name in authors:
                        book.authors.add(authors[author_name])
                books[book_data['title']] = book
                self.stdout.write(f'Created book: {book.title}')

        # Create sample users and borrowers
        users_data = [
            {
                'username': 'john_doe',
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'library_id': 'LIB001',
                'phone': '(555) 123-4567',
            },
            {
                'username': 'jane_smith',
                'email': 'jane.smith@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'library_id': 'LIB002',
                'phone': '(555) 234-5678',
            },
            {
                'username': 'mike_wilson',
                'email': 'mike.wilson@example.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'library_id': 'LIB003',
                'phone': '(555) 345-6789',
            },
            {
                'username': 'sarah_jones',
                'email': 'sarah.jones@example.com',
                'first_name': 'Sarah',
                'last_name': 'Jones',
                'library_id': 'LIB004',
                'phone': '(555) 456-7890',
            },
        ]

        borrowers = {}
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            if created:
                user.set_password('password123')  # Default password
                user.save()

            borrower, created = Borrower.objects.get_or_create(
                user=user,
                defaults={
                    'library_id': user_data['library_id'],
                    'phone': user_data['phone'],
                    'is_active': True,
                }
            )
            borrowers[user_data['username']] = borrower
            if created:
                self.stdout.write(f'Created borrower: {borrower.full_name}')

        # Create some sample borrowings
        borrowings_data = [
            {
                'borrower': 'john_doe',
                'book': 'To Kill a Mockingbird',
                'days_ago': 5,
                'due_days': 9,
            },
            {
                'borrower': 'jane_smith',
                'book': '1984',
                'days_ago': 10,
                'due_days': 4,
            },
            {
                'borrower': 'mike_wilson',
                'book': 'The Great Gatsby',
                'days_ago': 15,
                'due_days': -1,  # Overdue
            },
            {
                'borrower': 'sarah_jones',
                'book': 'Harry Potter and the Philosopher\'s Stone',
                'days_ago': 3,
                'due_days': 11,
            },
        ]

        for borrowing_data in borrowings_data:
            borrower = borrowers[borrowing_data['borrower']]
            book = books[borrowing_data['book']]
            
            # Update book availability
            book.available_copies -= 1
            book.save()

            borrow_date = timezone.now() - timedelta(days=borrowing_data['days_ago'])
            due_date = borrow_date + timedelta(days=14)
            
            borrowing, created = Borrowing.objects.get_or_create(
                borrower=borrower,
                book=book,
                borrow_date__date=borrow_date.date(),
                defaults={
                    'borrow_date': borrow_date,
                    'due_date': due_date,
                    'status': 'borrowed',
                }
            )
            
            if created:
                self.stdout.write(f'Created borrowing: {borrower.full_name} - {book.title}')

        # Create some fines for overdue books
        overdue_borrowings = Borrowing.objects.filter(
            return_date__isnull=True,
            due_date__lt=timezone.now()
        )
        
        for borrowing in overdue_borrowings:
            fine, created = Fine.objects.get_or_create(
                borrowing=borrowing,
                defaults={
                    'amount': borrowing.fine_amount,
                    'status': 'pending',
                }
            )
            if created:
                self.stdout.write(f'Created fine: ${fine.amount} for {borrowing.borrower.full_name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
        self.stdout.write('Sample login credentials:')
        self.stdout.write('Username: john_doe, Password: password123')
        self.stdout.write('Username: jane_smith, Password: password123')
        self.stdout.write('Username: mike_wilson, Password: password123')
        self.stdout.write('Username: sarah_jones, Password: password123')
