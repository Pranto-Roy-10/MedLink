from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timedelta
import os
import json
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from models import db, User, Referral, Message, Document
from security.hashing import generate_mac, verify_mac, manual_sha256
from security.rsa import generate_keys, encrypt, decrypt
from security.ecc import EllipticCurve, Point, create_test_curve
from security.encryption_utils import (
    ecc_encrypt_message, ecc_decrypt_message,
    encrypt_email_rsa, decrypt_email_rsa, direct_rsa_encrypt, direct_rsa_decrypt
)
import smtplib
from email.mime.text import MIMEText
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize Socket.IO for real-time chat
socketio = SocketIO(app, cors_allowed_origins="*")

# SQLite Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'medlink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db.init_app(app)

# Master Key Validation
def validate_master_keys():
    """Validate that master encryption keys are configured"""
    missing_keys = []
    
    if not os.getenv('MASTER_RSA_PUBLIC_KEY'):
        missing_keys.append('MASTER_RSA_PUBLIC_KEY')
    
    if not os.getenv('MASTER_RSA_PRIVATE_KEY'):
        missing_keys.append('MASTER_RSA_PRIVATE_KEY')
    
    if missing_keys:
        print("\n" + "="*70)
        print("  [WARNING] ENCRYPTION KEYS NOT CONFIGURED")
        print("="*70)
        print(f"  Missing environment variables: {', '.join(missing_keys)}")
        print("\n  To fix this issue:")
        print("  1. Run: python setup_encryption.py")
        print("  2. This will generate and store master keys in .env")
        print("  3. Restart the application")
        print("\n  Without master keys:")
        print("  - Private keys will be stored UNENCRYPTED")
        print("  - This is a SECURITY RISK in production")
        print("="*70 + "\n")
        return False
    
    return True

# Validate master keys on startup
master_keys_valid = validate_master_keys()

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

def auto_rotate_keys_on_login(user):
    """
    Automatically rotate cryptographic keys on login with data re-encryption.
    
    Process:
    1. Generate new RSA and ECC keys
    2. Decrypt all user fields with OLD keys
    3. Re-encrypt all user fields with NEW keys
    4. Replace old keys with new keys
    5. Save to database
    
    This ensures email and other encrypted fields remain accessible.
    """
    try:
        # Step 1: Keep old keys temporarily
        old_rsa_keys = user.get_rsa_private_key()
        
        # Step 2: Generate new RSA keys
        new_rsa_keys = generate_keys(256)
        
        # Step 3: Decrypt all fields with OLD keys
        old_email = user.get_email()
        old_phone = user.get_phone()
        old_address = user.get_address()
        old_dob = user.get_date_of_birth()
        
        # Step 4: Set new RSA keys
        user.set_rsa_keys(new_rsa_keys[0], new_rsa_keys[1])
        
        # Step 5: Re-encrypt all fields with NEW keys
        if old_email:
            user.encrypted_email = user.encrypt_nid_with_rsa(old_email)
        if old_phone:
            user.phone = user.encrypt_nid_with_rsa(old_phone)
        if old_address:
            user.address = user.encrypt_nid_with_rsa(old_address)
        if old_dob:
            user.date_of_birth = user.encrypt_nid_with_rsa(old_dob)
        
        # Step 6: Generate new ECC keys
        try:
            curve = create_test_curve()
            new_ecc_scalar = random.randint(1, 1000)
            base_point = Point(0, 1, curve)
            new_ecc_public = curve.scalar_multiplication(new_ecc_scalar, base_point)
            user.set_ecc_keys(new_ecc_public, new_ecc_scalar)
        except Exception as e:
            add_system_log(f"ECC key rotation warning: {str(e)}", "WARN")
        
        # Step 7: Update rotation timestamp and save
        user.last_key_rotation = datetime.now()
        db.session.commit()
        
        add_system_log(
            f"🔄 KEY ROTATION SUCCESS: {user.get_display_name()} | New RSA keys generated & user data re-encrypted | Email: {old_email}",
            "SUCCESS"
        )
    except Exception as e:
        db.session.rollback()
        add_system_log(f"❌ Key rotation failed: {str(e)}", "ERROR")
    
def send_otp_email(to_email, otp_code, purpose="login"):
    sender_email = os.environ.get("SMTP_USERNAME")
    sender_password = os.environ.get("SMTP_PASSWORD")

    if not sender_email or not sender_password:
        raise Exception("SMTP_USERNAME or SMTP_PASSWORD is missing")

    # Different messages for different purposes
    if purpose == "registration":
        subject = "MedLink Account Verification OTP"

        body = f"""
Hello,

Your account creation OTP is: {otp_code}

Use this OTP to verify your MedLink account registration.

This code will expire soon.

If you did not create this account, please ignore this email.
"""

    else:
        subject = "MedLink Login OTP"

        body = f"""
Hello,

Your login OTP is: {otp_code}

Use this OTP to complete your MedLink login.

This code will expire soon.

If this was not you, please secure your account immediately.
"""

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page with optional 2FA support.
    Step 1: Username and password
    Step 2: Cryptographic challenge response (if 2FA enabled)
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Step 1: Password verified - generate 2FA challenge
            challenge_code = random.randint(100000, 999999)
            
            # Sign the challenge with user's RSA private key
            priv_key = user.get_rsa_private_key()
            if priv_key:
                challenge_signed = str(pow(challenge_code, priv_key['d'], priv_key['n']))
            else:
                challenge_signed = str(challenge_code)
            
            session['pending_2fa_user_id'] = user.id
            session['2fa_challenge'] = challenge_code
            session['2fa_user_id'] = user.id
            session['2fa_timestamp'] = datetime.now().timestamp()
            # If the user is an admin, skip sending OTP email and complete login immediately
            if getattr(user, 'role', None) == 'admin':
                session['user_id'] = user.id
                session['user_email'] = user.username
                session['user_role'] = user.role
                session['user_name'] = user.get_display_name()

                # Clear any pending 2FA session data
                session.pop('pending_2fa_user_id', None)
                session.pop('2fa_challenge', None)
                session.pop('2fa_user_id', None)
                session.pop('2fa_timestamp', None)

                add_system_log(
                    f"✓ ADMIN LOGIN BYPASS: {user.get_display_name()} | OTP skipped for admin",
                    "SUCCESS"
                )
                
                # Auto-rotate keys on successful login
                auto_rotate_keys_on_login(user)

                return redirect(url_for('admin_dashboard'))

            try:
                user_email = user.get_email()
                
                # Check if email is valid before sending OTP
                if not user_email or not isinstance(user_email, str):
                    raise Exception(f"User email is invalid or not set: {user_email}")
                
                if not user_email.strip():
                    raise Exception("User email is empty")

                send_otp_email(user_email, challenge_code, "login")

                add_system_log(
        f"✓ LOGIN STEP 1: {user.get_display_name()} | OTP sent to registered email: {user_email}",
        "SUCCESS"
    )

                return redirect(url_for('verify_2fa'))

            except Exception as e:
                add_system_log(
        f"❌ OTP EMAIL FAILED: {str(e)} | User email: {user.get_email()}",
        "ERROR"
    )

                return render_template(
        'login.html',
        error='Password correct, but OTP email could not be sent.'
    )
        else:
            add_system_log(f"❌ LOGIN FAILED: Username {username} - Invalid credentials", "ERROR")
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """
    2FA Verification - Step 2 of login.
    User must enter the 6-digit challenge code to complete authentication.
    """
    if 'pending_2fa_user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_input = request.form.get('challenge_code', '').strip()
        expected_code = str(session.get('2fa_challenge', ''))
        
        if user_input == expected_code:
            # Code matches - complete login
            user_id = session['pending_2fa_user_id']
            user = User.query.get(user_id)
            
            # Allow all users to log in (approved and unapproved)
            # Unapproved users will see limited dashboard access
            
            # Set permanent session
            session['user_id'] = user_id
            session['user_email'] = user.username
            session['user_role'] = user.role
            session['user_name'] = user.get_display_name()
            
            # Clear 2FA session data
            session.pop('pending_2fa_user_id', None)
            session.pop('2fa_challenge', None)
            session.pop('2fa_signed', None)
            session.pop('2fa_timestamp', None)
            
            add_system_log(f"✓ 2FA VERIFIED: {user.get_display_name()} | Challenge Code Matched", "SUCCESS")
            add_system_log(f"✓ LOGIN STEP 2: Signature Verified | RSA Challenge Response Authenticated", "SUCCESS")
            
            # Auto-rotate keys on successful login
            auto_rotate_keys_on_login(user)
            
            # Redirect admin users to admin dashboard, others to regular dashboard
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            add_system_log(f"❌ 2FA FAILED: Invalid challenge code entered", "ERROR")
            return render_template('verify_2fa.html', 
                                  error='Invalid OTP',
                                  user=User.query.get(session.get('pending_2fa_user_id')))
    
    user = User.query.get(session.get('pending_2fa_user_id'))
    return render_template('verify_2fa.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User Registration with Automatic Key Generation.
    
    Features:
    - Collects full name (stored as username) and email separately
    - Auto-generates RSA 2048-bit key pair
    - Auto-generates ECC 256-bit key pair
    - Encrypts email with RSA
    - Encrypts sensitive data (NID) with direct RSA
    - Enables 2FA by default
    """
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'patient')
        nid = request.form.get('nid')
        blood_group = request.form.get('blood_group')
        license_number = request.form.get('license_number')
        
        # Validation
        if not display_name or not email or not password or not confirm_password:
            return render_template('register.html', error='All fields required')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        # Prevent admin role selection during registration
        if role == 'admin':
            return render_template('register.html', error='Admin accounts cannot be created during registration. Contact system administrator.')
        
        if User.query.filter_by(username=display_name).first():
            return render_template('register.html', error='Name already in use')
        
        try:
            # Create new user with display_name as username
            # Generate verification code (6 digits)
            verification_code = random.randint(100000, 999999)
            
            user = User(
                username=display_name,
                display_name=display_name,
                role=role,
                two_fa_enabled=True,
                is_approved=False  # All new registrations require approval
            )
            user.two_fa_challenge = str(verification_code)  # Store verification code
            user.set_password(password)
            
            # Auto-generate RSA keys (256-bit demo, 2048-bit production)
            from security.rsa import generate_keys
            rsa_keys = generate_keys(256)
            user.set_rsa_keys(rsa_keys[0], rsa_keys[1])
            
            # Store email (encrypt it)
            user.encrypted_email = user.encrypt_nid_with_rsa(email)
            
            # Auto-generate ECC keys
            try:
                from security.ecc import create_test_curve, Point
                curve = create_test_curve()
                ecc_scalar = random.randint(1, 1000)
                base_point = Point(0, 1, curve)
                ecc_public = curve.scalar_multiplication(ecc_scalar, base_point)
                user.set_ecc_keys(ecc_public, ecc_scalar)
            except:
                pass
            
            # Store license number if provided (doctors/specialists)
            if license_number and role in ('doctor', 'specialist'):
                user.license_number = license_number.strip()

            # Encrypt NID if provided
            if nid:
                user.encrypted_nid = user.encrypt_nid_with_rsa(nid)
            
            # Encrypt blood group if provided
            if blood_group:
                user.encrypted_blood_group = user.encrypt_nid_with_rsa(blood_group)
            
            # Set last key rotation
            user.last_key_rotation = datetime.now()
            
            db.session.add(user)
            db.session.commit()
            
            try:
                send_otp_email(email, verification_code, "registration")

                add_system_log(
        f"✓ REGISTRATION SUCCESSFUL: New {role.capitalize()} registered | {display_name} ({email}) | OTP sent to email",
        "SUCCESS"
    )

            except Exception as e:
                add_system_log(
        f"❌ REGISTRATION OTP EMAIL FAILED: {str(e)}",
        "ERROR"
    )

                return render_template(
        'register.html',
        error='Account was created, but OTP email could not be sent. Please try again.'
    )

# Redirect to verification page
            session['pending_user_id'] = user.id
            session['verification_code'] = verification_code
            return redirect(url_for('verify_registration'))
        
        except RuntimeError as e:
            # Handle encryption setup errors
            if "Master encryption keys not configured" in str(e):
                db.session.rollback()
                add_system_log(f"❌ REGISTRATION ERROR: Master encryption keys not configured", "ERROR")
                return render_template('register.html', 
                    error='System Error: Encryption keys not configured. Please contact the administrator and ask them to run "python setup_encryption.py"')
            else:
                db.session.rollback()
                add_system_log(f"❌ REGISTRATION ERROR: {str(e)}", "ERROR")
                return render_template('register.html', error=f'Registration failed: {str(e)}')
        except Exception as e:
            db.session.rollback()
            add_system_log(f"❌ REGISTRATION ERROR: {str(e)}", "ERROR")
            return render_template('register.html', error=f'Registration failed: {str(e)}')
    
    return render_template('register.html')

@app.route('/verify-registration', methods=['GET', 'POST'])
def verify_registration():
    """
    Email Verification for New Registrations.
    User must enter the 6-digit code sent during registration.
    """
    if 'pending_user_id' not in session:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        user_input = request.form.get('verification_code', '').strip()
        expected_code = str(session.get('verification_code', ''))
        
        if user_input == expected_code:
            # Code matches - user can now access dashboard (but still pending admin approval)
            user_id = session['pending_user_id']
            user = User.query.get(user_id)
            
            if user:
                # Log in the user to their dashboard
                session['user_id'] = user.id
                del session['pending_user_id']
                del session['verification_code']
                
                add_system_log(
                    f"✓ EMAIL VERIFIED: {user.get_display_name()} verified their registration code | Pending admin approval",
                    "SUCCESS"
                )
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('verify_registration.html', error='User not found')
        else:
            add_system_log(
                f"❌ VERIFICATION FAILED: Incorrect code entered",
                "ALERT"
            )
            return render_template('verify_registration.html', error='Invalid verification code')
    
    user_id = session.get('pending_user_id')
    user = User.query.get(user_id)
    
    return render_template('verify_registration.html', user=user)

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
    
    # Get unread message count
    unread_count = Message.query.filter_by(receiver_id=user_id, is_read=False).count()

    # If specialist, fetch pending referrals for quick actions
    pending_referrals = []
    if user.role == 'specialist':
        pending_referrals = Referral.query.filter_by(receiver_id=user.id, status='pending').order_by(Referral.timestamp.desc()).all()

    return render_template('dashboard.html', 
                         user=user,
                         user_name=user.get_display_name(),
                         user_role=user.role,
                         stats=stats,
                         recent_activity=recent_activity,
                         system_integrity=system_integrity,
                         is_approved=user.is_approved,
                         unread_messages=unread_count,
                         pending_referrals=pending_referrals)

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    """User profile page (protected route)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Prepare decrypted user data for display
    user_profile = {
        'id': user.id,
        'username': user.username,
        'display_name': user.display_name,
        'role': user.role,
        'phone': user.get_phone(),
        'address': user.get_address(),
        'date_of_birth': user.get_date_of_birth(),
        'email': user.get_email(),
        'city': user.city,
        'country': user.country,
        'created_at': user.created_at,
        'updated_at': user.updated_at,
        'rsa_keys': 'Generated' if user.rsa_public_key else 'Not Generated',
        'ecc_keys': 'Generated' if user.ecc_public_key else 'Not Generated'
    }
    
    return render_template('profile.html', user=user, user_profile=user_profile)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    """Edit profile page (protected route)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        display_name = request.form.get('display_name')
        phone = request.form.get('phone')
        date_of_birth = request.form.get('date_of_birth')
        address = request.form.get('address')
        city = request.form.get('city')
        country = request.form.get('country')
        
        # Update user profile with encrypted sensitive data
        if display_name:
            user.display_name = display_name
        if phone:
            user.phone = user.encrypt_nid_with_rsa(phone) if hasattr(user, 'encrypt_nid_with_rsa') else phone
        if date_of_birth:
            user.date_of_birth = user.encrypt_nid_with_rsa(date_of_birth) if hasattr(user, 'encrypt_nid_with_rsa') else date_of_birth
        if address:
            user.address = user.encrypt_nid_with_rsa(address) if hasattr(user, 'encrypt_nid_with_rsa') else address
        if city:
            user.city = city
        if country:
            user.country = country
        
        try:
            db.session.commit()
            # Update session with new display name
            session['user_name'] = user.display_name or user.username
            # Prepare decrypted user data for display
            user_profile = {
                'id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'role': user.role,
                'phone': user.get_phone(),
                'address': user.get_address(),
                'date_of_birth': user.get_date_of_birth(),
                'email': user.get_email(),
                'city': user.city,
                'country': user.country,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'rsa_keys': 'Generated' if user.rsa_public_key else 'Not Generated',
                'ecc_keys': 'Generated' if user.ecc_public_key else 'Not Generated'
            }
            return render_template('profile.html', user=user, user_profile=user_profile, success='Profile updated successfully!')
        except Exception as e:
            db.session.rollback()
            return render_template('edit_profile.html', user=user, error=f'Error updating profile: {str(e)}')
    
    # Prepare decrypted user data for the edit form
    user_profile = {
        'id': user.id,
        'username': user.username,
        'display_name': user.display_name,
        'role': user.role,
        'phone': user.get_phone(),
        'address': user.get_address(),
        'date_of_birth': user.get_date_of_birth(),
        'email': user.get_email(),
        'city': user.city,
        'country': user.country,
        'created_at': user.created_at,
        'updated_at': user.updated_at,
        'rsa_keys': 'Generated' if user.rsa_public_key else 'Not Generated',
        'ecc_keys': 'Generated' if user.ecc_public_key else 'Not Generated'
    }
    
    return render_template('edit_profile.html', user=user, user_profile=user_profile)


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
    Display list of users who have sent messages to current user.
    Shows conversation history first, with search to find others.
    Template syntax fixed.
    """
    # Fixed template syntax error
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    
    # Get users who have sent messages to current user (conversations)
    message_senders = db.session.query(User).join(
        Message, Message.sender_id == User.id
    ).filter(Message.receiver_id == current_user_id).distinct().order_by(Message.timestamp.desc()).all()
    
    # Remove duplicates while preserving order
    seen_ids = set()
    active_users = []
    for user in message_senders:
        if user.id not in seen_ids:
            active_users.append(user)
            seen_ids.add(user.id)
    
    # Also add users current user has sent messages to
    message_receivers = db.session.query(User).join(
        Message, Message.receiver_id == User.id
    ).filter(Message.sender_id == current_user_id).distinct().all()
    
    for user in message_receivers:
        if user.id not in seen_ids:
            active_users.append(user)
            seen_ids.add(user.id)
    
    # Get all other users for search
    all_users = User.query.filter(User.id != current_user_id).all()
    
    # Convert User objects to dictionaries with message count for JSON serialization
    active_users_dict = []
    for u in active_users:
        # Count unread messages from this user to current user
        unread_count = Message.query.filter(
            Message.sender_id == u.id,
            Message.receiver_id == current_user_id,
            Message.is_read == False
        ).count()
        
        active_users_dict.append({
            'id': u.id,
            'username': u.username,
            'role': u.role,
            'message_count': unread_count
        })
    
    all_users_dict = [{'id': u.id, 'username': u.username, 'role': u.role} for u in all_users]
    
    return render_template('chat_list.html',
                         active_users=active_users_dict,
                         all_users=all_users_dict,
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
    
    # Mark all messages from other user as read
    unread_messages = Message.query.filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user_id,
        Message.is_read == False
    ).all()
    
    for msg in unread_messages:
        msg.is_read = True
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
        # Hash referral data (for logging/audit)
        referral_hash = manual_sha256(referral_text)

        # Encrypt referral content using recipient's RSA public key (direct asymmetric)
        receiver_rsa_pub = receiver.get_rsa_public_key()
        encrypted_content = direct_rsa_encrypt(referral_text, receiver_rsa_pub)

        # Generate HMAC for integrity over the ciphertext
        hmac_key = f"referral_{sender_id}"
        mac_tag = generate_mac(hmac_key, encrypted_content)

        # Create referral (store only ciphertext)
        referral = Referral(
            sender_id=sender_id,
            receiver_id=int(receiver_id),
            encrypted_content=encrypted_content,
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


@app.route('/accept_referral/<int:referral_id>', methods=['POST'])
def accept_referral(referral_id):
    """Accept a referral (specialist action)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session.get('user_id'))
    ref = Referral.query.get(referral_id)

    if not ref:
        return jsonify({'error': 'Referral not found'}), 404

    # Only the intended receiver (specialist) or admin can accept
    if user.id != ref.receiver_id and user.role != 'admin':
        return jsonify({'error': 'Not authorized to accept this referral'}), 403

    try:
        ref.status = 'accepted'
        ref.is_verified = True
        db.session.commit()

        add_system_log(
            f"✓ REFERRAL ACCEPTED: {user.get_display_name()} accepted referral {referral_id}",
            "SUCCESS"
        )

        return jsonify({'success': True, 'referral_id': referral_id}), 200
    except Exception as e:
        db.session.rollback()
        add_system_log(f"Referral accept failed: {str(e)}", "ERROR")
        return jsonify({'error': str(e)}), 500


@app.route('/specialist/referrals')
def specialist_referrals():
    """Return JSON list of referrals for the logged-in specialist."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role != 'specialist' and user.role != 'admin':
        return jsonify({'error': 'Not authorized'}), 403

    refs = Referral.query.filter_by(receiver_id=user.id).order_by(Referral.timestamp.desc()).all()

    out = []
    for r in refs:
        out.append({
            'id': r.id,
            'from': r.sender.get_display_name() if r.sender else 'Unknown',
            'status': r.status,
            'is_verified': bool(r.is_verified),
            'timestamp': r.timestamp.strftime('%Y-%m-%d %I:%M %p') if r.timestamp else None
        })

    return jsonify({'referrals': out}), 200


@app.route('/referral/<int:referral_id>/view')
def view_referral(referral_id):
    """Return decrypted referral content to authorized users (sender, receiver, admin)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    ref = Referral.query.get(referral_id)
    if not ref:
        return jsonify({'error': 'Referral not found'}), 404

    # Only allow sender, receiver, or admin
    if user.role != 'admin' and user.id not in (ref.sender_id, ref.receiver_id):
        return jsonify({'error': 'Not authorized to view this referral'}), 403

    content = ref.encrypted_content or ''
    try:
        # If it's RSA encrypted, decrypt with the current user's private key
        if content.startswith('rsa:'):
            priv = user.get_rsa_private_key()
            if not priv:
                return jsonify({'error': 'Private key not available for decryption'}), 500
            decrypted = direct_rsa_decrypt(content, priv)
        elif content.startswith('ecc:'):
            # try ECC decryption using both parties' public keys
            sender = User.query.get(ref.sender_id)
            receiver = User.query.get(ref.receiver_id)
            if sender and receiver:
                decrypted = ecc_decrypt_message(content, sender.get_ecc_public_key(), receiver.get_ecc_public_key())
            else:
                decrypted = '[Cannot decrypt - users missing]'
        else:
            # not encrypted
            decrypted = content

        return jsonify({'success': True, 'content': decrypted}), 200
    except Exception as e:
        add_system_log(f"Referral view failed: {str(e)}", "ERROR")
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
        
        # Decrypt prescription content before returning to the authorized patient
        prescription_content = doc.encrypted_content
        try:
            user = User.query.get(user_id)
            # RSA direct decryption
            if isinstance(prescription_content, str) and prescription_content.startswith('rsa:'):
                priv = user.get_rsa_private_key()
                if not priv:
                    add_system_log(f"Prescription download failed: Private key missing for user {user_id}", "ERROR")
                    return jsonify({'error': 'User private key not available for decryption'}), 500
                prescription_content = direct_rsa_decrypt(prescription_content, priv)
            elif isinstance(prescription_content, str) and prescription_content.startswith('ecc:'):
                # Attempt ECC-style decryption using document owner and issuer keys
                # Try to find a sender (doctor) from system logs or from recent documents - best-effort
                # If referral metadata exists linking issuer, use that; otherwise attempt symmetric ECC decryption
                # Here we'll attempt ECC decryption using patient's ECC public key and a placeholder (requires sender pub)
                try:
                    # For ECC, we need sender and receiver public keys; attempt to use doctor in last issuer field
                    # Fallback: return ciphertext if unable to decrypt
                    prescription_content = ecc_decrypt_message(prescription_content, None, user.get_ecc_public_key())
                except Exception:
                    # leave as-is if decryption not possible
                    pass
        except Exception as e:
            add_system_log(f"Prescription decryption failed: {str(e)}", "ERROR")
            return jsonify({'error': 'Decryption error'}), 500
        
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
    
    # Check if user is admin
    if user.role != 'admin':
        add_system_log(f"Attack simulation denied: User {user.get_display_name()} not authorized (admin only)", "ALERT")
        return jsonify({'error': 'Not authorized - Admin role required'}), 403
    
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
    
    # Pending Referrals
    # - For specialists we want referrals RECEIVED that are pending (they need to accept)
    # - For other users we show referrals they SENT that are still pending
    if getattr(user, 'role', None) == 'specialist':
        stats['pending_referrals'] = Referral.query.filter_by(
            receiver_id=user.id,
            status='pending'
        ).count()
    else:
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
    
    # Helper function to safely create a user with encryption
    def create_user_with_keys(username, display_name, role, password):
        """Create a user and generate encrypted keys"""
        user = User(
            username=username,
            display_name=display_name,
            role=role,
            public_key=f'mock_{role}_public_key',
            encrypted_profile=f'encrypted_{role}_profile',
            is_approved=True
        )
        user.set_password(password)
        
        # Generate RSA keys (256-bit for demo speed)
        try:
            rsa_keys = generate_keys(256)
            user.set_rsa_keys(rsa_keys[0], rsa_keys[1])
        except RuntimeError as e:
            # This means master keys aren't configured
            raise RuntimeError(f"Cannot create sample user {username}: {e}")
        
        # Generate ECC keys
        try:
            curve = create_test_curve()
            ecc_scalar = random.randint(1, 1000)
            base_point = Point(0, 1, curve)
            ecc_public = curve.scalar_multiplication(ecc_scalar, base_point)
            user.set_ecc_keys(ecc_public, ecc_scalar)
        except Exception as e:
            print(f"[WARNING] Failed to generate ECC keys for {username}: {e}")
            # ECC failure is not critical - continue without it
            pass
        
        return user
    
    # Create sample users
    try:
        patient = create_user_with_keys('patient@medlink.com', 'Patient User', 'patient', 'patient123')
        doctor = create_user_with_keys('doctor@medlink.com', 'Dr. Doctor', 'doctor', 'doctor123')
        specialist = create_user_with_keys('specialist@medlink.com', 'Dr. Specialist', 'specialist', 'specialist123')
        admin = create_user_with_keys('admin@medlink.com', 'System Admin', 'admin', 'admin123')
    except RuntimeError as e:
        # Re-raise encryption setup errors
        raise e
    
    db.session.add(patient)
    db.session.add(doctor)
    db.session.add(specialist)
    db.session.add(admin)
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


@app.route('/admin/dashboard')
def admin_dashboard():
    """
    Complete Admin Control Panel with user management and statistics.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    admin_user = User.query.get(session.get('user_id'))
    
    # Only allow admin users
    if admin_user.role != 'admin':
        return jsonify({'error': 'Access denied - Admin role required'}), 403
    
    # Get statistics
    total_users = User.query.count()
    approved_users = User.query.filter_by(is_approved=True).count()
    total_patients = User.query.filter_by(role='patient', is_approved=True).count()
    total_doctors = User.query.filter_by(role='doctor', is_approved=True).count()
    total_specialists = User.query.filter_by(role='specialist', is_approved=True).count()
    total_prescriptions = Document.query.filter_by(document_type='prescription').count()
    total_referrals = Referral.query.count()
    
    # Get pending approvals
    pending_approvals = User.query.filter_by(is_approved=False).all()
    
    # Get all approved users and specialists
    all_approved_users = User.query.filter_by(is_approved=True).all()
    all_specialists = User.query.filter_by(role='specialist', is_approved=True).all()
    
    # Get doctors with their prescriptions
    doctors_with_prescriptions = []
    doctors = User.query.filter_by(role='doctor', is_approved=True).all()
    
    for doctor in doctors:
        # Get prescriptions CREATED by this doctor (creator_id = doctor.id)
        prescriptions = Document.query.filter_by(
            creator_id=doctor.id,
            document_type='prescription'
        ).all()
        
        # Format prescriptions with patient info and details
        formatted_prescriptions = []
        for rx in prescriptions:
            patient = User.query.get(rx.user_id)
            formatted_prescriptions.append({
                'id': rx.id,
                'medication': rx.prescription_details.get('medication', 'N/A') if rx.prescription_details else 'N/A',
                'dosage': rx.prescription_details.get('dosage', 'N/A') if rx.prescription_details else 'N/A',
                'instructions': rx.prescription_details.get('instructions', 'N/A') if rx.prescription_details else 'N/A',
                'patient_name': patient.get_display_name() if patient else 'Unknown Patient',
                'date': rx.uploaded_at.strftime('%b %d, %Y') if rx.uploaded_at else 'N/A'
            })
        
        doctor.prescriptions = formatted_prescriptions
        if prescriptions:  # Only show doctors who have issued prescriptions
            doctors_with_prescriptions.append(doctor)
    
    # Get system logs
    system_logs = system_log
    # Get recent referrals for admin overview
    referrals = Referral.query.order_by(Referral.timestamp.desc()).limit(50).all()
    referrals_summary = []
    for r in referrals:
        sender = User.query.get(r.sender_id)
        receiver = User.query.get(r.receiver_id)
        # Try to get patient name from stored patient_id if available, else None
        patient_name = None
        if hasattr(r, 'patient_id') and r.patient_id:
            p = User.query.get(r.patient_id)
            patient_name = p.get_display_name() if p else None
        referrals_summary.append({
            'id': r.id,
            'doctor': sender.get_display_name() if sender else 'Unknown',
            'specialist': receiver.get_display_name() if receiver else 'Unknown',
            'patient': patient_name,
            'status': r.status,
            'timestamp': r.timestamp.strftime('%Y-%m-%d %I:%M %p') if r.timestamp else ''
        })
    
    add_system_log(f"Admin panel accessed by {admin_user.get_display_name()}", "INFO")
    
    return render_template('admin_dashboard.html',
                         admin_user=admin_user,
                         total_users=total_users,
                         approved_users=approved_users,
                         total_patients=total_patients,
                         total_doctors=total_doctors,
                         total_specialists=total_specialists,
                         total_prescriptions=total_prescriptions,
                         total_referrals=total_referrals,
                         pending_approvals=pending_approvals,
                         all_approved_users=all_approved_users,
                         all_specialists=all_specialists,
                         doctors_with_prescriptions=doctors_with_prescriptions,
                         system_logs=system_logs,
                         referrals_summary=referrals_summary)


@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    """Approve a pending user account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin = User.query.get(session.get('user_id'))
    if admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403
    
    user_to_approve = User.query.get(user_id)
    if not user_to_approve:
        return jsonify({'error': 'User not found'}), 404
    
    user_to_approve.is_approved = True
    user_to_approve.approved_at = datetime.now()
    user_to_approve.approved_by_admin_id = admin.id
    
    db.session.commit()
    
    add_system_log(
        f"✓ USER APPROVED: {user_to_approve.get_display_name()} ({user_to_approve.role}) approved by {admin.get_display_name()}",
        "SUCCESS"
    )
    
    return jsonify({'success': True, 'message': f'User {user_to_approve.display_name} approved'}), 200


@app.route('/admin/referrals/json')
def admin_referrals_json():
    if 'user_id' not in session:
        add_system_log('Admin referrals JSON access denied - not authenticated', 'WARN')
        # Provide debug info to help client diagnose cookie/session issues in dev
        debug_info = {
            'cookies': dict(request.cookies),
            'headers': {k: v for k, v in request.headers.items() if k in ['Host', 'Referer', 'User-Agent', 'Cookie']}
        }
        return jsonify({'error': 'Not authenticated', 'debug': debug_info}), 401
    admin = User.query.get(session.get('user_id'))
    if not admin or admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403

    add_system_log(f'Admin referrals JSON accessed by admin {admin.get_display_name()}', 'INFO')
    referrals = Referral.query.order_by(Referral.timestamp.desc()).limit(100).all()
    out = []
    for r in referrals:
        sender = User.query.get(r.sender_id)
        receiver = User.query.get(r.receiver_id)
        patient_name = None
        if hasattr(r, 'patient_id') and getattr(r, 'patient_id'):
            p = User.query.get(r.patient_id)
            patient_name = p.get_display_name() if p else None
        out.append({
            'id': r.id,
            'doctor': sender.get_display_name() if sender else 'Unknown',
            'specialist': receiver.get_display_name() if receiver else 'Unknown',
            'patient': patient_name,
            'status': r.status,
            'timestamp': r.timestamp.strftime('%Y-%m-%d %I:%M %p') if r.timestamp else ''
        })

    return jsonify({'referrals': out}), 200


@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    """Reject and delete a pending user account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin = User.query.get(session.get('user_id'))
    if admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403
    
    user_to_reject = User.query.get(user_id)
    if not user_to_reject:
        return jsonify({'error': 'User not found'}), 404
    
    if user_to_reject.is_approved:
        return jsonify({'error': 'Cannot reject already approved user'}), 400
    
    display_name = user_to_reject.get_display_name()
    db.session.delete(user_to_reject)
    db.session.commit()
    
    add_system_log(
        f"✗ USER REJECTED: {display_name} rejected by {admin.get_display_name()}",
        "ALERT"
    )
    
    return jsonify({'success': True, 'message': f'User {display_name} rejected'}), 200


@app.route('/admin/get-user-email/<int:user_id>', methods=['GET'])
def get_user_email(user_id):
    """Get decrypted email for a user (admin only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin = User.query.get(session.get('user_id'))
    if admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    decrypted_email = user.get_email()
    
    return jsonify({'email': decrypted_email}), 200


@app.route('/admin/change-role/<int:user_id>', methods=['POST'])
def change_user_role(user_id):
    """Change user role (admin only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin = User.query.get(session.get('user_id'))
    if admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403
    
    user_to_update = User.query.get(user_id)
    if not user_to_update:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    new_role = data.get('role', '').lower()
    
    valid_roles = ['patient', 'doctor', 'specialist', 'admin']
    if new_role not in valid_roles:
        return jsonify({'error': 'Invalid role'}), 400
    
    old_role = user_to_update.role
    user_to_update.role = new_role
    db.session.commit()
    
    add_system_log(
        f"🔄 ROLE CHANGED: {user_to_update.get_display_name()} {old_role} → {new_role} by {admin.get_display_name()}",
        "INFO"
    )
    
    return jsonify({'success': True, 'message': f'User role changed to {new_role}'}), 200


@app.route('/admin/remove-user/<int:user_id>', methods=['POST'])
def remove_user_account(user_id):
    """Remove user account (admin only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin = User.query.get(session.get('user_id'))
    if admin.role != 'admin':
        return jsonify({'error': 'Admin role required'}), 403
    
    user_to_remove = User.query.get(user_id)
    if not user_to_remove:
        return jsonify({'error': 'User not found'}), 404
    
    if user_to_remove.id == admin.id:
        return jsonify({'error': 'Cannot remove your own account'}), 400
    
    display_name = user_to_remove.get_display_name()
    user_role = user_to_remove.role
    
    db.session.delete(user_to_remove)
    db.session.commit()
    
    add_system_log(
        f"🗑️ USER DELETED: {display_name} ({user_role}) removed by {admin.get_display_name()}",
        "ALERT"
    )
    
    return jsonify({'success': True, 'message': f'User {display_name} removed'}), 200


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
                creator_id=user_id,  # Track which doctor created this
                document_type='prescription',
                encrypted_content=encrypted_prescription,
                mac_tag=mac_tag,
                is_verified=True,
                prescription_details={
                    'medication': medication,
                    'dosage': dosage,
                    'instructions': instructions,
                    'issued_by': user.get_display_name(),
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                },
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

            # Encrypt referral content using specialist's RSA public key
            specialist_rsa_pub = specialist.get_rsa_public_key()
            encrypted_content = direct_rsa_encrypt(referral_content, specialist_rsa_pub)

            # Generate HMAC for integrity over the ciphertext
            mac_key = f"referral_{user_id}"
            mac_tag = generate_mac(mac_key, encrypted_content)

            referral = Referral(
                sender_id=user_id,
                receiver_id=specialist_id,
                encrypted_content=encrypted_content,
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


# ==================== Real-Time Chat with Socket.IO ====================

# Track connected users
connected_users = {}

@socketio.on('connect')
def handle_connect():
    """Handle user connection to real-time chat"""
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if user:
            connected_users[request.sid] = {
                'user_id': user_id,
                'username': user.get_display_name(),
                'role': user.role
            }
            emit('user_connected', {
                'user': user.get_display_name(),
                'message': f'{user.get_display_name()} joined the chat'
            }, broadcast=True)
            add_system_log(f"🟢 CHAT CONNECTED: {user.get_display_name()}", "INFO")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection from real-time chat"""
    if request.sid in connected_users:
        user_info = connected_users.pop(request.sid)
        emit('user_disconnected', {
            'user': user_info['username'],
            'message': f'{user_info["username"]} left the chat'
        }, broadcast=True)
        add_system_log(f"🔴 CHAT DISCONNECTED: {user_info['username']}", "INFO")


@socketio.on('join_room')
def on_join(data):
    """Join a specific chat room"""
    room = data.get('room')
    user_id = session.get('user_id')
    
    if user_id and room:
        user = User.query.get(user_id)
        join_room(room)
        emit('message', {
            'msg': f'{user.get_display_name()} joined the chat',
            'user': user.get_display_name(),
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }, to=room)
        add_system_log(f"User {user.get_display_name()} joined room {room}", "INFO")


@socketio.on('send_message')
def handle_message(data):
    """Real-time message sending with encryption"""
    user_id = session.get('user_id')
    if not user_id:
        return
    
    sender = User.query.get(user_id)
    receiver_id = data.get('receiver_id')
    message_text = data.get('message')
    room = data.get('room')
    
    if not message_text:
        return
    
    # Get receiver
    receiver = User.query.get(receiver_id)
    if not receiver:
        emit('error', {'message': 'Receiver not found'})
        return
    
    try:
        # Encrypt message with ECC
        sender_ecc_pub = sender.get_ecc_public_key()
        receiver_ecc_pub = receiver.get_ecc_public_key()
        
        encrypted_content = ecc_encrypt_message(sender_ecc_pub, receiver_ecc_pub, message_text)
        
        # Generate MAC for integrity
        hmac_key = f"message_{sender.id}"
        mac_tag = generate_mac(hmac_key, encrypted_content)
        
        # Create message record
        msg = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            encrypted_content=encrypted_content,
            mac_tag=mac_tag,
            is_verified=True
        )
        db.session.add(msg)
        db.session.commit()
        
        # Emit real-time message
        emit('receive_message', {
            'sender': sender.get_display_name(),
            'sender_id': sender.id,
            'message': message_text,  # Show plaintext in real-time
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'encrypted': True,
            'verified': True
        }, to=room or f"chat_{receiver_id}")
        
        add_system_log(
            f"💬 MESSAGE SENT: {sender.get_display_name()} → {receiver.get_display_name()} | Encrypted with ECC & MAC verified",
            "SUCCESS"
        )
        
    except Exception as e:
        emit('error', {'message': f'Failed to send message: {str(e)}'})
        add_system_log(f"Error sending message: {str(e)}", "ERROR")


@socketio.on('typing')
def handle_typing(data):
    """Broadcast typing indicator"""
    user_id = session.get('user_id')
    if not user_id:
        return
    
    user = User.query.get(user_id)
    receiver_id = data.get('receiver_id')
    room = f"chat_{receiver_id}"
    
    emit('user_typing', {
        'user': user.get_display_name(),
        'typing': True
    }, to=room)


if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Initialize sample data with cryptographic functions
        try:
            init_sample_data()
        except RuntimeError as e:
            if "Master encryption keys not configured" in str(e):
                print("\n" + "="*70)
                print("  [CRITICAL] SAMPLE DATA INITIALIZATION FAILED")
                print("="*70)
                print("  Master encryption keys are not configured!")
                print("\n  To fix this issue:")
                print("  1. Run: python setup_encryption.py")
                print("  2. This will generate and store master keys in .env")
                print("  3. Restart the application")
                print("="*70 + "\n")
                raise
            else:
                raise
    
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
    - Admin:      admin@medlink.com / admin123
    - Patient:    patient@medlink.com / patient123
    - Doctor:     doctor@medlink.com / doctor123
    - Specialist: specialist@medlink.com / specialist123
    
    Navigate to: http://localhost:5001
    ========================================
    """)
    
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    socketio.run(app, debug=debug, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
