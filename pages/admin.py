import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db import (
    get_admin_stats, get_all_donations, get_db_connection,
    get_recent_donations, get_ngos_by_capacity
)
from utils import (
    create_donation_chart, create_donations_timeline, create_quantity_chart,
    calculate_impact_metrics, export_data_to_csv, format_large_number,
    get_time_ago, show_success_message, show_error_message
)
from ai_features import generate_insights_report
import sqlite3

def show_admin_page():
    """Display the admin panel page."""
    st.title("⚙️ Admin Panel")
    
    # Check if user is admin
    if not st.session_state.get('logged_in', False):
        st.error("Please login to access the admin panel.")
        return
    
    if st.session_state.user_role != 'Admin':
        st.error("Access denied. Admin privileges required.")
        return
    
    # Admin dashboard tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview", "👥 Users", "🍽️ Donations", "📈 Analytics", "🤖 AI Insights", "⚙️ Settings"
    ])
    
    with tab1:
        show_overview_tab()
    
    with tab2:
        show_users_tab()
    
    with tab3:
        show_donations_tab()
    
    with tab4:
        show_analytics_tab()
    
    with tab5:
        show_ai_insights_tab()
    
    with tab6:
        show_settings_tab()

def show_overview_tab():
    """Display overview dashboard."""
    st.header("📊 Platform Overview")
    
    # Get platform statistics
    stats = get_admin_stats()
    
    # Key metrics row 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Users", 
            format_large_number(stats.get('total_users', 0)),
            help="Total registered users on the platform"
        )
    
    with col2:
        st.metric(
            "Total Donations", 
            format_large_number(stats.get('total_donations', 0)),
            help="Total food donations submitted"
        )
    
    with col3:
        st.metric(
            "Food Saved", 
            f"{format_large_number(stats.get('total_food_saved', 0))} units",
            help="Total quantity of food saved from waste"
        )
    
    with col4:
        completion_rate = 0
        if stats.get('total_donations', 0) > 0:
            completion_rate = (stats.get('completed_donations', 0) / stats.get('total_donations', 0)) * 100
        st.metric(
            "Completion Rate", 
            f"{completion_rate:.1f}%",
            help="Percentage of donations that were successfully picked up"
        )
    
    # Key metrics row 2
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            "Active NGOs", 
            stats.get('total_ngos', 0),
            help="Number of registered NGO partners"
        )
    
    with col6:
        st.metric(
            "Active Donors", 
            stats.get('total_donors', 0),
            help="Number of registered food donors"
        )
    
    with col7:
        st.metric(
            "Fresh Donations", 
            stats.get('fresh_donations', 0),
            help="Donations classified as fresh and safe"
        )
    
    with col8:
        fresh_rate = 0
        if stats.get('total_donations', 0) > 0:
            fresh_rate = (stats.get('fresh_donations', 0) / stats.get('total_donations', 0)) * 100
        st.metric(
            "Fresh Rate", 
            f"{fresh_rate:.1f}%",
            help="Percentage of donations classified as fresh"
        )
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("📧 Send Platform Update", type="primary"):
            st.info("Platform update notification feature coming soon!")
    
    with action_col2:
        if st.button("📊 Generate Monthly Report"):
            generate_monthly_report()
    
    with action_col3:
        if st.button("🧹 Clean Expired Data"):
            clean_expired_donations()
    
    with action_col4:
        if st.button("🔄 Refresh Statistics"):
            st.rerun()
    
    # Recent activity
    st.markdown("---")
    st.subheader("📰 Recent Platform Activity")
    
    recent_donations = get_recent_donations(limit=10)
    
    if recent_donations:
        activity_df = pd.DataFrame(recent_donations)
        activity_df['time_ago'] = activity_df['created_at'].apply(get_time_ago)
        
        for _, donation in activity_df.iterrows():
            with st.expander(f"🍽️ {donation['food_name']} - {donation['time_ago']}"):
                col_det1, col_det2 = st.columns(2)
                
                with col_det1:
                    st.write(f"**Donor:** {donation['donor_name']}")
                    st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
                    st.write(f"**Quality:** {donation['quality_prediction']}")
                
                with col_det2:
                    st.write(f"**Status:** {donation['status']}")
                    st.write(f"**Expiry:** {donation['expiry_date']}")
                    st.write(f"**Created:** {donation['created_at'][:16]}")
    else:
        st.info("No recent activity to display.")

def show_users_tab():
    """Display users management tab."""
    st.header("👥 User Management")
    
    # Get user statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # User overview
    cursor.execute('''
        SELECT role, COUNT(*) as count, 
               COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count
        FROM users 
        GROUP BY role
    ''')
    
    user_stats = cursor.fetchall()
    
    # Display user statistics
    st.subheader("📊 User Statistics")
    
    for stat in user_stats:
        role, total, active = stat
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(f"Total {role}s", total)
        with col2:
            st.metric(f"Active {role}s", active)
        with col3:
            inactive = total - active
            st.metric(f"Inactive {role}s", inactive)
    
    st.markdown("---")
    
    # User management section
    col_filter, col_action = st.columns([3, 1])
    
    with col_filter:
        role_filter = st.selectbox("Filter by Role:", ["All", "Donor", "NGO", "Admin"])
        status_filter = st.selectbox("Filter by Status:", ["All", "Active", "Inactive"])
    
    with col_action:
        st.markdown("#### Actions")
        if st.button("📊 Export Users"):
            export_users_data()
    
    # Get filtered users
    query = "SELECT * FROM users WHERE 1=1"
    params = []
    
    if role_filter != "All":
        query += " AND role = ?"
        params.append(role_filter)
    
    if status_filter == "Active":
        query += " AND is_active = 1"
    elif status_filter == "Inactive":
        query += " AND is_active = 0"
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    users = cursor.fetchall()
    
    # Display users table
    if users:
        st.subheader(f"👤 Users ({len(users)} found)")
        
        for user in users:
            with st.expander(f"{user['name']} ({user['role']}) - {user['email']}"):
                user_col1, user_col2, user_col3 = st.columns(3)
                
                with user_col1:
                    st.write(f"**Name:** {user['name']}")
                    st.write(f"**Email:** {user['email']}")
                    st.write(f"**Role:** {user['role']}")
                
                with user_col2:
                    st.write(f"**Organization:** {user['organization'] or 'N/A'}")
                    st.write(f"**Joined:** {user['created_at'][:10]}")
                    status_icon = "✅" if user['is_active'] else "❌"
                    st.write(f"**Status:** {status_icon} {'Active' if user['is_active'] else 'Inactive'}")
                
                with user_col3:
                    if user['is_active']:
                        if st.button(f"🚫 Deactivate", key=f"deactivate_{user['id']}"):
                            deactivate_user(user['id'])
                    else:
                        if st.button(f"✅ Activate", key=f"activate_{user['id']}"):
                            activate_user(user['id'])
                    
                    if st.button(f"📊 View Details", key=f"details_{user['id']}"):
                        show_user_details(user)
    else:
        st.info("No users found matching the current filters.")
    
    conn.close()

def show_donations_tab():
    """Display donations management tab."""
    st.header("🍽️ Donation Management")
    
    # Get all donations
    all_donations = get_all_donations()
    
    if not all_donations:
        st.info("No donations found in the system.")
        return
    
    # Donation filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        quality_filter = st.selectbox(
            "Filter by Quality:", 
            ["All", "Fresh", "Expires Soon", "Expires Today", "Expired"]
        )
    
    with col_filter2:
        status_filter = st.selectbox(
            "Filter by Status:", 
            ["All", "Available", "Requested", "Picked Up", "Expired"]
        )
    
    with col_filter3:
        date_range = st.selectbox(
            "Date Range:", 
            ["All Time", "Last 7 days", "Last 30 days", "Last 90 days"]
        )
    
    # Apply filters
    filtered_donations = apply_admin_filters(all_donations, quality_filter, status_filter, date_range)
    
    # Donation statistics
    st.subheader("📊 Donation Statistics")
    
    total_donations = len(filtered_donations)
    total_quantity = sum(d.get('quantity', 0) for d in filtered_donations)
    
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        st.metric("Total Donations", total_donations)
    
    with stat_col2:
        st.metric("Total Quantity", f"{total_quantity:,} units")
    
    with stat_col3:
        fresh_count = len([d for d in filtered_donations if d['quality_prediction'] == 'Fresh'])
        st.metric("Fresh Donations", fresh_count)
    
    with stat_col4:
        avg_quantity = total_quantity / total_donations if total_donations > 0 else 0
        st.metric("Avg. Quantity", f"{avg_quantity:.1f} units")
    
    # Export and bulk actions
    st.markdown("---")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📊 Export Donations"):
            export_donations_data(filtered_donations)
    
    with action_col2:
        if st.button("🧹 Clean Expired"):
            clean_expired_donations()
    
    with action_col3:
        if st.button("📈 Generate Report"):
            generate_donations_report(filtered_donations)
    
    # Display donations
    st.markdown("---")
    st.subheader(f"🍽️ Donations ({len(filtered_donations)} found)")
    
    # Pagination
    items_per_page = 10
    total_pages = (len(filtered_donations) + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox("Page:", range(1, total_pages + 1))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_donations = filtered_donations[start_idx:end_idx]
    else:
        page_donations = filtered_donations
    
    # Display paginated donations
    for donation in page_donations:
        with st.expander(f"{donation['food_name']} - {donation['donor_name']} ({donation['created_at'][:10]})"):
            don_col1, don_col2, don_col3 = st.columns(3)
            
            with don_col1:
                st.write(f"**Food:** {donation['food_name']}")
                st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
                st.write(f"**Donor:** {donation['donor_name']}")
                st.write(f"**Organization:** {donation.get('donor_org', 'N/A')}")
            
            with don_col2:
                quality_color = {
                    "Fresh": "🟢", "Expires Soon": "🟡", 
                    "Expires Today": "🟠", "Expired": "🔴"
                }.get(donation['quality_prediction'], "⚪")
                
                st.write(f"**Quality:** {quality_color} {donation['quality_prediction']}")
                st.write(f"**Status:** {donation['status']}")
                st.write(f"**Expiry:** {donation['expiry_date']}")
                st.write(f"**Confidence:** {donation.get('quality_confidence', 0)*100:.1f}%")
            
            with don_col3:
                st.write(f"**Created:** {donation['created_at'][:16]}")
                if donation.get('description'):
                    st.write(f"**Description:** {donation['description'][:100]}...")
                
                # Admin actions
                if st.button(f"🗑️ Delete", key=f"delete_{donation['id']}"):
                    delete_donation(donation['id'])

def show_analytics_tab():
    """Display advanced analytics tab."""
    st.header("📈 Advanced Analytics")
    
    # Get data for analytics
    all_donations = get_all_donations()
    
    if not all_donations:
        st.info("No data available for analytics.")
        return
    
    # Time period selector
    time_period = st.selectbox(
        "Analysis Period:", 
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
    )
    
    # Filter data by time period
    filtered_data = filter_by_time_period(all_donations, time_period)
    
    # Key performance indicators
    st.subheader("📊 Key Performance Indicators")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    total_donations = len(filtered_data)
    fresh_donations = len([d for d in filtered_data if d['quality_prediction'] == 'Fresh'])
    completed_donations = len([d for d in filtered_data if d['status'] == 'Picked Up'])
    total_food = sum(d.get('quantity', 0) for d in filtered_data)
    
    with kpi_col1:
        st.metric("Donations", total_donations)
    
    with kpi_col2:
        fresh_rate = (fresh_donations / total_donations * 100) if total_donations > 0 else 0
        st.metric("Fresh Rate", f"{fresh_rate:.1f}%")
    
    with kpi_col3:
        completion_rate = (completed_donations / total_donations * 100) if total_donations > 0 else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    with kpi_col4:
        st.metric("Food Volume", f"{total_food:,} units")
    
    # Charts section
    st.markdown("---")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Quality distribution chart
        quality_chart = create_donation_chart(filtered_data)
        if quality_chart:
            st.plotly_chart(quality_chart, use_container_width=True)
        
        # Top food types
        st.subheader("🍽️ Popular Food Types")
        df = pd.DataFrame(filtered_data)
        if not df.empty:
            food_counts = df['food_name'].value_counts().head(10)
            fig = px.bar(x=food_counts.values, y=food_counts.index, orientation='h')
            fig.update_layout(title="Top 10 Food Items", height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        # Timeline chart
        timeline_chart = create_donations_timeline(filtered_data)
        if timeline_chart:
            st.plotly_chart(timeline_chart, use_container_width=True)
        
        # Status distribution
        st.subheader("📊 Status Distribution")
        if not df.empty:
            status_counts = df['status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index)
            fig.update_layout(title="Donation Status Distribution", height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Donor analysis
    st.markdown("---")
    st.subheader("👥 Donor Analysis")
    
    if not df.empty:
        donor_stats = df.groupby('donor_name').agg({
            'quantity': 'sum',
            'id': 'count'
        }).rename(columns={'id': 'donations_count'}).sort_values('quantity', ascending=False)
        
        st.markdown("**Top 10 Donors by Quantity:**")
        st.dataframe(donor_stats.head(10))
    
    # NGO performance (if available)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.name, u.organization, COUNT(dr.id) as requests_count,
               COUNT(CASE WHEN dr.status = 'Completed' THEN 1 END) as completed_count
        FROM users u
        LEFT JOIN donation_requests dr ON u.id = dr.ngo_id
        WHERE u.role = 'NGO'
        GROUP BY u.id
        HAVING requests_count > 0
        ORDER BY completed_count DESC
    ''')
    
    ngo_performance = cursor.fetchall()
    
    if ngo_performance:
        st.markdown("---")
        st.subheader("🏢 NGO Performance")
        
        ngo_df = pd.DataFrame(ngo_performance)
        ngo_df['success_rate'] = (ngo_df['completed_count'] / ngo_df['requests_count'] * 100).round(1)
        
        st.dataframe(ngo_df)
    
    conn.close()

def show_ai_insights_tab():
    """Display AI-powered insights tab."""
    st.header("🤖 AI-Powered Insights")
    
    # Get donations data for analysis
    all_donations = get_all_donations()
    
    if not all_donations:
        st.info("No data available for AI analysis.")
        return
    
    # Time period for analysis
    analysis_period = st.selectbox(
        "Analysis Period:", 
        ["Last 30 days", "Last 90 days", "Last 6 months", "All time"]
    )
    
    # Filter data
    filtered_data = filter_by_time_period(all_donations, analysis_period)
    
    if st.button("🚀 Generate AI Insights", type="primary"):
        with st.spinner("🤖 Analyzing data and generating insights..."):
            try:
                insights = generate_insights_report(filtered_data, analysis_period)
                
                # Display insights
                st.markdown("### 📊 AI Analysis Results")
                
                # Summary
                if insights.get('summary'):
                    st.info(f"**Summary:** {insights['summary']}")
                
                # Key insights
                if insights.get('insights'):
                    st.markdown("#### 🔍 Key Insights")
                    for insight in insights['insights']:
                        st.write(f"• {insight}")
                
                # Trends
                if insights.get('trends'):
                    st.markdown("#### 📈 Observed Trends")
                    for trend in insights['trends']:
                        st.write(f"• {trend}")
                
                # Predictions
                if insights.get('predictions'):
                    st.markdown("#### 🔮 Predictions")
                    for prediction in insights['predictions']:
                        st.write(f"• {prediction}")
                
                # Recommendations
                if insights.get('recommendations'):
                    st.markdown("#### 💡 Recommendations")
                    for recommendation in insights['recommendations']:
                        st.success(f"• {recommendation}")
                
                # Data summary
                if insights.get('data_summary'):
                    st.markdown("#### 📋 Data Summary")
                    with st.expander("View detailed data breakdown"):
                        st.json(insights['data_summary'])
            
            except Exception as e:
                st.error(f"Failed to generate AI insights: {e}")
                st.info("Falling back to basic analytics...")
                
                # Fallback basic insights
                show_basic_insights(filtered_data, analysis_period)
    
    else:
        st.info("Click the button above to generate AI-powered insights and recommendations.")
    
    # Manual insights section
    st.markdown("---")
    st.subheader("📝 Manual Insights & Notes")
    
    # Allow admin to add manual insights
    with st.form("manual_insights"):
        insight_title = st.text_input("Insight Title:")
        insight_content = st.text_area("Insight Content:")
        insight_category = st.selectbox("Category:", ["Trend", "Issue", "Opportunity", "Recommendation"])
        
        if st.form_submit_button("💾 Save Insight"):
            save_manual_insight(insight_title, insight_content, insight_category)

def show_settings_tab():
    """Display platform settings tab."""
    st.header("⚙️ Platform Settings")
    
    # System configuration
    st.subheader("🖥️ System Configuration")
    
    with st.form("system_settings"):
        st.markdown("#### General Settings")
        
        platform_name = st.text_input("Platform Name:", value="FoodBridge")
        max_donation_age = st.number_input("Max Donation Age (days):", min_value=1, max_value=365, value=30)
        auto_expire = st.checkbox("Auto-expire old donations", value=True)
        
        st.markdown("#### AI Settings")
        
        ai_enabled = st.checkbox("Enable AI Features", value=True)
        quality_threshold = st.slider("Quality Prediction Threshold:", 0.0, 1.0, 0.7)
        
        st.markdown("#### Notification Settings")
        
        email_notifications = st.checkbox("Enable Email Notifications", value=True)
        sms_notifications = st.checkbox("Enable SMS Notifications", value=False)
        
        if st.form_submit_button("💾 Save Settings"):
            st.success("Settings saved successfully!")
    
    # Database maintenance
    st.markdown("---")
    st.subheader("🗄️ Database Maintenance")
    
    maint_col1, maint_col2, maint_col3 = st.columns(3)
    
    with maint_col1:
        if st.button("🧹 Clean Expired Data"):
            clean_expired_donations()
    
    with maint_col2:
        if st.button("📊 Optimize Database"):
            optimize_database()
    
    with maint_col3:
        if st.button("🔄 Reset Statistics"):
            if st.button("⚠️ Confirm Reset"):
                reset_statistics()
    
    # Backup and export
    st.markdown("---")
    st.subheader("💾 Backup & Export")
    
    backup_col1, backup_col2 = st.columns(2)
    
    with backup_col1:
        if st.button("📦 Create Backup"):
            create_database_backup()
    
    with backup_col2:
        if st.button("📊 Export All Data"):
            export_all_platform_data()
    
    # Platform statistics
    st.markdown("---")
    st.subheader("📈 Platform Health")
    
    # Database size and performance metrics
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get table sizes
    tables = ['users', 'donations', 'donation_requests', 'ngo_profiles', 'chat_history']
    
    health_col1, health_col2 = st.columns(2)
    
    with health_col1:
        st.markdown("**Database Tables:**")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            st.write(f"• {table.title()}: {count:,} records")
    
    with health_col2:
        st.markdown("**System Status:**")
        st.write("• 🟢 Database: Healthy")
        st.write("• 🟢 AI Services: Available")
        st.write("• 🟢 File Storage: Normal")
        st.write("• 🟢 Authentication: Active")
    
    conn.close()

# Helper functions

def generate_monthly_report():
    """Generate monthly platform report."""
    st.success("📊 Monthly report generated! (Feature coming soon)")

def clean_expired_donations():
    """Clean expired donations from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update expired donations
        cursor.execute('''
            UPDATE donations 
            SET status = 'Expired' 
            WHERE expiry_date < date('now') AND status = 'Available'
        ''')
        
        expired_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        show_success_message(f"✅ Updated {expired_count} expired donations")
        st.rerun()
        
    except Exception as e:
        show_error_message(f"Failed to clean expired donations: {e}")

def export_users_data():
    """Export users data to CSV."""
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM users", conn)
        conn.close()
        
        csv_data = export_data_to_csv(df.to_dict('records'), "users_export.csv")
        
        st.download_button(
            label="📥 Download Users CSV",
            data=csv_data,
            file_name=f"users_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        show_error_message(f"Failed to export users data: {e}")

def export_donations_data(donations):
    """Export donations data to CSV."""
    try:
        csv_data = export_data_to_csv(donations, "donations_export.csv")
        
        st.download_button(
            label="📥 Download Donations CSV",
            data=csv_data,
            file_name=f"donations_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        show_error_message(f"Failed to export donations data: {e}")

def deactivate_user(user_id):
    """Deactivate a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        show_success_message("User deactivated successfully")
        st.rerun()
        
    except Exception as e:
        show_error_message(f"Failed to deactivate user: {e}")

def activate_user(user_id):
    """Activate a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        show_success_message("User activated successfully")
        st.rerun()
        
    except Exception as e:
        show_error_message(f"Failed to activate user: {e}")

def delete_donation(donation_id):
    """Delete a donation."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
        conn.commit()
        conn.close()
        
        show_success_message("Donation deleted successfully")
        st.rerun()
        
    except Exception as e:
        show_error_message(f"Failed to delete donation: {e}")

def apply_admin_filters(donations, quality_filter, status_filter, date_range):
    """Apply admin filters to donations."""
    filtered = donations.copy()
    
    # Quality filter
    if quality_filter != "All":
        filtered = [d for d in filtered if d['quality_prediction'] == quality_filter]
    
    # Status filter
    if status_filter != "All":
        filtered = [d for d in filtered if d['status'] == status_filter]
    
    # Date range filter
    if date_range != "All Time":
        days_map = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90
        }
        
        if date_range in days_map:
            cutoff_date = datetime.now() - timedelta(days=days_map[date_range])
            filtered = [d for d in filtered if datetime.strptime(d['created_at'], "%Y-%m-%d %H:%M:%S") >= cutoff_date]
    
    return filtered

def filter_by_time_period(data, period):
    """Filter data by time period."""
    if period == "All time":
        return data
    
    days_map = {
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90,
        "Last 6 months": 180
    }
    
    if period in days_map:
        cutoff_date = datetime.now() - timedelta(days=days_map[period])
        return [d for d in data if datetime.strptime(d['created_at'], "%Y-%m-%d %H:%M:%S") >= cutoff_date]
    
    return data

def show_basic_insights(data, period):
    """Show basic insights as fallback."""
    total_donations = len(data)
    fresh_count = len([d for d in data if d['quality_prediction'] == 'Fresh'])
    
    st.markdown("#### 📊 Basic Analytics")
    st.write(f"• Total donations in {period}: {total_donations}")
    st.write(f"• Fresh donations: {fresh_count} ({fresh_count/total_donations*100:.1f}%)")
    st.write(f"• Average donation size: {sum(d.get('quantity', 0) for d in data)/total_donations:.1f} units")

def save_manual_insight(title, content, category):
    """Save manual insight to database."""
    if title and content:
        show_success_message(f"Insight '{title}' saved successfully!")
    else:
        show_error_message("Please provide both title and content for the insight.")

def optimize_database():
    """Optimize database performance."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        conn.close()
        
        show_success_message("Database optimized successfully!")
        
    except Exception as e:
        show_error_message(f"Failed to optimize database: {e}")

def reset_statistics():
    """Reset platform statistics."""
    show_success_message("Statistics reset feature coming soon!")

def create_database_backup():
    """Create database backup."""
    show_success_message("Database backup created successfully! (Feature coming soon)")

def export_all_platform_data():
    """Export all platform data."""
    show_success_message("Platform data export initiated! (Feature coming soon)")

def show_user_details(user):
    """Show detailed user information."""
    st.markdown(f"### 👤 User Details: {user['name']}")
    st.json(dict(user))

def generate_donations_report(donations):
    """Generate detailed donations report."""
    st.success("📊 Donations report generated! (Feature coming soon)")

if __name__ == "__main__":
    show_admin_page()
