import streamlit as st
from ai_features import chatbot_response, generate_donation_suggestions
from db import get_chat_history, save_chat_message, get_db_connection
from utils import show_error_message, show_success_message
import datetime

def show_chatbot_page():
    """Display the AI chatbot page."""
    st.title("🤖 FoodBridge AI Assistant")
    
    # Check if user is logged in
    if not st.session_state.get('logged_in', False):
        st.error("Please login to use the chatbot.")
        return
    
    st.markdown("""
    Welcome to the FoodBridge AI Assistant! I'm here to help you with:
    - Food donation guidelines and best practices
    - Food safety and storage recommendations  
    - NGO coordination and matching
    - Platform features and navigation
    - Donation logistics and pickup procedures
    """)
    
    # Chatbot interface tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📚 Quick Help", "📝 Chat History"])
    
    with tab1:
        show_chat_interface()
    
    with tab2:
        show_quick_help()
    
    with tab3:
        show_chat_history_tab()

def show_chat_interface():
    """Display the main chat interface."""
    st.header("💬 Chat with AI Assistant")
    
    # Initialize chat history in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
        # Add welcome message
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": f"Hello {st.session_state.user_name}! I'm your FoodBridge AI Assistant. How can I help you with food donation today? 🍽️",
            "timestamp": datetime.datetime.now().strftime("%H:%M")
        })
    
    # Chat container
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        for message in st.session_state.chat_messages:
            if message["role"] == "user":
                # User message (right aligned)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background-color: #007bff; color: white; padding: 10px 15px; 
                                border-radius: 15px 15px 5px 15px; max-width: 70%; word-wrap: break-word;">
                        <strong>You:</strong> {message['content']}
                        <div style="font-size: 0.8em; opacity: 0.8; margin-top: 5px;">
                            {message['timestamp']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Assistant message (left aligned)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background-color: #f1f3f4; color: #333; padding: 10px 15px; 
                                border-radius: 15px 15px 15px 5px; max-width: 70%; word-wrap: break-word;">
                        <strong>🤖 Assistant:</strong> {message['content']}
                        <div style="font-size: 0.8em; opacity: 0.6; margin-top: 5px;">
                            {message['timestamp']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input form
    st.markdown("---")
    
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Type your message:",
                placeholder="Ask me about food donation, safety guidelines, NGO matching...",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.form_submit_button("📤 Send", type="primary")
    
    # Process user input
    if send_button and user_input.strip():
        # Add user message to chat
        timestamp = datetime.datetime.now().strftime("%H:%M")
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Get AI response
        with st.spinner("🤖 Thinking..."):
            try:
                ai_response = chatbot_response(user_input, st.session_state.user_id)
                
                # Add AI response to chat
                st.session_state.chat_messages.append({
                    "role": "assistant", 
                    "content": ai_response,
                    "timestamp": datetime.datetime.now().strftime("%H:%M")
                })
                
                # Refresh the page to show new messages
                st.rerun()
                
            except Exception as e:
                error_message = "Sorry, I'm having trouble processing your request right now. Please try again."
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "timestamp": datetime.datetime.now().strftime("%H:%M")
                })
                st.rerun()
    
    # Quick action buttons
    st.markdown("---")
    st.markdown("#### 🚀 Quick Actions")
    
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("🍽️ Donation Tips"):
            send_quick_message("Give me tips for donating food safely")
    
    with quick_col2:
        if st.button("🏢 Find NGOs"):
            send_quick_message("How do I find the right NGO for my donation?")
    
    with quick_col3:
        if st.button("📦 Storage Guide"):
            send_quick_message("What are the best practices for food storage before donation?")
    
    with quick_col4:
        if st.button("🚚 Pickup Process"):
            send_quick_message("How does the pickup process work?")
    
    # Clear chat button
    st.markdown("---")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()

def show_quick_help():
    """Display quick help and FAQs."""
    st.header("📚 Quick Help & FAQs")
    
    # Personalized suggestions based on user role
    suggestions = generate_donation_suggestions(
        st.session_state.user_role, 
        {"name": st.session_state.user_name}
    )
    
    if suggestions:
        st.subheader("💡 Personalized Suggestions")
        for suggestion in suggestions:
            st.info(suggestion)
    
    st.markdown("---")
    
    # FAQ sections
    faq_categories = {
        "🍽️ Food Donation": [
            {
                "question": "What types of food can I donate?",
                "answer": "You can donate fresh fruits, vegetables, cooked meals, packaged foods, dairy products, and baked goods. Ensure all items are safe, properly stored, and within expiry dates."
            },
            {
                "question": "How do I know if my food is safe to donate?",
                "answer": "Check expiry dates, ensure proper storage conditions, look for signs of spoilage, and use our AI quality assessment tool when uploading your donation."
            },
            {
                "question": "What information should I provide when donating?",
                "answer": "Include food name, quantity, expiry date, storage requirements, and any allergen information. Photos help with quality assessment."
            }
        ],
        "🏢 For NGOs": [
            {
                "question": "How do I request food donations?",
                "answer": "Browse available donations in the dashboard, review details, and click 'Request Pickup' to submit your request with contact information."
            },
            {
                "question": "How are donations matched to NGOs?",
                "answer": "Our AI system considers your capacity, location, specialization, and donation size to suggest the best matches for efficient distribution."
            },
            {
                "question": "What should I do after receiving a donation?",
                "answer": "Confirm pickup completion, distribute food promptly, and update your capacity status for future matching."
            }
        ],
        "🛡️ Food Safety": [
            {
                "question": "What are the cold chain requirements?",
                "answer": "Perishable items must be kept at proper temperatures: refrigerated items at 0-4°C, frozen items below -18°C. Transport should maintain these temperatures."
            },
            {
                "question": "How do I handle allergen information?",
                "answer": "Always label common allergens (nuts, dairy, gluten, etc.) clearly and include this information in your donation description."
            },
            {
                "question": "What if food expires during transport?",
                "answer": "Check expiry dates before pickup. If food expires during transport, do not distribute and dispose of safely according to local guidelines."
            }
        ],
        "📱 Platform Features": [
            {
                "question": "How does the AI quality prediction work?",
                "answer": "Our AI analyzes expiry dates, food types, and optionally images to predict freshness. It considers storage requirements and provides confidence scores."
            },
            {
                "question": "Can I track my donation impact?",
                "answer": "Yes! View your impact metrics in the dashboard, including total donations, food saved, NGOs helped, and estimated meals provided."
            },
            {
                "question": "How do I update my profile information?",
                "answer": "Profile management features are coming soon. For now, contact support for any updates needed."
            }
        ]
    }
    
    # Display FAQ categories
    for category, faqs in faq_categories.items():
        with st.expander(f"{category} ({len(faqs)} questions)"):
            for faq in faqs:
                st.markdown(f"**Q: {faq['question']}**")
                st.markdown(f"A: {faq['answer']}")
                st.markdown("---")
    
    # Emergency contacts and support
    st.markdown("---")
    st.subheader("🆘 Need More Help?")
    
    support_col1, support_col2 = st.columns(2)
    
    with support_col1:
        st.markdown("**📞 Emergency Food Safety Issues:**")
        st.markdown("- Contact local health authorities")
        st.markdown("- Report through platform immediately")
        st.markdown("- Stop distribution if safety is compromised")
    
    with support_col2:
        st.markdown("**💬 Platform Support:**")
        st.markdown("- Use the chat assistant for instant help")
        st.markdown("- Email: support@foodbridge.com")
        st.markdown("- Response time: Within 24 hours")

def show_chat_history_tab():
    """Display chat history from database."""
    st.header("📝 Chat History")
    
    # Get chat history from database
    try:
        chat_history = get_chat_history(st.session_state.user_id, limit=50)
        
        if not chat_history:
            st.info("No chat history found. Start a conversation to see your history here!")
            return
        
        # Display options
        col1, col2 = st.columns(2)
        
        with col1:
            show_count = st.selectbox("Show conversations:", [10, 25, 50, "All"])
        
        with col2:
            if st.button("🗑️ Clear History"):
                if st.button("⚠️ Confirm Clear"):
                    clear_chat_history()
        
        # Filter and display history
        if show_count != "All" and isinstance(show_count, int):
            display_history = chat_history[-show_count:]
        else:
            display_history = chat_history
        
        st.markdown(f"**Showing {len(display_history)} conversations:**")
        
        # Group conversations by date
        conversations_by_date = {}
        for chat in display_history:
            date = chat['created_at'][:10]  # YYYY-MM-DD
            if date not in conversations_by_date:
                conversations_by_date[date] = []
            conversations_by_date[date].append(chat)
        
        # Display conversations grouped by date
        for date in sorted(conversations_by_date.keys(), reverse=True):
            with st.expander(f"📅 {date} ({len(conversations_by_date[date])} conversations)"):
                for chat in conversations_by_date[date]:
                    # User message
                    st.markdown(f"**👤 You ({chat['created_at'][11:16]}):**")
                    st.markdown(f"> {chat['message']}")
                    
                    # AI response
                    st.markdown(f"**🤖 Assistant:**")
                    st.markdown(f"> {chat['response']}")
                    
                    st.markdown("---")
        
        # Export option
        st.markdown("---")
        if st.button("📥 Export Chat History"):
            export_chat_history(display_history)
    
    except Exception as e:
        show_error_message(f"Failed to load chat history: {e}")

def send_quick_message(message):
    """Send a quick message to the chatbot."""
    # Add to session chat
    timestamp = datetime.datetime.now().strftime("%H:%M")
    st.session_state.chat_messages.append({
        "role": "user",
        "content": message,
        "timestamp": timestamp
    })
    
    # Get AI response
    try:
        ai_response = chatbot_response(message, st.session_state.user_id)
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.datetime.now().strftime("%H:%M")
        })
    except Exception as e:
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": "Sorry, I couldn't process that request right now.",
            "timestamp": datetime.datetime.now().strftime("%H:%M")
        })
    
    # Switch to chat tab and refresh
    st.rerun()

def clear_chat_history():
    """Clear chat history from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (st.session_state.user_id,))
        conn.commit()
        conn.close()
        
        show_success_message("Chat history cleared successfully!")
        st.rerun()
        
    except Exception as e:
        show_error_message(f"Failed to clear chat history: {e}")

def export_chat_history(history):
    """Export chat history to downloadable format."""
    try:
        # Convert to CSV format
        import pandas as pd
        
        export_data = []
        for chat in history:
            export_data.append({
                "Date": chat['created_at'][:10],
                "Time": chat['created_at'][11:16],
                "User_Message": chat['message'],
                "AI_Response": chat['response']
            })
        
        df = pd.DataFrame(export_data)
        csv_data = df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Chat History CSV",
            data=csv_data,
            file_name=f"chat_history_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        show_error_message(f"Failed to export chat history: {e}")

# Chatbot helper functions

def get_contextual_suggestions(user_role, current_page=None):
    """Get contextual suggestions based on user role and current page."""
    suggestions = []
    
    if user_role == "Donor":
        suggestions = [
            "How do I donate food safely?",
            "What foods are most needed?",
            "How do I know if my food is fresh enough to donate?",
            "What happens after I submit a donation?"
        ]
    elif user_role == "NGO":
        suggestions = [
            "How do I request food donations?",
            "What information should I provide when requesting pickup?",
            "How are donations matched to NGOs?",
            "How do I update my organization's capacity?"
        ]
    elif user_role == "Admin":
        suggestions = [
            "How can I monitor platform performance?",
            "What are the key metrics to track?",
            "How do I manage user accounts?",
            "What AI insights are available?"
        ]
    
    return suggestions

def format_ai_response(response):
    """Format AI response for better display."""
    # Add emoji and formatting to common response types
    if "food safety" in response.lower():
        response = "🛡️ " + response
    elif "donation" in response.lower():
        response = "🍽️ " + response
    elif "ngo" in response.lower():
        response = "🏢 " + response
    elif "pickup" in response.lower():
        response = "🚚 " + response
    
    return response

if __name__ == "__main__":
    show_chatbot_page()
