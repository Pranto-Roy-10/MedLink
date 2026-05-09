"""Test script to verify key rotation on login"""
from models import db, User
from app import app

def get_key_hash(user):
    """Get a hash of the current RSA key for comparison"""
    key = user.get_rsa_private_key()
    if key:
        return f"{str(key['d'])[:30]}__{str(key['n'])[:30]}"
    return None

with app.app_context():
    user = User.query.filter_by(username='patient@medlink.com').first()
    
    if user:
        print("=" * 60)
        print("KEY ROTATION TEST")
        print("=" * 60)
        
        # Get key before
        key_before = get_key_hash(user)
        print(f"\n✓ BEFORE: {key_before}")
        
        # Simulate login by calling auto_rotate_keys_on_login
        from app import auto_rotate_keys_on_login
        print("\n▶ Calling auto_rotate_keys_on_login...")
        auto_rotate_keys_on_login(user)
        
        # Refresh from DB
        db.session.refresh(user)
        
        # Get key after
        key_after = get_key_hash(user)
        print(f"\n✓ AFTER: {key_after}")
        
        if key_before != key_after:
            print("\n✅ KEY ROTATION SUCCESSFUL! Keys changed!")
        else:
            print("\n❌ KEY ROTATION FAILED! Keys are the same!")
            
        print("\n" + "=" * 60)
    else:
        print("User 'patient@medlink.com' not found!")
