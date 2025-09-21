import os
import json
from typing import List, Dict, Tuple
import streamlit as st  import openai                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        import openai
from db import get_ngos_by_capacity, save_chat_message, get_chat_history
from tensorflow.keras.models import load_model

# Load the model once at the start
try:
    model = load_model("./model.h5")
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def initialize_openai():
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        return None
    return OpenAI(api_key=api_key)

def chatbot_response(user_message: str, user_id: int) -> str:
    """
    Generate chatbot response for food donation related queries.
    
    Args:
        user_message: User's message
        user_id: User ID for conversation context
    
    Returns:
        AI-generated response
    """
    try:
        client = initialize_openai()
        if not client:
            return "Sorry, I'm currently unable to process your request. Please try again later."
        
        # Get conversation context
        chat_history = get_chat_history(user_id, limit=5)
        
        # Build conversation context
        conversation_context = ""
        for chat in chat_history[-3:]:  # Last 3 exchanges
            conversation_context += f"User: {chat['message']}\nAssistant: {chat['response']}\n\n"
        
        # System prompt for food donation context
        system_prompt = """You are FoodBridge Assistant, an AI helper for a food donation platform that connects donors with NGOs.

        Your expertise includes:
        - Food donation processes and best practices
        - Food safety and storage guidelines
        - NGO matching and coordination
        - Donation logistics and pickup procedures
        - Food quality assessment
        - Nutritional information
        - Waste reduction strategies
        - Legal aspects of food donation

        Guidelines:
        - Be helpful, friendly, and informative
        - Focus on food donation, safety, and platform features
        - Provide actionable advice
        - Encourage safe food donation practices
        - Direct users to appropriate platform features
        - Keep responses concise but comprehensive
        - If asked about topics outside food donation, politely redirect to food-related topics
        """
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation context if available
        if conversation_context:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation context:\n{conversation_context}"
            })
        
        messages.append({"role": "user", "content": user_message})
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            max_completion_tokens=500
        )
        
        ai_response = response.choices[0].message.content
        
        # Save conversation to database
        save_chat_message(user_id, user_message, ai_response)
        
        return ai_response
        
    except Exception as e:
        print(f"Error in chatbot response: {e}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again later or contact support."

def generate_donation_summary(donation_data: Dict) -> str:
    """
    Generate human-readable summary of a donation using AI.
    
    Args:
        donation_data: Dictionary containing donation details
    
    Returns:
        AI-generated donation summary
    """
    try:
        client = initialize_openai()
        if not client:
            return f"Donation of {donation_data.get('quantity')} {donation_data.get('unit')} of {donation_data.get('food_name')}"
        
        prompt = f"""Create a human-readable, engaging summary for this food donation:

        Food Name: {donation_data.get('food_name')}
        Quantity: {donation_data.get('quantity')} {donation_data.get('unit')}
        Quality: {donation_data.get('quality_prediction')}
        Expiry Date: {donation_data.get('expiry_date')}
        Description: {donation_data.get('description', 'No description provided')}
        Donor: {donation_data.get('donor_name', 'Anonymous')}

        Create a brief, positive summary (2-3 sentences) that:
        - Highlights the donation value
        - Mentions freshness/quality
        - Shows impact potential
        - Maintains professional tone
        """
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=150
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating donation summary: {e}")
        return f"Fresh donation of {donation_data.get('quantity')} {donation_data.get('unit')} {donation_data.get('food_name')} available for pickup."
def predict_food_quality(image_array):
    if model is None:
        return "Unknown"
    prediction = model.predict(image_array)  # Model returns numbers
    label = "Fresh" if prediction[0][0] > 0.5 else "Spoiled"
    return label

def suggest_best_ngo(donation_data: Dict, available_ngos: List[Dict] = []) -> Dict:
    """
    Suggest the best NGO for a donation based on various factors.
    
    Args:
        donation_data: Dictionary containing donation details
        available_ngos: List of available NGOs
    
    Returns:
        Dictionary with suggested NGO and reasoning
    """
    try:
        if not available_ngos:
            available_ngos = get_ngos_by_capacity()
        
        if not available_ngos:
            return {
                "suggested_ngo": None,
                "reasoning": "No NGOs currently available in the system.",
                "alternatives": []
            }
        
        client = initialize_openai()
        if not client:
            # Fallback to simple matching
            return simple_ngo_matching(donation_data, available_ngos)
        
        # Prepare NGO data for AI analysis
        ngos_info = []
        for ngo in available_ngos:
            ngos_info.append({
                "id": ngo["id"],
                "name": ngo["name"],
                "organization": ngo["organization"],
                "capacity": ngo["capacity"],
                "location": ngo.get("location", "Not specified"),
                "specialization": ngo.get("specialization", "General")
            })
        
        prompt = f"""Analyze this food donation and recommend the best NGO match:

        DONATION DETAILS:
        - Food: {donation_data.get('food_name')}
        - Quantity: {donation_data.get('quantity')} {donation_data.get('unit')}
        - Quality: {donation_data.get('quality_prediction')}
        - Expiry: {donation_data.get('expiry_date')}

        AVAILABLE NGOs:
        {json.dumps(ngos_info, indent=2)}

        Consider these factors:
        1. NGO capacity vs donation quantity
        2. Specialization match (if any)
        3. Location proximity (if available)
        4. Overall suitability

        Respond with JSON in this format:
        {{
            "recommended_ngo_id": number,
            "reasoning": "explanation of why this NGO is best",
            "confidence": number between 0.0 and 1.0,
            "alternative_ids": [list of 2-3 alternative NGO IDs]
        }}
        """
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=300
        )
        
        response_content = response.choices[0].message.content
        if response_content:
            result = json.loads(response_content)
        else:
            return simple_ngo_matching(donation_data, available_ngos)
        
        # Find the recommended NGO
        recommended_ngo = None
        for ngo in available_ngos:
            if ngo["id"] == result.get("recommended_ngo_id"):
                recommended_ngo = ngo
                break
        
        # Find alternatives
        alternative_ngos = []
        for alt_id in result.get("alternative_ids", []):
            for ngo in available_ngos:
                if ngo["id"] == alt_id:
                    alternative_ngos.append(ngo)
                    break
        
        return {
            "suggested_ngo": recommended_ngo,
            "reasoning": result.get("reasoning", "AI-based matching"),
            "confidence": result.get("confidence", 0.8),
            "alternatives": alternative_ngos
        }
        
    except Exception as e:
        print(f"Error in AI NGO matching: {e}")
        return simple_ngo_matching(donation_data, available_ngos)

def simple_ngo_matching(donation_data: Dict, available_ngos: List[Dict]) -> Dict:
    """
    Simple rule-based NGO matching as fallback.
    
    Args:
        donation_data: Dictionary containing donation details
        available_ngos: List of available NGOs
    
    Returns:
        Dictionary with suggested NGO and reasoning
    """
    if not available_ngos:
        return {
            "suggested_ngo": None,
            "reasoning": "No NGOs available",
            "alternatives": []
        }
    
    quantity = donation_data.get('quantity', 0)
    
    # Sort NGOs by capacity (descending)
    sorted_ngos = sorted(available_ngos, key=lambda x: x.get('capacity', 0), reverse=True)
    
    # Simple matching logic
    if quantity >= 50:  # Large donation
        suggested_ngo = sorted_ngos[0]  # Highest capacity NGO
        reasoning = "Matched with highest capacity NGO for large donation"
    elif quantity >= 20:  # Medium donation
        mid_index = len(sorted_ngos) // 2
        suggested_ngo = sorted_ngos[mid_index] if mid_index < len(sorted_ngos) else sorted_ngos[0]
        reasoning = "Matched with medium capacity NGO for moderate donation"
    else:  # Small donation
        suggested_ngo = sorted_ngos[-1]  # Smallest capacity NGO
        reasoning = "Matched with appropriate capacity NGO for small donation"
    
    alternatives = [ngo for ngo in sorted_ngos[:3] if ngo != suggested_ngo]
    
    return {
        "suggested_ngo": suggested_ngo,
        "reasoning": reasoning,
        "confidence": 0.7,
        "alternatives": alternatives
    }

def generate_insights_report(donations_data: List[Dict], time_period: str = "month") -> Dict:
    """
    Generate predictive insights and trends from donation data.
    
    Args:
        donations_data: List of donation records
        time_period: Time period for analysis
    
    Returns:
        Dictionary with insights and predictions
    """
    try:
        if not donations_data:
            return {
                "summary": "No data available for analysis",
                "trends": [],
                "predictions": [],
                "recommendations": []
            }
        
        client = initialize_openai()
        if not client:
            return generate_simple_insights(donations_data, time_period)
        
        # Prepare data summary for AI analysis
        data_summary = {
            "total_donations": len(donations_data),
            "food_types": {},
            "quality_distribution": {},
            "quantity_ranges": {},
            "donor_activity": {}
        }
        
        for donation in donations_data:
            # Food types
            food_name = donation.get('food_name', 'Unknown')
            data_summary["food_types"][food_name] = data_summary["food_types"].get(food_name, 0) + 1
            
            # Quality distribution
            quality = donation.get('quality_prediction', 'Unknown')
            data_summary["quality_distribution"][quality] = data_summary["quality_distribution"].get(quality, 0) + 1
            
            # Quantity analysis
            quantity = donation.get('quantity', 0)
            if quantity < 10:
                range_key = "small"
            elif quantity < 50:
                range_key = "medium"
            else:
                range_key = "large"
            data_summary["quantity_ranges"][range_key] = data_summary["quantity_ranges"].get(range_key, 0) + 1
        
        prompt = f"""Analyze this food donation data and provide insights:

        DATA SUMMARY for {time_period}:
        {json.dumps(data_summary, indent=2)}

        Provide analysis in JSON format:
        {{
            "key_insights": ["list of 3-4 key insights"],
            "trends": ["list of observed trends"],
            "predictions": ["list of 2-3 predictions for future"],
            "recommendations": ["list of actionable recommendations"],
            "impact_summary": "overall impact assessment"
        }}

        Focus on:
        - Donation patterns and food waste reduction
        - Quality trends and donor behavior
        - Seasonal patterns (if applicable)
        - Efficiency improvements
        - NGO matching optimization
        """
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=600
        )
        
        response_content = response.choices[0].message.content
        if response_content:
            result = json.loads(response_content)
        else:
            return generate_simple_insights(donations_data, time_period)
        
        return {
            "summary": result.get("impact_summary", "Analysis completed"),
            "insights": result.get("key_insights", []),
            "trends": result.get("trends", []),
            "predictions": result.get("predictions", []),
            "recommendations": result.get("recommendations", []),
            "data_summary": data_summary
        }
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        return generate_simple_insights(donations_data, time_period)

def generate_simple_insights(donations_data: List[Dict], time_period: str) -> Dict:
    """
    Generate simple insights without AI as fallback.
    
    Args:
        donations_data: List of donation records
        time_period: Time period for analysis
    
    Returns:
        Dictionary with basic insights
    """
    if not donations_data:
        return {
            "summary": f"No donations recorded in the selected {time_period}",
            "insights": [],
            "trends": [],
            "predictions": [],
            "recommendations": []
        }
    
    total_donations = len(donations_data)
    fresh_donations = len([d for d in donations_data if d.get('quality_prediction') == 'Fresh'])
    total_quantity = sum(d.get('quantity', 0) for d in donations_data)
    
    insights = [
        f"Total of {total_donations} donations recorded in {time_period}",
        f"{fresh_donations} donations ({(fresh_donations/total_donations)*100:.1f}%) were classified as fresh",
        f"Total food quantity: {total_quantity} units saved from waste",
        f"Average donation size: {total_quantity/total_donations:.1f} units"
    ]
    
    trends = [
        "Fresh food donations are being processed efficiently",
        "Regular donation activity indicates active user engagement"
    ]
    
    recommendations = [
        "Continue promoting fresh food donations",
        "Encourage donors to donate before expiry dates",
        "Expand NGO network for better distribution"
    ]
    
    return {
        "summary": f"Analysis of {total_donations} donations from {time_period}",
        "insights": insights,
        "trends": trends,
        "predictions": ["Continued growth in donations expected"],
        "recommendations": recommendations
    }

def generate_donation_suggestions(user_role: str, user_data: Dict = None) -> List[str]:
    """
    Generate personalized donation suggestions based on user role and data.
    
    Args:
        user_role: Role of the user (Donor, NGO, Admin)
        user_data: Additional user context
    
    Returns:
        List of personalized suggestions
    """
    suggestions = []
    
    if user_role == "Donor":
        suggestions = [
            "🍞 Consider donating bread or baked goods before closing time",
            "🥬 Fresh produce donations are always in high demand",
            "📱 Upload photos of your donations for better quality assessment",
            "⏰ Schedule regular donation pickups for consistent impact",
            "🤝 Connect with local NGOs for direct coordination"
        ]
    elif user_role == "NGO":
        suggestions = [
            "📋 Update your capacity regularly for better matching",
            "🏪 Check for fresh donations daily",
            "📞 Maintain good communication with donors",
            "📍 Update location information for efficient logistics",
            "📊 Track your impact metrics for reporting"
        ]
    elif user_role == "Admin":
        suggestions = [
            "📈 Monitor donation trends for platform improvements",
            "🔧 Optimize matching algorithms based on success rates",
            "📢 Promote the platform to increase donor base",
            "🎯 Focus on quality over quantity metrics",
            "🤖 Leverage AI insights for strategic decisions"
        ]
    
    return suggestions[:3]  # Return top 3 suggestions
