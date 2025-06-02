import random
import string
from django.contrib.auth.models import User

def generate_username(first_name, last_name):
    """Generate a unique username based on patient's name."""
    base_username = f"{first_name.lower()}{last_name.lower()}"
    username = base_username
    counter = 1
    
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def generate_password():
    """Generate a secure random password."""
    # Define character sets
    letters = string.ascii_letters
    digits = string.digits
    special_chars = "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        random.choice(letters.upper()),
        random.choice(letters.lower()),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill rest with random characters
    for _ in range(8):  # Add 8 more characters
        password.append(random.choice(letters + digits + special_chars))
    
    # Shuffle the password characters
    random.shuffle(password)
    
    return ''.join(password) 