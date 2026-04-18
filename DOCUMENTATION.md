# MedLink - Complete Documentation

**Project Status:** ✅ **COMPLETE & OPERATIONAL**  
**Last Updated:** April 18, 2026  
**Version:** 2.0 with Full Messaging System  

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation & Setup](#installation--setup)
3. [Demo Credentials](#demo-credentials)
4. [Features Overview](#features-overview)
5. [Technical Stack](#technical-stack)
6. [Project Structure](#project-structure)
7. [Security Implementation](#security-implementation)
8. [API Endpoints](#api-endpoints)
9. [Database Schema](#database-schema)
10. [Usage Examples](#usage-examples)
11. [Messaging System](#messaging-system)
12. [Lab Defense Guide](#lab-defense-guide)

---

## Quick Start

### 1. Start the Application
```bash
cd /Users/prantoroy/Desktop/MedLink/MedLink
python app.py
```

### 2. Open in Browser
```
http://localhost:5001
```

### 3. Login with Demo Credentials
```
Patient:    patient@medlink.com / patient123
Doctor:     doctor@medlink.com / doctor123
Specialist: specialist@medlink.com / specialist123
Admin:      admin@medlink.com / admin123
```

---

## Installation & Setup

### Prerequisites
- Python 3.9+
- pip package manager

### Step-by-Step Setup

#### 1. Clone/Navigate to Repository
```bash
cd /Users/prantoroy/Desktop/MedLink/MedLink
```

#### 2. Create Virtual Environment (Optional)
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Run Application
```bash
python app.py
```

The application will start at: **http://localhost:5001**

---

## Demo Credentials

### Patient Portal
- **Email:** patient@medlink.com
- **Password:** patient123
- **Access:** View prescriptions, chat with doctors, accept referrals

### Doctor Portal
- **Email:** doctor@medlink.com
- **Password:** doctor123
- **Access:** Create prescriptions, refer specialists, send messages

### Specialist Portal
- **Email:** specialist@medlink.com
- **Password:** specialist123
- **Access:** Receive referrals, provide consultations, view cases

### Admin Portal
- **Email:** admin@medlink.com
- **Password:** admin123
- **Access:** User management, system monitoring, admin dashboard

---

## Features Overview

### ✨ User Interface
- **Modern, High-Fidelity Design** with professional clinical aesthetics
- **Responsive Layout** optimized for mobile, tablet, and desktop
- **Smooth Animations** with fade-in-up effects and scale transitions
- **Clean Color Scheme** with Clinical Blue, Teal accents, and off-white backgrounds

### 🔒 Security Features
- **End-to-End Message Encryption** (ECC + HMAC)
- **RSA Digital Signatures** for referrals
- **SHA-256 Password Hashing** with salt
- **HMAC Message Authentication** to prevent tampering
- **Session-Based Authentication** with 2FA verification codes

### 💬 Messaging System
- **Real-Time Chat** with 2-second auto-refresh
- **Unread Message Tracking** with badge count on sidebar
- **Active Conversations First** in chat list
- **User Search** to find and start new conversations
- **Encrypted Message History** persisted in database
- **Message Read Status** automatically tracked

### 📋 Medical Features
- **Prescription Management** with steganographic storage
- **Specialist Referrals** with RSA signatures
- **Patient Health Records** with encryption
- **Consultation Tracking** between providers

### 📊 Admin Features
- **User Management** and approval system
- **System Monitoring** dashboard
- **Activity Logging** with timestamps
- **Security Audit** trail

---

## Technical Stack

### Backend
- **Framework:** Flask 2.3.3
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** Session-based with 2FA
- **Cryptography:** Custom ECC, RSA, SHA-256, HMAC implementations

### Frontend
- **HTML5** with Jinja2 templating
- **CSS:** Tailwind CSS with custom animations
- **JavaScript:** Vanilla JS for real-time features
- **Fonts:** Inter (body), Plus Jakarta Sans (headings)

### Security Modules
- **RSA:** 6-step key generation with Miller-Rabin primes
- **ECC:** Elliptic curve point arithmetic with scalar multiplication
- **SHA-256:** Manual implementation with bitwise operations
- **HMAC:** HMAC-SHA256 for message authentication

---

## Project Structure

```
MedLink/
├── app.py                          # Main Flask application (700+ lines)
├── models.py                       # Database models with encryption
├── requirements.txt                # Python dependencies
│
├── security/                       # Cryptography package
│   ├── __init__.py                # Package initialization
│   ├── rsa.py                     # RSA encryption (250+ lines)
│   ├── ecc.py                     # Elliptic curve cryptography (350+ lines)
│   ├── encryption_utils.py        # Message encryption/decryption
│   └── hashing.py                 # SHA-256, HMAC, password hashing (400+ lines)
│
├── templates/                      # HTML templates
│   ├── base.html                  # Base template with sidebar
│   ├── index.html                 # Landing page
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── verify_2fa.html            # 2FA verification
│   ├── verify_registration.html   # Email verification
│   ├── dashboard.html             # Main dashboard
│   ├── profile.html               # User profile
│   ├── chat.html                  # One-on-one chat
│   ├── chat_list.html             # Chat conversations list
│   ├── create_prescription.html    # Prescription creation
│   ├── patient_prescriptions.html  # Patient prescription view
│   ├── refer_specialist.html       # Specialist referral
│   ├── edit_profile.html           # Edit profile
│   ├── admin_dashboard.html        # Admin dashboard
│   ├── attack_simulator.html       # HMAC attack demo
│   ├── encrypt_demo.html           # Encryption demo
│   └── rotate_keys.html            # Key rotation demo
│
├── DOCUMENTATION.md               # This comprehensive guide
└── medlink.db                     # SQLite database
```

---

## Security Implementation

### 1. RSA Encryption

**Algorithm:** 6-Step Key Generation
```
Step 1: Generate large primes p and q
Step 2: Calculate N = p × q (modulus)
Step 3: Calculate φ(N) = (p-1) × (q-1)
Step 4: Choose e where gcd(e, φ(N)) = 1
Step 5: Calculate d = e^(-1) mod φ(N)
Step 6: Return public key (e, N), private key (d, N)
```

**Implementation Details:**
- Miller-Rabin primality test with O(k log³ n) complexity
- Extended Euclidean algorithm for modular inverse
- Encryption: C ≡ M^e (mod N)
- Decryption: M ≡ C^d (mod N)
- File: `security/rsa.py` (250+ lines)

**Usage:**
```python
from security import RSAKeyGenerator, rsa_encrypt_hex, rsa_decrypt_hex

# Generate keys
rsa_gen = RSAKeyGenerator()
public_key, private_key = rsa_gen.generate_keys()

# Encrypt
ciphertext = rsa_encrypt_hex("Hello", public_key)

# Decrypt
plaintext = rsa_decrypt_hex(ciphertext, private_key)
```

### 2. Elliptic Curve Cryptography (ECC)

**Curve Equation:** y² ≡ x³ + ax + b (mod p)

**Point Arithmetic:**
```
Point Addition: λ = (yQ - yP)/(xQ - xP) mod p
Point Doubling: λ = (3x² + a)/(2y) mod p
Scalar Multiplication: Double-and-Add algorithm O(log k)
```

**Implementation Details:**
- Full point addition with special case handling
- Efficient scalar multiplication
- Complete curve validation
- File: `security/ecc.py` (350+ lines)

**Usage:**
```python
from security import EllipticCurve

# Create curve: y² = x³ + x + 1 (mod 1009)
curve = EllipticCurve(a=1, b=1, p=1009)

# Define point
P = (2, 2)

# Scalar multiplication: 5*P
Q = curve.scalar_multiplication(5, P)
```

### 3. SHA-256 Hashing

**Implementation:** Manual bitwise operations from scratch
- 64 rounds of hash function
- Logical functions: Ch, Maj, Σ0, Σ1, σ0, σ1
- Message schedule extension
- Hash value finalization
- File: `security/hashing.py` (400+ lines)

**Usage:**
```python
from security import sha256

hash_value = sha256("message")
# Returns: 64-character hexadecimal string
```

### 4. HMAC-SHA256

**Algorithm:** HMAC(K, M) = H((K ⊕ opad) || H((K ⊕ ipad) || M))

**Features:**
- Message authentication code generation
- Tamper detection
- Key derivation with padding
- File: `security/hashing.py` (included with SHA-256)

**Usage:**
```python
from security import hmac_sha256

tag = hmac_sha256("secret_key", "message")
# Returns: 64-character HMAC hex string

# Verify
is_valid = hmac_sha256("secret_key", "message") == tag
```

### 5. Password Hashing

**Implementation:** SHA-256 with random salt
```python
from security import hash_password, verify_password

# Hash password
hashed = hash_password("user_password")

# Verify password
is_valid = verify_password("user_password", hashed)
```

---

## API Endpoints

### Authentication Routes

#### POST /register
Register new user
```json
{
  "username": "john_doe",
  "email": "john@medlink.com",
  "password": "secure_password",
  "role": "patient"  // or "doctor", "specialist"
}
```
**Response:** Redirect to verification page

#### POST /login
User login
```json
{
  "email": "user@medlink.com",
  "password": "password"
}
```
**Response:** RSA challenge code (2FA step 1)

#### POST /verify-2fa
2FA code verification
```json
{
  "verification_code": "123456"
}
```
**Response:** Redirect to dashboard if successful

#### GET /logout
Logout user  
**Response:** Redirect to login page

### Dashboard Routes

#### GET /dashboard
Main dashboard page  
**Access:** Authenticated users  
**Features:** Activity overview, unread message count, pending approvals

#### GET /profile
User profile page  
**Access:** Authenticated users

#### POST /update-profile
Update user information  
**Access:** Authenticated users

### Messaging Routes

#### GET /chat-list
List all conversations  
**Features:**
- Shows active conversations first
- Displays unread message count
- Search bar to find new users

#### GET /chat/<user_id>
Open chat with user  
**Features:**
- Displays encrypted message history
- Auto-refresh every 2 seconds
- Auto-marks messages as read
- Real-time message decryption

#### POST /send_message
Send encrypted message
```json
{
  "receiver_id": 2,
  "message_content": "Hello, secure message"
}
```
**Response:** Encrypted message stored in database

### Medical Features Routes

#### GET /create-prescription
Create new prescription  
**Access:** Doctors only

#### POST /create-prescription
Submit prescription  
**Features:** End-to-end encryption, HMAC authentication

#### GET /patient-prescriptions
View patient's prescriptions  
**Access:** Patients (own), Doctors (assigned)

#### GET /refer-specialist
Create specialist referral  
**Access:** Doctors only

#### POST /refer-specialist
Submit referral  
**Features:** RSA digital signature, message encryption

### Admin Routes

#### GET /admin/dashboard
Admin control panel  
**Access:** Admin only  
**Features:** User management, activity monitoring

#### POST /admin/approve-user/<user_id>
Approve pending user  
**Access:** Admin only

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username VARCHAR(255) UNIQUE,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255),
  role VARCHAR(50),  -- 'patient', 'doctor', 'specialist', 'admin'
  is_verified BOOLEAN DEFAULT FALSE,
  is_approved BOOLEAN DEFAULT FALSE,
  two_fa_challenge VARCHAR(50),
  rsa_public_key TEXT,
  rsa_private_key TEXT,
  ecc_public_key TEXT,
  created_at TIMESTAMP
);
```

### Messages Table
```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  sender_id INTEGER,
  receiver_id INTEGER,
  content TEXT,  -- ECC encrypted
  hmac_tag VARCHAR(64),
  is_read BOOLEAN DEFAULT FALSE,
  timestamp TIMESTAMP,
  FOREIGN KEY(sender_id) REFERENCES users(id),
  FOREIGN KEY(receiver_id) REFERENCES users(id)
);
```

### Referrals Table
```sql
CREATE TABLE referrals (
  id INTEGER PRIMARY KEY,
  from_doctor_id INTEGER,
  to_specialist_id INTEGER,
  patient_id INTEGER,
  reason TEXT,
  rsa_signature TEXT,
  status VARCHAR(50),
  created_at TIMESTAMP,
  FOREIGN KEY(from_doctor_id) REFERENCES users(id),
  FOREIGN KEY(to_specialist_id) REFERENCES users(id),
  FOREIGN KEY(patient_id) REFERENCES users(id)
);
```

### Prescriptions Table
```sql
CREATE TABLE prescriptions (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER,
  patient_id INTEGER,
  medication VARCHAR(255),
  dosage VARCHAR(100),
  duration VARCHAR(100),
  document_steganographic TEXT,
  hmac_tag VARCHAR(64),
  created_at TIMESTAMP,
  FOREIGN KEY(doctor_id) REFERENCES users(id),
  FOREIGN KEY(patient_id) REFERENCES users(id)
);
```

---

## Usage Examples

### Example 1: Send Encrypted Message

```python
# 1. Login as patient
# Navigate to chat list

# 2. Find or search for doctor
# Click on doctor's name

# 3. In chat window, type message
# "I'm experiencing chest pain"

# 4. Backend automatically:
# - Encrypts message with ECC
# - Computes HMAC tag
# - Stores in database
# - Marks as unread for recipient

# 5. Doctor receives:
# - Unread badge on chat icon
# - Red "X new" badge on patient's card
# - Auto-decrypt message when opening chat
```

### Example 2: Create and Sign Referral

```python
# 1. Login as doctor
# Click "Refer Specialist"

# 2. Fill in:
# - Select patient
# - Select specialist
# - Reason: "Cardiology consultation"

# 3. Backend processes:
# - Generates RSA signature using doctor's private key
# - Encrypts referral details with specialist's public key
# - Stores in database with HMAC tag

# 4. Specialist receives:
# - Notification of pending referral
# - Can verify doctor's signature
# - Can decrypt referral details
```

### Example 3: Create Prescription

```python
# 1. Login as doctor
# Click "Create Prescription"

# 2. Fill in:
# - Select patient
# - Medication: "Aspirin"
# - Dosage: "500mg"
# - Duration: "10 days"

# 3. Backend:
# - Encrypts prescription with patient's ECC public key
# - Embeds in image using steganography
# - Computes HMAC for integrity

# 4. Patient can:
# - View prescription details
# - Download encrypted document
# - Verify authenticity with HMAC
```

### Example 4: Verify Message Wasn't Tampered

```python
# 1. Message received and stored:
# content = "encrypted_data"
# hmac_tag = "abc123def456..."

# 2. When displaying message:
# computed_tag = hmac_sha256(secret_key, content)
# if computed_tag == hmac_tag:
#   display "✅ Message verified - authentic"
# else:
#   display "⚠️ Warning: Message may have been tampered"
```

---

## Messaging System

### Features

#### 1. Real-Time Chat (2-second polling)
```javascript
// Auto-refresh messages every 2 seconds
setInterval(() => {
  fetch(`/chat/${userId}`)
    .then(response => response.text())
    .then(data => updateChatWindow(data))
}, 2000);
```

#### 2. Unread Message Tracking
- Backend counts unread messages per conversation
- Red badge shows count on sidebar chat icon
- Red "X new" badges on each conversation card
- Count deducts when messages are marked as read

#### 3. Active Conversations First
```
Your Conversations Section:
├── Rohim (Patient) - 3 new
├── patient@medlink.com (Patient) - 0 new
└── Dr. Doctor (Doctor) - 5 new

Search Results:
├── New User 1
└── New User 2
```

#### 4. End-to-End Encryption
- Messages encrypted with ECC + HMAC
- Only sender and receiver can read
- Encrypted ciphertext stored in database
- Automatic decryption on client side

#### 5. Message Read Status
```sql
-- Marked as read when chat is opened
UPDATE messages 
SET is_read = TRUE 
WHERE receiver_id = :user_id AND sender_id = :other_user
```

---

## Lab Defense Guide

### Quick Demo Script

#### 1. Security Features (5 minutes)
```
1. Show RSA key generation:
   - Open security/rsa.py
   - Highlight 6-step algorithm
   - Run demo: python -c "from security import RSAKeyGenerator; ..."

2. Show Message Encryption:
   - Login as Doctor
   - Send message to Patient
   - Check Live System Status
   - Show [SUCCESS] encrypted message log

3. Show HMAC Protection:
   - Visit /attack-simulator
   - Attempt to tamper with message
   - Show HMAC mismatch warning
```

#### 2. System Integration (5 minutes)
```
1. User Registration & 2FA:
   - Click Register
   - Enter demo data
   - Get 6-digit verification code
   - Enter code to verify

2. Admin Approval:
   - Login as Admin
   - Approve pending users
   - Switch role to show dashboard redirect

3. Chat System:
   - Login as Doctor
   - Send message to Patient
   - Show auto-refresh
   - Show unread badge deduction
```

#### 3. Encryption Demo (5 minutes)
```
1. Prescription Encryption:
   - Create prescription as Doctor
   - Download as Patient
   - Show steganographic storage

2. Referral Signing:
   - Create referral as Doctor
   - Show RSA signature verification
   - Specialist receives encrypted referral
```

### Technical Q&A Prep

**Q: How does message encryption work?**
A: We use ECC for key agreement + AES-256 for encryption + HMAC-SHA256 for authentication.

**Q: Why HMAC and not just ECC?**
A: HMAC provides message authentication and prevents tampering. ECC encrypts, HMAC authenticates.

**Q: What's the computational complexity?**
A: RSA: O(k log³ n), ECC scalar: O(log k), SHA-256: O(n) where n is message length.

**Q: How are passwords stored?**
A: SHA-256 with random salt: hash = SHA256(password + random_salt), salt stored with hash.

**Q: Can the admin decrypt user messages?**
A: No - messages are encrypted client-side with user's ECC public key. Admin has no access to private keys.

---

## Key Statistics

- **Total Code:** 2000+ lines
- **Security Package:** 1000+ lines (RSA, ECC, SHA-256, HMAC)
- **Flask App:** 700+ lines
- **Templates:** 15 HTML files
- **Database:** SQLite with 4 main tables

## Support & Testing

### Run Tests
```bash
python -m pytest tests/
```

### Check Logs
```
View Live System Status at: http://localhost:5001/system-log
```

### Debug Mode
```python
# In app.py, set:
app.run(debug=True)
```

---

## Version History

**v2.0 (April 18, 2026)**
- ✅ Complete messaging system with encryption
- ✅ Real-time chat with auto-refresh
- ✅ Unread message tracking
- ✅ Message read status tracking
- ✅ Fixed Jinja2 template syntax
- ✅ JSON serialization for User objects

**v1.0 (April 17, 2026)**
- ✅ RSA encryption implementation
- ✅ ECC implementation
- ✅ SHA-256 hashing
- ✅ HMAC authentication
- ✅ User authentication with 2FA
- ✅ Prescription management
- ✅ Specialist referrals
- ✅ Admin dashboard

---

**For more information or support, refer to the code comments in app.py and security/ modules.**
