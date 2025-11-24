"""
WSGI config for readify project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'readify.settings')

application = get_wsgi_application()
