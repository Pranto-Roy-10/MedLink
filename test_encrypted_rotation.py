"""Test key rotation with encrypted key storage"""
from models import db, User
from app import app, auto_rotate_keys_on_login

with app.app_context():
    # Get a user
    user = User.query.first()
    
    if user:
        print("=" * 60)
        print("TESTING ENCRYPTED KEY ROTATION")
        print("=" * 60)
        print(f"\n👤 User: {user.username}")
        
        # Get private key before rotation
        key_before = user.get_rsa_private_key()
        if key_before:
            print(f"\n✓ Before Rotation:")
            print(f"  RSA Private Key (d): {str(key_before['d'])[:40]}...")
            print(f"  Raw DB value starts with: {user.rsa_private_key[:20]}...")
        
        # Check if it's encrypted
        if user.rsa_private_key.startswith("rsa:"):
            print(f"  🔒 In DB: ENCRYPTED")
        else:
            print(f"  ❌ In DB: PLAINTEXT")
        
        # Rotate keys
        print(f"\n▶ Rotating keys...")
        auto_rotate_keys_on_login(user)
        db.session.refresh(user)
        
        # Get private key after rotation
        key_after = user.get_rsa_private_key()
        if key_after:
            print(f"\n✓ After Rotation:")
            print(f"  RSA Private Key (d): {str(key_after['d'])[:40]}...")
            print(f"  Raw DB value starts with: {user.rsa_private_key[:20]}...")
        
        # Check if it's encrypted
        if user.rsa_private_key.startswith("rsa:"):
            print(f"  🔒 In DB: ENCRYPTED")
        else:
            print(f"  ❌ In DB: PLAINTEXT")
        
        # Verify keys changed
        if key_before and key_after and key_before['d'] != key_after['d']:
            print(f"\n✅ Key Rotation Successful!")
            print(f"   Keys changed: YES")
        else:
            print(f"\n❌ Key Rotation Failed!")
        
        print("\n" + "=" * 60)
    else:
        print("No users found")
