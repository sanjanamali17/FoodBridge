import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
import os

def format_date(date_string: str) -> str:
    """Format date string for display."""
    try:
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return date_obj.strftime("%B %d, %Y")
    except:
        try:
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            return date_obj.strftime("%B %d, %Y")
        except:
            return date_string

def days_until_expiry(expiry_date: str) -> int:
    """Calculate days until expiry."""
    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        today = datetime.date.today()
        return (expiry - datetime.now().date()).days
    except:
        return 0

def get_quality_color(quality: str) -> str:
    """Get color code for quality status."""
    colors = {
        "Fresh": "#2E8B57",
        "Expires Soon": "#FF8C00",
        "Expires Today": "#FF6347",
        "Expired": "#DC143C",
        "Unknown": "#808080"
    }
    return colors.get(quality, "#808080")

def get_status_emoji(status: str) -> str:
    """Get emoji for donation status."""
    emojis = {
        "Available": "✅",
        "Requested": "📋",
        "Picked Up": "🚚",
        "Expired": "❌"
    }
    return emojis.get(status, "❓")

def create_donation_chart(donations_data):
    """Create donation statistics chart."""
    if not donations_data:
        return None
    
    df = pd.DataFrame(donations_data)
    
    # Quality distribution pie chart
    quality_counts = df['quality_prediction'].value_counts()
    
    fig = px.pie(
        values=quality_counts.values,
        names=quality_counts.index,
        title="Food Quality Distribution",
        color_discrete_map={
            "Fresh": "#2E8B57",
            "Expires Soon": "#FF8C00",
            "Expires Today": "#FF6347",
            "Expired": "#DC143C"
        }
    )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        font=dict(size=12)
    )
    
    return fig

def create_donations_timeline(donations_data):
    """Create timeline chart of donations."""
    if not donations_data:
        return None
    
    df = pd.DataFrame(donations_data)
    df['date'] = pd.to_datetime(df['created_at']).dt.date
    
    # Group by date and quality
    timeline_data = df.groupby(['date', 'quality_prediction']).size().unstack(fill_value=0)
    
    fig = go.Figure()
    
    colors = {
        "Fresh": "#2E8B57",
        "Expires Soon": "#FF8C00", 
        "Expires Today": "#FF6347",
        "Expired": "#DC143C"
    }
    
    for quality in timeline_data.columns:
        fig.add_trace(go.Scatter(
            x=timeline_data.index,
            y=timeline_data[quality],
            mode='lines+markers',
            name=quality,
            line=dict(color=colors.get(quality, "#808080")),
            stackgroup='one'
        ))
    
    fig.update_layout(
        title="Donations Over Time",
        xaxis_title="Date",
        yaxis_title="Number of Donations",
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_quantity_chart(donations_data):
    """Create quantity analysis chart."""
    if not donations_data:
        return None
    
    df = pd.DataFrame(donations_data)
    
    # Group donations by food type and sum quantities
    food_quantities = df.groupby('food_name')['quantity'].sum().sort_values(ascending=False).head(10)
    
    fig = px.bar(
        x=food_quantities.index,
        y=food_quantities.values,
        title="Top 10 Donated Food Items by Quantity",
        labels={'x': 'Food Items', 'y': 'Total Quantity'}
    )
    
    fig.update_layout(
        height=400,
        xaxis_tickangle=-45
    )
    
    return fig

def create_ngo_activity_chart(requests_data):
    """Create NGO activity chart."""
    if not requests_data:
        return None
    
    df = pd.DataFrame(requests_data)
    
    # Count requests by NGO
    ngo_requests = df.groupby('ngo_name').size().sort_values(ascending=False).head(10)
    
    fig = px.bar(
        x=ngo_requests.values,
        y=ngo_requests.index,
        orientation='h',
        title="Most Active NGOs",
        labels={'x': 'Number of Requests', 'y': 'NGO Name'}
    )
    
    fig.update_layout(height=400)
    
    return fig

def display_donation_card(donation, show_request_button=False):
    """Display a donation as a card."""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {donation['food_name']}")
            st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
            if donation.get('description'):
                st.write(f"**Description:** {donation['description']}")
        
        with col2:
            quality_color = get_quality_color(donation['quality_prediction'])
            st.markdown(f"**Quality:** <span style='color: {quality_color}'>{donation['quality_prediction']}</span>", 
                       unsafe_allow_html=True)
            
            expiry_days = days_until_expiry(donation['expiry_date'])
            if expiry_days >= 0:
                st.write(f"**Expires in:** {expiry_days} days")
            else:
                st.write(f"**Expired:** {abs(expiry_days)} days ago")
            
            st.write(f"**Donated by:** {donation.get('donor_name', 'Anonymous')}")
        
        with col3:
            status_emoji = get_status_emoji(donation['status'])
            st.write(f"**Status:** {status_emoji} {donation['status']}")
            
            if show_request_button and donation['status'] == 'Available':
                if st.button(f"Request Pickup", key=f"request_{donation['id']}"):
                    return donation['id']
    
    st.markdown("---")
    return None

def save_uploaded_image(uploaded_file, folder="uploads"):
    """Save uploaded image and return path."""
    if uploaded_file is None:
        return None
    
    # Create uploads directory if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    filepath = os.path.join(folder, filename)
    
    # Save the file
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def image_to_base64(image_path):
    """Convert image to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except:
        return None

def display_image_preview(image_path, width=200):
    """Display image preview."""
    if image_path and os.path.exists(image_path):
        try:
            image = Image.open(image_path)
            st.image(image, width=width, caption="Food Image")
        except:
            st.write("🖼️ Image preview unavailable")
    else:
        st.write("📷 No image uploaded")

def calculate_impact_metrics(donations_data):
    """Calculate impact metrics from donations."""
    if not donations_data:
        return {
            "total_donations": 0,
            "food_saved_kg": 0,
            "meals_provided": 0,
            "co2_saved": 0
        }
    
    total_donations = len(donations_data)
    
    # Estimate food saved in kg (rough conversion)
    food_saved = sum(donation.get('quantity', 0) for donation in donations_data)
    
    # Estimate meals (assuming 0.5kg per meal)
    meals_provided = int(food_saved * 2)
    
    # Estimate CO2 saved (approximate 2.5kg CO2 per kg of food waste avoided)
    co2_saved = round(food_saved * 2.5, 1)
    
    return {
        "total_donations": total_donations,
        "food_saved_kg": food_saved,
        "meals_provided": meals_provided,
        "co2_saved": co2_saved
    }

def export_data_to_csv(data, filename):
    """Export data to CSV for download."""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    # Convert to CSV
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    return csv_buffer.getvalue()

def show_success_message(message, duration=3):
    """Show success message with auto-hide."""
    success_placeholder = st.empty()
    success_placeholder.success(message)
    
    # Note: Auto-hide functionality would require JavaScript
    # For now, just display the message

def show_error_message(message):
    """Show error message."""
    st.error(message)

def show_info_message(message):
    """Show info message."""
    st.info(message)

def validate_email(email):
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[-1]

def validate_phone(phone):
    """Basic phone validation."""
    return phone.replace("-", "").replace(" ", "").isdigit()

def get_food_categories():
    """Get list of food categories for classification."""
    return [
        "Grains & Cereals",
        "Fruits & Vegetables", 
        "Dairy Products",
        "Meat & Poultry",
        "Seafood",
        "Bakery Items",
        "Canned Goods",
        "Beverages",
        "Snacks & Confectionery",
        "Other"
    ]

def get_units_list():
    """Get list of measurement units."""
    return [
        "kg", "grams", "pounds",
        "liters", "ml", "gallons",
        "pieces", "packets", "boxes",
        "cans", "bottles", "bags"
    ]

def format_large_number(number):
    """Format large numbers for display."""
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    else:
        return str(number)

def get_time_ago(date_string):
    """Get human-readable time ago string."""
    try:
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    except:
        return date_string
