# FoodBridge

Abstract

Every day, tons of edible food is wasted in hostels, restaurants, and events. Meanwhile, millions go hungry.
FoodBridge leverages AI-based image classification and a smart web interface to identify spoiled vs. fresh food, and connect donors with nearby NGOs for timely food redistribution — reducing waste and improving social impact.

Problem Statement

Food waste in India: ~68 million tons/year are wasted.
Manual donation processes are time-consuming and lack real-time monitoring.
NGOs often don't know when food is available.
No freshness/spoilage check is done — leading to potential health risks.
Proposed Solution
Detect leftover food at hostels/events.


Use an AI model to classify spoiled vs. fresh food.

Donors upload an image → AI decides freshness.

Fresh food is matched with nearby NGOs for pickup.

Admin dashboard tracks donations, pickups, and feedback.

System Architecture:

Food Donor (uploads image + food details)
            ⬇
   AI Spoilage Classifier
            ⬇
   If fresh → Show Nearby NGOs
            ⬇
NGO receives alert → Pickup
            ⬇
Admin Dashboard (track donations, feedback)

Competitive Analysis
Platform	Offers	Limitations
Feeding India (Zomato)	Partners with restaurants for bulk donations; Event-based & scheduled meals	No AI freshness check; Not for small-scale donors; No real-time public donation app
Robin Hood Army	Volunteer-based food pickups; No monetary donations	Manual WhatsApp-based coordination; No spoilage detection or tracking
No Food Waste (NFW)	Mobile app to upload food details; Admin verifies and dispatches volunteers	No AI freshness detection; Admin delays due to manual verification

FoodBridge Advantages:

AI-based food spoilage detection ✅

Real-time NGO-donor matching ✅

Individual + restaurant donors ✅

Expiry alerts/freshness score ✅

QR code pickup verification ✅

Chatbot or guided flow ✅

Tech Stack

Frontend: Streamlit

Backend: Python (Flask or FastAPI)

Database: MongoDB

AI/ML: Image Classification using CNN (Keras/TensorFlow)

Other Tools: Google Maps API for location tracking

Key Modules

User Authentication: Login/Register for Donors & NGOs

Food Upload Module: Upload image + food details

AI Detection: Checks if food is spoiled or fresh

Matchmaking Engine: Suggests nearby NGOs

Dashboard: Track donations, pending pickups

Admin Panel: Monitor activities & generate reports

Conclusion

FoodBridge addresses a real-world problem at the intersection of food waste and hunger using AI and a user-friendly platform. It’s scalable, impactful, and encourages community-driven food sharing. With proper guidance and adoption, it can become a real solution implemented at scale.
