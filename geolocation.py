"""
Geolocation-based NGO matching system for FoodBridge platform.
Provides proximity-based recommendations and distance calculations.
"""

import streamlit as st
import math
from typing import List, Dict, Tuple, Optional
import sqlite3
from db import get_db_connection
import json

class GeoLocationService:
    """Service for handling geolocation and proximity calculations."""
    
    def __init__(self):
        self.init_location_tables()
    
    def init_location_tables(self):
        """Initialize location-related database tables."""
        conn = get_db_connection()
        try:
            # Add location columns to existing tables if they don't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    address TEXT,
                    city TEXT,
                    postal_code TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id)
                )
            """)
            
            # Create index for efficient proximity queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_locations_coords 
                ON user_locations (latitude, longitude)
            """)
            
            conn.commit()
        except Exception as e:
            st.error(f"Error initializing location tables: {e}")
        finally:
            conn.close()
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        
        return c * r
    
    def save_user_location(
        self, 
        user_id: int, 
        latitude: float, 
        longitude: float, 
        address: str = "", 
        city: str = "", 
        postal_code: str = ""
    ) -> bool:
        """Save or update user location."""
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO user_locations 
                (user_id, latitude, longitude, address, city, postal_code, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, latitude, longitude, address, city, postal_code,
                st.session_state.get('current_timestamp', '2024-01-01T00:00:00')
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            st.error(f"Error saving location: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_location(self, user_id: int) -> Optional[Dict]:
        """Get user location data."""
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT latitude, longitude, address, city, postal_code, updated_at
                FROM user_locations 
                WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'latitude': row[0],
                    'longitude': row[1],
                    'address': row[2],
                    'city': row[3],
                    'postal_code': row[4],
                    'updated_at': row[5]
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting user location: {e}")
            return None
        finally:
            conn.close()
    
    def find_nearby_ngos(
        self, 
        donor_latitude: float, 
        donor_longitude: float, 
        max_distance_km: float = 50,
        min_capacity: int = 1
    ) -> List[Dict]:
        """
        Find NGOs within specified distance from donor location.
        
        Args:
            donor_latitude: Donor's latitude
            donor_longitude: Donor's longitude
            max_distance_km: Maximum distance in kilometers
            min_capacity: Minimum NGO capacity required
            
        Returns:
            List of NGOs with distance information
        """
        conn = get_db_connection()
        try:
            # Get NGOs with location data
            cursor = conn.execute("""
                SELECT u.id, u.name, u.email, ul.latitude, ul.longitude, ul.address, ul.city,
                       COALESCE(u.capacity, 10) as capacity
                FROM users u
                JOIN user_locations ul ON u.id = ul.user_id
                WHERE u.role = 'NGO' 
                AND u.capacity >= ?
            """, (min_capacity,))
            
            ngos_with_distance = []
            
            for row in cursor.fetchall():
                ngo_lat, ngo_lon = row[3], row[4]
                distance = self.calculate_distance(
                    donor_latitude, donor_longitude, ngo_lat, ngo_lon
                )
                
                if distance <= max_distance_km:
                    ngos_with_distance.append({
                        'id': row[0],
                        'name': row[1],
                        'email': row[2],
                        'latitude': ngo_lat,
                        'longitude': ngo_lon,
                        'address': row[5],
                        'city': row[6],
                        'capacity': row[7],
                        'distance_km': round(distance, 2),
                        'proximity_score': self._calculate_proximity_score(distance, max_distance_km)
                    })
            
            # Sort by distance (closest first)
            ngos_with_distance.sort(key=lambda x: x['distance_km'])
            
            return ngos_with_distance
            
        except Exception as e:
            st.error(f"Error finding nearby NGOs: {e}")
            return []
        finally:
            conn.close()
    
    def _calculate_proximity_score(self, distance: float, max_distance: float) -> float:
        """Calculate proximity score (higher is better, max 1.0)."""
        if distance >= max_distance:
            return 0.0
        return round(1.0 - (distance / max_distance), 3)
    
    def get_location_suggestions(self, query: str) -> List[Dict]:
        """
        Get location suggestions based on query.
        This is a simplified implementation - in production, you'd use a geocoding API.
        """
        
        # Sample locations for major Indian cities (for demo purposes)
        sample_locations = [
            {"name": "Mumbai, Maharashtra", "lat": 19.0760, "lon": 72.8777},
            {"name": "Delhi, India", "lat": 28.7041, "lon": 77.1025},
            {"name": "Bangalore, Karnataka", "lat": 12.9716, "lon": 77.5946},
            {"name": "Chennai, Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
            {"name": "Hyderabad, Telangana", "lat": 17.3850, "lon": 78.4867},
            {"name": "Pune, Maharashtra", "lat": 18.5204, "lon": 73.8567},
            {"name": "Kolkata, West Bengal", "lat": 22.5726, "lon": 88.3639},
            {"name": "Ahmedabad, Gujarat", "lat": 23.0225, "lon": 72.5714},
            {"name": "Jaipur, Rajasthan", "lat": 26.9124, "lon": 75.7873},
            {"name": "Surat, Gujarat", "lat": 21.1702, "lon": 72.8311},
        ]
        
        if not query:
            return sample_locations[:5]
        
        # Simple fuzzy matching
        query_lower = query.lower()
        matches = [
            loc for loc in sample_locations 
            if query_lower in loc['name'].lower()
        ]
        
        return matches[:5] if matches else sample_locations[:3]

class ProximityMatcher:
    """Enhanced NGO matching with proximity considerations."""
    
    def __init__(self):
        self.geo_service = GeoLocationService()
    
    def get_enhanced_ngo_recommendations(
        self, 
        donation_data: Dict, 
        donor_location: Optional[Dict] = None,
        max_distance_km: float = 25,
        include_capacity_match: bool = True
    ) -> Dict:
        """
        Get NGO recommendations enhanced with proximity data.
        
        Args:
            donation_data: Donation information
            donor_location: Donor's location data
            max_distance_km: Maximum search radius
            include_capacity_match: Whether to consider capacity matching
            
        Returns:
            Enhanced recommendation results with proximity scores
        """
        
        # Get basic NGO suggestions (existing logic)
        from ai_features import suggest_best_ngo
        base_suggestions = suggest_best_ngo(donation_data)
        
        # If no donor location provided, return basic suggestions
        if not donor_location or 'latitude' not in donor_location:
            return {
                **base_suggestions,
                'proximity_enabled': False,
                'message': 'Location-based matching not available'
            }
        
        # Find nearby NGOs
        nearby_ngos = self.geo_service.find_nearby_ngos(
            donor_location['latitude'],
            donor_location['longitude'],
            max_distance_km,
            min_capacity=donation_data.get('quantity', 1) if include_capacity_match else 1
        )
        
        if not nearby_ngos:
            return {
                **base_suggestions,
                'proximity_enabled': True,
                'nearby_ngos': [],
                'message': f'No NGOs found within {max_distance_km}km radius'
            }
        
        # Enhance recommendations with proximity data
        enhanced_recommendation = self._combine_recommendations(
            base_suggestions, nearby_ngos, donation_data
        )
        
        return enhanced_recommendation
    
    def _combine_recommendations(
        self, 
        base_suggestions: Dict, 
        nearby_ngos: List[Dict], 
        donation_data: Dict
    ) -> Dict:
        """Combine capacity-based and proximity-based recommendations."""
        
        # Create enhanced NGO profiles
        enhanced_ngos = []
        
        for ngo in nearby_ngos:
            # Calculate combined score
            proximity_score = ngo['proximity_score']
            capacity_score = self._calculate_capacity_score(ngo, donation_data)
            
            # Weighted combined score (60% proximity, 40% capacity match)
            combined_score = (proximity_score * 0.6) + (capacity_score * 0.4)
            
            enhanced_ngo = {
                **ngo,
                'capacity_score': capacity_score,
                'combined_score': round(combined_score, 3),
                'match_reasons': self._generate_match_reasons(ngo, donation_data)
            }
            
            enhanced_ngos.append(enhanced_ngo)
        
        # Sort by combined score
        enhanced_ngos.sort(key=lambda x: x['combined_score'], reverse=True)
        
        # Select top recommendation
        top_ngo = enhanced_ngos[0] if enhanced_ngos else None
        alternatives = enhanced_ngos[1:4] if len(enhanced_ngos) > 1 else []
        
        return {
            'suggested_ngo': top_ngo,
            'alternatives': alternatives,
            'proximity_enabled': True,
            'total_nearby': len(nearby_ngos),
            'reasoning': self._generate_enhanced_reasoning(top_ngo, donation_data) if top_ngo else "No suitable NGOs found nearby"
        }
    
    def _calculate_capacity_score(self, ngo: Dict, donation_data: Dict) -> float:
        """Calculate how well NGO capacity matches donation quantity."""
        ngo_capacity = ngo.get('capacity', 10)
        donation_quantity = donation_data.get('quantity', 1)
        
        if ngo_capacity >= donation_quantity:
            # Prefer NGOs with capacity close to donation size (not too large)
            if ngo_capacity <= donation_quantity * 2:
                return 1.0
            elif ngo_capacity <= donation_quantity * 5:
                return 0.8
            else:
                return 0.6
        else:
            # NGO capacity is less than donation
            return 0.3
    
    def _generate_match_reasons(self, ngo: Dict, donation_data: Dict) -> List[str]:
        """Generate human-readable reasons for the match."""
        reasons = []
        
        # Distance-based reasons
        distance = ngo['distance_km']
        if distance < 5:
            reasons.append(f"Very close location ({distance}km away)")
        elif distance < 15:
            reasons.append(f"Convenient pickup distance ({distance}km)")
        else:
            reasons.append(f"Within reasonable distance ({distance}km)")
        
        # Capacity-based reasons
        capacity = ngo.get('capacity', 10)
        quantity = donation_data.get('quantity', 1)
        
        if capacity >= quantity * 2:
            reasons.append(f"High capacity ({capacity} units)")
        elif capacity >= quantity:
            reasons.append(f"Adequate capacity ({capacity} units)")
        
        # Location-based reasons
        if ngo.get('city'):
            reasons.append(f"Located in {ngo['city']}")
        
        return reasons
    
    def _generate_enhanced_reasoning(self, ngo: Dict, donation_data: Dict) -> str:
        """Generate detailed reasoning for the top recommendation."""
        
        food_name = donation_data.get('food_name', 'food item')
        quantity = donation_data.get('quantity', 1)
        unit = donation_data.get('unit', 'units')
        
        distance = ngo['distance_km']
        capacity = ngo.get('capacity', 10)
        combined_score = ngo['combined_score']
        
        reasoning = f"""
Selected {ngo['name']} as the best match for your {food_name} donation ({quantity} {unit}):

🎯 **Match Score: {combined_score:.1f}/1.0**
📍 **Distance: {distance}km** - {"Very close" if distance < 5 else "Convenient" if distance < 15 else "Reasonable"} pickup location
📦 **Capacity: {capacity} units** - {"Excellent" if capacity >= quantity * 2 else "Good"} capacity match
🏙️ **Location: {ngo.get('city', 'Unknown city')}**

This NGO offers the best combination of proximity and capacity for efficient food distribution.
        """.strip()
        
        return reasoning

def get_proximity_matcher() -> ProximityMatcher:
    """Get the global proximity matcher instance."""
    if 'proximity_matcher' not in st.session_state:
        st.session_state.proximity_matcher = ProximityMatcher()
    return st.session_state.proximity_matcher

def display_location_input(user_id: int, user_role: str = "Donor") -> Optional[Dict]:
    """
    Display location input widget and save location.
    
    Returns:
        Location data if successfully saved, None otherwise
    """
    
    geo_service = GeoLocationService()
    
    st.markdown(f"### 📍 {user_role} Location")
    st.info("Adding your location helps us find the best NGO matches nearby!")
    
    # Check if user already has a location
    existing_location = geo_service.get_user_location(user_id)
    
    if existing_location:
        st.success(f"✅ Current location: {existing_location.get('address', 'Coordinates saved')}")
        
        if st.button("📝 Update Location"):
            st.session_state.show_location_form = True
        
        if not st.session_state.get('show_location_form', False):
            return existing_location
    
    # Location input form
    st.markdown("#### Enter Your Location")
    
    # Method selection
    input_method = st.radio(
        "How would you like to provide your location?",
        ["🔍 Search Address", "📍 Enter Coordinates", "📋 Manual Entry"],
        key=f"location_method_{user_id}"
    )
    
    location_data = None
    
    if input_method == "🔍 Search Address":
        
        # Address search
        search_query = st.text_input(
            "Search for your city or address:",
            placeholder="e.g., Mumbai, Bangalore, Delhi",
            key=f"location_search_{user_id}"
        )
        
        if search_query:
            suggestions = geo_service.get_location_suggestions(search_query)
            
            if suggestions:
                st.markdown("**Suggestions:**")
                
                for i, suggestion in enumerate(suggestions):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"📍 {suggestion['name']}")
                    
                    with col2:
                        if st.button("Select", key=f"select_loc_{user_id}_{i}"):
                            location_data = {
                                'latitude': suggestion['lat'],
                                'longitude': suggestion['lon'],
                                'address': suggestion['name'],
                                'city': suggestion['name'].split(',')[0]
                            }
                            
                            if geo_service.save_user_location(
                                user_id, 
                                location_data['latitude'], 
                                location_data['longitude'],
                                location_data['address'],
                                location_data['city']
                            ):
                                st.success("✅ Location saved successfully!")
                                st.session_state.show_location_form = False
                                st.rerun()
    
    elif input_method == "📍 Enter Coordinates":
        
        col1, col2 = st.columns(2)
        
        with col1:
            latitude = st.number_input(
                "Latitude:",
                min_value=-90.0,
                max_value=90.0,
                value=19.0760,  # Mumbai default
                format="%.6f",
                key=f"lat_{user_id}"
            )
        
        with col2:
            longitude = st.number_input(
                "Longitude:",
                min_value=-180.0,
                max_value=180.0,
                value=72.8777,  # Mumbai default
                format="%.6f",
                key=f"lon_{user_id}"
            )
        
        address = st.text_input(
            "Address (optional):",
            placeholder="Enter a descriptive address",
            key=f"coord_address_{user_id}"
        )
        
        if st.button("💾 Save Coordinates", key=f"save_coords_{user_id}"):
            if geo_service.save_user_location(user_id, latitude, longitude, address):
                st.success("✅ Location saved successfully!")
                location_data = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'address': address
                }
                st.session_state.show_location_form = False
                st.rerun()
    
    else:  # Manual Entry
        
        address = st.text_input(
            "Full Address:",
            placeholder="Enter your complete address",
            key=f"manual_address_{user_id}"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            city = st.text_input(
                "City:",
                placeholder="e.g., Mumbai",
                key=f"manual_city_{user_id}"
            )
        
        with col2:
            postal_code = st.text_input(
                "Postal Code:",
                placeholder="e.g., 400001",
                key=f"manual_postal_{user_id}"
            )
        
        # For manual entry, we'll use approximate coordinates for major cities
        if st.button("💾 Save Address", key=f"save_manual_{user_id}"):
            if address and city:
                # Get approximate coordinates for the city
                suggestions = geo_service.get_location_suggestions(city)
                
                if suggestions:
                    coords = suggestions[0]
                    if geo_service.save_user_location(
                        user_id, coords['lat'], coords['lon'], 
                        address, city, postal_code
                    ):
                        st.success("✅ Location saved successfully!")
                        location_data = {
                            'latitude': coords['lat'],
                            'longitude': coords['lon'],
                            'address': address,
                            'city': city,
                            'postal_code': postal_code
                        }
                        st.session_state.show_location_form = False
                        st.rerun()
                else:
                    st.warning("City not found. Please use coordinate entry method.")
            else:
                st.error("Please fill in required fields (Address and City)")
    
    return location_data

def display_proximity_results(recommendations: Dict, donation_data: Dict) -> None:
    """Display proximity-based recommendation results."""
    
    if not recommendations.get('proximity_enabled'):
        st.info("📍 Add your location to get proximity-based NGO recommendations!")
        return
    
    st.markdown("### 🎯 Location-Based NGO Recommendations")
    
    total_nearby = recommendations.get('total_nearby', 0)
    
    if total_nearby == 0:
        st.warning("No NGOs found in your area. Consider expanding search radius or try other NGOs.")
        return
    
    st.success(f"Found {total_nearby} NGO{'s' if total_nearby != 1 else ''} in your area!")
    
    # Top recommendation
    top_ngo = recommendations.get('suggested_ngo')
    if top_ngo:
        st.markdown("#### 🏆 Best Match")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("NGO Name", top_ngo['name'])
        
        with col2:
            st.metric("Distance", f"{top_ngo['distance_km']} km")
        
        with col3:
            st.metric("Match Score", f"{top_ngo['combined_score']:.1f}/1.0")
        
        st.markdown(f"**Reasoning:** {recommendations.get('reasoning', '')}")
        
        # Match reasons
        reasons = top_ngo.get('match_reasons', [])
        if reasons:
            st.markdown("**Why this NGO?**")
            for reason in reasons:
                st.write(f"• {reason}")
    
    # Alternative NGOs
    alternatives = recommendations.get('alternatives', [])
    if alternatives:
        st.markdown("#### 🔄 Alternative Options")
        
        for i, ngo in enumerate(alternatives[:3]):
            with st.expander(f"Option {i+1}: {ngo['name']} ({ngo['distance_km']}km)"):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Distance:** {ngo['distance_km']} km")
                    st.write(f"**Capacity:** {ngo.get('capacity', 'Unknown')} units")
                
                with col2:
                    st.write(f"**Match Score:** {ngo['combined_score']:.1f}/1.0")
                    if ngo.get('city'):
                        st.write(f"**Location:** {ngo['city']}")
                
                if ngo.get('match_reasons'):
                    st.write("**Match Reasons:**")
                    for reason in ngo['match_reasons']:
                        st.write(f"• {reason}")