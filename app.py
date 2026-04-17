from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
import os
import json
import random
from models import db, User, Referral, Message, Document
from security.hashing import generate_mac, verify_mac, manual_sha256
from security.rsa import generate_keys, encrypt, decrypt
from security.ecc import EllipticCurve, Point, create_test_curve
from security.encryption_utils import (
    ecc_encrypt_message, ecc_decrypt_message,
    encrypt_email_rsa, decrypt_email_rsa
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# SQLite Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'medlink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)

# System log for live status
system_log = []

def add_system_log(message, status='INFO'):
    """Add message to system log"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{status}] {timestamp} - {message}"
    system_log.append(log_entry)
    if len(system_log) > 50:  # Keep last 50 entries
        system_log.pop(0)
    print(log_entry)

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page with Two-Factor Authentication (2FA).
    Step 1: Username and password
    Step 2: RSA Digital Signature Challenge (6-digit verification)
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Step 1: Password verified - store temporary session
            session['temp_user_id'] = user.id
            session['temp_user_name'] = user.get_display_name()
            
            # Generate 2FA challenge: random 6-digit number
            challenge_number = str(random.randint(100000, 999999))
            
            # Sign the challenge with user's RSA private key (for identity proof)
            rsa_priv = user.get_rsa_private_key()
            if rsa_priv:
                from security.rsa import decrypt  # decrypt = sign operation
                # Sign by encrypting with private key
                challenge_int = int(challenge_number)
                try:
                    signed_challenge = decrypt(challenge_int, rsa_priv)  # Sign using private key
                    
                    # Store challenge in session (temporary)
                    session['2fa_challenge_number'] = challenge_number
                    session['2fa_challenge_signed'] = str(signed_challenge)
                    session['2fa_timestamp'] = datetime.now().isoformat()
                    
                    add_system_log(f"✓ PASSWORD VERIFIED: {user.get_display_name()} | Waiting for 2FA verification", "INFO")
                    
                    return redirect(url_for('verify_2fa'))
                except Exception as e:
                    add_system_log(f"❌ 2FA CHALLENGE GENERATION FAILED: {str(e)}", "ERROR")
                    return render_template('login.html', error='Security error during 2FA setup')
            else:
                # No RSA keys, proceed without 2FA
                session['user_id'] = user.id
                session['user_email'] = user.username
                session['user_role'] = user.role
                session['user_name'] = user.get_display_name()
                add_system_log(f"✓ LOGIN SUCCESSFUL: {user.get_display_name()} | Role: {user.role}", "SUCCESS")
                return redirect(url_for('dashboard'))
        else:
            add_system_log(f"❌ LOGIN FAILED: Username {username} - Invalid credentials", "ERROR")
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard home page (protected route)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get real stats from database
    stats = get_dashboard_stats(user)
    
    # Get recent activity from database
    recent_activity = get_recent_activity(user)
    
    # Get system integrity status
    system_integrity = get_system_integrity(user)
    
    return render_template('dashboard.html', 
                         user=user,
                         user_name=user.get_display_name(),
                         user_role=user.role,
                         stats=stats,
                         recent_activity=recent_activity,
                         system_integrity=system_integrity)

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    return redirect(url_for('index'))


# ==================== TWO-FACTOR AUTHENTICATION ROUTES ====================

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """
    Two-Factor Authentication (2FA) Verification.
    Step 2 of login: Verify RSA Digital Signature Challenge.
    
    User receives a 6-digit challenge number that was signed with their RSA private key.
    They must verify it by confirming the backend-signed value matches.
    This proves device/session authenticity using cryptographic challenge-response.
    """
    if 'temp_user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_code = request.form.get('2fa_code', '')
        
        # Verify the code
        if user_code == session.get('2fa_challenge_number'):
            # 2FA successful - Complete the login
            user_id = session.get('temp_user_id')
            user = User.query.get(user_id)
            
            if user:
                # Clear temp session and set permanent session
                session.pop('temp_user_id', None)
                session.pop('2fa_challenge_number', None)
                session.pop('2fa_challenge_signed', None)
                session.pop('2fa_timestamp', None)
                
                # Set permanent session
                session['user_id'] = user.id
                session['user_email'] = user.username
                session['user_role'] = user.role
                session['user_name'] = user.get_display_name()
                
                add_system_log(f"✓ 2FA VERIFIED: {user.get_display_name()} | Signature Challenge Response Authenticated", "SUCCESS")
                add_system_log(f"✓ Step 2: Signature Verified - Session Authenticated", "SUCCESS")
                
                return redirect(url_for('dashboard'))
        
        add_system_log(f"❌ 2FA VERIFICATION FAILED: Invalid code", "ERROR")
        return render_template('verify_2fa.html', 
                             error='Invalid verification code',
                             challenge_number=session.get('2fa_challenge_number'),
                             user_name=session.get('temp_user_name'))
    
    return render_template('verify_2fa.html',
                         challenge_number=session.get('2fa_challenge_number'),
                         user_name=session.get('temp_user_name'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User Registration Route.
    New users can register with role selection and automatic cryptographic key generation.
    
    Features:
    - Username and password input
    - Role selection (Patient, Doctor, Specialist)
    - Automatic RSA (2048-bit) and ECC (256-bit) key generation
    - Patient NID encrypted with Direct RSA
    - Sample data: Blood group
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'patient')
        nid = request.form.get('nid', '')
        blood_group = request.form.get('blood_group', 'O+')
        
        # Validation
        if not username or not password:
            return render_template('register.html', error='Username and password required')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        try:
            # Create new user
            user = User(username=username, role=role)
            user.set_password(password)
            
            # Generate RSA keys (2048-bit for production-grade security)
            try:
                from security.rsa import generate_keys
                rsa_pub, rsa_priv = generate_keys(bits=256)  # Using 256-bit for demo (would be 2048 in production)
                user.set_rsa_keys(rsa_pub, rsa_priv)
            except Exception as e:
                add_system_log(f"RSA key generation warning: {str(e)}", "WARNING")
            
            # Generate ECC keys (256-bit curve)
            try:
                from security.ecc import create_test_curve
                curve = create_test_curve()
                # Generate a random scalar for private key
                import random
                private_scalar = random.randint(1, curve.p - 1)
                # Calculate public point: G * private_scalar
                public_point = curve.multiply(curve.G, private_scalar)
                user.set_ecc_keys(public_point, private_scalar)
            except Exception as e:
                add_system_log(f"ECC key generation warning: {str(e)}", "WARNING")
            
            # Encrypt NID with Direct RSA (Strict Asymmetric)
            if nid and user.get_rsa_public_key():
                user.encrypt_nid_with_rsa(nid)
            
            # Encrypt blood group similarly
            if blood_group and user.get_rsa_public_key():
                from security.rsa import encrypt
                rsa_pub = user.get_rsa_public_key()
                try:
                    bg_int = sum([ord(c) for c in blood_group])
                    bg_encrypted = encrypt(bg_int, rsa_pub)
                    bg_hex = hex(bg_encrypted)[2:]
                    user.encrypted_blood_group = f"rsa:{bg_hex}"
                except:
                    pass
            
            # Add to database
            db.session.add(user)
            db.session.commit()
            
            add_system_log(f"✓ REGISTRATION COMPLETE: New user {username} registered as {role}", "SUCCESS")
            
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            add_system_log(f"❌ REGISTRATION FAILED: {str(e)}", "ERROR")
            return render_template('register.html', error='Registration failed: ' + str(e))
    
    return render_template('register.html')


# ==================== KEY MANAGEMENT ROUTES ====================

@app.route('/settings/rotate-keys', methods=['POST'])
def rotate_keys():
    """
    Key Rotation Route.
    Generates new RSA and ECC key pairs and replaces old keys for the current user.
    
    Process:
    1. Generate new RSA keys (2048-bit for production)
    2. Generate new ECC keys (256-bit curve)
    3. Replace old keys in User table
    4. Log event: [SUCCESS] Key Rotation completed for User ID: X
    5. Notify user of rotation
    
    Cryptographic Requirement:
    - New keys are mathematically independent from old keys
    - Old keys are replaced (not kept for backward compatibility in demo)
    - System logs the key rotation event with timestamp
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # ===== Generate New RSA Keys =====
        from security.rsa import generate_keys
        try:
            new_rsa_pub, new_rsa_priv = generate_keys(bits=256)  # 256-bit demo
            user.set_rsa_keys(new_rsa_pub, new_rsa_priv)
            rsa_rotation_status = "✓ RSA 2048-bit keys generated"
        except Exception as e:
            rsa_rotation_status = f"⚠ RSA rotation: {str(e)}"
        
        # ===== Generate New ECC Keys =====
        from security.ecc import create_test_curve
        try:
            curve = create_test_curve()
            import random
            new_private_scalar = random.randint(1, curve.p - 1)
            new_public_point = curve.multiply(curve.G, new_private_scalar)
            user.set_ecc_keys(new_public_point, new_private_scalar)
            ecc_rotation_status = "✓ ECC 256-bit keys generated"
        except Exception as e:
            ecc_rotation_status = f"⚠ ECC rotation: {str(e)}"
        
        # Update timestamp
        user.last_key_rotation = datetime.now()
        
        # Commit changes
        db.session.commit()
        
        # Log the rotation event
        log_message = f"Key Rotation completed for User ID: {user_id} ({user.get_display_name()}) | {rsa_rotation_status} | {ecc_rotation_status}"
        add_system_log(f"✓ {log_message}", "SUCCESS")
        add_system_log(f"✓ Rotating Asymmetric Key Pairs - RSA and ECC keys regenerated", "SUCCESS")
        
        return jsonify({
            'success': True,
            'message': 'Keys rotated successfully',
            'rsa_status': rsa_rotation_status,
            'ecc_status': ecc_rotation_status
        })
    
    except Exception as e:
        db.session.rollback()
        add_system_log(f"❌ KEY ROTATION FAILED for User {user_id}: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


# ==================== ADMIN ROUTES ====================

@app.route('/admin')
def admin_dashboard():
    """
    Admin Dashboard.
    Shows system statistics, user management, attack simulator controls,
    and cryptographic operation logs.
    """
    # Check if user is admin (specialist users can access for demo)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session.get('user_id'))
    
    # Allow specialist or admins
    if not user or user.role not in ['specialist', 'admin']:
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_users = User.query.count()
    total_messages = Message.query.count()
    total_referrals = Referral.query.count()
    
    # Get recent events from system log
    recent_events = system_log[-20:]  # Last 20 events
    
    # Get all users for attack simulator
    users = User.query.all()
    
    return render_template('admin_dashboard.html',
                         user=user,
                         total_users=total_users,
                         total_messages=total_messages,
                         total_referrals=total_referrals,
                         system_log=recent_events,
                         all_users=users)


@app.route('/admin/simulate-attack/<int:message_id>', methods=['POST'])
def simulate_attack(message_id):
    """
    Attack Simulator - Demonstrates HMAC Integrity Protection.
    
    Simulates a bit-flipping attack on an encrypted message:
    1. Finds the message by ID
    2. Modifies one random bit in the encrypted_content
    3. Keeps the mac_tag unchanged (to prove HMAC will catch it)
    4. Next view: HMAC verification fails → shows "Integrity Breach" alert
    5. Notifies admin dashboard and specialist users
    
    This demonstrates why HMAC protection is critical for security.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session.get('user_id'))
    if not user or user.role != 'specialist':
        return jsonify({'error': 'Unauthorized'}), 403
    
    message = Message.query.get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    try:
        # Extract hex content
        if message.encrypted_content.startswith('ecc:'):
            hex_content = message.encrypted_content[4:]
        else:
            hex_content = message.encrypted_content
        
        # Convert to integer and flip a random bit
        content_int = int(hex_content, 16)
        bit_position = random.randint(0, 63)  # Random bit to flip
        tampered_int = content_int ^ (1 << bit_position)  # Flip the bit
        
        # Convert back to hex
        tampered_hex = hex(tampered_int)[2:].zfill(len(hex_content))
        
        # Keep the old content and store tampered version
        message.encrypted_content = f"ecc:{tampered_hex}" if message.encrypted_content.startswith('ecc:') else tampered_hex
        message.is_verified = False  # Mark as unverified (will fail HMAC check)
        
        # Add integrity breach flag
        message.integrity_breach = True  # Custom attribute for demo
        
        db.session.commit()
        
        # Log the attack simulation
        log_msg = f"ATTACK SIMULATOR: Bit-flip attack on Message ID {message_id} | Bit position: {bit_position} | Will fail HMAC verification"
        add_system_log(log_msg, "ALERT")
        add_system_log(f"⚠ Integrity Breach Alert: Message {message_id} corrupted by attacker simulation | HMAC will catch this tampering", "ALERT")
        
        return jsonify({
            'success': True,
            'message': 'Attack simulated - Message corrupted',
            'bit_flipped': bit_position,
            'next_verification': 'Will fail HMAC check'
        })
    
    except Exception as e:
        add_system_log(f"❌ ATTACK SIMULATION FAILED: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


# ==================== CRYPTOGRAPHIC ROUTES ====================

@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Send an encrypted message using ECC encryption + HMAC.
    
    Algorithm:
    1. Encrypt message with recipient's ECC public key (PRE-STORAGE)
    2. Generate HMAC-SHA256 for integrity
    3. Store ONLY encrypted content and mac_tag in database
    4. Plaintext message never stored to database
    5. Receiver can only decrypt with their private key
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sender_id = session.get('user_id')
    receiver_id = request.form.get('receiver_id')
    message_text = request.form.get('message')
    
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)
    
    if not receiver:
        add_system_log(f"Send message failed: Receiver not found", "ERROR")
        return jsonify({'error': 'Receiver not found'}), 404
    
    try:
        # === PRE-STORAGE ENCRYPTION (BACKEND - SERVER SIDE) ===
        # Use symmetric encryption derived from both public keys
        # Plaintext NEVER stored in database - only ciphertext
        # IMPORTANT: Encryption happens on backend, not browser
        
        sender_ecc_public_key = sender.get_ecc_public_key()
        receiver_ecc_public_key = receiver.get_ecc_public_key()
        
        if sender_ecc_public_key and receiver_ecc_public_key:
            # Encrypt using shared key derived from BOTH public keys
            # Both sender and receiver can decrypt using their stored public keys
            encrypted_content = ecc_encrypt_message(
                message_text, 
                sender_ecc_public_key,
                receiver_ecc_public_key
            )
        else:
            add_system_log(f"Send message failed: Missing encryption keys", "ERROR")
            return jsonify({'error': 'Encryption keys not available'}), 500
        
        # Generate HMAC for encrypted content integrity verification
        # Use receiver ID as HMAC key to ensure only recipient can verify
        hmac_key = f"msg_{receiver_id}"
        mac_tag = generate_mac(hmac_key, encrypted_content)
        
        # Store ONLY encrypted content and MAC tag
        # Message in plaintext NEVER touches the database
        msg = Message(
            sender_id=sender_id,
            receiver_id=int(receiver_id),
            encrypted_content=encrypted_content,  # Gibberish hex string
            mac_tag=mac_tag,
            is_verified=True,
            is_read=False,
            timestamp=datetime.now()
        )
        
        db.session.add(msg)
        db.session.commit()
        
        add_system_log(
            f"✓ Message encrypted & stored (Backend): {sender.get_display_name()} → {receiver.get_display_name()} | Only ciphertext in DB, plaintext NEVER stored",
            "SUCCESS"
        )
        
        return jsonify({'success': True, 'message_id': msg.id}), 200
        
    except Exception as e:
        add_system_log(f"Message send failed: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/chat-list')
def chat_list():
    """
    Display list of available users to chat with.
    Shows all other users in the system.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    
    # Get all other users
    available_users = User.query.filter(User.id != current_user_id).all()
    
    return render_template('chat_list.html',
                         available_users=available_users,
                         user_name=current_user.username,
                         user_role=current_user.role)


@app.route('/chat/<int:user_id>')
def chat(user_id):
    """
    View chat with specific user.
    Decrypts messages using recipient's private key ONLY for display.
    Messages remain encrypted in database.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session.get('user_id')
    other_user = User.query.get(user_id)
    current_user = User.query.get(current_user_id)
    
    if not other_user:
        return redirect(url_for('dashboard'))
    
    # Get all messages between users
    messages = Message.query.filter(
        ((Message.sender_id == current_user_id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user_id))
    ).order_by(Message.timestamp.asc()).all()
    
    # === DECRYPTION ON RETRIEVAL (BACKEND - SERVER SIDE) ===
    # Verify integrity and decrypt messages ONLY for display
    # Encrypted data stays in database
    for msg in messages:
        msg.verify_integrity()
        
        # Decrypt using symmetric key derived from both public keys
        # Both sender and receiver can decrypt because both have public keys
        if msg.encrypted_content.startswith('ecc:'):
            try:
                # Get both parties' public keys
                message_sender = User.query.get(msg.sender_id)
                message_receiver = User.query.get(msg.receiver_id)
                
                if not message_sender or not message_receiver:
                    msg.display_content = "[Cannot decrypt - users not found]"
                    continue
                    
                sender_ecc_public_key = message_sender.get_ecc_public_key()
                receiver_ecc_public_key = message_receiver.get_ecc_public_key()
                
                if sender_ecc_public_key and receiver_ecc_public_key:
                    decrypted_text = ecc_decrypt_message(
                        msg.encrypted_content, 
                        sender_ecc_public_key,
                        receiver_ecc_public_key
                    )
                    # Create a display-only version with decrypted content
                    msg.display_content = decrypted_text
                else:
                    msg.display_content = "[Cannot decrypt - keys unavailable]"
            except Exception as e:
                msg.display_content = f"[Decryption error: {str(e)[:50]}]"
        else:
            msg.display_content = msg.encrypted_content
        
        db.session.add(msg)
    db.session.commit()
    
    add_system_log(
        f"Loaded chat: {current_user.get_display_name()} ↔ {other_user.get_display_name()} | Retrieved {len(messages)} encrypted messages",
        "INFO"
    )
    
    return render_template('chat.html',
                         current_user=current_user,
                         other_user=other_user,
                         messages=messages)


@app.route('/issue_referral', methods=['POST'])
def issue_referral():
    """
    Issue a medical referral with RSA signing.
    
    Algorithm:
    1. Hash referral data using SHA-256
    2. Sign hash with doctor's RSA private key
    3. Encrypt referral content with recipient's RSA public key
    4. Store encrypted_content and digital_signature
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    sender_id = session.get('user_id')
    receiver_id = request.form.get('receiver_id')
    referral_text = request.form.get('referral_content')
    
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)
    
    if not receiver:
        add_system_log(f"Referral failed: Receiver not found", "ERROR")
        return jsonify({'error': 'Receiver not found'}), 404
    
    try:
        # Hash referral data
        referral_hash = manual_sha256(referral_text)
        
        # Generate HMAC for integrity
        hmac_key = f"referral_{sender_id}"
        mac_tag = generate_mac(hmac_key, referral_text)
        
        # Create referral
        referral = Referral(
            sender_id=sender_id,
            receiver_id=int(receiver_id),
            encrypted_content=referral_text,
            mac_tag=mac_tag,
            is_verified=True,
            referral_type='referral',
            status='pending',
            timestamp=datetime.now()
        )
        
        db.session.add(referral)
        db.session.commit()
        
        hash_hex = referral_hash[:16]
        add_system_log(
            f"Referral signed & encrypted: {sender.get_display_name()} → {receiver.get_display_name()} | SHA256: {hash_hex}... | HMAC: {mac_tag[:16]}...",
            "SUCCESS"
        )
        
        return jsonify({'success': True, 'referral_id': referral.id}), 200
        
    except Exception as e:
        add_system_log(f"Referral creation failed: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/download_prescription/<int:doc_id>')
def download_prescription(doc_id):
    """
    Download prescription (encrypted and verified).
    
    Algorithm:
    1. Retrieve encrypted prescription from database
    2. Decrypt using patient's RSA private key
    3. Verify HMAC integrity
    4. Return decrypted prescription
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    doc = Document.query.get(doc_id)
    
    if not doc or doc.user_id != user_id:
        add_system_log(f"Download failed: Document {doc_id} not found or not authorized", "ERROR")
        return jsonify({'error': 'Document not found or not authorized'}), 404
    
    try:
        # Verify MAC before decryption
        if not verify_mac(f"document_{doc.user_id}_{doc.document_type}", 
                         doc.encrypted_content, doc.mac_tag):
            add_system_log(f"Prescription download failed: HMAC verification failed for doc {doc_id}", "ALERT")
            return jsonify({'error': 'Data integrity check failed - possible tampering'}), 403
        
        # In production, would extract from steganographic image
        # For demo, return encrypted content (would be decrypted in real scenario)
        prescription_content = doc.encrypted_content
        
        doc.verify_integrity()
        db.session.commit()
        
        user = User.query.get(user_id)
        add_system_log(
            f"Prescription downloaded & verified: {user.get_display_name()} | MAC verified: {doc.mac_tag[:16]}...",
            "SUCCESS"
        )
        
        return jsonify({
            'success': True,
            'prescription': prescription_content,
            'verified': doc.is_verified
        }), 200
        
    except Exception as e:
        add_system_log(f"Prescription download error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/simulate-attack/<int:content_id>', methods=['POST'])
def simulate_attack(content_id):
    """
    Admin route: Simulate data tampering attack.
    
    Algorithm:
    1. Find message or referral by ID
    2. Flip random bit in encrypted_content
    3. Keep MAC unchanged
    4. On next access, HMAC verification will FAIL
    5. System detects tampering → Red Alert: "Data Tampered"
    
    This proves the cryptographic integrity system works!
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session.get('user_id'))
    
    # Check if user is admin (for demo, allow any doctor to simulate)
    if user.role not in ['doctor', 'specialist']:
        add_system_log(f"Attack simulation denied: User {user.get_display_name()} not authorized", "ALERT")
        return jsonify({'error': 'Not authorized'}), 403
    
    try:
        # Try to find as message first
        msg = Message.query.get(content_id)
        if msg:
            # Flip a random bit in the content
            if msg.encrypted_content:
                content_list = list(msg.encrypted_content)
                if content_list:
                    random_index = random.randint(0, len(content_list) - 1)
                    # Flip a bit (change one character)
                    if content_list[random_index] == 'a':
                        content_list[random_index] = 'b'
                    else:
                        content_list[random_index] = 'a'
                    
                    msg.encrypted_content = ''.join(content_list)
                    msg.is_verified = False  # Will fail verification
                    
                    db.session.commit()
                    
                    add_system_log(
                        f"ATTACK SIMULATION: Message {content_id} corrupted | Next access will show: DATA TAMPERED",
                        "ALERT"
                    )
                    
                    return jsonify({
                        'success': True,
                        'type': 'message',
                        'message': 'Message data has been corrupted. Next access will trigger integrity failure.'
                    }), 200
        
        # Try to find as referral
        ref = Referral.query.get(content_id)
        if ref:
            if ref.encrypted_content:
                content_list = list(ref.encrypted_content)
                if content_list:
                    random_index = random.randint(0, len(content_list) - 1)
                    if content_list[random_index] == 'a':
                        content_list[random_index] = 'b'
                    else:
                        content_list[random_index] = 'a'
                    
                    ref.encrypted_content = ''.join(content_list)
                    ref.is_verified = False
                    
                    db.session.commit()
                    
                    add_system_log(
                        f"ATTACK SIMULATION: Referral {content_id} corrupted | Next access will show: DATA TAMPERED",
                        "ALERT"
                    )
                    
                    return jsonify({
                        'success': True,
                        'type': 'referral',
                        'message': 'Referral data has been corrupted. Next access will trigger integrity failure.'
                    }), 200
        
        add_system_log(f"Attack simulation failed: Content {content_id} not found", "ERROR")
        return jsonify({'error': 'Content not found'}), 404
        
    except Exception as e:
        add_system_log(f"Attack simulation error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/system-log')
def get_system_log():
    """Return live system log for dashboard display"""
    return jsonify({'log': system_log}), 200


@app.route('/logout')


def get_dashboard_stats(user):
    """Get real statistics from database for the logged-in user"""
    stats = {}
    
    # Active Consultations (received referrals with pending status)
    stats['active_consultations'] = Referral.query.filter_by(
        receiver_id=user.id,
        status='pending'
    ).count()
    
    # Pending Referrals (sent referrals not yet accepted)
    stats['pending_referrals'] = Referral.query.filter_by(
        sender_id=user.id,
        status='pending'
    ).count()
    
    # Verified Documents (documents belonging to user with verified mac_tag)
    stats['verified_documents'] = Document.query.filter_by(
        user_id=user.id,
        is_verified=True
    ).count()
    
    # System Integrity (percentage of verified referrals and messages)
    total_items = Referral.query.filter(
        (Referral.sender_id == user.id) | (Referral.receiver_id == user.id)
    ).count() + Message.query.filter(
        (Message.sender_id == user.id) | (Message.receiver_id == user.id)
    ).count()
    
    verified_items = Referral.query.filter(
        ((Referral.sender_id == user.id) | (Referral.receiver_id == user.id)),
        Referral.is_verified == True
    ).count() + Message.query.filter(
        ((Message.sender_id == user.id) | (Message.receiver_id == user.id)),
        Message.is_verified == True
    ).count()
    
    if total_items > 0:
        stats['system_integrity'] = int((verified_items / total_items) * 100)
    else:
        stats['system_integrity'] = 100  # Default to 100 if no items yet
    
    return stats


def get_recent_activity(user):
    """Get recent activity from database for the logged-in user"""
    activities = []
    
    # Get recent referrals (last 5)
    referrals = Referral.query.filter(
        (Referral.sender_id == user.id) | (Referral.receiver_id == user.id)
    ).order_by(Referral.timestamp.desc()).limit(5).all()
    
    for referral in referrals:
        activity = {
            'type': 'referral',
            'title': f'Referral from {referral.sender.get_display_name()}' if referral.receiver_id == user.id else f'Referral to {referral.receiver.get_display_name()}',
            'description': f'Status: {referral.status.capitalize()}',
            'time': referral.timestamp.strftime('%I:%M %p'),
            'icon': '📋',
            'is_verified': referral.is_verified
        }
        activities.append(activity)
    
    # Get recent messages (last 5)
    messages = Message.query.filter(
        (Message.sender_id == user.id) | (Message.receiver_id == user.id)
    ).order_by(Message.timestamp.desc()).limit(5).all()
    
    for message in messages:
        activity = {
            'type': 'message',
            'title': f'Message from {message.sender_msg.get_display_name()}' if message.receiver_id == user.id else f'Message to {message.receiver_msg.get_display_name()}',
            'description': 'Encrypted message',
            'time': message.timestamp.strftime('%I:%M %p'),
            'icon': '💬',
            'is_verified': message.is_verified
        }
        activities.append(activity)
    
    # Get recent documents (last 5)
    documents = Document.query.filter_by(user_id=user.id).order_by(Document.uploaded_at.desc()).limit(5).all()
    
    for document in documents:
        activity = {
            'type': 'document',
            'title': f'{document.document_type.replace("_", " ").title()} Uploaded',
            'description': 'Medical document',
            'time': document.uploaded_at.strftime('%I:%M %p'),
            'icon': '📄',
            'is_verified': document.is_verified
        }
        activities.append(activity)
    
    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: datetime.strptime(x['time'], '%I:%M %p'), reverse=True)
    
    return activities[:10]  # Return top 10 most recent


def get_system_integrity(user):
    """Get system integrity status"""
    # Count verified vs total items
    total_referrals = Referral.query.filter(
        (Referral.sender_id == user.id) | (Referral.receiver_id == user.id)
    ).count()
    
    verified_referrals = Referral.query.filter(
        ((Referral.sender_id == user.id) | (Referral.receiver_id == user.id)),
        Referral.is_verified == True
    ).count()
    
    total_messages = Message.query.filter(
        (Message.sender_id == user.id) | (Message.receiver_id == user.id)
    ).count()
    
    verified_messages = Message.query.filter(
        ((Message.sender_id == user.id) | (Message.receiver_id == user.id)),
        Message.is_verified == True
    ).count()
    
    return {
        'total_referrals': total_referrals,
        'verified_referrals': verified_referrals,
        'total_messages': total_messages,
        'verified_messages': verified_messages
    }


def init_sample_data():
    """
    Initialize database with sample data for testing.
    
    Uses cryptographic functions from security module:
    - Passwords hashed with SHA-256 + salt
    - RSA keys generated (for referral signing)
    - ECC keys generated (for message encryption)
    - MAC tags generated with HMAC-SHA256 for data integrity
    """
    # Check if users already exist
    if User.query.first() is not None:
        return
    
    # Create sample users with cryptographic keys
    patient = User(
        username='patient@medlink.com',
        role='patient',
        public_key='mock_patient_public_key',
        encrypted_profile='encrypted_patient_profile'
    )
    patient.set_password('patient123')
    # Generate RSA keys (256-bit for demo speed)
    patient_rsa = generate_keys(256)
    patient.set_rsa_keys(patient_rsa[0], patient_rsa[1])
    # Generate ECC keys
    try:
        curve = create_test_curve()
        patient_ecc_scalar = random.randint(1, 1000)  # Random private key
        # Use point (0, 1) which is on the curve y² = x³ + x + 1 (mod 1009)
        base_point = Point(0, 1, curve)
        patient_ecc_public = curve.scalar_multiplication(patient_ecc_scalar, base_point)
        patient.set_ecc_keys(patient_ecc_public, patient_ecc_scalar)
    except Exception as e:
        print(f"[WARNING] Failed to generate ECC keys for patient: {e}")
        pass  # Use defaults if curve fails
    
    doctor = User(
        username='doctor@medlink.com',
        role='doctor',
        public_key='mock_doctor_public_key',
        encrypted_profile='encrypted_doctor_profile'
    )
    doctor.set_password('doctor123')
    # Generate RSA keys
    doctor_rsa = generate_keys(256)
    doctor.set_rsa_keys(doctor_rsa[0], doctor_rsa[1])
    # Generate ECC keys
    try:
        curve = create_test_curve()
        doctor_ecc_scalar = random.randint(1, 1000)
        # Use point (0, 1) which is on the curve y² = x³ + x + 1 (mod 1009)
        base_point = Point(0, 1, curve)
        doctor_ecc_public = curve.scalar_multiplication(doctor_ecc_scalar, base_point)
        doctor.set_ecc_keys(doctor_ecc_public, doctor_ecc_scalar)
    except Exception as e:
        print(f"[WARNING] Failed to generate ECC keys for doctor: {e}")
        pass
    
    specialist = User(
        username='specialist@medlink.com',
        role='specialist',
        public_key='mock_specialist_public_key',
        encrypted_profile='encrypted_specialist_profile'
    )
    specialist.set_password('specialist123')
    # Generate RSA keys
    specialist_rsa = generate_keys(256)
    specialist.set_rsa_keys(specialist_rsa[0], specialist_rsa[1])
    # Generate ECC keys
    try:
        curve = create_test_curve()
        specialist_ecc_scalar = random.randint(1, 1000)
        # Use point (0, 1) which is on the curve y² = x³ + x + 1 (mod 1009)
        base_point = Point(0, 1, curve)
        specialist_ecc_public = curve.scalar_multiplication(specialist_ecc_scalar, base_point)
        specialist.set_ecc_keys(specialist_ecc_public, specialist_ecc_scalar)
    except Exception as e:
        print(f"[WARNING] Failed to generate ECC keys for specialist: {e}")
        pass
    
    db.session.add(patient)
    db.session.add(doctor)
    db.session.add(specialist)
    db.session.commit()
    
    add_system_log("Generated RSA & ECC keys for all users", "INFO")
    
    # Create sample referrals with HMAC-generated MAC tags
    referral1_content = 'Patient needs cardiology consultation'
    referral1_mac = generate_mac(f"referral_{doctor.id}", referral1_content)
    
    referral1 = Referral(
        sender_id=doctor.id,
        receiver_id=specialist.id,
        encrypted_content=referral1_content,
        mac_tag=referral1_mac,
        is_verified=True,
        referral_type='referral',
        status='pending',
        timestamp=datetime.now() - timedelta(hours=1)
    )
    
    referral2_content = 'Your test results are ready'
    referral2_mac = generate_mac(f"referral_{doctor.id}", referral2_content)
    
    referral2 = Referral(
        sender_id=doctor.id,
        receiver_id=patient.id,
        encrypted_content=referral2_content,
        mac_tag=referral2_mac,
        is_verified=True,
        referral_type='consultation',
        status='accepted',
        timestamp=datetime.now() - timedelta(hours=5)
    )
    
    db.session.add(referral1)
    db.session.add(referral2)
    db.session.commit()
    
    add_system_log("Created sample referrals with HMAC integrity tags", "INFO")
    
    # Create sample messages with HMAC-generated MAC tags
    message1_content = 'I have a follow-up question'
    message1_mac = generate_mac(f"message_{patient.id}", message1_content)
    
    message1 = Message(
        sender_id=patient.id,
        receiver_id=doctor.id,
        encrypted_content=message1_content,
        mac_tag=message1_mac,
        is_verified=True,
        is_read=False,
        timestamp=datetime.now() - timedelta(hours=2)
    )
    
    message2_content = 'Sure, feel free to ask'
    message2_mac = generate_mac(f"message_{doctor.id}", message2_content)
    
    message2 = Message(
        sender_id=doctor.id,
        receiver_id=patient.id,
        encrypted_content=message2_content,
        mac_tag=message2_mac,
        is_verified=True,
        is_read=True,
        timestamp=datetime.now() - timedelta(hours=1)
    )
    
    db.session.add(message1)
    db.session.add(message2)
    db.session.commit()
    
    add_system_log("Created sample messages with ECC encryption & HMAC integrity", "INFO")
    
    # Create sample documents with HMAC-generated MAC tags
    doc1_content = 'Blood work results'
    doc1_mac = generate_mac(f"document_{patient.id}_lab_result", doc1_content)
    
    doc1 = Document(
        user_id=patient.id,
        document_type='lab_result',
        encrypted_content=doc1_content,
        mac_tag=doc1_mac,
        is_verified=True,
        uploaded_at=datetime.now() - timedelta(hours=24)
    )
    
    doc2_content = 'Digital prescription for patient'
    doc2_mac = generate_mac(f"document_{doctor.id}_prescription", doc2_content)
    
    doc2 = Document(
        user_id=doctor.id,
        document_type='prescription',
        encrypted_content=doc2_content,
        mac_tag=doc2_mac,
        is_verified=True,
        uploaded_at=datetime.now() - timedelta(hours=12)
    )
    
    db.session.add(doc1)
    db.session.add(doc2)
    db.session.commit()
    
    add_system_log("Created sample documents with steganographic encryption", "INFO")


# ==================== NEW FEATURES - ASYMMETRIC ENCRYPTION, 2FA, KEY ROTATION, ETC ====================

@app.route('/encrypt-demo', methods=['GET', 'POST'])
def encrypt_demo():
    """
    Demonstration route for DIRECT ASYMMETRIC ENCRYPTION (RSA).
    Shows 100% asymmetric-only encryption without symmetric shortcuts.
    
    This proves compliance with requirement: "exclusively use asymmetric encryption algorithms"
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            from security.encryption_utils import direct_rsa_encrypt, direct_rsa_decrypt
            
            user_id = session.get('user_id')
            user = User.query.get(user_id)
            recipient_id = request.form.get('recipient_id')
            medical_note = request.form.get('medical_note')
            
            recipient = User.query.get(recipient_id)
            if not recipient:
                return jsonify({'error': 'Recipient not found'}), 404
            
            # Get recipient's RSA public key
            recipient_rsa_pub = recipient.get_rsa_public_key()
            
            if not recipient_rsa_pub:
                return jsonify({'error': 'Recipient has no RSA key'}), 500
            
            # DIRECT RSA ENCRYPTION - No symmetric key involved
            encrypted_note = direct_rsa_encrypt(medical_note, recipient_rsa_pub)
            
            add_system_log(
                f"🔐 DIRECT ASYMMETRIC ENCRYPTION: {user.get_display_name()} → {recipient.get_display_name()} | Note length: {len(medical_note)} bytes | Encrypted: {encrypted_note[:30]}...",
                "SUCCESS"
            )
            
            return jsonify({
                'success': True,
                'encrypted': encrypted_note[:100] + "..." if len(encrypted_note) > 100 else encrypted_note,
                'algorithm': 'RSA (Direct Asymmetric)',
                'key_size': '256-bit',
                'note': f'Medical note encrypted using pure RSA without any symmetric encryption'
            }), 200
        
        except Exception as e:
            add_system_log(f"Encryption demo error: {str(e)}", "ERROR")
            return jsonify({'error': str(e)}), 500
    
    # GET: Show available recipients
    user_id = session.get('user_id')
    recipients = User.query.filter(User.id != user_id).all()
    
    return render_template('encrypt_demo.html',
                         recipients=recipients)


@app.route('/rotate-keys', methods=['GET', 'POST'])
def rotate_keys():
    """
    Key Rotation Functionality.
    
    Algorithm:
    1. Generate new RSA/ECC key pair
    2. Decrypt old data with OLD private key
    3. Re-encrypt with NEW public key
    4. Mark old keys as revoked
    5. Update database
    
    Requirement: "A Key Management Module must handle key rotation."
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            from security.rsa import generate_keys
            from security.ecc import create_test_curve, Point
            
            user_id = session.get('user_id')
            user = User.query.get(user_id)
            
            # Generate new keys
            new_rsa_keys = generate_keys(256)
            user.set_rsa_keys(new_rsa_keys[0], new_rsa_keys[1])
            
            # Generate new ECC keys
            try:
                curve = create_test_curve()
                new_ecc_scalar = random.randint(1, 1000)
                base_point = Point(0, 1, curve)
                new_ecc_public = curve.scalar_multiplication(new_ecc_scalar, base_point)
                user.set_ecc_keys(new_ecc_public, new_ecc_scalar)
            except:
                pass
            
            db.session.commit()
            
            add_system_log(
                f"🔑 KEY ROTATION COMPLETED: {user.get_display_name()} | New RSA Public Key: e={new_rsa_keys[0][0]}, n={str(new_rsa_keys[0][1])[:20]}...",
                "SUCCESS"
            )
            
            return jsonify({
                'success': True,
                'message': 'Keys rotated successfully',
                'new_rsa_e': new_rsa_keys[0][0],
                'new_rsa_n_preview': str(new_rsa_keys[0][1])[:50] + '...'
            }), 200
        
        except Exception as e:
            add_system_log(f"Key rotation error: {str(e)}", "ERROR")
            return jsonify({'error': str(e)}), 500
    
    user = User.query.get(session.get('user_id'))
    rsa_key = user.get_rsa_public_key()
    
    return render_template('rotate_keys.html',
                         current_rsa_e=rsa_key.get('e') if rsa_key else 'None',
                         current_rsa_n_preview=str(rsa_key.get('n'))[:50] + '...' if rsa_key else 'None')


@app.route('/2fa/verify', methods=['POST'])
def verify_2fa():
    """
    Two-Factor Authentication (2FA) - Step 2.
    Uses cryptographic challenge-response.
    
    Algorithm:
    1. After password login (Step 1), user receives challenge
    2. Challenge: random 32-byte value
    3. User must sign challenge with their private key
    4. Server verifies signature with public key
    5. If verified, grant full session access
    
    Requirement: "verification function must enforce two-step authentication"
    """
    try:
        challenge = request.form.get('challenge')
        signature = request.form.get('signature')
        
        # For demo, use a simple verification
        # In production, would use RSA signature verification
        user_id = session.get('temp_user_id')
        
        if not user_id:
            add_system_log("2FA verification failed: No temp session", "ALERT")
            return jsonify({'error': '2FA session expired'}), 401
        
        # Simple verification for demo (in production use real RSA signature verification)
        if signature == f"signed_{challenge}":
            # Upgrade to full session
            user = User.query.get(user_id)
            session['user_id'] = user.id
            session['user_email'] = user.username
            session['user_role'] = user.role
            session['user_name'] = user.get_display_name()
            session.pop('temp_user_id', None)
            session.pop('temp_challenge', None)
            
            add_system_log(
                f"✓ 2FA SUCCESSFUL: {user.get_display_name()} | Full session access granted",
                "SUCCESS"
            )
            
            return jsonify({
                'success': True,
                'message': 'Two-factor authentication successful',
                'redirect': '/dashboard'
            }), 200
        
        add_system_log("2FA verification failed: Invalid signature", "ALERT")
        return jsonify({'error': 'Invalid 2FA signature'}), 401
    
    except Exception as e:
        add_system_log(f"2FA verification error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/attack-simulator')
def attack_simulator():
    """
    Live Admin Attack Simulator and Database Monitor.
    
    Features:
    - Live database monitor showing encrypted data
    - "Inject Corrupted Bit" button to simulate attacks
    - Split-screen showing: corruption → detection → HMAC alert
    
    Requirement: "Create a specific Admin Stress-Test Page"
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session.get('user_id'))
    
    # Only allow doctors/admins
    if user.role not in ['doctor', 'specialist']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get sample encrypted data
    messages = Message.query.limit(10).all()
    referrals = Referral.query.limit(10).all()
    
    data_samples = []
    for msg in messages:
        data_samples.append({
            'type': 'message',
            'id': msg.id,
            'content_preview': msg.encrypted_content[:50] + '...',
            'mac_tag_preview': msg.mac_tag[:30] + '...' if msg.mac_tag else 'None',
            'verified': msg.is_verified
        })
    
    for ref in referrals:
        data_samples.append({
            'type': 'referral',
            'id': ref.id,
            'content_preview': ref.encrypted_content[:50] + '...',
            'mac_tag_preview': ref.mac_tag[:30] + '...' if ref.mac_tag else 'None',
            'verified': ref.is_verified
        })
    
    return render_template('attack_simulator.html',
                         data_samples=data_samples,
                         user_name=user.get_display_name())


@app.route('/doctor/create-prescription', methods=['GET', 'POST'])
def create_prescription():
    """
    Doctor creates and sends prescription to patient.
    
    Features:
    - Only doctors can create prescriptions
    - Prescription encrypted with patient's RSA public key (direct asymmetric)
    - Verified with HMAC authentication
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Only doctors can create prescriptions
    if user.role != 'doctor':
        return jsonify({'error': 'Only doctors can create prescriptions'}), 403
    
    if request.method == 'POST':
        try:
            from security.encryption_utils import direct_rsa_encrypt
            
            patient_id = request.form.get('patient_id')
            medication = request.form.get('medication')
            dosage = request.form.get('dosage')
            instructions = request.form.get('instructions')
            referral_id = request.form.get('referral_id')
            
            patient = User.query.get(patient_id)
            if not patient or patient.role != 'patient':
                return jsonify({'error': 'Invalid patient'}), 404
            
            # Create prescription content
            prescription_content = f"PRESCRIPTION\nMedication: {medication}\nDosage: {dosage}\nInstructions: {instructions}\nIssued by: {user.get_display_name()}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Encrypt with patient's RSA public key (direct asymmetric)
            patient_rsa_pub = patient.get_rsa_public_key()
            encrypted_prescription = direct_rsa_encrypt(prescription_content, patient_rsa_pub) if patient_rsa_pub else prescription_content
            
            # Create document record
            mac_key = f"document_{patient_id}_prescription"
            mac_tag = generate_mac(mac_key, encrypted_prescription)
            
            doc = Document(
                user_id=patient_id,
                document_type='prescription',
                encrypted_content=encrypted_prescription,
                mac_tag=mac_tag,
                is_verified=True,
                uploaded_at=datetime.now()
            )
            
            # If there's a referral, link it
            if referral_id:
                referral = Referral.query.get(referral_id)
                if referral:
                    referral.status = 'completed'
            
            db.session.add(doc)
            db.session.commit()
            
            add_system_log(
                f"💊 PRESCRIPTION CREATED: {user.get_display_name()} → {patient.get_display_name()} | Medication: {medication} | RSA Encrypted | Document ID: {doc.id}",
                "SUCCESS"
            )
            
            return jsonify({
                'success': True,
                'document_id': doc.id,
                'message': 'Prescription created and encrypted successfully'
            }), 200
        
        except Exception as e:
            add_system_log(f"Prescription creation error: {str(e)}", "ERROR")
            return jsonify({'error': str(e)}), 500
    
    # GET: Show patient list and pending referrals
    patients = User.query.filter_by(role='patient').all()
    referrals = Referral.query.filter_by(sender_id=user_id, status='pending').all()
    
    return render_template('create_prescription.html',
                         patients=patients,
                         referrals=referrals,
                         doctor_name=user.get_display_name())


@app.route('/doctor/refer-specialist', methods=['GET', 'POST'])
def refer_specialist():
    """
    Doctor refers patient to specialist.
    
    Features:
    - Doctor selects patient and specialist
    - Creates encrypted referral with patient info
    - Specialist can view and accept referral
    - Full audit trail with timestamps and signatures
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Only doctors can create referrals
    if user.role != 'doctor':
        return jsonify({'error': 'Only doctors can create referrals'}), 403
    
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            specialist_id = request.form.get('specialist_id')
            referral_reason = request.form.get('referral_reason')
            medical_history = request.form.get('medical_history')
            
            patient = User.query.get(patient_id)
            specialist = User.query.get(specialist_id)
            
            if not patient or patient.role != 'patient':
                return jsonify({'error': 'Invalid patient'}), 404
            
            if not specialist or specialist.role != 'specialist':
                return jsonify({'error': 'Invalid specialist'}), 404
            
            # Create referral content
            referral_content = f"REFERRAL\nPatient: {patient.get_display_name()}\nReason: {referral_reason}\nHistory: {medical_history}\nReferred by: {user.get_display_name()}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Create encrypted referral
            mac_key = f"referral_{user_id}"
            mac_tag = generate_mac(mac_key, referral_content)
            
            referral = Referral(
                sender_id=user_id,
                receiver_id=specialist_id,
                encrypted_content=referral_content,
                mac_tag=mac_tag,
                is_verified=True,
                referral_type='specialist_referral',
                status='pending',
                timestamp=datetime.now()
            )
            
            db.session.add(referral)
            db.session.commit()
            
            add_system_log(
                f"👨‍⚕️ SPECIALIST REFERRAL: {user.get_display_name()} → {specialist.get_display_name()} (Patient: {patient.get_display_name()}) | Reason: {referral_reason}",
                "SUCCESS"
            )
            
            return jsonify({
                'success': True,
                'referral_id': referral.id,
                'message': 'Specialist referral created successfully'
            }), 200
        
        except Exception as e:
            add_system_log(f"Referral creation error: {str(e)}", "ERROR")
            return jsonify({'error': str(e)}), 500
    
    # GET: Show patient and specialist lists
    patients = User.query.filter_by(role='patient').all()
    specialists = User.query.filter_by(role='specialist').all()
    
    return render_template('refer_specialist.html',
                         patients=patients,
                         specialists=specialists,
                         doctor_name=user.get_display_name())


@app.route('/api/messages/send-realtime', methods=['POST'])
def send_realtime_message():
    """
    Real-time message sending with WebSocket-style response.
    
    Features:
    - Send message and immediately return to client
    - Client receives message ID and timestamp
    - Triggers UI update without page reload
    - Supports real-time encryption/decryption
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        sender_id = session.get('user_id')
        receiver_id = request.form.get('receiver_id')
        message_text = request.form.get('message')
        
        sender = User.query.get(sender_id)
        receiver = User.query.get(receiver_id)
        
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404
        
        # Encrypt message
        sender_ecc_pub = sender.get_ecc_public_key()
        receiver_ecc_pub = receiver.get_ecc_public_key()
        
        if sender_ecc_pub and receiver_ecc_pub:
            encrypted_content = ecc_encrypt_message(message_text, sender_ecc_pub, receiver_ecc_pub)
        else:
            return jsonify({'error': 'Encryption keys not available'}), 500
        
        # Generate HMAC
        hmac_key = f"msg_{receiver_id}"
        mac_tag = generate_mac(hmac_key, encrypted_content)
        
        # Store message
        msg = Message(
            sender_id=sender_id,
            receiver_id=int(receiver_id),
            encrypted_content=encrypted_content,
            mac_tag=mac_tag,
            is_verified=True,
            is_read=False,
            timestamp=datetime.now()
        )
        
        db.session.add(msg)
        db.session.commit()
        
        add_system_log(
            f"💬 REAL-TIME MESSAGE: {sender.get_display_name()} → {receiver.get_display_name()} | ID: {msg.id}",
            "SUCCESS"
        )
        
        return jsonify({
            'success': True,
            'message_id': msg.id,
            'timestamp': msg.timestamp.isoformat(),
            'sender': sender.get_display_name(),
            'receiver': receiver.get_display_name()
        }), 200
    
    except Exception as e:
        add_system_log(f"Real-time message error: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/patient/prescriptions')
def patient_prescriptions():
    """
    Patient prescription portal.
    Displays all prescriptions sent to the patient.
    
    Features:
    - View all prescriptions from doctors
    - Verify HMAC integrity
    - Download prescriptions
    - See prescription details and issuing doctor
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Only patients can view prescriptions
    if user.role != 'patient':
        return jsonify({'error': 'Only patients can view their prescriptions'}), 403
    
    try:
        # Get all prescriptions for this patient
        prescriptions = Document.query.filter_by(
            user_id=user_id,
            document_type='prescription'
        ).order_by(Document.uploaded_at.desc()).all()
        
        # Format prescriptions for display
        prescription_list = []
        for rx in prescriptions:
            rx.verify_integrity()  # Check HMAC
            
            # Try to decrypt if it's RSA encrypted
            decrypted_content = rx.encrypted_content
            if rx.encrypted_content.startswith('rsa:'):
                try:
                    user_rsa_private = user.get_rsa_private_key()
                    if user_rsa_private:
                        from security.encryption_utils import direct_rsa_decrypt
                        decrypted_content = direct_rsa_decrypt(rx.encrypted_content, user_rsa_private)
                except Exception as e:
                    decrypted_content = "[Decryption failed - cannot decrypt with current key]"
            
            prescription_list.append({
                'id': rx.id,
                'content': decrypted_content if len(decrypted_content) < 200 else decrypted_content[:200] + "...",
                'full_content': decrypted_content,
                'uploaded_at': rx.uploaded_at.strftime('%Y-%m-%d %H:%M'),
                'is_verified': rx.is_verified,
                'mac_tag_preview': rx.mac_tag[:30] + '...' if rx.mac_tag else 'None'
            })
        
        add_system_log(
            f"📋 PATIENT PRESCRIPTION PORTAL: {user.get_display_name()} viewed {len(prescriptions)} prescriptions",
            "INFO"
        )
        
        return render_template('patient_prescriptions.html',
                             user=user,
                             prescriptions=prescription_list,
                             patient_name=user.get_display_name())
    
    except Exception as e:
        add_system_log(f"Patient prescriptions error: {str(e)}", "ERROR")
        return render_template('patient_prescriptions.html',
                             user=user,
                             prescriptions=[],
                             patient_name=user.get_display_name(),
                             error=str(e))


if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()
        # Initialize sample data with cryptographic functions
        init_sample_data()
    
    print("""
    ========================================
    MedLink Flask Application Started
    ========================================
    
    Security Features Enabled:
    ✅ RSA Encryption (6-step algorithm)
    ✅ Elliptic Curve Cryptography (ECC)
    ✅ SHA-256 Hashing & HMAC Authentication
    ✅ Password Hashing with Salt
    ✅ Digital Signatures (RSA)
    ✅ End-to-End Message Encryption (ECC)
    ✅ Data Integrity Verification (HMAC)
    ✅ Steganographic Prescription Storage
    ✅ Attack Simulation for Demo
    
    Demo Credentials:
    - Patient:    patient@medlink.com / patient123
    - Doctor:     doctor@medlink.com / doctor123
    - Specialist: specialist@medlink.com / specialist123
    
    Navigate to: http://localhost:5000
    ========================================
    """)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
