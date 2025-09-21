import datetime
from typing import Tuple, Dict
import streamlit as st
from PIL import Image
import os
import base64
import io

# Import enhanced AI models
try:
    from ai_models import predict_food_quality_enhanced
    ENHANCED_AI_AVAILABLE = True
except ImportError:
    ENHANCED_AI_AVAILABLE = False


def predict_food_quality(expiry_date: str,
                         food_name: str = "",
                         image_data=None) -> Tuple[str, float]:
    """
    Predict food quality based on expiry date and optional image analysis.
    Now enhanced with deep learning capabilities when available.
    
    Args:
        expiry_date: Expiry date in YYYY-MM-DD format
        food_name: Name of the food item
        image_data: Optional image data for analysis
    
    Returns:
        Tuple of (prediction, confidence_score)
    """

    # Use enhanced AI model if available
    if ENHANCED_AI_AVAILABLE and image_data:
        try:
            prediction, confidence, analysis_details = predict_food_quality_enhanced(
                image_data, food_name, expiry_date)

            # Store analysis details in session state for display
            if 'last_analysis_details' not in st.session_state:
                st.session_state.last_analysis_details = {}
            st.session_state.last_analysis_details = analysis_details

            return prediction, confidence

        except Exception as e:
            st.warning(
                f"Enhanced AI analysis failed, falling back to basic analysis: {e}"
            )
            # Fall through to basic analysis

    # Basic analysis (original implementation)
    try:
        # Rule-based prediction using expiry date
        expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
        today = datetime.date.today()
        days_until_expiry = (expiry - today).days

        # Basic rule-based logic
        if days_until_expiry < 0:
            prediction = "Expired"
            confidence = 0.95
        elif days_until_expiry == 0:
            prediction = "Expires Today"
            confidence = 0.85
        elif days_until_expiry <= 2:
            prediction = "Expires Soon"
            confidence = 0.80
        else:
            prediction = "Fresh"
            confidence = 0.90

        # Adjust confidence based on food type
        if food_name:
            perishable_foods = [
                'milk', 'fish', 'meat', 'dairy', 'yogurt', 'cheese'
            ]
            semi_perishable = ['bread', 'fruits', 'vegetables', 'eggs']

            food_lower = food_name.lower()

            if any(item in food_lower for item in perishable_foods):
                # More strict for perishable items
                if days_until_expiry <= 1 and prediction == "Fresh":
                    prediction = "Expires Soon"
                    confidence = 0.75
            elif any(item in food_lower for item in semi_perishable):
                # Moderate for semi-perishable
                confidence = min(confidence, 0.85)
            else:
                # Less strict for non-perishable items
                if prediction == "Expires Soon" and days_until_expiry >= 1:
                    prediction = "Fresh"
                    confidence = 0.80

        # Optional: Image analysis using OpenAI (if image provided)
        if image_data and os.getenv("OPENAI_API_KEY"):
            try:
                image_prediction, image_confidence = analyze_food_image(
                    image_data, food_name)
                # Combine predictions (weighted average)
                if image_prediction == "Fresh" and prediction in [
                        "Fresh", "Expires Soon"
                ]:
                    prediction = "Fresh"
                    confidence = (confidence * 0.6 + image_confidence * 0.4)
                elif image_prediction == "Expired":
                    prediction = "Expired"
                    confidence = max(confidence, image_confidence)
            except Exception as e:
                print(f"Image analysis failed: {e}")

        return prediction, round(confidence, 2)

    except Exception as e:
        print(f"Error in food quality prediction: {e}")
        return "Unknown", 0.5


def analyze_food_image(image_data, food_name: str = "") -> Tuple[str, float]:
    """
    Analyze food image using OpenAI Vision API.
    
    Args:
        image_data: Image data (PIL Image or bytes)
        food_name: Optional food name for context
    
    Returns:
        Tuple of (prediction, confidence_score)
    """
    try:
        from openai import OpenAI
        import json

        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return "Unknown", 0.5

        client = OpenAI(api_key=openai_api_key)

        # Convert image to base64
        if isinstance(image_data, Image.Image):
            buffered = io.BytesIO()
            image_data.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
        else:
            img_bytes = image_data

        img_base64 = base64.b64encode(img_bytes).decode()

        # Prepare prompt
        food_context = f" The food item is: {food_name}." if food_name else ""

        prompt = f"""Analyze this food image and determine its freshness quality.{food_context}
        
        Look for signs of:
        - Freshness: bright colors, firm texture, no discoloration
        - Spoilage: dark spots, mold, wilting, discoloration, unusual texture
        - Overall condition and safety for consumption
        
        Respond with JSON in this exact format:
        {{
            "prediction": "Fresh" or "Expired" or "Expires Soon",
            "confidence": number between 0.0 and 1.0,
            "reasoning": "brief explanation of your assessment"
        }}"""

        # Make API call
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{
                "role":
                "user",
                "content": [{
                    "type": "text",
                    "text": prompt
                }, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                }]
            }],
            response_format={"type": "json_object"},
            max_completion_tokens=500)

        # Parse response
        response_content = response.choices[0].message.content
        if response_content:
            result = json.loads(response_content)
            prediction = result.get("prediction", "Unknown")
            confidence = float(result.get("confidence", 0.5))
        else:
            prediction = "Unknown"
            confidence = 0.5

        return prediction, confidence

    except Exception as e:
        print(f"Error in image analysis: {e}")
        return "Unknown", 0.5


def get_food_safety_tips(food_name: str, prediction: str) -> str:
    """
    Get food safety tips based on food type and prediction.
    
    Args:
        food_name: Name of the food item
        prediction: Quality prediction (Fresh, Expires Soon, Expired)
    
    Returns:
        Safety tips string
    """
    tips = []

    if prediction == "Expired":
        tips.append("⚠️ This food item appears to be expired. Do not consume.")
        tips.append("🗑️ Dispose of safely to avoid health risks.")
        return " ".join(tips)

    if prediction == "Expires Soon":
        tips.append(
            "⏰ This food expires soon. Use immediately or preserve properly.")

    # Food-specific tips
    food_lower = food_name.lower() if food_name else ""

    if any(item in food_lower
           for item in ['milk', 'dairy', 'yogurt', 'cheese']):
        tips.append("🥛 Keep refrigerated at all times.")
        tips.append("👃 Check for unusual smell before consuming.")
    elif any(item in food_lower for item in ['meat', 'chicken', 'fish']):
        tips.append("🍖 Ensure proper refrigeration and cook thoroughly.")
        tips.append("🌡️ Check internal temperature when cooking.")
    elif any(item in food_lower for item in ['bread', 'baked goods']):
        tips.append("🍞 Store in cool, dry place.")
        tips.append("👀 Check for mold before consuming.")
    elif any(item in food_lower for item in ['fruits', 'vegetables']):
        tips.append(
            "🥬 Store properly - some need refrigeration, others room temperature."
        )
        tips.append("🧽 Wash thoroughly before consumption.")
    else:
        tips.append("📦 Store according to package instructions.")
        tips.append("👀 Check for any visible signs of spoilage.")

    return " ".join(
        tips) if tips else "Store properly and consume before expiry date."


def calculate_nutritional_impact(food_name: str, quantity: int,
                                 unit: str) -> Dict:
    """
    Estimate nutritional impact of donated food.
    
    Args:
        food_name: Name of the food item
        quantity: Quantity of food
        unit: Unit of measurement
    
    Returns:
        Dictionary with estimated nutritional values
    """
    # Basic nutritional database (simplified)
    nutrition_db = {
        'rice': {
            'calories_per_100g': 130,
            'protein_per_100g': 2.7,
            'carbs_per_100g': 28
        },
        'bread': {
            'calories_per_100g': 265,
            'protein_per_100g': 9,
            'carbs_per_100g': 49
        },
        'milk': {
            'calories_per_100ml': 42,
            'protein_per_100ml': 3.4,
            'carbs_per_100ml': 5
        },
        'chicken': {
            'calories_per_100g': 165,
            'protein_per_100g': 31,
            'carbs_per_100g': 0
        },
        'vegetables': {
            'calories_per_100g': 25,
            'protein_per_100g': 3,
            'carbs_per_100g': 5
        },
        'fruits': {
            'calories_per_100g': 50,
            'protein_per_100g': 1,
            'carbs_per_100g': 13
        }
    }

    # Find matching food category
    food_lower = food_name.lower() if food_name else ""
    nutrition_data = None

    for category, data in nutrition_db.items():
        if category in food_lower:
            nutrition_data = data
            break

    # Default values if no match found
    if not nutrition_data:
        nutrition_data = {
            'calories_per_100g': 200,
            'protein_per_100g': 5,
            'carbs_per_100g': 20
        }

    # Convert quantity to grams/ml
    quantity_in_base_unit = quantity
    if unit.lower() in ['kg', 'kilograms']:
        quantity_in_base_unit *= 1000
    elif unit.lower() in ['l', 'liters', 'litres']:
        quantity_in_base_unit *= 1000

    # Calculate nutritional values
    multiplier = quantity_in_base_unit / 100

    estimated_calories = int(
        nutrition_data.get('calories_per_100g', 0) * multiplier)
    estimated_protein = round(
        nutrition_data.get('protein_per_100g', 0) * multiplier, 1)
    estimated_carbs = round(
        nutrition_data.get('carbs_per_100g', 0) * multiplier, 1)

    # Estimate meals served (assuming 500 calories per meal)
    meals_served = max(1, estimated_calories // 500)

    return {
        'estimated_calories': estimated_calories,
        'estimated_protein': estimated_protein,
        'estimated_carbs': estimated_carbs,
        'meals_served': meals_served
    }


def get_storage_recommendations(food_name: str, expiry_date: str) -> str:
    """
    Get storage recommendations for food items.
    
    Args:
        food_name: Name of the food item
        expiry_date: Expiry date string
    
    Returns:
        Storage recommendations string
    """
    food_lower = food_name.lower() if food_name else ""

    # Calculate days until expiry
    try:
        expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
        today = datetime.date.today()
        days_until_expiry = (expiry - today).days
    except:
        days_until_expiry = 0

    recommendations = []

    # Temperature recommendations
    if any(item in food_lower
           for item in ['milk', 'dairy', 'yogurt', 'cheese', 'meat', 'fish']):
        recommendations.append("🧊 Keep refrigerated (0-4°C)")
    elif any(item in food_lower for item in ['fruits', 'vegetables']):
        recommendations.append("🥗 Store in cool, dry place or refrigerate")
    else:
        recommendations.append(
            "🏠 Store in cool, dry place away from direct sunlight")

    # Urgency recommendations
    if days_until_expiry <= 1:
        recommendations.append("⚡ Use immediately or freeze if possible")
    elif days_until_expiry <= 3:
        recommendations.append("⏰ Priority item - use within next few days")

    # Container recommendations
    recommendations.append(
        "📦 Keep in original packaging or airtight container")

    return " | ".join(recommendations)
