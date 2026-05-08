import sys
import os
import shutil

# Ensure parent directory (project root) is on sys.path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Referral, User
from security.encryption_utils import direct_rsa_encrypt
from security.hashing import generate_mac

workspace_dir = os.path.abspath(os.path.dirname(__file__))
# medlink.db is one directory up
db_path = os.path.join(workspace_dir, '..', 'medlink.db')

if os.path.exists(db_path):
    backup_path = db_path + '.pre_migrate.bak'
    shutil.copy2(db_path, backup_path)
    print(f'Backup created: {backup_path}')
else:
    print('No medlink.db found at expected location; aborting.')
    exit(1)

with app.app_context():
    refs = Referral.query.all()
    migrated = 0
    for r in refs:
        ec = r.encrypted_content or ''
        # Skip if already looks encrypted
        if ec.startswith('rsa:') or ec.startswith('ecc:'):
            continue
        receiver = User.query.get(r.receiver_id)
        if not receiver:
            print(f'Skipping referral {r.id}: receiver not found')
            continue
        pub = receiver.get_rsa_public_key()
        try:
            encrypted = direct_rsa_encrypt(ec, pub)
            mac = generate_mac(f'referral_{r.sender_id}', encrypted)
            r.encrypted_content = encrypted
            r.mac_tag = mac
            r.is_verified = True
            db.session.add(r)
            migrated += 1
            print(f'Migrated referral {r.id}')
        except Exception as e:
            print(f'Failed to migrate referral {r.id}: {e}')
    db.session.commit()
    print(f'Done. Migrated {migrated} referrals.')
