#!/usr/bin/env python
"""
Run the Django development server with ASGI support for WebSocket connections.
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ultrasound_clinic.settings')
django.setup()

# Import and run the ASGI application
from ultrasound_clinic.asgi import application

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="127.0.0.1", port=8000, log_level="info")
