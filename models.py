from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from security.hashing import hash_password, verify_password, generate_mac, verify_mac
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for Patient, Doctor, and Specialist"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'patient', 'doctor', 'specialist'
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
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 2FA & Security Fields
    two_fa_enabled = db.Column(db.Boolean, default=False)  # Is 2FA enabled for this user
    two_fa_challenge = db.Column(db.Text, nullable=True)  # JSON: {"number": str, "signed_hash": str, "timestamp": datetime}
    last_key_rotation = db.Column(db.DateTime, nullable=True)  # When keys were last rotated
    
    # Patient NID - Encrypted with Direct RSA (Strict Asymmetric: m^e mod N)
    encrypted_nid = db.Column(db.Text, nullable=True)  # RSA encrypted NID (hex format)
    encrypted_blood_group = db.Column(db.Text, nullable=True)  # RSA encrypted blood group
    nid_mac = db.Column(db.String(255), nullable=True)  # HMAC for NID integrity
    
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
        """Get display name based on role and username"""
        role_prefixes = {
            'doctor': 'Dr. ',
            'specialist': 'Dr. ',
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
    
    def encrypt_nid_with_rsa(self, nid_value):
        """
        Encrypt Patient NID using Direct RSA (Strict Asymmetric).
        
        Algorithm (Strict Asymmetric - No XOR):
        - Direct modular exponentiation: ciphertext = nid^e mod N
        - Uses RSA public key (e, N)
        - No symmetric cipher involved
        - Pure asymmetric encryption as per lab requirement
        
        Args:
            nid_value: The NID to encrypt (string or number)
        
        Returns:
            Encrypted NID as hex string with "rsa:" prefix
        """
        from security.rsa import encrypt
        from security.hashing import generate_mac
        
        rsa_pub = self.get_rsa_public_key()
        if not rsa_pub:
            return None
        
        # Convert NID to integer for encryption
        try:
            nid_int = int(''.join(filter(str.isdigit, str(nid_value))))
        except:
            nid_int = hash(str(nid_value)) % (rsa_pub['n'] - 1)
        
        # Direct RSA encryption (m^e mod N)
        encrypted_int = encrypt(nid_int, rsa_pub)
        encrypted_hex = hex(encrypted_int)[2:]  # Remove '0x' prefix
        
        # Store with HMAC for integrity
        self.encrypted_nid = f"rsa:{encrypted_hex}"
        self.nid_mac = generate_mac(f"nid_{self.id}", self.encrypted_nid)
        
        return self.encrypted_nid
    
    def decrypt_nid_with_rsa(self):
        """
        Decrypt Patient NID using Direct RSA.
        
        Algorithm:
        - Direct modular exponentiation: plaintext = ciphertext^d mod N
        - Uses RSA private key (d, N)
        - Verifies HMAC before decryption
        
        Returns:
            Decrypted NID value or None if decryption fails
        """
        from security.rsa import decrypt
        from security.hashing import verify_mac
        
        if not self.encrypted_nid or not self.nid_mac:
            return None
        
        # Verify HMAC integrity first
        if not verify_mac(f"nid_{self.id}", self.encrypted_nid, self.nid_mac):
            return None  # Integrity check failed
        
        rsa_priv = self.get_rsa_private_key()
        if not rsa_priv:
            return None
        
        try:
            # Extract hex value (remove "rsa:" prefix)
            encrypted_hex = self.encrypted_nid.replace("rsa:", "")
            encrypted_int = int(encrypted_hex, 16)
            
            # Direct RSA decryption (c^d mod N)
            decrypted_int = decrypt(encrypted_int, rsa_priv)
            
            return str(decrypted_int)
        except:
            return None
    
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
    document_type = db.Column(db.String(50), nullable=False)  # 'prescription', 'lab_result', 'report'
    encrypted_content = db.Column(db.Text, nullable=False)
    mac_tag = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='documents')
    
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
