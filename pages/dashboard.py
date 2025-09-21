import streamlit as st
from db import get_available_donations, create_donation_request, get_ngo_requests
from utils import display_donation_card, create_donation_chart, calculate_impact_metrics, show_success_message, show_error_message
from ai_features import generate_donation_summary
from notifications import display_notification_badge, display_notifications_panel

def show_dashboard_page():
    """Display the NGO dashboard page."""
    st.title("📊 NGO Dashboard")
    
    # Check if user is logged in and is NGO or admin
    if not st.session_state.get('logged_in', False):
        st.error("Please login to access the dashboard.")
        return
    
    if st.session_state.user_role not in ['NGO', 'Admin']:
        st.error("Only NGOs and Admins can access this dashboard.")
        return
    
    # Show notification badge in sidebar for NGOs
    if st.session_state.user_role == 'NGO':
        display_notification_badge(st.session_state.user_id)
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Available Donations", "📨 My Requests", "📈 Analytics", "🎯 Impact", "🔔 Notifications"])
    
    with tab1:
        show_available_donations_tab()
    
    with tab2:
        show_my_requests_tab()
    
    with tab3:
        show_analytics_tab()
    
    with tab4:
        show_impact_tab()
    
    with tab5:
        show_notifications_tab()

def show_available_donations_tab():
    """Display available donations tab."""
    st.header("🍽️ Fresh Food Donations Available")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        quality_filter = st.selectbox(
            "Filter by Quality:",
            ["All", "Fresh", "Expires Soon", "Expires Today"]
        )
    
    with col2:
        quantity_filter = st.selectbox(
            "Filter by Quantity:",
            ["All", "Small (1-10)", "Medium (11-50)", "Large (50+)"]
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by:",
            ["Newest First", "Expiry Date", "Quantity"]
        )
    
    # Get available donations
    available_donations = get_available_donations()
    
    if not available_donations:
        st.info("🍽️ No fresh donations available at the moment. Please check back later!")
        return
    
    # Apply filters
    filtered_donations = apply_donation_filters(
        available_donations, quality_filter, quantity_filter, sort_by
    )
    
    if not filtered_donations:
        st.warning("No donations match your current filters.")
        return
    
    st.write(f"Showing {len(filtered_donations)} donations")
    
    # Display donations
    for donation in filtered_donations:
        with st.container():
            # Enhanced donation card
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"### 🍲 {donation['food_name']}")
                st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
                
                if donation.get('description'):
                    with st.expander("📝 Description"):
                        st.write(donation['description'])
            
            with col2:
                # Quality with color coding
                quality = donation['quality_prediction']
                quality_colors = {
                    "Fresh": "🟢",
                    "Expires Soon": "🟡", 
                    "Expires Today": "🟠",
                    "Expired": "🔴"
                }
                st.write(f"**Quality:** {quality_colors.get(quality, '⚪')} {quality}")
                
                # Days until expiry
                from utils import days_until_expiry
                days_left = days_until_expiry(donation['expiry_date'])
                if days_left >= 0:
                    st.write(f"**Expires in:** {days_left} days")
                else:
                    st.write(f"**Expired:** {abs(days_left)} days ago")
            
            with col3:
                st.write(f"**Donor:** {donation.get('donor_name', 'Anonymous')}")
                st.write(f"**Posted:** {donation['created_at'][:10]}")
                
                # Generate AI summary
                if st.button(f"✨ AI Summary", key=f"summary_{donation['id']}"):
                    with st.spinner("Generating summary..."):
                        try:
                            summary = generate_donation_summary(donation)
                            st.info(f"**AI Summary:** {summary}")
                        except:
                            st.warning("Could not generate summary")
            
            with col4:
                # Request pickup button
                if st.button(f"📞 Request Pickup", key=f"request_{donation['id']}", type="primary"):
                    request_pickup_modal(donation)
        
        st.markdown("---")

def request_pickup_modal(donation):
    """Show pickup request modal."""
    st.markdown(f"### 📞 Request Pickup: {donation['food_name']}")
    
    with st.form(f"request_form_{donation['id']}"):
        st.write("**Donation Details:**")
        st.write(f"- Food: {donation['food_name']}")
        st.write(f"- Quantity: {donation['quantity']} {donation['unit']}")
        st.write(f"- Quality: {donation['quality_prediction']}")
        st.write(f"- Expires: {donation['expiry_date']}")
        
        # Request details
        pickup_time = st.selectbox(
            "Preferred Pickup Time:",
            ["As soon as possible", "Within 2 hours", "Within 4 hours", "Within 8 hours", "Next day"]
        )
        
        transport_available = st.checkbox("We have our own transportation")
        
        notes = st.text_area(
            "Additional Notes (Optional):",
            placeholder="Any special requirements, contact information, or additional details..."
        )
        
        # Contact information
        st.subheader("📞 Contact Information")
        contact_person = st.text_input("Contact Person*", value=st.session_state.user_name)
        contact_phone = st.text_input("Phone Number*", placeholder="+1-234-567-8900")
        
        submitted = st.form_submit_button("🚀 Send Request", type="primary")
        
        if submitted:
            if not contact_person or not contact_phone:
                show_error_message("Please provide contact information")
                return
            
            # Prepare request notes
            full_notes = f"Pickup Time: {pickup_time}\n"
            full_notes += f"Transport: {'Available' if transport_available else 'Needed'}\n"
            full_notes += f"Contact: {contact_person} ({contact_phone})\n"
            if notes:
                full_notes += f"Notes: {notes}"
            
            try:
                request_id = create_donation_request(
                    donation_id=donation['id'],
                    ngo_id=st.session_state.user_id,
                    notes=full_notes
                )
                
                show_success_message(f"✅ Pickup request sent successfully! Request ID: {request_id}")
                st.rerun()
                
            except Exception as e:
                show_error_message(f"Failed to send request: {e}")

def show_my_requests_tab():
    """Display NGO's donation requests."""
    st.header("📨 My Pickup Requests")
    
    # Get NGO requests
    ngo_requests = get_ngo_requests(st.session_state.user_id)
    
    if not ngo_requests:
        st.info("🗂️ You haven't made any pickup requests yet.")
        return
    
    # Filter by status
    status_filter = st.selectbox(
        "Filter by Status:",
        ["All", "Pending", "Approved", "Rejected", "Completed"]
    )
    
    # Apply filter
    if status_filter != "All":
        filtered_requests = [req for req in ngo_requests if req['status'] == status_filter]
    else:
        filtered_requests = ngo_requests
    
    st.write(f"Showing {len(filtered_requests)} requests")
    
    # Display requests
    for request in filtered_requests:
        with st.expander(f"{request['food_name']} - {request['status']} ({request['requested_at'][:10]})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Food Item:** {request['food_name']}")
                st.write(f"**Quantity:** {request['quantity']} {request['unit']}")
                st.write(f"**Donor:** {request['donor_name']}")
                st.write(f"**Expiry Date:** {request['expiry_date']}")
            
            with col2:
                # Status with color coding
                status_colors = {
                    "Pending": "🟡",
                    "Approved": "🟢",
                    "Rejected": "🔴",
                    "Completed": "✅"
                }
                status_icon = status_colors.get(request['status'], '⚪')
                st.write(f"**Status:** {status_icon} {request['status']}")
                st.write(f"**Requested:** {request['requested_at'][:16]}")
            
            if request.get('notes'):
                st.markdown("**Request Notes:**")
                st.info(request['notes'])
            
            # Action buttons based on status
            if request['status'] == 'Approved':
                if st.button(f"✅ Mark as Completed", key=f"complete_{request['id']}"):
                    # Update request status to completed
                    st.success("Request marked as completed!")
                    st.rerun()
            
            elif request['status'] == 'Pending':
                st.info("⏳ Waiting for donor response...")

def show_analytics_tab():
    """Display analytics and charts."""
    st.header("📈 Donation Analytics")
    
    # Get data for charts
    available_donations = get_available_donations(limit=100)
    
    if not available_donations:
        st.info("No data available for analytics.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_available = len(available_donations)
    fresh_count = len([d for d in available_donations if d['quality_prediction'] == 'Fresh'])
    total_quantity = sum(d.get('quantity', 0) for d in available_donations)
    avg_quantity = total_quantity / total_available if total_available > 0 else 0
    
    with col1:
        st.metric("Total Available", total_available)
    with col2:
        st.metric("Fresh Items", fresh_count)
    with col3:
        st.metric("Total Quantity", f"{total_quantity:,} units")
    with col4:
        st.metric("Avg. Quantity", f"{avg_quantity:.1f} units")
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Quality distribution chart
        from utils import create_donation_chart
        quality_chart = create_donation_chart(available_donations)
        if quality_chart:
            st.plotly_chart(quality_chart, use_container_width=True)
    
    with col_chart2:
        # Quantity analysis chart
        from utils import create_quantity_chart
        quantity_chart = create_quantity_chart(available_donations)
        if quantity_chart:
            st.plotly_chart(quantity_chart, use_container_width=True)
    
    # Timeline chart
    from utils import create_donations_timeline
    timeline_chart = create_donations_timeline(available_donations)
    if timeline_chart:
        st.plotly_chart(timeline_chart, use_container_width=True)
    
    # Food categories analysis
    st.subheader("📊 Food Categories Analysis")
    
    import pandas as pd
    df = pd.DataFrame(available_donations)
    
    # Most common food types
    food_counts = df['food_name'].value_counts().head(10)
    
    col_table1, col_table2 = st.columns(2)
    
    with col_table1:
        st.markdown("**Top Food Items:**")
        for food, count in food_counts.items():
            st.write(f"• {food}: {count} donations")
    
    with col_table2:
        # Expiry analysis
        st.markdown("**Expiry Distribution:**")
        from utils import days_until_expiry
        
        expiry_ranges = {
            "Expires today": 0,
            "1-2 days": 0,
            "3-7 days": 0,
            "1+ weeks": 0
        }
        
        for donation in available_donations:
            days_left = days_until_expiry(donation['expiry_date'])
            if days_left == 0:
                expiry_ranges["Expires today"] += 1
            elif days_left <= 2:
                expiry_ranges["1-2 days"] += 1
            elif days_left <= 7:
                expiry_ranges["3-7 days"] += 1
            else:
                expiry_ranges["1+ weeks"] += 1
        
        for range_name, count in expiry_ranges.items():
            st.write(f"• {range_name}: {count} items")

def show_impact_tab():
    """Display impact metrics and achievements."""
    st.header("🎯 Impact Dashboard")
    
    # Get user's impact data
    from db import get_ngo_requests
    ngo_requests = get_ngo_requests(st.session_state.user_id)
    
    # Calculate impact metrics
    completed_requests = [req for req in ngo_requests if req['status'] == 'Completed']
    
    # Impact metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_requests = len(ngo_requests)
    completed_count = len(completed_requests)
    success_rate = (completed_count / total_requests * 100) if total_requests > 0 else 0
    
    # Calculate food rescued
    food_rescued = sum(req.get('quantity', 0) for req in completed_requests)
    estimated_meals = food_rescued * 2  # Rough estimate: 0.5kg per meal
    
    with col1:
        st.metric("Total Requests", total_requests)
    with col2:
        st.metric("Completed", completed_count)
    with col3:
        st.metric("Success Rate", f"{success_rate:.1f}%")
    with col4:
        st.metric("Food Rescued", f"{food_rescued} units")
    
    # Environmental impact
    st.markdown("### 🌱 Environmental Impact")
    
    co2_saved = food_rescued * 2.5  # kg CO2 per kg food
    water_saved = food_rescued * 250  # liters per kg food
    
    env_col1, env_col2, env_col3 = st.columns(3)
    
    with env_col1:
        st.metric("CO₂ Saved", f"{co2_saved:.1f} kg")
    with env_col2:
        st.metric("Water Saved", f"{water_saved:,.0f} L")
    with env_col3:
        st.metric("Meals Provided", f"{estimated_meals:,}")
    
    # Achievement badges
    st.markdown("### 🏆 Achievements")
    
    achievements = []
    
    if completed_count >= 1:
        achievements.append("🥉 First Rescue - Completed your first pickup")
    if completed_count >= 10:
        achievements.append("🥈 Regular Hero - 10 successful pickups")
    if completed_count >= 50:
        achievements.append("🥇 Food Champion - 50 successful pickups")
    if success_rate >= 80:
        achievements.append("⭐ Reliable Partner - 80%+ success rate")
    if food_rescued >= 100:
        achievements.append("📦 Big Impact - Rescued 100+ units of food")
    
    if achievements:
        for achievement in achievements:
            st.success(achievement)
    else:
        st.info("Complete your first pickup to start earning achievements! 🌟")
    
    # Monthly progress chart
    if completed_requests:
        st.markdown("### 📅 Monthly Progress")
        
        import pandas as pd
        from datetime import datetime
        
        # Group completed requests by month
        monthly_data = {}
        for req in completed_requests:
            month = req['requested_at'][:7]  # YYYY-MM format
            monthly_data[month] = monthly_data.get(month, 0) + 1
        
        if monthly_data:
            months = list(monthly_data.keys())
            counts = list(monthly_data.values())
            
            import plotly.express as px
            fig = px.bar(x=months, y=counts, title="Monthly Completed Requests")
            fig.update_layout(xaxis_title="Month", yaxis_title="Completed Requests")
            st.plotly_chart(fig, use_container_width=True)
    
    # Tips for improvement
    st.markdown("### 💡 Tips to Increase Impact")
    
    if success_rate < 70:
        st.info("💡 Improve your success rate by responding quickly to approved requests and maintaining good communication with donors.")
    
    if total_requests < 5:
        st.info("💡 Make more requests to increase your impact! Check the Available Donations tab regularly.")
    
    st.info("💡 Update your NGO profile with capacity and location information to get better matches.")

def apply_donation_filters(donations, quality_filter, quantity_filter, sort_by):
    """Apply filters to donations list."""
    filtered = donations.copy()
    
    # Quality filter
    if quality_filter != "All":
        filtered = [d for d in filtered if d['quality_prediction'] == quality_filter]
    
    # Quantity filter
    if quantity_filter != "All":
        if quantity_filter == "Small (1-10)":
            filtered = [d for d in filtered if d['quantity'] <= 10]
        elif quantity_filter == "Medium (11-50)":
            filtered = [d for d in filtered if 11 <= d['quantity'] <= 50]
        elif quantity_filter == "Large (50+)":
            filtered = [d for d in filtered if d['quantity'] > 50]
    
    # Sort
    if sort_by == "Newest First":
        filtered.sort(key=lambda x: x['created_at'], reverse=True)
    elif sort_by == "Expiry Date":
        filtered.sort(key=lambda x: x['expiry_date'])
    elif sort_by == "Quantity":
        filtered.sort(key=lambda x: x['quantity'], reverse=True)
    
    return filtered

def show_notifications_tab():
    """Display notifications tab for NGOs."""
    if st.session_state.user_role == 'NGO':
        display_notifications_panel(st.session_state.user_id)
    else:
        st.info("Notifications are available for NGO users only.")

if __name__ == "__main__":
    show_dashboard_page()
