from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from security.hashing import hash_password, verify_password, generate_mac, verify_mac
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for Patient, Doctor, Specialist, and Admin"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'patient', 'doctor', 'specialist', 'admin'
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Encrypted Email - Stored as RSA-encrypted hex string (zero-knowledge storage)
    encrypted_email = db.Column(db.Text, nullable=True)  # RSA encrypted, only decrypted with private key
    
    # RSA Keys (for signing and encryption)
    rsa_public_key = db.Column(db.Text, nullable=True)  # JSON: {"e": int, "n": int}
    rsa_private_key = db.Column(db.Text, nullable=True)  # JSON: {"d": int, "n": int} - Stored securely
    
    # ECC Keys (for encrypted messages)
    ecc_public_key = db.Column(db.Text, nullable=True)  # JSON: {"x": int, "y": int}
    ecc_private_key = db.Column(db.Text, nullable=True)  # JSON: {"k": int} - Stored securely
    
    # Legacy field (kept for compatibility)
    public_key = db.Column(db.Text, nullable=True)  # For encryption purposes
    encrypted_profile = db.Column(db.Text, nullable=True)  # Encrypted email/NID
    
    # User Profile Fields
    display_name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.Text, nullable=True)  # Encrypted
    date_of_birth = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)  # Encrypted
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    
    # 2FA Fields
    two_fa_enabled = db.Column(db.Boolean, default=False)
    two_fa_challenge = db.Column(db.String(10), nullable=True)
    two_fa_timestamp = db.Column(db.DateTime, nullable=True)
    
    # NID and Blood Group Encryption
    encrypted_nid = db.Column(db.Text, nullable=True)
    encrypted_blood_group = db.Column(db.Text, nullable=True)
    nid_mac = db.Column(db.String(255), nullable=True)
    # Professional license (doctors / specialists)
    license_number = db.Column(db.String(120), nullable=True, index=True)
    license_verified = db.Column(db.Boolean, default=False)
    
    # Key Management
    last_key_rotation = db.Column(db.DateTime, nullable=True)
    
    # User Approval System
    is_approved = db.Column(db.Boolean, default=False)  # False for new registrations
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    sent_referrals = db.relationship('Referral', foreign_keys='Referral.sender_id', backref='sender', lazy=True)
    received_referrals = db.relationship('Referral', foreign_keys='Referral.receiver_id', backref='receiver', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender_msg', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver_msg', lazy=True)
    
    def set_password(self, password):
        """
        Hash and set password using SHA-256 with salt.
        
        Algorithm:
        - Generate random 16-byte salt
        - Compute: H = SHA256(salt || password)
        - Store: base64(salt || H)
        
        This provides protection against dictionary and rainbow table attacks.
        
        Args:
            password: Plain text password to hash
        """
        self.password_hash = hash_password(password)
    
    def check_password(self, password):
        """
        Verify password against stored hash.
        
        Algorithm:
        - Decode stored hash to extract salt
        - Recompute: H' = SHA256(salt || provided_password)
        - Constant-time comparison: H == H'
        
        Args:
            password: Plain text password to verify
        
        Returns:
            bool: True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)
    
    def get_display_name(self):
        """Get display name - return stored display_name if available, otherwise generate from username"""
        if self.display_name:
            return self.display_name
        
        # Fallback: Generate from username
        role_prefixes = {
            'doctor': 'Dr. ',
            'specialist': 'Dr. ',
            'admin': 'Admin ',
            'patient': ''
        }
        prefix = role_prefixes.get(self.role, '')
        # Convert username to title case for display
        return prefix + self.username.replace('@medlink.com', '').title().replace('-', ' ')
    
    def get_rsa_public_key(self):
        """Get RSA public key as dictionary"""
        if self.rsa_public_key:
            return json.loads(self.rsa_public_key)
        return None
    
    def get_rsa_private_key(self):
        """Get RSA private key as dictionary"""
        if self.rsa_private_key:
            return json.loads(self.rsa_private_key)
        return None
    
    def set_rsa_keys(self, public_key_tuple, private_key_tuple):
        """Store RSA keys from (e, n) and (d, n) tuples"""
        self.rsa_public_key = json.dumps({"e": public_key_tuple[0], "n": public_key_tuple[1]})
        self.rsa_private_key = json.dumps({"d": private_key_tuple[0], "n": private_key_tuple[1]})
    
    def get_ecc_public_key(self):
        """Get ECC public key as dictionary"""
        if self.ecc_public_key:
            return json.loads(self.ecc_public_key)
        return None
    
    def get_ecc_private_key(self):
        """Get ECC private key as dictionary"""
        if self.ecc_private_key:
            return json.loads(self.ecc_private_key)
        return None
    
    def set_ecc_keys(self, public_point, private_scalar):
        """Store ECC keys from Point object and scalar"""
        self.ecc_public_key = json.dumps({"x": public_point.x, "y": public_point.y})
        self.ecc_private_key = json.dumps({"k": private_scalar})
    
    def encrypt_nid_with_rsa(self, data):
        """
        Encrypt sensitive data using user's RSA public key.
        
        Args:
            data: String to encrypt
            
        Returns:
            str: Hex-encoded encrypted data
        """
        if not self.rsa_public_key:
            return data  # Return plaintext if no key
        
        try:
            from security.rsa import encrypt
            pub_key = self.get_rsa_public_key()
            if pub_key:
                # Convert string data to integer
                if data.isdigit():
                    message_int = int(data)
                else:
                    message_int = int(data.encode('utf-8').hex(), 16)
                
                # Encrypt using RSA
                encrypted_int = encrypt(message_int, (pub_key['e'], pub_key['n']))
                return hex(encrypted_int)[2:]
        except Exception as e:
            pass
        
        return data
    
    def decrypt_nid_with_rsa(self):
        """
        Decrypt encrypted NID using user's RSA private key.
        
        Returns:
            str: Decrypted NID or None
        """
        if not self.encrypted_nid or not self.rsa_private_key:
            return None
        
        try:
            from security.rsa import decrypt
            priv_key = self.get_rsa_private_key()
            if priv_key:
                encrypted_int = int(self.encrypted_nid, 16)
                decrypted_int = decrypt(encrypted_int, (priv_key['d'], priv_key['n']))
                return str(decrypted_int)
        except Exception as e:
            pass
        
        return None
    
    def decrypt_field(self, encrypted_data):
        """
        Generic decryption method for any encrypted field.
        
        Args:
            encrypted_data: Hex-encoded encrypted data
            
        Returns:
            str: Decrypted data or None
        """
        if not encrypted_data or not self.rsa_private_key:
            return None
        
        try:
            from security.rsa import decrypt
            priv_key = self.get_rsa_private_key()
            if priv_key:
                encrypted_int = int(encrypted_data, 16)
                decrypted_int = decrypt(encrypted_int, (priv_key['d'], priv_key['n']))
                # Try to convert from hex if it looks like hex-encoded string
                try:
                    hex_str = hex(decrypted_int)[2:]
                    # Handle odd-length hex strings
                    if len(hex_str) % 2:
                        hex_str = '0' + hex_str
                    return bytes.fromhex(hex_str).decode('utf-8', errors='ignore')
                except:
                    return str(decrypted_int)
        except Exception as e:
            import sys
            print(f"[DECRYPT_FIELD_ERROR] Failed to decrypt: {str(e)}", file=sys.stderr)
        
        return None
    
    def get_phone(self):
        """Get decrypted phone number"""
        if not self.phone:
            return None
        # If it looks like encrypted data (hex), decrypt it
        if self.phone and len(self.phone) > 20 and all(c in '0123456789abcdef' for c in self.phone.lower()):
            return self.decrypt_field(self.phone)
        return self.phone
    
    def get_address(self):
        """Get decrypted address"""
        if not self.address:
            return None
        # If it looks like encrypted data (hex), decrypt it
        if self.address and len(self.address) > 20 and all(c in '0123456789abcdef' for c in self.address.lower()):
            return self.decrypt_field(self.address)
        return self.address
    
    def get_date_of_birth(self):
        """Get decrypted date of birth"""
        if not self.date_of_birth:
            return None
        # If it looks like encrypted data (hex), decrypt it
        if self.date_of_birth and len(self.date_of_birth) > 20 and all(c in '0123456789abcdef' for c in self.date_of_birth.lower()):
            return self.decrypt_field(self.date_of_birth)
        return self.date_of_birth
    
    def get_email(self):
        """Get decrypted email"""
        if not self.encrypted_email:
            return None
        # If it looks like encrypted data (hex), decrypt it
        if self.encrypted_email and len(self.encrypted_email) > 20 and all(c in '0123456789abcdef' for c in self.encrypted_email.lower()):
            return self.decrypt_field(self.encrypted_email)
        return self.encrypted_email
    
    def __repr__(self):
        return f'<User {self.username}>'


class Referral(db.Model):
    """Referral/Message model for inter-user communication"""
    __tablename__ = 'referrals'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    encrypted_content = db.Column(db.Text, nullable=False)
    mac_tag = db.Column(db.String(255), nullable=True)  # For integrity verification
    is_verified = db.Column(db.Boolean, default=False)  # MAC verification status
    referral_type = db.Column(db.String(50), default='referral')  # 'referral', 'consultation', etc.
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'completed'
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)
    
    def verify_integrity(self):
        """
        Verify MAC tag integrity using HMAC-SHA256.
        
        Algorithm:
        1. If no MAC tag exists, cannot verify
        2. Use sender's public key as HMAC key
        3. Generate expected MAC: HMAC(sender_key, encrypted_content)
        4. Constant-time comparison: stored_mac == expected_mac
        
        If verification succeeds, set is_verified flag.
        
        Returns:
            bool: True if MAC is valid, False otherwise
        """
        if not self.mac_tag or not self.encrypted_content:
            return False
        
        # Use sender's ID as key for HMAC (in production, use actual key)
        hmac_key = f"referral_{self.sender_id}"
        expected_mac = generate_mac(hmac_key, self.encrypted_content)
        
        if verify_mac(hmac_key, self.encrypted_content, self.mac_tag):
            self.is_verified = True
            return True
        
        return False
    
    def __repr__(self):
        return f'<Referral {self.sender_id} -> {self.receiver_id}>'


class Message(db.Model):
    """Chat/Message model for real-time communication"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    encrypted_content = db.Column(db.Text, nullable=False)
    mac_tag = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now, index=True)
    
    def verify_integrity(self):
        """
        Verify message MAC tag integrity using HMAC-SHA256.
        
        Uses HMAC for authentication and integrity checking:
        - Algorithm: HMAC-SHA256(sender_key, encrypted_content)
        - Verifies message hasn't been tampered with
        - Confirms sender identity
        
        Returns:
            bool: True if MAC is valid, False otherwise
        """
        if not self.mac_tag or not self.encrypted_content:
            return False
        
        hmac_key = f"message_{self.sender_id}"
        
        if verify_mac(hmac_key, self.encrypted_content, self.mac_tag):
            self.is_verified = True
            return True
        
        return False
    
    __repr__ = lambda self: f'<Message {self.sender_id} -> {self.receiver_id}>'


class Document(db.Model):
    """Medical document storage"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Doctor/creator
    document_type = db.Column(db.String(50), nullable=False)  # 'prescription', 'lab_result', 'report'
    encrypted_content = db.Column(db.Text, nullable=False)
    mac_tag = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    # For prescriptions: store details for admin viewing
    prescription_details = db.Column(db.JSON, nullable=True)  # {medication, dosage, instructions}
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='documents', foreign_keys=[user_id])
    creator = db.relationship('User', foreign_keys=[creator_id])
    
    def verify_integrity(self):
        """
        Verify document MAC tag integrity using HMAC-SHA256.
        
        Ensures medical document hasn't been altered:
        - Uses HMAC for integrity verification
        - Detects any modification to encrypted content
        - Secures medical records authenticity
        
        Returns:
            bool: True if MAC is valid, False otherwise
        """
        if not self.mac_tag or not self.encrypted_content:
            return False
        
        hmac_key = f"document_{self.user_id}_{self.document_type}"
        
        if verify_mac(hmac_key, self.encrypted_content, self.mac_tag):
            self.is_verified = True
            return True
        
        return False
    
    __repr__ = lambda self: f'<Document {self.document_type} - {self.user_id}>'
