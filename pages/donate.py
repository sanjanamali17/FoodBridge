import streamlit as st
import datetime
from model import predict_food_quality, get_food_safety_tips, calculate_nutritional_impact, get_storage_recommendations
from db import create_donation
from utils import save_uploaded_image, get_units_list, show_success_message, show_error_message
from ai_features import generate_donation_summary, suggest_best_ngo

def show_donate_page():
    """Display the food donation page."""
    st.title("🍲 Donate Food")
    
    # Check if user is logged in and is a donor or admin
    if not st.session_state.get('logged_in', False):
        st.error("Please login to donate food.")
        return
    
    if st.session_state.user_role not in ['Donor', 'Admin']:
        st.error("Only Donors and Admins can access this page.")
        return
    
    st.markdown("### Help reduce food waste by donating fresh food to those in need!")
    
    # Donation form
    with st.form("donation_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Food Details")
            
            # Basic food information
            food_name = st.text_input(
                "Food Name*",
                placeholder="e.g., Fresh Bread, Cooked Rice, Mixed Vegetables",
                help="Enter the name of the food item you want to donate"
            )
            
            # Quantity and unit
            col_qty, col_unit = st.columns([1, 1])
            with col_qty:
                quantity = st.number_input(
                    "Quantity*",
                    min_value=1,
                    value=1,
                    help="Enter the quantity of food"
                )
            
            with col_unit:
                unit = st.selectbox(
                    "Unit*",
                    get_units_list(),
                    help="Select the unit of measurement"
                )
            
            # Expiry date
            expiry_date = st.date_input(
                "Expiry Date*",
                min_value=datetime.date.today(),
                value=datetime.date.today() + datetime.timedelta(days=3),
                help="Select the expiry date of the food item"
            )
            
            # Description
            description = st.text_area(
                "Description (Optional)",
                placeholder="Additional details about the food item, storage conditions, ingredients, etc.",
                help="Provide any additional information that might be helpful"
            )
        
        with col2:
            st.subheader("Additional Information")
            
            # Image upload
            uploaded_image = st.file_uploader(
                "Upload Food Image (Optional)",
                type=['png', 'jpg', 'jpeg'],
                help="Upload a clear image of the food item for quality assessment"
            )
            
            if uploaded_image:
                st.image(uploaded_image, caption="Food Image Preview", width=200)
            
            # Special instructions
            st.markdown("#### Special Notes")
            special_handling = st.checkbox("Requires special handling")
            refrigeration_needed = st.checkbox("Needs refrigeration")
            allergen_info = st.text_input("Allergen Information", placeholder="Contains nuts, dairy, etc.")
        
        # Form submission
        col_submit, col_cancel = st.columns([1, 1])
        
        with col_submit:
            submitted = st.form_submit_button("🚀 Donate Food", type="primary")
        
        with col_cancel:
            if st.form_submit_button("🗑️ Clear Form"):
                st.rerun()
    
    # Process form submission
    if submitted:
        # Validation
        if not food_name or not quantity or not unit:
            show_error_message("Please fill in all required fields marked with *")
            return
        
        # Save uploaded image if provided
        image_path = None
        if uploaded_image:
            try:
                image_path = save_uploaded_image(uploaded_image)
                st.success("✅ Image uploaded successfully!")
            except Exception as e:
                st.warning(f"Failed to upload image: {e}")
        
        # Predict food quality
        with st.spinner("🤖 Analyzing food quality..."):
            try:
                # Show AI model status
                from model import ENHANCED_AI_AVAILABLE
                if ENHANCED_AI_AVAILABLE and uploaded_image:
                    st.info("🧠 Using enhanced deep learning analysis with MobileNet")
                elif uploaded_image:
                    st.info("📊 Using basic analysis (enhanced AI unavailable)")
                else:
                    st.info("📅 Using date-based analysis (no image provided)")
                
                quality_prediction, confidence = predict_food_quality(
                    expiry_date=str(expiry_date),
                    food_name=food_name,
                    image_data=uploaded_image
                )
                
                st.success(f"✅ Quality Assessment Complete!")
                
                # Display quality prediction
                col_qual1, col_qual2 = st.columns(2)
                with col_qual1:
                    st.metric("Predicted Quality", quality_prediction)
                with col_qual2:
                    st.metric("Confidence", f"{confidence*100:.1f}%")
                
            except Exception as e:
                st.error(f"Error in quality prediction: {e}")
                quality_prediction, confidence = "Unknown", 0.5
        
        # Save donation to database
        try:
            # Prepare additional info
            additional_notes = []
            if special_handling:
                additional_notes.append("Requires special handling")
            if refrigeration_needed:
                additional_notes.append("Needs refrigeration")
            if allergen_info:
                additional_notes.append(f"Allergens: {allergen_info}")
            
            final_description = description
            if additional_notes:
                final_description += " | " + " | ".join(additional_notes)
            
            donation_id = create_donation(
                donor_id=st.session_state.user_id,
                food_name=food_name,
                quantity=quantity,
                unit=unit,
                expiry_date=str(expiry_date),
                description=final_description,
                quality_prediction=quality_prediction,
                quality_confidence=confidence,
                image_path=image_path or ""
            )
            
            # Send notifications to matching NGOs
            if donation_id and quality_prediction in ["Fresh", "Expires Soon", "Expires Today"]:
                try:
                    from notifications import get_donation_notification_service
                    
                    # Get NGO recommendations for notifications
                    donation_data = {
                        'id': donation_id,
                        'food_name': food_name,
                        'quantity': quantity,
                        'unit': unit,
                        'quality_prediction': quality_prediction,
                        'expiry_date': str(expiry_date),
                        'description': final_description,
                        'donor_name': st.session_state.get('user_name', 'Anonymous')
                    }
                    
                    # Get matching NGOs
                    ngo_suggestion = suggest_best_ngo(donation_data)
                    matching_ngos = []
                    
                    if ngo_suggestion.get('suggested_ngo'):
                        matching_ngos.append(ngo_suggestion['suggested_ngo'])
                    
                    if ngo_suggestion.get('alternatives'):
                        matching_ngos.extend(ngo_suggestion['alternatives'][:2])  # Top 2 alternatives
                    
                    # Send notifications
                    if matching_ngos:
                        notification_service = get_donation_notification_service()
                        notification_ids = notification_service.notify_new_donation(
                            donation_data, matching_ngos
                        )
                        
                        if notification_ids:
                            st.success(f"✉️ Notified {len(notification_ids)} NGO{'s' if len(notification_ids) != 1 else ''} about your donation!")
                
                except Exception as e:
                    st.warning(f"Donation created successfully, but notification delivery failed: {e}")
            
            st.success("🎉 Food donation created successfully!")
            
            # Display enhanced quality analysis if available
            if hasattr(st.session_state, 'last_analysis_details') and st.session_state.last_analysis_details:
                st.markdown("### 🤖 Enhanced AI Quality Analysis")
                
                analysis = st.session_state.last_analysis_details
                
                # Show combined analysis results
                if analysis.get('combined_approach'):
                    col_rule, col_image = st.columns(2)
                    
                    with col_rule:
                        st.markdown("#### 📅 Date-Based Analysis")
                        rule_data = analysis.get('rule_based', {})
                        st.metric("Prediction", rule_data.get('prediction', 'Unknown'))
                        st.metric("Confidence", f"{rule_data.get('confidence', 0)*100:.1f}%")
                    
                    with col_image:
                        st.markdown("#### 🖼️ Image-Based Analysis")
                        image_data = analysis.get('image_based', {})
                        st.metric("Prediction", image_data.get('prediction', 'Unknown'))
                        st.metric("Confidence", f"{image_data.get('confidence', 0)*100:.1f}%")
                    
                    # Visual features analysis
                    visual_features = analysis.get('visual_features', {})
                    if visual_features:
                        st.markdown("#### 👁️ Visual Analysis")
                        
                        spoilage = visual_features.get('spoilage_indicators', {})
                        if spoilage.get('potential_spoilage'):
                            st.warning("⚠️ Visual analysis detected potential spoilage indicators")
                        else:
                            st.success("✅ No obvious spoilage indicators detected")
                        
                        # Show detailed metrics in an expander
                        with st.expander("🔍 Detailed Visual Metrics"):
                            st.write(f"**Brightness:** {visual_features.get('brightness', 0):.1f}")
                            st.write(f"**Texture Score:** {visual_features.get('texture_score', 0):.4f}")
                            st.write(f"**Dark Spots:** {spoilage.get('dark_spots_percentage', 0):.1f}%")
                            st.write(f"**Color Variation:** {spoilage.get('color_variation', 0):.2f}")
                
                # Generate and show recommendations
                try:
                    from ai_models import get_quality_recommendations
                    recommendations = get_quality_recommendations(
                        quality_prediction, confidence, analysis, food_name
                    )
                    
                    if recommendations:
                        st.markdown("#### 💡 AI Recommendations")
                        for rec in recommendations:
                            st.info(rec)
                            
                except ImportError:
                    pass
            
            # Display donation summary
            st.markdown("### 📋 Donation Summary")
            
            donation_data = {
                'food_name': food_name,
                'quantity': quantity,
                'unit': unit,
                'quality_prediction': quality_prediction,
                'expiry_date': str(expiry_date),
                'description': final_description,
                'donor_name': st.session_state.user_name
            }
            
            # Generate AI summary
            with st.spinner("✨ Generating donation summary..."):
                try:
                    ai_summary = generate_donation_summary(donation_data)
                    st.info(f"**AI Summary:** {ai_summary}")
                except Exception as e:
                    st.warning("Could not generate AI summary")
            
            # Show food safety tips
            safety_tips = get_food_safety_tips(food_name, quality_prediction)
            if safety_tips:
                st.markdown("#### 🛡️ Food Safety Guidelines")
                st.info(safety_tips)
            
            # Show storage recommendations
            storage_tips = get_storage_recommendations(food_name, str(expiry_date))
            if storage_tips:
                st.markdown("#### 📦 Storage Recommendations")
                st.info(storage_tips)
            
            # Calculate nutritional impact
            nutritional_impact = calculate_nutritional_impact(food_name, quantity, unit)
            
            st.markdown("#### 🎯 Estimated Impact")
            impact_col1, impact_col2, impact_col3, impact_col4 = st.columns(4)
            
            with impact_col1:
                st.metric("Calories", f"{nutritional_impact['estimated_calories']:,}")
            with impact_col2:
                st.metric("Protein (g)", nutritional_impact['estimated_protein'])
            with impact_col3:
                st.metric("Carbs (g)", nutritional_impact['estimated_carbs'])
            with impact_col4:
                st.metric("Meals Served", nutritional_impact['meals_served'])
            
            # Suggest best NGO match
            if quality_prediction == "Fresh":
                with st.spinner("🎯 Finding best NGO match..."):
                    try:
                        ngo_suggestion = suggest_best_ngo(donation_data)
                        
                        if ngo_suggestion['suggested_ngo']:
                            st.markdown("#### 🏢 Recommended NGO Match")
                            recommended_ngo = ngo_suggestion['suggested_ngo']
                            
                            st.success(f"**{recommended_ngo['name']}** ({recommended_ngo['organization']})")
                            st.write(f"**Reasoning:** {ngo_suggestion['reasoning']}")
                            st.write(f"**Capacity:** {recommended_ngo['capacity']} units")
                            
                            if ngo_suggestion.get('alternatives'):
                                st.markdown("**Alternative NGOs:**")
                                for alt_ngo in ngo_suggestion['alternatives']:
                                    st.write(f"• {alt_ngo['name']} (Capacity: {alt_ngo['capacity']})")
                    
                    except Exception as e:
                        st.warning("Could not generate NGO recommendations at this time")
            
            # Show next steps
            st.markdown("### ✅ Next Steps")
            st.markdown("""
            1. **NGOs will be notified** of your fresh donation
            2. **Interested NGOs can request pickup** through the platform
            3. **You'll be contacted** for coordination once a request is made
            4. **Track your donation impact** through your dashboard
            """)
            
            # Clear form after successful submission
            if st.button("🆕 Make Another Donation"):
                st.rerun()
        
        except Exception as e:
            st.error(f"Error creating donation: {e}")
    
    # Show donation tips
    st.markdown("---")
    st.markdown("### 💡 Donation Tips")
    
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.markdown("""
        **Before Donating:**
        - ✅ Check expiry dates carefully
        - ✅ Ensure food is properly stored
        - ✅ Take clear photos for assessment
        - ✅ Provide accurate descriptions
        """)
    
    with tips_col2:
        st.markdown("""
        **Food Safety:**
        - 🛡️ Only donate safe, edible food
        - 🧊 Maintain cold chain for perishables  
        - 📦 Use proper packaging
        - 🏷️ Label allergen information clearly
        """)
    
    # Show recent user donations
    st.markdown("---")
    st.markdown("### 📊 Your Recent Donations")
    
    from db import get_user_donations
    user_donations = get_user_donations(st.session_state.user_id)
    
    if user_donations:
        # Show last 5 donations
        for donation in user_donations[:5]:
            with st.expander(f"{donation['food_name']} - {donation['created_at'][:10]}"):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write(f"**Quantity:** {donation['quantity']} {donation['unit']}")
                    st.write(f"**Quality:** {donation['quality_prediction']}")
                    st.write(f"**Status:** {donation['status']}")
                
                with col_info2:
                    st.write(f"**Expiry Date:** {donation['expiry_date']}")
                    st.write(f"**Created:** {donation['created_at'][:16]}")
                    if donation['description']:
                        st.write(f"**Notes:** {donation['description']}")
    else:
        st.info("No previous donations found. This will be your first donation! 🎉")

if __name__ == "__main__":
    show_donate_page()
