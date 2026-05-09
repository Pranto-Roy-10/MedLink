"""Test that email survives key rotation"""
from models import db, User
from app import app

with app.app_context():
    # Use a user with email
    user = User.query.filter_by(username='patient@medlink.com').first()
    
    if user:
        print("=" * 60)
        print("EMAIL RE-ENCRYPTION TEST")
        print("=" * 60)
        
        # Get email before rotation
        email_before = user.get_email()
        print(f"\n✓ Email BEFORE rotation: {email_before}")
        
        # Rotate keys
        from app import auto_rotate_keys_on_login
        auto_rotate_keys_on_login(user)
        db.session.refresh(user)
        
        # Get email after rotation
        email_after = user.get_email()
        print(f"✓ Email AFTER rotation:  {email_after}")
        
        # Check if email is the same
        if email_before == email_after and email_before:
            print("\n✅ EMAIL RE-ENCRYPTION SUCCESSFUL!")
            print(f"   Email persisted through key rotation: {email_after}")
        else:
            print("\n❌ EMAIL RE-ENCRYPTION FAILED!")
            print(f"   Before: {email_before}")
            print(f"   After:  {email_after}")
            
        print("\n" + "=" * 60)
    else:
        print("User not found!")
