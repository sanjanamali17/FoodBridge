import sqlite3
import hashlib
import datetime
from typing import List, Dict, Optional
import os

DATABASE_PATH = "foodbridge.db"

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Donor', 'NGO', 'Admin')),
            organization TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Donations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit TEXT NOT NULL,
            expiry_date DATE NOT NULL,
            description TEXT,
            image_path TEXT,
            quality_prediction TEXT NOT NULL,
            quality_confidence REAL,
            status TEXT DEFAULT 'Available' CHECK (status IN ('Available', 'Requested', 'Picked Up', 'Expired')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (donor_id) REFERENCES users (id)
        )
    ''')
    
    # Donation requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donation_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donation_id INTEGER NOT NULL,
            ngo_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Completed')),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (donation_id) REFERENCES donations (id),
            FOREIGN KEY (ngo_id) REFERENCES users (id)
        )
    ''')
    
    # NGO profiles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ngo_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 50,
            location TEXT,
            contact_person TEXT,
            phone TEXT,
            serves_area TEXT,
            specialization TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    
    # Create default admin user if not exists
    create_default_admin(cursor)
    
    conn.close()

def create_default_admin(cursor):
    """Create a default admin user if none exists."""
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Admin'")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        admin_password = hash_password("admin123")
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, organization)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Admin User", "admin@foodbridge.com", admin_password, "Admin", "FoodBridge"))

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash

def create_user(name: str, email: str, password: str, role: str, organization: str = "") -> bool:
    """Create a new user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, organization)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, password_hash, role, organization))
        
        user_id = cursor.lastrowid
        
        # Create NGO profile if user is NGO
        if role == 'NGO':
            cursor.execute('''
                INSERT INTO ngo_profiles (user_id, capacity, contact_person)
                VALUES (?, ?, ?)
            ''', (user_id, 100, name))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        if 'conn' in locals():
            conn.close()
        return False
    except Exception as e:
        print(f"Error creating user: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate a user and return user data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, role, organization, password_hash
        FROM users WHERE email = ? AND is_active = 1
    ''', (email,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'organization': user['organization']
        }
    return None

def create_donation(donor_id: int, food_name: str, quantity: int, unit: str, 
                   expiry_date: str, description: str, quality_prediction: str, 
                   quality_confidence: float, image_path: str = "") -> int:
    """Create a new donation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO donations (donor_id, food_name, quantity, unit, expiry_date, 
                             description, image_path, quality_prediction, quality_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (donor_id, food_name, quantity, unit, expiry_date, description, 
          image_path, quality_prediction, quality_confidence))
    
    donation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return donation_id or 0

def get_available_donations(limit: int = None) -> List[Dict]:
    """Get all available donations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT d.*, u.name as donor_name, u.organization as donor_org
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.status = 'Available' AND d.quality_prediction = 'Fresh'
        ORDER BY d.created_at DESC
    '''
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query)
    donations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return donations

def get_user_donations(user_id: int) -> List[Dict]:
    """Get donations by a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM donations
        WHERE donor_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    
    donations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return donations

def get_all_donations() -> List[Dict]:
    """Get all donations (for admin)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT d.*, u.name as donor_name, u.organization as donor_org
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        ORDER BY d.created_at DESC
    ''')
    
    donations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return donations

def create_donation_request(donation_id: int, ngo_id: int, notes: str = "") -> int:
    """Create a donation request."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO donation_requests (donation_id, ngo_id, notes)
        VALUES (?, ?, ?)
    ''', (donation_id, ngo_id, notes))
    
    # Update donation status
    cursor.execute('''
        UPDATE donations SET status = 'Requested' WHERE id = ?
    ''', (donation_id,))
    
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return request_id or 0

def get_ngo_requests(ngo_id: int) -> List[Dict]:
    """Get donation requests for an NGO."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT dr.*, d.food_name, d.quantity, d.unit, d.expiry_date,
               u.name as donor_name
        FROM donation_requests dr
        JOIN donations d ON dr.donation_id = d.id
        JOIN users u ON d.donor_id = u.id
        WHERE dr.ngo_id = ?
        ORDER BY dr.requested_at DESC
    ''', (ngo_id,))
    
    requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return requests

def get_user_stats(user_id: int) -> Dict:
    """Get statistics for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # For donors
    cursor.execute('''
        SELECT 
            COUNT(*) as total_donations,
            SUM(quantity) as total_quantity,
            COUNT(CASE WHEN quality_prediction = 'Fresh' THEN 1 END) as fresh_donations
        FROM donations WHERE donor_id = ?
    ''', (user_id,))
    
    stats = dict(cursor.fetchone())
    
    # Additional stats
    cursor.execute('''
        SELECT COUNT(DISTINCT dr.ngo_id) as ngos_helped
        FROM donation_requests dr
        JOIN donations d ON dr.donation_id = d.id
        WHERE d.donor_id = ?
    ''', (user_id,))
    
    ngo_stats = cursor.fetchone()
    stats['ngos_helped'] = ngo_stats['ngos_helped'] if ngo_stats else 0
    stats['donations'] = stats['total_donations']
    stats['food_saved'] = stats['total_quantity'] or 0
    
    conn.close()
    return stats

def get_admin_stats() -> Dict:
    """Get overall platform statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total_donations,
            SUM(quantity) as total_food_saved,
            COUNT(CASE WHEN quality_prediction = 'Fresh' THEN 1 END) as fresh_donations,
            COUNT(CASE WHEN status = 'Picked Up' THEN 1 END) as completed_donations
        FROM donations
    ''')
    
    stats = dict(cursor.fetchone())
    
    # User stats
    cursor.execute('SELECT COUNT(*) as total_users FROM users WHERE is_active = 1')
    user_stats = cursor.fetchone()
    stats['total_users'] = user_stats['total_users']
    
    cursor.execute('SELECT COUNT(*) as total_ngos FROM users WHERE role = "NGO" AND is_active = 1')
    ngo_stats = cursor.fetchone()
    stats['total_ngos'] = ngo_stats['total_ngos']
    
    cursor.execute('SELECT COUNT(*) as total_donors FROM users WHERE role = "Donor" AND is_active = 1')
    donor_stats = cursor.fetchone()
    stats['total_donors'] = donor_stats['total_donors']
    
    conn.close()
    return stats

def get_recent_donations(limit: int = 10) -> List[Dict]:
    """Get recent donations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT d.*, u.name as donor_name
        FROM donations d
        JOIN users u ON d.donor_id = u.id
        ORDER BY d.created_at DESC
        LIMIT ?
    ''', (limit,))
    
    donations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return donations

def get_ngos_by_capacity(min_capacity: int = 0) -> List[Dict]:
    """Get NGOs sorted by capacity."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.name, u.organization, np.capacity, np.location, np.specialization
        FROM users u
        JOIN ngo_profiles np ON u.id = np.user_id
        WHERE u.role = 'NGO' AND u.is_active = 1 AND np.capacity >= ?
        ORDER BY np.capacity DESC
    ''', (min_capacity,))
    
    ngos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return ngos

def save_chat_message(user_id: int, message: str, response: str):
    """Save chat conversation to database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO chat_history (user_id, message, response)
        VALUES (?, ?, ?)
    ''', (user_id, message, response))
    
    conn.commit()
    conn.close()

def get_chat_history(user_id: int, limit: int = 10) -> List[Dict]:
    """Get chat history for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT message, response, created_at
        FROM chat_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return history[::-1]  # Reverse to show chronological order
