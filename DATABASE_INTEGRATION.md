# MedLink - Database Integration Summary

## ✅ Completed Tasks

### 1. Database Schema (models.py)
Created a robust SQLAlchemy ORM with four models:

**User Model** (`users` table):
- `id`: Primary key (Integer)
- `username`: Unique email address (String) 
- `role`: User type - 'patient', 'doctor', 'specialist' (String)
- `password_hash`: Hashed password using Werkzeug security (String)
- `public_key`: For future encryption (Text, nullable)
- `encrypted_profile`: Encrypted email/NID storage (Text, nullable)
- `created_at`: Timestamp (DateTime)
- `updated_at`: Timestamp (DateTime)

**Referral Model** (`referrals` table):
- `id`: Primary key (Integer)
- `sender_id`: FK to User (Integer)
- `receiver_id`: FK to User (Integer)
- `encrypted_content`: Encrypted referral data (Text)
- `mac_tag`: Message authentication code for integrity (String)
- `is_verified`: MAC verification status (Boolean)
- `referral_type`: Type of referral (String)
- `status`: pending/accepted/completed (String)
- `timestamp`: Creation time (DateTime)

**Message Model** (`messages` table):
- `id`: Primary key (Integer)
- `sender_id`: FK to User (Integer)
- `receiver_id`: FK to User (Integer)
- `encrypted_content`: Encrypted message (Text)
- `mac_tag`: Integrity verification tag (String)
- `is_verified`: MAC verification status (Boolean)
- `is_read`: Message read status (Boolean)
- `timestamp`: Creation time (DateTime)

**Document Model** (`documents` table):
- `id`: Primary key (Integer)
- `user_id`: FK to User (Integer)
- `document_type`: prescription/lab_result/report (String)
- `encrypted_content`: Encrypted document (Text)
- `mac_tag`: Integrity verification tag (String)
- `is_verified`: MAC verification status (Boolean)
- `uploaded_at`: Upload timestamp (DateTime)

### 2. Route Refactoring (app.py)

**Updated Routes:**
- `GET /` - Landing page (unchanged)
- `GET/POST /login` - Now queries database for user authentication
- `GET /dashboard` - Queries real database stats and activities
- `GET /logout` - Clears session and redirects

**New Helper Functions:**
- `get_dashboard_stats(user)` - Calculates real statistics from database
  - Counts active consultations (received pending referrals)
  - Counts pending referrals (sent pending referrals)
  - Counts verified documents
  - Calculates system integrity percentage
  
- `get_recent_activity(user)` - Retrieves last 10 activities
  - Queries referrals, messages, and documents
  - Combines and sorts by timestamp
  - Includes verification status for each item
  
- `get_system_integrity(user)` - Returns verification metrics
  - Total and verified referrals count
  - Total and verified messages count

- `init_sample_data()` - Populates database with demo data
  - 3 sample users (patient, doctor, specialist)
  - 2 sample referrals
  - 2 sample messages
  - 2 sample documents
  - All with mock encryption fields and verified status

### 3. Frontend Integration (Templates)

**Login Template (login.html):**
- Changed field from `email` to `username`
- Maintained all styling and security messaging
- Demo credentials still displayed

**Dashboard Template (dashboard.html):**
- **Stats Section**: Now uses Jinja2 template variables
  - `{{ stats.active_consultations }}`
  - `{{ stats.pending_referrals }}`
  - `{{ stats.verified_documents }}`
  - `{{ stats.system_integrity }}`

- **Recent Activity**: Dynamic loop with `{% for activity in recent_activity %}`
  - Displays activity type, title, description, time
  - Shows "Verified" badge based on `{{ activity.is_verified }}`
  - Shows "No activity yet" if empty

- **Security Overview**: Dynamic status based on database
  - Changes color and message based on system integrity percentage
  - Shows real count: "{{ system_integrity.verified_referrals }} verified referral(s). {{ system_integrity.verified_messages }} verified message(s)."

## 🗄️ Database Configuration

**Database**: SQLite (`medlink.db`)
**ORM**: Flask-SQLAlchemy 3.0.5
**Location**: Project root directory

**Initialization**:
```python
with app.app_context():
    db.create_all()           # Creates all tables
    init_sample_data()         # Populates demo data
```

Tables are automatically created on first run if they don't exist.

## 🔐 Encryption & Integrity Fields

Fields prepared for future encryption implementation:
- `User.encrypted_profile` - Encrypted user email/NID
- `User.public_key` - User's public encryption key
- `Referral.encrypted_content` - Encrypted referral data
- `Referral.mac_tag` - Message authentication code
- `Message.encrypted_content` - Encrypted message
- `Message.mac_tag` - Message authentication code
- `Document.encrypted_content` - Encrypted document
- `Document.mac_tag` - Document authentication code

**Verification Methods**: Each model has `verify_integrity()` method (placeholder for future encryption implementation)

## 📊 Real Data Examples

### Patient Dashboard Shows:
- Active Consultations: 0 (no pending referrals received)
- Pending Referrals: 0 (none sent)
- Verified Documents: 1 (lab results)
- System Integrity: 100%
- Recent Activity: 4 items from database (document, messages, referral)

### Doctor Dashboard Shows:
- Active Consultations: 0
- Pending Referrals: 1 (referral to specialist)
- Verified Documents: 1 (prescription)
- System Integrity: 100%
- Recent Activity: 5 items (referrals sent to patient and specialist, messages, prescription)

### Security Overview:
Displays dynamic counts based on user's verified items:
- "1 verified referral(s). 2 verified message(s)." (Patient)
- "2 verified referral(s). 2 verified message(s)." (Doctor)

## 📝 Demo Credentials

```
Patient:
  Email: patient@medlink.com
  Password: patient123

Doctor:
  Email: doctor@medlink.com
  Password: doctor123

Specialist:
  Email: specialist@medlink.com
  Password: specialist123
```

## 🎯 Key Features

✅ **SQLite Database**: Lightweight, file-based database
✅ **SQLAlchemy ORM**: Type-safe, efficient queries
✅ **Password Hashing**: Werkzeug security for password storage
✅ **Role-Based Access**: Patient/Doctor/Specialist dashboards
✅ **Real Statistics**: All numbers calculated from database
✅ **Recent Activity Feed**: Dynamic, sorted by timestamp
✅ **Integrity Verification**: MAC tag fields for future encryption
✅ **Sample Data**: Pre-populated for testing all roles
✅ **Relationships**: Proper foreign keys and back-references
✅ **Timestamps**: Created/updated at fields on models

## 🔧 Code Quality

- No high-level encryption libraries used (as requested)
- Fields prepared for future encryption implementation
- Proper separation of concerns (models, routes, templates)
- DRY principle: Reusable helper functions
- Flask best practices: App context usage, session management
- Jinja2 templates: Dynamic, real data from database
- Database optimization: Indexed foreign keys, efficient queries

## 📦 File Structure

```
MedLink/
├── app.py                    # Flask app with database routes
├── models.py                 # SQLAlchemy ORM models
├── medlink.db                # SQLite database (created on first run)
├── requirements.txt          # Dependencies (Flask, SQLAlchemy)
├── templates/
│   ├── base.html            # Base template
│   ├── index.html           # Landing page
│   ├── login.html           # Login form
│   └── dashboard.html       # Dynamic dashboard
└── README.md                # This file
```

## 🚀 Running the Application

```bash
cd c:\Users\prano\OneDrive\Desktop\MedLife\MedLink
python app.py
```

Then visit: **http://localhost:5000**

## ✨ What's Next

Ready for future enhancements:
- [ ] Implement actual encryption (AES) for encrypted_content fields
- [ ] MAC tag verification logic for integrity checking
- [ ] User registration system
- [ ] Password reset functionality
- [ ] Two-factor authentication
- [ ] Real-time chat with WebSockets
- [ ] PDF export for medical documents
- [ ] Email notifications
- [ ] Database migrations with Alembic

## 📋 Notes

- Database is created automatically on first run
- Sample data is initialized only if no users exist
- All timestamps are in UTC
- System integrity shows 100% for demo (all items verified)
- Display names use role prefix (e.g., "Dr. Doctor" for doctor role)
- Responsive design maintained throughout
- Off-white minimalist UI fully preserved
