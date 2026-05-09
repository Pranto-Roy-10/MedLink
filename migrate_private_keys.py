"""
Private Key Encryption Migration Script
Encrypts any unencrypted private keys in the database.
Useful after master keys are configured.

Usage:
    python migrate_private_keys.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from models import db, User
from app import app
from security.asymmetric_encryption import AsymmetricEncryption


def check_if_encrypted(key_string):
    """Check if a key is encrypted (starts with 'rsa:')"""
    if not key_string:
        return False
    return isinstance(key_string, str) and key_string.startswith('rsa:')


def migrate_rsa_private_keys():
    """Encrypt any unencrypted RSA private keys"""
    print("[*] Checking RSA private keys...")
    
    unencrypted_count = 0
    encrypted_count = 0
    
    with app.app_context():
        users = User.query.all()
        
        for user in users:
            if not user.rsa_private_key:
                continue
            
            # Check if already encrypted
            if check_if_encrypted(user.rsa_private_key):
                encrypted_count += 1
                continue
            
            # Encrypt unencrypted key
            try:
                encrypted_key = AsymmetricEncryption.encrypt_private_key_with_master_key(
                    user.rsa_private_key
                )
                user.rsa_private_key = encrypted_key
                unencrypted_count += 1
                print(f"    [✓] Encrypted RSA key for {user.username}")
            except Exception as e:
                print(f"    [!] Failed to encrypt RSA key for {user.username}: {e}")
        
        # Commit all changes
        if unencrypted_count > 0:
            db.session.commit()
            print(f"\n[✓] Successfully encrypted {unencrypted_count} RSA private key(s)")
            print(f"[✓] {encrypted_count} RSA key(s) were already encrypted")
        else:
            print(f"[✓] All RSA keys are already encrypted ({encrypted_count} total)")
    
    return unencrypted_count


def migrate_ecc_private_keys():
    """Encrypt any unencrypted ECC private keys"""
    print("\n[*] Checking ECC private keys...")
    
    unencrypted_count = 0
    encrypted_count = 0
    
    with app.app_context():
        users = User.query.all()
        
        for user in users:
            if not user.ecc_private_key:
                continue
            
            # Check if already encrypted
            if check_if_encrypted(user.ecc_private_key):
                encrypted_count += 1
                continue
            
            # Encrypt unencrypted key
            try:
                encrypted_key = AsymmetricEncryption.encrypt_private_key_with_master_key(
                    user.ecc_private_key
                )
                user.ecc_private_key = encrypted_key
                unencrypted_count += 1
                print(f"    [✓] Encrypted ECC key for {user.username}")
            except Exception as e:
                print(f"    [!] Failed to encrypt ECC key for {user.username}: {e}")
        
        # Commit all changes
        if unencrypted_count > 0:
            db.session.commit()
            print(f"\n[✓] Successfully encrypted {unencrypted_count} ECC private key(s)")
            print(f"[✓] {encrypted_count} ECC key(s) were already encrypted")
        else:
            print(f"[✓] All ECC keys are already encrypted ({encrypted_count} total)")
    
    return unencrypted_count


if __name__ == '__main__':
    try:
        # Check if master keys are configured
        if not os.getenv('MASTER_RSA_PUBLIC_KEY'):
            print("[!] ERROR: MASTER_RSA_PUBLIC_KEY not found in .env")
            print("[!] Run setup_encryption.py first to generate master keys")
            sys.exit(1)
        
        print("[*] Starting private key encryption migration...\n")
        
        rsa_count = migrate_rsa_private_keys()
        ecc_count = migrate_ecc_private_keys()
        
        total = rsa_count + ecc_count
        if total > 0:
            print(f"\n[✓] Migration complete! Encrypted {total} private key(s)")
        else:
            print(f"\n[✓] Migration complete! All keys are already encrypted")
        
    except Exception as e:
        print(f"\n[!] Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
