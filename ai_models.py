"""
Enhanced AI models for FoodBridge platform using deep learning.
This module provides image-based food quality prediction using MobileNet/EfficientNet.
"""

import os
import numpy as np
import cv2
from PIL import Image
import streamlit as st
from typing import Tuple, Optional
import tensorflow as tf
from tensorflow import keras
import base64
import io
import datetime

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.get_logger().setLevel('ERROR')

class FoodQualityPredictor:
    """Enhanced food quality predictor using deep learning models."""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.food_categories = [
            'Fresh', 'Slightly_Stale', 'Stale', 'Spoiled'
        ]
        
    def load_model(self):
        """Load or create the food quality prediction model."""
        try:
            # Try to load pre-trained model if exists
            model_path = "models/food_quality_model.h5"
            if os.path.exists(model_path):
                self.model = keras.models.load_model(model_path)
                st.success("✅ Pre-trained food quality model loaded successfully!")
            else:
                # Create new model based on MobileNetV2
                self.model = self._create_mobilenet_model()
                st.info("🤖 Created new MobileNet-based food quality model")
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            st.warning(f"Could not load deep learning model: {e}")
            self.model_loaded = False
            return False
    
    def _create_mobilenet_model(self):
        """Create a MobileNetV2-based model for food quality prediction."""
        
        # Load pre-trained MobileNetV2 without top layers
        base_model = keras.applications.MobileNetV2(
            weights='imagenet',
            include_top=False,
            input_shape=(224, 224, 3)
        )
        
        # Freeze base model layers
        base_model.trainable = False
        
        # Add custom classification layers
        model = keras.Sequential([
            base_model,
            keras.layers.GlobalAveragePooling2D(),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(len(self.food_categories), activation='softmax')
        ])
        
        # Compile model
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def preprocess_image(self, image_data) -> Optional[np.ndarray]:
        """Preprocess image for model prediction."""
        try:
            # Convert image data to PIL Image
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            elif hasattr(image_data, 'read'):
                # File-like object
                image = Image.open(image_data)
            else:
                image = image_data
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to model input size
            image = image.resize((224, 224))
            
            # Convert to numpy array and normalize
            img_array = np.array(image, dtype=np.float32)
            img_array = img_array / 255.0  # Normalize to [0, 1]
            
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
            
        except Exception as e:
            st.error(f"Error preprocessing image: {e}")
            return None
    
    def predict_quality(self, image_data, food_name: str = "") -> Tuple[str, float, dict]:
        """
        Predict food quality from image using deep learning.
        
        Args:
            image_data: Image data (PIL Image, bytes, or file-like object)
            food_name: Name of the food item for context
            
        Returns:
            Tuple of (prediction, confidence, detailed_results)
        """
        
        # Load model if not loaded
        if not self.model_loaded:
            if not self.load_model():
                return self._fallback_prediction(food_name)
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_data)
            if processed_image is None:
                return self._fallback_prediction(food_name)
            
            # Make prediction
            predictions = self.model.predict(processed_image, verbose=0)
            
            # Get prediction results
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            predicted_quality = self.food_categories[predicted_class_idx]
            
            # Map to simplified categories
            quality_mapping = {
                'Fresh': 'Fresh',
                'Slightly_Stale': 'Expires Soon',
                'Stale': 'Expires Today',
                'Spoiled': 'Expired'
            }
            
            final_quality = quality_mapping.get(predicted_quality, 'Unknown')
            
            # Create detailed results
            detailed_results = {
                'raw_predictions': {
                    self.food_categories[i]: float(predictions[0][i]) 
                    for i in range(len(self.food_categories))
                },
                'predicted_class': predicted_quality,
                'food_name': food_name,
                'model_type': 'MobileNetV2',
                'analysis_timestamp': datetime.datetime.now().isoformat()
            }
            
            return final_quality, confidence, detailed_results
            
        except Exception as e:
            st.warning(f"Deep learning prediction failed: {e}")
            return self._fallback_prediction(food_name)
    
    def _fallback_prediction(self, food_name: str) -> Tuple[str, float, dict]:
        """Fallback prediction when deep learning model fails."""
        
        # Simple heuristic based on food name
        fresh_keywords = ['fresh', 'new', 'crisp', 'ripe']
        spoiled_keywords = ['old', 'stale', 'moldy', 'rotten']
        
        food_lower = food_name.lower()
        
        if any(keyword in food_lower for keyword in fresh_keywords):
            prediction = 'Fresh'
            confidence = 0.7
        elif any(keyword in food_lower for keyword in spoiled_keywords):
            prediction = 'Expired'
            confidence = 0.8
        else:
            prediction = 'Fresh'  # Default to fresh for safety
            confidence = 0.6
        
        detailed_results = {
            'fallback_reason': 'Deep learning model unavailable',
            'heuristic_based': True,
            'food_name': food_name,
            'analysis_timestamp': datetime.datetime.now().isoformat()
        }
        
        return prediction, confidence, detailed_results
    
    def analyze_food_features(self, image_data) -> dict:
        """
        Analyze visual features of food image.
        
        Args:
            image_data: Image data
            
        Returns:
            Dictionary with visual analysis results
        """
        try:
            # Preprocess image for analysis
            processed_image = self.preprocess_image(image_data)
            if processed_image is None:
                return {}
            
            # Convert back to uint8 for OpenCV operations
            cv_image = (processed_image[0] * 255).astype(np.uint8)
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # Color analysis
            mean_color = np.mean(cv_image, axis=(0, 1))
            
            # Brightness analysis
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Texture analysis (simplified)
            edges = cv2.Canny(gray, 50, 150)
            texture_score = np.sum(edges) / (edges.shape[0] * edges.shape[1])
            
            # Color distribution
            hist_b = cv2.calcHist([cv_image], [0], None, [256], [0, 256])
            hist_g = cv2.calcHist([cv_image], [1], None, [256], [0, 256])
            hist_r = cv2.calcHist([cv_image], [2], None, [256], [0, 256])
            
            # Detect potential spoilage indicators
            spoilage_indicators = self._detect_spoilage_indicators(cv_image)
            
            return {
                'mean_color': {
                    'blue': float(mean_color[0]),
                    'green': float(mean_color[1]),
                    'red': float(mean_color[2])
                },
                'brightness': float(brightness),
                'texture_score': float(texture_score),
                'spoilage_indicators': spoilage_indicators,
                'color_distribution': {
                    'blue_variance': float(np.var(hist_b)),
                    'green_variance': float(np.var(hist_g)),
                    'red_variance': float(np.var(hist_r))
                }
            }
            
        except Exception as e:
            st.warning(f"Feature analysis failed: {e}")
            return {}
    
    def _detect_spoilage_indicators(self, cv_image) -> dict:
        """Detect visual indicators of food spoilage."""
        
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        
        # Detect dark spots (potential mold/spoilage)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        dark_threshold = np.percentile(gray, 10)  # Bottom 10% of brightness
        dark_spots = np.sum(gray < dark_threshold)
        dark_percentage = (dark_spots / (gray.shape[0] * gray.shape[1])) * 100
        
        # Detect brown/yellow discoloration
        brown_lower = np.array([10, 50, 50])
        brown_upper = np.array([30, 255, 200])
        brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
        brown_percentage = (np.sum(brown_mask > 0) / (brown_mask.shape[0] * brown_mask.shape[1])) * 100
        
        # Detect unusual color variations
        color_std = np.std(cv_image, axis=(0, 1))
        color_variation = np.mean(color_std)
        
        return {
            'dark_spots_percentage': float(dark_percentage),
            'brown_discoloration_percentage': float(brown_percentage),
            'color_variation': float(color_variation),
            'potential_spoilage': dark_percentage > 15 or brown_percentage > 20
        }

# Global instance
food_quality_predictor = FoodQualityPredictor()

def predict_food_quality_enhanced(image_data, food_name: str = "", expiry_date: str = "") -> Tuple[str, float, dict]:
    """
    Enhanced food quality prediction combining deep learning and rule-based methods.
    
    Args:
        image_data: Image data for visual analysis
        food_name: Name of the food item
        expiry_date: Expiry date for additional context
        
    Returns:
        Tuple of (prediction, confidence, analysis_details)
    """
    
    # Rule-based prediction from expiry date
    rule_based_prediction = "Fresh"
    rule_confidence = 0.8
    
    if expiry_date:
        try:
            expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
            today = datetime.date.today()
            days_until_expiry = (expiry - today).days
            
            if days_until_expiry < 0:
                rule_based_prediction = "Expired"
                rule_confidence = 0.95
            elif days_until_expiry == 0:
                rule_based_prediction = "Expires Today"
                rule_confidence = 0.85
            elif days_until_expiry <= 2:
                rule_based_prediction = "Expires Soon"
                rule_confidence = 0.80
            else:
                rule_based_prediction = "Fresh"
                rule_confidence = 0.90
        except:
            pass
    
    # Image-based prediction
    if image_data:
        image_prediction, image_confidence, image_details = food_quality_predictor.predict_quality(
            image_data, food_name
        )
        
        # Visual feature analysis
        visual_features = food_quality_predictor.analyze_food_features(image_data)
        
        # Combine predictions
        if rule_based_prediction == "Expired" or image_prediction == "Expired":
            final_prediction = "Expired"
            final_confidence = max(rule_confidence, image_confidence)
        elif rule_based_prediction == "Fresh" and image_prediction == "Fresh":
            final_prediction = "Fresh"
            final_confidence = (rule_confidence + image_confidence) / 2
        else:
            # Take the more conservative prediction
            if rule_based_prediction in ["Expires Soon", "Expires Today"] or \
               image_prediction in ["Expires Soon", "Expires Today"]:
                final_prediction = "Expires Soon"
                final_confidence = (rule_confidence + image_confidence) / 2
            else:
                final_prediction = image_prediction
                final_confidence = image_confidence
        
        # Fix days_until_expiry calculation
        days_until_expiry = None
        if expiry_date:
            try:
                expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
                today = datetime.date.today()
                days_until_expiry = (expiry - today).days
            except:
                pass
        
        analysis_details = {
            'combined_approach': True,
            'rule_based': {
                'prediction': rule_based_prediction,
                'confidence': rule_confidence,
                'days_until_expiry': days_until_expiry
            },
            'image_based': {
                'prediction': image_prediction,
                'confidence': image_confidence,
                'details': image_details
            },
            'visual_features': visual_features,
            'final_prediction': final_prediction,
            'final_confidence': final_confidence
        }
        
    else:
        # No image provided, use rule-based only
        final_prediction = rule_based_prediction
        final_confidence = rule_confidence
        
        analysis_details = {
            'rule_based': {
                'prediction': rule_based_prediction,
                'confidence': rule_confidence
            },
            'image_based': None,
            'combined_approach': False,
            'note': 'No image provided, using expiry date analysis only'
        }
    
    return final_prediction, final_confidence, analysis_details

def get_quality_recommendations(prediction: str, confidence: float, analysis_details: dict, food_name: str) -> list:
    """Get specific recommendations based on quality analysis."""
    
    recommendations = []
    
    if prediction == "Expired":
        recommendations.extend([
            "⚠️ Do not donate this food item - it appears to be expired",
            "🗑️ Dispose of safely to prevent foodborne illness",
            "📋 Check storage conditions to prevent future spoilage"
        ])
    elif prediction == "Expires Today":
        recommendations.extend([
            "⏰ Urgent donation - use today only",
            "🧊 Ensure cold chain maintenance during transport",
            "📞 Contact NGOs immediately for quick pickup"
        ])
    elif prediction == "Expires Soon":
        recommendations.extend([
            "📅 Priority donation - use within 1-2 days",
            "❄️ Keep refrigerated until pickup",
            "🏃 Schedule pickup as soon as possible"
        ])
    else:  # Fresh
        recommendations.extend([
            "✅ Excellent for donation - food appears fresh",
            "📦 Maintain proper storage conditions",
            "🤝 Good candidate for NGO matching"
        ])
    
    # Add confidence-based recommendations
    if confidence < 0.7:
        recommendations.append("🔍 Manual inspection recommended due to lower confidence score")
    
    # Add food-specific recommendations
    food_lower = food_name.lower()
    if any(item in food_lower for item in ['meat', 'fish', 'dairy']):
        recommendations.append("🌡️ Extra care needed - perishable protein item")
    elif any(item in food_lower for item in ['fruits', 'vegetables']):
        recommendations.append("🥬 Check for bruising or soft spots before donation")
    
    # Add visual analysis recommendations
    if analysis_details.get('visual_features', {}).get('spoilage_indicators', {}).get('potential_spoilage'):
        recommendations.append("👀 Visual analysis detected potential spoilage signs - inspect carefully")
    
    return recommendations