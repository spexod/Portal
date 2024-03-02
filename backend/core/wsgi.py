"""
WSGI config for the project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/
"""

import os
import sys
sys.path.append('/home/ubuntu/SpExServer/backend')
os.environ.setdefault("PYTHON_EGG_CACHE", "/home/ubuntu/SpExServer/backend/egg_cache")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
