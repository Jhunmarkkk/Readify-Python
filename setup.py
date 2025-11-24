#!/usr/bin/env python
"""
Setup script for Readify Library Management System
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Readify Library Management System")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('backend/manage.py'):
        print("✗ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Change to backend directory
    os.chdir('backend')
    
    # Install dependencies
    if not run_command('pip install -r requirements.txt', 'Installing dependencies'):
        print("✗ Failed to install dependencies. Please check your Python environment.")
        sys.exit(1)
    
    # Run migrations
    if not run_command('python manage.py makemigrations', 'Creating database migrations'):
        print("✗ Failed to create migrations")
        sys.exit(1)
    
    if not run_command('python manage.py migrate', 'Applying database migrations'):
        print("✗ Failed to apply migrations")
        sys.exit(1)
    
    # Create superuser
    print("\n📝 Creating superuser account...")
    print("Please enter the following information for your admin account:")
    
    # Try to create superuser non-interactively first
    create_superuser_cmd = """
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created successfully!')
else:
    print('Superuser already exists!')
EOF
"""
    
    if run_command(create_superuser_cmd, 'Creating superuser'):
        print("✓ Superuser created: username='admin', password='admin123'")
    else:
        print("⚠️  Could not create superuser automatically. Please create it manually:")
        print("   python manage.py createsuperuser")
    
    # Populate sample data
    print("\n📚 Populating sample data...")
    if run_command('python manage.py populate_sample_data', 'Loading sample data'):
        print("✓ Sample data loaded successfully")
    else:
        print("⚠️  Could not load sample data. You can do it manually later:")
        print("   python manage.py populate_sample_data")
    
    # Collect static files
    if not run_command('python manage.py collectstatic --noinput', 'Collecting static files'):
        print("⚠️  Failed to collect static files. This might cause issues in production.")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start the development server:")
    print("   cd backend")
    print("   python manage.py runserver")
    print("\n2. Open your browser and go to:")
    print("   http://127.0.0.1:8000")
    print("\n3. Login with admin account:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n4. Or login with sample borrower accounts:")
    print("   Username: john_doe, Password: password123")
    print("   Username: jane_smith, Password: password123")
    print("   Username: mike_wilson, Password: password123")
    print("   Username: sarah_jones, Password: password123")
    print("\n📖 For more information, check the README.md file")
    print("=" * 50)

if __name__ == '__main__':
    main()
