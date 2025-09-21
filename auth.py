import streamlit as st
from db import authenticate_user, create_user
import hashlib

def initialize_auth():
    """Initialize authentication session state."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_organization' not in st.session_state:
        st.session_state.user_organization = None

def login_user(email: str, password: str) -> bool:
    """Login a user with email and password."""
    user_data = authenticate_user(email, password)
    
    if user_data:
        st.session_state.logged_in = True
        st.session_state.user_id = user_data['id']
        st.session_state.user_name = user_data['name']
        st.session_state.user_role = user_data['role']
        st.session_state.user_organization = user_data['organization']
        st.session_state.current_page = 'home'
        return True
    
    return False

def register_user(name: str, email: str, password: str, role: str, organization: str = "") -> bool:
    """Register a new user."""
    if not name or not email or not password or not role:
        return False
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        return False
    
    # Password strength check
    if len(password) < 6:
        return False
    
    return create_user(name, email, password, role, organization)

def logout_user():
    """Logout the current user."""
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.session_state.user_role = None
    st.session_state.user_organization = None
    st.session_state.current_page = 'home'

def require_auth(allowed_roles=None):
    """Decorator to require authentication for a page."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get('logged_in', False):
                st.error("Please login to access this page.")
                return
            
            if allowed_roles and st.session_state.user_role not in allowed_roles:
                st.error("You don't have permission to access this page.")
                return
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    """Get current user information."""
    if st.session_state.get('logged_in', False):
        return {
            'id': st.session_state.user_id,
            'name': st.session_state.user_name,
            'role': st.session_state.user_role,
            'organization': st.session_state.user_organization
        }
    return None

def is_admin():
    """Check if current user is admin."""
    return st.session_state.get('user_role') == 'Admin'

def is_ngo():
    """Check if current user is NGO."""
    return st.session_state.get('user_role') == 'NGO'

def is_donor():
    """Check if current user is donor."""
    return st.session_state.get('user_role') == 'Donor'
