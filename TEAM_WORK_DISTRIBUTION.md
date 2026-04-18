# MedLink Team Work Distribution

## Project Overview
MedLink is a secure medical collaboration platform with advanced cryptographic features. The project is divided among 3 team members, each specializing in different cryptographic algorithms while contributing to the overall security infrastructure.

---

## 👨‍💻 Team Member 1: ECC (Elliptic Curve Cryptography) Specialist

### Primary Responsibility
**Elliptic Curve Cryptography (ECC) Implementation and Integration**

### Assigned Work Areas

#### 1. **ECC Module Development** (`security/ecc.py`)
- **Responsibility**: Implement SECP256K1 elliptic curve cryptography
- **Key Functions**:
  - `Point` class: Represents points on the elliptic curve
  - `EllipticCurve` class: Core ECC operations (addition, doubling, scalar multiplication)
  - `create_test_curve()`: Initialize curve with standard parameters
  - Point arithmetic operations and validation

- **Code Flow**:
  ```
  Point(x, y) → ECC Curve Operations → Encrypted Output
  ```

#### 2. **Message Encryption** (`security/encryption_utils.py`)
- **Responsibility**: Implement `ecc_encrypt_message()` and `ecc_decrypt_message()` functions
- **Data Flow**:
  ```
  User Input (Chat Message)
         ↓
  ecc_encrypt_message(message, receiver_public_key)
         ↓
  Ephemeral key generation
         ↓
  ECDH key agreement
         ↓
  Symmetric encryption (XOR-based)
         ↓
  Encrypted message + ephemeral public key
         ↓
  Sent to Database/Network
  ```

#### 3. **Real-Time Chat Encryption** (`app.py` routes)
- **Responsibility**: Integrate ECC encryption into chat functionality
- **Routes to Handle**:
  - `/chat/<chat_id>` - Fetch encrypted messages
  - `/send_message` - Encrypt messages before storage
  - `/api/messages/send-realtime` - Real-time SocketIO encryption

- **Data Processing**:
  ```
  User types message in chat.html
         ↓
  JavaScript captures input
         ↓
  Encrypt using ECC public key (sent from server)
         ↓
  POST to /send_message with encrypted_message
         ↓
  app.py receives encrypted data
         ↓
  Store in database (Message model)
         ↓
  Broadcast to recipient via SocketIO
         ↓
  Recipient decrypts using their private key
  ```

#### 4. **Key Management for ECC**
- **Responsibility**: Generate and manage ECC key pairs
- **Database Fields** (`models.py`):
  - `ecc_public_key` - User's public key
  - `ecc_private_key` - User's private key (encrypted storage)

- **Implementation Location**: `models.py` - User model methods
  - `generate_ecc_keys()`
  - `get_ecc_public_key()`
  - `get_ecc_private_key()`

#### 5. **Frontend Integration** (`templates/base.html`, `templates/chat.html`)
- **Responsibility**: JavaScript crypto helper functions for ECC
- **Tasks**:
  - Create `ecc_encrypt.js` utilities
  - Integrate key exchange before messaging
  - Handle ephemeral key generation on client-side

### Files Under Responsibility
- ✅ `security/ecc.py` - Core ECC implementation
- ✅ `security/encryption_utils.py` - ECC encryption/decryption functions
- ✅ `templates/chat.html` - Chat UI with encryption
- ✅ `models.py` - ECC key storage fields
- ✅ `app.py` - Routes: `/chat`, `/send_message`, `/api/messages/send-realtime`

### Testing Responsibilities
- Unit tests for ECC point operations
- Integration tests for message encryption/decryption
- Test key generation and validation
- Test edge cases (point at infinity, invalid curves)

---

## 👨‍💻 Team Member 2: RSA (Rivest-Shamir-Adleman) Specialist

### Primary Responsibility
**RSA Encryption Implementation and Two-Factor Authentication**

### Assigned Work Areas

#### 1. **RSA Module Development** (`security/rsa.py`)
- **Responsibility**: Implement 1024-bit RSA cryptography
- **Key Functions**:
  - `generate_keys(key_size)` - Generate public/private key pairs
  - `encrypt(plaintext, public_key)` - RSA encryption
  - `decrypt(ciphertext, private_key)` - RSA decryption
  - `sign(message, private_key)` - Digital signature generation
  - `verify(message, signature, public_key)` - Signature verification

- **Code Flow**:
  ```
  Plaintext → RSA Encrypt (Public Key)
         ↓
  Ciphertext (encrypted with n, e)
         ↓
  Transmitted securely
         ↓
  RSA Decrypt (Private Key, d)
         ↓
  Original Plaintext
  ```

#### 2. **Two-Factor Authentication (2FA)** (`app.py`)
- **Responsibility**: Implement RSA-based 2FA challenge-response system
- **Routes to Handle**:
  - `/login` (POST) - Generate 2FA challenge
  - `/verify-2fa` (GET/POST) - Verify challenge response

- **Authentication Flow**:
  ```
  User enters email/password (login.html)
         ↓
  app.py: login() validates credentials
         ↓
  Generate random challenge_code (100000-999999)
         ↓
  Retrieve user's RSA private key
         ↓
  Sign challenge: signature = challenge^d mod n
         ↓
  Store in session:
    - pending_2fa_user_id
    - 2fa_challenge
    - 2fa_signed
         ↓
  Redirect to /verify-2fa page
         ↓
  User enters 6-digit challenge code
         ↓
  app.py: verify_2fa() compares input with session challenge
         ↓
  If matches: Complete login, set session user_id
         ↓
  Redirect to /dashboard
  ```

#### 3. **Email Encryption** (`security/encryption_utils.py`)
- **Responsibility**: Implement `encrypt_email_rsa()` and `decrypt_email_rsa()` functions
- **Use Cases**:
  - Encrypt user email addresses for secure storage
  - Protect email during transmission
  - Admin email management

- **Data Flow**:
  ```
  User registers with email
         ↓
  encrypt_email_rsa(email, admin_public_key)
         ↓
  Store encrypted email in database
         ↓
  Retrieve and decrypt_email_rsa(encrypted_email, admin_private_key)
         ↓
  Display to authorized users
  ```

#### 4. **Digital Signatures for Authentication** (`app.py`)
- **Responsibility**: Implement digital signatures for message authentication
- **Usage Locations**:
  - Sign prescription documents for non-repudiation
  - Authenticate API requests
  - Verify document integrity

- **Implementation Example**:
  ```
  Doctor creates prescription (create_prescription.html)
         ↓
  app.py receives prescription data
         ↓
  Generate signature: doc_signature = hash(prescription)^d mod n
         ↓
  Store signature with prescription in database
         ↓
  When verifying: Verify signature matches original data
  ```

#### 5. **Key Management for RSA**
- **Database Fields** (`models.py`):
  - `rsa_public_key` - User's public key (JSON format)
  - `rsa_private_key` - User's private key (encrypted storage)

- **Methods to Implement**:
  - `generate_rsa_keys()` - On user registration
  - `get_rsa_public_key()` - For encryption operations
  - `get_rsa_private_key()` - For decryption/signing

#### 6. **Admin Key Management** (`templates/rotate_keys.html`)
- **Responsibility**: Provide interface for RSA key rotation
- **Routes to Handle**:
  - `/rotate-keys` (GET) - Display current keys
  - `/api/rotate-keys` (POST) - Rotate RSA keys
  - `/api/re-encrypt-data` (POST) - Re-encrypt all data with new keys

### Files Under Responsibility
- ✅ `security/rsa.py` - Core RSA implementation (encryption, decryption, signing)
- ✅ `security/encryption_utils.py` - Email encryption functions
- ✅ `templates/login.html` - Login form UI
- ✅ `templates/verify_2fa.html` - 2FA verification UI
- ✅ `templates/rotate_keys.html` - Key rotation interface
- ✅ `models.py` - RSA key storage fields
- ✅ `app.py` - Routes: `/login`, `/verify-2fa`, `/rotate-keys`

### Testing Responsibilities
- Unit tests for RSA key generation
- Test RSA encryption/decryption
- Test digital signatures
- Test 2FA challenge-response
- Test edge cases (large numbers, prime validation)

---

## 👨‍💻 Team Member 3: Security Features & Infrastructure

### Primary Responsibility
**Hashing, HMAC, Data Integrity, and Security Infrastructure**

### Assigned Work Areas

#### 1. **SHA-256 Hashing Implementation** (`security/hashing.py`)
- **Responsibility**: Implement SHA-256 cryptographic hash function
- **Key Functions**:
  - `manual_sha256(data)` - SHA-256 hash computation
  - `hash_password(password)` - Password hashing with salt
  - `verify_password(password, hashed)` - Password verification

- **Code Flow**:
  ```
  User enters password (register.html / login.html)
         ↓
  hash_password(password)
         ↓
  Generate random salt
         ↓
  Compute: SHA256(salt + password + salt) iteratively
         ↓
  Store hash + salt in database
         ↓
  On login: verify_password(input, stored_hash)
  ```

#### 2. **HMAC Authentication** (`security/hashing.py`)
- **Responsibility**: Implement HMAC-SHA256 for message authentication
- **Functions**:
  - `generate_mac(message, key)` - Generate HMAC
  - `verify_mac(message, mac, key)` - Verify HMAC

- **Use Cases**:
  - Message authentication in API calls
  - Document integrity verification
  - Session data integrity

- **Data Flow**:
  ```
  User sends data to server
         ↓
  app.py receives POST request with data
         ↓
  Compute HMAC: mac = HMAC-SHA256(data, secret_key)
         ↓
  Store: { data, mac }
         ↓
  For verification: Recompute HMAC and compare
         ↓
  If mismatch: Data has been tampered, reject
  ```

#### 3. **Password Security** (`models.py`, `app.py`)
- **Responsibility**: Implement secure password management
- **User Model Methods** (`models.py`):
  - `set_password(password)` - Hash and store password
  - `check_password(password)` - Verify user password

- **Routes Using Password Hashing**:
  - `/register` (POST) - Hash password on registration
  - `/login` (POST) - Verify password during login
  - `/edit-profile` (POST) - Update password if provided

#### 4. **Database Model Design** (`models.py`)
- **Responsibility**: Design secure database schema
- **Models to Maintain**:
  - `User` - With encrypted password, RSA keys, ECC keys
  - `Message` - With encrypted content, HMAC
  - `Referral` - With signed and encrypted data
  - `Document` - With steganographic encoding

- **Security Features in Models**:
  ```python
  class User(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      username = db.Column(db.String(80), unique=True, nullable=False)
      email = db.Column(db.String(120), unique=True, nullable=False)
      password_hash = db.Column(db.String(255), nullable=False)  # SHA256
      password_salt = db.Column(db.String(255), nullable=False)
      rsa_public_key = db.Column(db.Text)
      rsa_private_key = db.Column(db.Text)  # Encrypted
      ecc_public_key = db.Column(db.Text)
      ecc_private_key = db.Column(db.Text)  # Encrypted
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
  ```

#### 5. **Session & Access Control** (`app.py`)
- **Responsibility**: Implement secure session management
- **Security Measures**:
  - Session-based authentication
  - CSRF protection
  - Role-based access control (RBAC)
  - Protected routes with `@login_required` decorator

- **Protected Routes Implementation**:
  ```
  User accesses /dashboard (protected)
         ↓
  Check: is user_id in session?
         ↓
  If NO: Redirect to /login
         ↓
  If YES: Verify session validity
         ↓
  Check: Does user have permission for role?
         ↓
  If authorized: Render page
         ↓
  If not: 403 Forbidden error
  ```

#### 6. **System Logging & Audit Trail** (`app.py`)
- **Responsibility**: Maintain comprehensive security logs
- **Functions**:
  - `add_system_log(message, status)` - Log security events
  - Log authentication attempts
  - Log encryption operations
  - Log key rotations
  - Log suspicious activities

- **Log Entries to Track**:
  ```
  [SUCCESS] 15:21:06 - ✓ LOGIN STEP 1: User | Challenge Generated: 943772
  [SUCCESS] 15:21:11 - ✓ 2FA VERIFIED: User | Challenge Code Matched
  [ERROR] 15:06:40 - ❌ LOGIN FAILED: Username - Invalid credentials
  [INFO] 15:22:21 - Admin panel accessed by System Admin
  ```

#### 7. **Data Integrity & Verification** (`app.py`)
- **Responsibility**: Ensure data hasn't been modified
- **Implementation**:
  - Verify HMAC on critical operations
  - Check digital signatures on documents
  - Validate encrypted message integrity
  - Audit trail for all modifications

#### 8. **Attack Simulation & Demo** (`templates/attack_simulator.html`)
- **Responsibility**: Educational tools for security demonstration
- **Features**:
  - Show impact of weak passwords
  - Demonstrate encryption importance
  - Educational attacks (for learning)

### Files Under Responsibility
- ✅ `security/hashing.py` - SHA256, HMAC, password hashing
- ✅ `models.py` - Database schema with security fields
- ✅ `app.py` - Authentication routes, session management, logging
- ✅ `templates/register.html` - Registration with password validation
- ✅ `templates/edit_profile.html` - Profile editing with password change
- ✅ `templates/system_log.html` - System activity viewer

### Testing Responsibilities
- Unit tests for SHA256 implementation
- Test HMAC generation and verification
- Test password hashing security
- Test session management
- Test access control on protected routes
- Load testing for performance

---

## 🔄 Collaboration Points

### Cross-Team Dependencies

```
┌─────────────────────────────────────────────────────────┐
│                    DATABASE (models.py)                  │
│    All teams contribute to User model and encryption    │
│                        fields                            │
└────┬──────────────┬─────────────────────────┬───────────┘
     │              │                         │
     ↓              ↓                         ↓
┌─────────────┐  ┌──────────────┐  ┌───────────────────┐
│   Team 1    │  │   Team 2     │  │     Team 3        │
│ ECC/Curves  │  │ RSA/2FA      │  │ Hashing/Integrity │
├─────────────┤  ├──────────────┤  ├───────────────────┤
│ ecc.py      │  │ rsa.py       │  │ hashing.py        │
│ Messages    │  │ Signatures   │  │ Sessions          │
│ Chat        │  │ Auth         │  │ Audit Trail       │
└─────────────┘  └──────────────┘  └───────────────────┘
```

### Shared Responsibilities
1. **encryption_utils.py** - All teams contribute utility functions
2. **app.py** - All teams implement their routes and logic
3. **models.py** - All teams add their encryption fields
4. **templates/** - All teams create/modify templates for their features

### Communication Protocol
- **Daily Sync**: Team standup on progress
- **Integration Points**: 
  - When adding encryption fields to User model
  - When creating new routes in app.py
  - When implementing new encryption utilities
- **Code Review**: Each team reviews others' cryptographic implementations
- **Testing**: Full integration testing before deployment

---

## 📊 Data Flow: User Registration to Secure Chat

```
1. REGISTRATION (templates/register.html)
   ├─→ Team 3: Hash password with SHA256 + salt
   ├─→ Team 2: Generate RSA key pair (1024-bit)
   ├─→ Team 1: Generate ECC key pair (SECP256K1)
   └─→ Store in User model: password_hash, RSA keys, ECC keys

2. LOGIN (templates/login.html)
   ├─→ Team 3: Verify password hash
   ├─→ Team 2: Generate 2FA challenge, sign with RSA
   └─→ Redirect to 2FA page

3. TWO-FACTOR AUTH (templates/verify_2fa.html)
   ├─→ Team 2: Verify challenge code
   └─→ Create session, redirect to dashboard

4. REAL-TIME CHAT (templates/chat.html)
   ├─→ User A types message
   ├─→ Team 1: Encrypt message using User B's ECC public key
   ├─→ Team 3: Generate HMAC for integrity
   ├─→ POST to /send_message
   ├─→ Team 1: app.py decrypts for verification
   ├─→ Store encrypted message in database
   ├─→ SocketIO broadcast to User B
   ├─→ User B decrypts using their ECC private key
   └─→ Display in chat UI

5. PRESCRIPTIONS (templates/create_prescription.html)
   ├─→ Doctor creates prescription
   ├─→ Team 2: Sign with RSA digital signature
   ├─→ Team 1: Optionally encrypt sensitive fields
   ├─→ Team 3: Generate HMAC for integrity check
   └─→ Store in Document model
```

---

## 🎯 Deliverables Checklist

### Team Member 1 (ECC)
- [ ] ECC point operations implemented (add, double, scalar multiply)
- [ ] SECP256K1 curve initialized
- [ ] Message encryption/decryption working
- [ ] Chat messages encrypted end-to-end
- [ ] Key exchange mechanism in place
- [ ] All ECC routes tested

### Team Member 2 (RSA)
- [ ] RSA key generation (1024-bit) implemented
- [ ] RSA encryption/decryption working
- [ ] Digital signatures implemented
- [ ] 2FA challenge-response working
- [ ] Email encryption functional
- [ ] Key rotation working

### Team Member 3 (Security)
- [ ] SHA-256 hashing implemented
- [ ] HMAC-SHA256 generation and verification
- [ ] Password hashing with salt
- [ ] User authentication routes secure
- [ ] Session management functional
- [ ] Access control implemented
- [ ] System logging active
- [ ] All models secure with encryption fields

---

## 🚀 Deployment Checklist

- [ ] All cryptographic functions tested independently
- [ ] Integration tests pass between all modules
- [ ] No hardcoded secrets (all in environment variables)
- [ ] Database securely initialized
- [ ] All routes have proper error handling
- [ ] Security headers configured
- [ ] HTTPS enabled (if deploying to production)
- [ ] Session management configured
- [ ] All team members reviewed each other's code
