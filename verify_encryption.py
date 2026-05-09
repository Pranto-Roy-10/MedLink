"""
Quick verification script to check if private keys are encrypted in the database.
Displays the first 50 characters of private keys to confirm they start with "rsa:"
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from models import db, User
from app import app

def verify_encryption():
    """Check if private keys are encrypted in database"""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("[!] No users found in database")
            return
        
        print("\n" + "="*70)
        print("  PRIVATE KEY ENCRYPTION VERIFICATION")
        print("="*70 + "\n")
        
        encrypted_count = 0
        unencrypted_count = 0
        
        for user in users:
            print(f"User: {user.username} ({user.role})")
            
            # Check RSA private key
            if user.rsa_private_key:
                is_encrypted = user.rsa_private_key.startswith('rsa:')
                preview = user.rsa_private_key[:50]
                status = "✅ ENCRYPTED" if is_encrypted else "❌ UNENCRYPTED"
                print(f"  RSA Key:  {status}")
                print(f"    Preview: {preview}...")
                if is_encrypted:
                    encrypted_count += 1
                else:
                    unencrypted_count += 1
            else:
                print(f"  RSA Key:  (not set)")
            
            # Check ECC private key
            if user.ecc_private_key:
                is_encrypted = user.ecc_private_key.startswith('rsa:')
                preview = user.ecc_private_key[:50]
                status = "✅ ENCRYPTED" if is_encrypted else "❌ UNENCRYPTED"
                print(f"  ECC Key:  {status}")
                print(f"    Preview: {preview}...")
                if is_encrypted:
                    encrypted_count += 1
                else:
                    unencrypted_count += 1
            else:
                print(f"  ECC Key:  (not set)")
            
            print()
        
        # Summary
        print("="*70)
        print(f"  Total encrypted keys: {encrypted_count}")
        print(f"  Total unencrypted keys: {unencrypted_count}")
        print("="*70)
        
        if unencrypted_count == 0 and encrypted_count > 0:
            print("\n  ✅ SUCCESS: All private keys are encrypted!")
            print("     Private keys will remain encrypted after database deletion.")
        elif unencrypted_count > 0:
            print(f"\n  ⚠️  WARNING: {unencrypted_count} unencrypted key(s) found!")
            print("     Run: python migrate_private_keys.py")
        else:
            print("\n  [!] No private keys found in database")

if __name__ == '__main__':
    try:
        verify_encryption()
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
