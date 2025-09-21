import streamlit as st
import sqlite3
from auth import initialize_auth, login_user, register_user, logout_user
from db import init_database
import os
from ai_features import predict_food_quality

image_input = ... # get from Streamlit file uploader
quality = predict_food_quality(image_input)

# Initialize database
init_database()

# Configure page
st.set_page_config(
    page_title="FoodBridge - AI-Powered Food Donation Platform",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize authentication
initialize_auth()

def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #2E8B57;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 3rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Check if user is logged in
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # Sidebar navigation
    with st.sidebar:
        st.title("🍽️ FoodBridge")
        
        if st.session_state.logged_in:
            st.success(f"Welcome, {st.session_state.user_name}!")
            st.write(f"Role: {st.session_state.user_role}")
            
            # Navigation menu
            if st.session_state.user_role == "Admin":
                pages = {
                    "🏠 Home": "home",
                    "🍲 Donate Food": "donate",
                    "📊 Dashboard": "dashboard", 
                    "⚙️ Admin Panel": "admin",
                    "🤖 Chatbot": "chatbot"
                }
            elif st.session_state.user_role == "NGO":
                pages = {
                    "🏠 Home": "home",
                    "📊 Dashboard": "dashboard",
                    "🤖 Chatbot": "chatbot"
                }
            else:  # Donor
                pages = {
                    "🏠 Home": "home",
                    "🍲 Donate Food": "donate",
                    "🤖 Chatbot": "chatbot"
                }
            
            selected_page = st.selectbox("Navigate to:", list(pages.keys()))
            st.session_state.current_page = pages[selected_page]
            
            if st.button("🚪 Logout"):
                logout_user()
                st.rerun()
        else:
            st.write("Please login to continue")
            auth_choice = st.selectbox("Choose Action:", ["Login", "Register"])
            
            if auth_choice == "Login":
                show_login_form()
            else:
                show_register_form()

    # Main content area
    if st.session_state.logged_in:
        if st.session_state.get('current_page', 'home') == 'home':
            show_home_page()
        elif st.session_state.current_page == 'donate':
            show_donate_page()
        elif st.session_state.current_page == 'dashboard':
            show_dashboard_page()
        elif st.session_state.current_page == 'admin':
            show_admin_page()
        elif st.session_state.current_page == 'chatbot':
            show_chatbot_page()
    else:
        show_landing_page()

def show_landing_page():
    st.markdown('<div class="main-header">🍽️ FoodBridge</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Food Donation Platform</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 For Donors")
        st.write("- Easy food donation process")
        st.write("- AI-powered quality assessment")
        st.write("- Track donation impact")
        
    with col2:
        st.markdown("### 🏢 For NGOs")
        st.write("- Access fresh food donations")
        st.write("- Request pickup services")
        st.write("- Manage beneficiaries")
        
    with col3:
        st.markdown("### 🤖 AI Features")
        st.write("- Smart quality prediction")
        st.write("- Intelligent NGO matching")
        st.write("- Donation insights")

def show_login_form():
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if login_user(email, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials!")

def show_register_form():
    st.subheader("Register")
    with st.form("register_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Donor", "NGO", "Admin"])
        organization = st.text_input("Organization (if applicable)")
        
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if register_user(name, email, password, role, organization):
                st.success("Registration successful! Please login.")
            else:
                st.error("Registration failed. Email might already exist.")

def show_home_page():
    st.title("🏠 Welcome to FoodBridge Dashboard")
    
    # Quick stats
    from db import get_user_stats
    stats = get_user_stats(st.session_state.user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Donations", stats.get('donations', 0))
    with col2:
        st.metric("Food Saved (kg)", stats.get('food_saved', 0))
    with col3:
        st.metric("NGOs Helped", stats.get('ngos_helped', 0))
    with col4:
        st.metric("Fresh Donations", stats.get('fresh_donations', 0))
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("Recent Activity")
    from db import get_recent_donations
    recent_donations = get_recent_donations(limit=5)
    
    if recent_donations:
        for donation in recent_donations:
            with st.expander(f"{donation['food_name']} - {donation['created_at'][:10]}"):
                st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
                st.write(f"**Quality:** {donation['quality_prediction']}")
                st.write(f"**Status:** {donation['status']}")
    else:
        st.info("No recent donations found.")

def show_donate_page():
    # Import and run donate page
    import sys
    sys.path.append('pages')
    from pages.donate import show_donate_page as donate_page
    donate_page()

def show_dashboard_page():
    # Import and run dashboard page
    import sys
    sys.path.append('pages')
    from pages.dashboard import show_dashboard_page as dashboard_page
    dashboard_page()

def show_admin_page():
    # Import and run admin page
    import sys
    sys.path.append('pages')
    from pages.admin import show_admin_page as admin_page
    admin_page()

def show_chatbot_page():
    # Import and run chatbot page
    import sys
    sys.path.append('pages')
    from pages.chatbot import show_chatbot_page as chatbot_page
    chatbot_page()

if __name__ == "__main__":
    main()
