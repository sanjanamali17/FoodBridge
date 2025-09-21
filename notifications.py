"""
Real-time notification system for FoodBridge platform.
Handles NGO notifications for new donations, pickup reminders, and system alerts.
"""

import streamlit as st
import datetime
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import sqlite3
from db import get_db_connection

@dataclass
class Notification:
    """Notification data structure."""
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str  # 'new_donation', 'pickup_reminder', 'system_alert', 'match_alert'
    priority: str  # 'low', 'medium', 'high', 'urgent'
    created_at: str
    read_at: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Optional[Dict] = None

class NotificationManager:
    """Manages notifications for FoodBridge users."""
    
    def __init__(self):
        self.init_notifications_table()
    
    def init_notifications_table(self):
        """Initialize the notifications table."""
        conn = get_db_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    created_at TEXT NOT NULL,
                    read_at TEXT NULL,
                    action_url TEXT NULL,
                    metadata TEXT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Create index for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user_created 
                ON notifications (user_id, created_at DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_unread 
                ON notifications (user_id, read_at) WHERE read_at IS NULL
            """)
            
            conn.commit()
        except Exception as e:
            st.error(f"Error initializing notifications table: {e}")
        finally:
            conn.close()
    
    def create_notification(
        self, 
        user_id: int, 
        title: str, 
        message: str, 
        notification_type: str,
        priority: str = 'medium',
        action_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Create a new notification.
        
        Returns:
            Notification ID if successful, -1 if failed
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO notifications 
                (user_id, title, message, notification_type, priority, created_at, action_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, title, message, notification_type, priority,
                datetime.datetime.now().isoformat(),
                action_url,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            st.error(f"Error creating notification: {e}")
            return -1
        finally:
            conn.close()
    
    def get_user_notifications(
        self, 
        user_id: int, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a specific user."""
        conn = get_db_connection()
        try:
            query = """
                SELECT id, user_id, title, message, notification_type, priority,
                       created_at, read_at, action_url, metadata
                FROM notifications 
                WHERE user_id = ?
            """
            params = [user_id]
            
            if unread_only:
                query += " AND read_at IS NULL"
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            notifications = []
            
            for row in cursor.fetchall():
                metadata = json.loads(row[9]) if row[9] else None
                notifications.append(Notification(
                    id=row[0],
                    user_id=row[1],
                    title=row[2],
                    message=row[3],
                    notification_type=row[4],
                    priority=row[5],
                    created_at=row[6],
                    read_at=row[7],
                    action_url=row[8],
                    metadata=metadata
                ))
            
            return notifications
            
        except Exception as e:
            st.error(f"Error getting notifications: {e}")
            return []
        finally:
            conn.close()
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        conn = get_db_connection()
        try:
            conn.execute("""
                UPDATE notifications 
                SET read_at = ? 
                WHERE id = ? AND user_id = ?
            """, (datetime.datetime.now().isoformat(), notification_id, user_id))
            
            conn.commit()
            return conn.total_changes > 0
            
        except Exception as e:
            st.error(f"Error marking notification as read: {e}")
            return False
        finally:
            conn.close()
    
    def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                UPDATE notifications 
                SET read_at = ? 
                WHERE user_id = ? AND read_at IS NULL
            """, (datetime.datetime.now().isoformat(), user_id))
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            st.error(f"Error marking all notifications as read: {e}")
            return 0
        finally:
            conn.close()
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM notifications 
                WHERE user_id = ? AND read_at IS NULL
            """, (user_id,))
            
            return cursor.fetchone()[0]
            
        except Exception as e:
            st.error(f"Error getting unread count: {e}")
            return 0
        finally:
            conn.close()
    
    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """Delete a notification."""
        conn = get_db_connection()
        try:
            conn.execute("""
                DELETE FROM notifications 
                WHERE id = ? AND user_id = ?
            """, (notification_id, user_id))
            
            conn.commit()
            return conn.total_changes > 0
            
        except Exception as e:
            st.error(f"Error deleting notification: {e}")
            return False
        finally:
            conn.close()
    
    def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """Clean up notifications older than specified days."""
        conn = get_db_connection()
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_old)).isoformat()
            
            cursor = conn.execute("""
                DELETE FROM notifications 
                WHERE created_at < ? AND read_at IS NOT NULL
            """, (cutoff_date,))
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            st.error(f"Error cleaning up notifications: {e}")
            return 0
        finally:
            conn.close()

class DonationNotificationService:
    """Service for handling donation-related notifications."""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
    
    def notify_new_donation(self, donation_data: Dict, matching_ngos: List[Dict]) -> List[int]:
        """
        Notify matching NGOs about a new donation.
        
        Args:
            donation_data: Donation information
            matching_ngos: List of NGOs that match the donation criteria
            
        Returns:
            List of notification IDs created
        """
        notification_ids = []
        
        for ngo in matching_ngos:
            try:
                # Create personalized notification message
                title = f"🎁 New Donation Available: {donation_data.get('food_name', 'Food Item')}"
                
                message = self._create_donation_notification_message(donation_data, ngo)
                
                # Determine priority based on expiry and quality
                priority = self._get_donation_priority(donation_data)
                
                # Create metadata for the notification
                metadata = {
                    'donation_id': donation_data.get('id'),
                    'food_name': donation_data.get('food_name'),
                    'quantity': donation_data.get('quantity'),
                    'quality': donation_data.get('quality_prediction'),
                    'expiry_date': donation_data.get('expiry_date'),
                    'donor_name': donation_data.get('donor_name'),
                    'match_score': ngo.get('match_score', 0)
                }
                
                notification_id = self.notification_manager.create_notification(
                    user_id=ngo['id'],
                    title=title,
                    message=message,
                    notification_type='new_donation',
                    priority=priority,
                    action_url=f"/NGO Dashboard?donation_id={donation_data.get('id')}",
                    metadata=metadata
                )
                
                if notification_id > 0:
                    notification_ids.append(notification_id)
                    
            except Exception as e:
                st.error(f"Error notifying NGO {ngo.get('name', 'Unknown')}: {e}")
        
        return notification_ids
    
    def _create_donation_notification_message(self, donation_data: Dict, ngo: Dict) -> str:
        """Create a personalized notification message for an NGO."""
        
        food_name = donation_data.get('food_name', 'Food item')
        quantity = donation_data.get('quantity', 'Unknown')
        unit = donation_data.get('unit', 'units')
        quality = donation_data.get('quality_prediction', 'Unknown')
        expiry_date = donation_data.get('expiry_date', 'Unknown')
        donor_name = donation_data.get('donor_name', 'Anonymous')
        
        # Calculate urgency
        urgency_msg = ""
        if quality in ['Expires Today', 'Expires Soon']:
            urgency_msg = " ⚡ URGENT PICKUP NEEDED"
        
        message = f"""
Hi {ngo.get('name', 'Team')},
        
A new donation matches your capacity and needs:{urgency_msg}

📦 **{food_name}** - {quantity} {unit}
🏷️ Quality: {quality}
📅 Expires: {expiry_date}
👤 Donor: {donor_name}

This donation was matched to your organization based on your capacity ({ngo.get('capacity', 'N/A')} units) and current needs.

Click to view details and request pickup if interested.
        """.strip()
        
        return message
    
    def _get_donation_priority(self, donation_data: Dict) -> str:
        """Determine notification priority based on donation characteristics."""
        
        quality = donation_data.get('quality_prediction', '').lower()
        
        if 'expires today' in quality or 'expired' in quality:
            return 'urgent'
        elif 'expires soon' in quality:
            return 'high'
        elif 'fresh' in quality:
            return 'medium'
        else:
            return 'low'
    
    def notify_pickup_reminder(self, pickup_request: Dict) -> int:
        """Send pickup reminder notification."""
        
        try:
            title = f"📋 Pickup Reminder: {pickup_request.get('food_name', 'Food Item')}"
            
            message = f"""
Reminder: You have a scheduled pickup today.

📦 Item: {pickup_request.get('food_name')}
📍 Location: {pickup_request.get('pickup_location', 'See donation details')}
⏰ Scheduled: {pickup_request.get('pickup_time', 'Not specified')}
📞 Donor: {pickup_request.get('donor_contact', 'Contact via platform')}

Please confirm pickup completion once done.
            """.strip()
            
            return self.notification_manager.create_notification(
                user_id=pickup_request['ngo_id'],
                title=title,
                message=message,
                notification_type='pickup_reminder',
                priority='high',
                action_url=f"/NGO Dashboard?pickup_id={pickup_request.get('id')}",
                metadata={
                    'pickup_id': pickup_request.get('id'),
                    'donation_id': pickup_request.get('donation_id'),
                    'pickup_date': pickup_request.get('pickup_date')
                }
            )
            
        except Exception as e:
            st.error(f"Error creating pickup reminder: {e}")
            return -1

def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    if 'notification_manager' not in st.session_state:
        st.session_state.notification_manager = NotificationManager()
    return st.session_state.notification_manager

def get_donation_notification_service() -> DonationNotificationService:
    """Get the global donation notification service instance."""
    if 'donation_notification_service' not in st.session_state:
        st.session_state.donation_notification_service = DonationNotificationService()
    return st.session_state.donation_notification_service

def display_notification_badge(user_id: int) -> None:
    """Display notification badge in the UI."""
    
    notification_manager = get_notification_manager()
    unread_count = notification_manager.get_unread_count(user_id)
    
    if unread_count > 0:
        st.sidebar.markdown(f"""
        <div style="
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 2px 10px rgba(238, 90, 36, 0.3);
        ">
            🔔 {unread_count} new notification{'s' if unread_count != 1 else ''}
        </div>
        """, unsafe_allow_html=True)

def display_notifications_panel(user_id: int) -> None:
    """Display notifications panel for a user."""
    
    notification_manager = get_notification_manager()
    
    st.markdown("### 🔔 Notifications")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    with col2:
        if st.button("✅ Mark All Read"):
            count = notification_manager.mark_all_read(user_id)
            if count > 0:
                st.success(f"Marked {count} notifications as read")
                st.rerun()
    
    with col3:
        show_read = st.checkbox("Show Read", value=False)
    
    # Get notifications
    notifications = notification_manager.get_user_notifications(
        user_id, 
        unread_only=not show_read,
        limit=20
    )
    
    if not notifications:
        st.info("📭 No notifications to display")
        return
    
    # Display notifications
    for notification in notifications:
        
        # Determine notification styling
        if notification.read_at:
            opacity = "0.7"
            bg_color = "#f8f9fa"
        else:
            opacity = "1.0"
            bg_color = get_priority_color(notification.priority)
        
        # Create notification card
        with st.container():
            st.markdown(f"""
            <div style="
                background: {bg_color};
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                opacity: {opacity};
                border-left: 4px solid {get_priority_border_color(notification.priority)};
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <h4 style="margin: 0 0 8px 0; color: #2c3e50;">
                            {get_priority_icon(notification.priority)} {notification.title}
                        </h4>
                        <p style="margin: 0 0 8px 0; color: #34495e; line-height: 1.4;">
                            {notification.message.replace('\\n', '<br>')}
                        </p>
                        <small style="color: #7f8c8d;">
                            {format_notification_time(notification.created_at)} | 
                            {notification.notification_type.replace('_', ' ').title()}
                        </small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons for each notification
            col_read, col_action, col_delete = st.columns([1, 2, 1])
            
            with col_read:
                if not notification.read_at:
                    if st.button(f"✅ Read", key=f"read_{notification.id}"):
                        notification_manager.mark_notification_read(notification.id, user_id)
                        st.rerun()
            
            with col_action:
                if notification.action_url:
                    st.markdown(f"[🔗 View Details]({notification.action_url})")
            
            with col_delete:
                if st.button(f"🗑️ Delete", key=f"delete_{notification.id}"):
                    notification_manager.delete_notification(notification.id, user_id)
                    st.rerun()

def get_priority_color(priority: str) -> str:
    """Get background color based on priority."""
    colors = {
        'urgent': '#ffebee',
        'high': '#fff3e0',
        'medium': '#f3e5f5',
        'low': '#e8f5e8'
    }
    return colors.get(priority, '#f8f9fa')

def get_priority_border_color(priority: str) -> str:
    """Get border color based on priority."""
    colors = {
        'urgent': '#f44336',
        'high': '#ff9800',
        'medium': '#9c27b0',
        'low': '#4caf50'
    }
    return colors.get(priority, '#e0e0e0')

def get_priority_icon(priority: str) -> str:
    """Get icon based on priority."""
    icons = {
        'urgent': '🚨',
        'high': '⚡',
        'medium': '📋',
        'low': 'ℹ️'
    }
    return icons.get(priority, '📋')

def format_notification_time(created_at: str) -> str:
    """Format notification timestamp for display."""
    try:
        created = datetime.datetime.fromisoformat(created_at)
        now = datetime.datetime.now()
        diff = now - created
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
            
    except:
        return "Unknown time"