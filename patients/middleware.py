from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
import re
import logging

class NavigationControlMiddleware(MiddlewareMixin):
    """
    Middleware to control navigation and redirect invalid attempts to forbidden page.
    This helps prevent users from typing URLs directly or using browser back button inappropriately.
    Also restricts non-staff users to only landing, login, and patient portal pages.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Skip middleware for certain paths
        skip_paths = [
            '/forbidden/',
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
        ]
        
        # Check if current path should be skipped
        for skip_path in skip_paths:
            if request.path.startswith(skip_path):
                return None
        
        # Handle root path redirects first (before other access control)
        # Note: The landing page is mapped to root path '/', so we don't redirect here
        # The root path is handled by the LandingView directly
        
        # Access control for non-staff users
        if hasattr(request, 'user') and request.user.is_authenticated:
            # If user is authenticated but not staff, restrict access
            if not request.user.is_staff:
                # Allowed paths for non-staff users (patients)
                allowed_paths = [
                    '/patient-portal/',
                    '/patient-login/',
                    '/patient-logout/',
                    '/patient-exam/',
                    '/patient-settings/',
                    '/patient-appointments/',
                    '/patient-bills/',
                    '/',  # root path (landing page)
                ]
                
                # Check if current path is allowed for non-staff users
                path_allowed = False
                for allowed_path in allowed_paths:
                    if request.path.startswith(allowed_path):
                        path_allowed = True
                        break
                
                # If path is not allowed for non-staff users, redirect to patient portal
                if not path_allowed:
                    return redirect('patient-portal')
        
        # If user is not authenticated, only allow landing and login pages
        elif not request.user.is_authenticated:
            allowed_unauthenticated_paths = [
                '/',  # root path (landing page)
                '/staff-login/',
                '/patient-login/',
                '/static/',
                '/media/',
            ]
            
            path_allowed = False
            for allowed_path in allowed_unauthenticated_paths:
                if request.path.startswith(allowed_path):
                    path_allowed = True
                    break
            
            # If path is not allowed for unauthenticated users, redirect to landing
            if not path_allowed:
                return redirect('landing')
        
        # Check for direct URL access patterns that should be forbidden
        forbidden_patterns = [
            # Direct access to form pages without proper flow
            r'^/patient/\d+/update/$',
            r'^/patient/\d+/delete/$',
            r'^/patient/\d+/exam/new/$',
            r'^/exam/\d+/update/$',
            r'^/patient/\d+/annotate/$',
            r'^/image/\d+/annotate/$',
            r'^/patient/\d+/upload-image/$',
            r'^/ultrasound-image/\d+/delete/$',
            r'^/patient-appointments/\d+/update/$',
            r'^/patient-appointments/\d+/cancel/$',
            r'^/staff/appointments/\d+/',
            r'^/custom-admin/users/\d+/edit/$',
            r'^/custom-admin/users/\d+/change-password/$',
        ]
        
        # Check if current path matches forbidden patterns
        for pattern in forbidden_patterns:
            if re.match(pattern, request.path):
                # Check if this is a POST request (form submission) - allow it
                if request.method == 'POST':
                    continue
                
                # Check if user has proper referrer (came from a valid page)
                referer = request.META.get('HTTP_REFERER', '')
                if not referer:
                    # No referrer means direct URL access - redirect to forbidden
                    return redirect('forbidden')
                
                # Check if referrer is from the same domain and a valid page
                from django.conf import settings
                if not referer.startswith(request.build_absolute_uri('/')):
                    # External referrer - redirect to forbidden
                    return redirect('forbidden')
                
                # Check if referrer is from a valid page in the application
                valid_referrer_patterns = [
                    r'/patients/',
                    r'/patient/\d+/',
                    r'/exam/\d+/',
                    r'/custom-admin/',
                    r'/patient-portal/',
                    r'/patient-appointments/',
                    r'/staff/appointments/',
                ]
                
                valid_referrer = False
                for ref_pattern in valid_referrer_patterns:
                    if re.search(ref_pattern, referer):
                        valid_referrer = True
                        break
                
                if not valid_referrer:
                    # Invalid referrer - redirect to forbidden
                    return redirect('forbidden')
        
        return None
    
    def process_response(self, request, response):
        # Add headers to prevent caching of sensitive pages
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Add no-cache headers for authenticated users on sensitive pages
            sensitive_paths = [
                '/patient/',
                '/exam/',
                '/custom-admin/',
                '/patient-portal/',
                '/patient-appointments/',
            ]
            
            for path in sensitive_paths:
                if request.path.startswith(path):
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                    break
        
        return response


class PrivilegeElevationMiddleware(MiddlewareMixin):
    """
    Middleware to handle temporary privilege elevation for staff users.
    Uses session flag to temporarily grant admin permissions without changing the authenticated user.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        self.logger = logging.getLogger(__name__)

    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check for elevation flag
            if request.session.get('elevated_admin', False) and request.user.is_staff:
                # Temporarily elevate permissions for the current request
                # This is for display purposes in templates, the actual user object isn't changed
                request.user.is_superuser = True
                # No need to change is_staff, as superusers are implicitly staff
                self.logger.debug(f"User {request.user.username} temporarily elevated to superuser privileges by middleware.")
            # No 'else' block needed here to revert, as the views handle re-logging the original user
            # and the request.user object will be fresh on subsequent requests after a re-login.

        return None

    def process_response(self, request, response):
        return response
