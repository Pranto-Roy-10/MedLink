# Private Key Encryption Setup Guide

## Overview

This guide explains how to ensure private keys remain encrypted after database deletion and when running the project again.

## Quick Start

### Step 1: Generate Master Encryption Keys (First Time Only)

Run the setup script to generate and configure master RSA keys:

```bash
python setup_encryption.py
```

This will:

- Generate a 2048-bit RSA key pair
- Create or update the `.env` file with `MASTER_RSA_PUBLIC_KEY` and `MASTER_RSA_PRIVATE_KEY`
- Display the keys (keep them safe!)

**Important:** The .env file contains sensitive keys. Do NOT commit it to version control!

### Step 2: Start the Application

After running `setup_encryption.py`, you can start the application normally:

```bash
python app.py
```

New user registrations will automatically have encrypted private keys stored in the database.

### Step 3: Migrate Existing Unencrypted Keys (If Needed)

If your database already has unencrypted private keys from before the encryption was set up, you can migrate them:

```bash
python migrate_private_keys.py
```

This script will:

- Check all RSA private keys in the database
- Check all ECC private keys in the database
- Encrypt any unencrypted keys using the master RSA key
- Report how many keys were encrypted

## Workflow After Database Deletion

When you delete the database and run the project again:

1. **The .env file persists** (it contains your master keys)
2. **Run the app** - it will detect if master keys are configured
3. **Register new users** - their private keys will be automatically encrypted using the master key
4. **Private keys remain encrypted** in the new database

## Security Notes

### Master Keys Storage

- Master RSA keys are stored in `.env` file
- Keep `.env` safe and never commit to version control
- Backup `.env` securely - if lost, old encrypted keys cannot be decrypted

### Private Key Encryption Process

When a user registers:

1. RSA key pair is generated (2048-bit)
2. ECC key pair is generated (256-bit)
3. Private keys are encrypted with the master RSA public key
4. Encrypted keys are stored as `"rsa:hexencoded_ciphertext"` in the database
5. Public keys are stored in plaintext (they're public)

### Decryption on Use

When the user logs in or private keys are needed:

1. Encrypted key is retrieved from database (starts with `"rsa:`)
2. Master RSA private key decrypts it
3. Private key is used for cryptographic operations
4. Private key is never stored in plaintext in memory

## Troubleshooting

### Error: "MASTER_RSA_PUBLIC_KEY not found in .env"

**Solution:** Run `python setup_encryption.py` to generate and configure master keys.

### Error: "Master encryption keys not configured" during registration

**Solution:**

1. Run `python setup_encryption.py`
2. Restart the Flask application
3. Try registration again

### Encrypted keys not decrypting

**Possible causes:**

- Master RSA private key was lost/changed
- Database was migrated to a different machine with different .env
- Key corruption

**Solution:** Check that `.env` contains valid master keys from `setup_encryption.py`

### Want to re-encrypt all keys with new master keys?

1. Backup your current `.env`
2. Run `python setup_encryption.py` (generates new master keys)
3. Run `python migrate_private_keys.py` (re-encrypts all keys with new master)

## Key Rotation

The application also supports automatic key rotation on login:

- New RSA and ECC keys are generated for each user
- Old encrypted fields are decrypted and re-encrypted with new keys
- This happens automatically when users log in (see `auto_rotate_keys_on_login()`)

## For Developers

### Manual Master Key Generation

If you prefer to generate master keys manually:

```python
from security.rsa import generate_keys

# Generate 2048-bit RSA key pair
public_key, private_key = generate_keys(2048)

print(f"MASTER_RSA_PUBLIC_KEY={public_key}")
print(f"MASTER_RSA_PRIVATE_KEY={private_key}")
```

Then add these to your `.env` file:

```
MASTER_RSA_PUBLIC_KEY=(n, e) values
MASTER_RSA_PRIVATE_KEY=(n, d) values
```

### Testing Encryption

To verify that private keys are being encrypted:

```python
from models import User, db
from app import app

with app.app_context():
    user = User.query.first()
    print(f"RSA Private Key (from DB): {user.rsa_private_key[:20]}...")
    print(f"Starts with 'rsa:': {user.rsa_private_key.startswith('rsa:')}")

    # Should print True if encrypted
```

## Production Checklist

- [ ] Generate master keys with `python setup_encryption.py`
- [ ] Backup `.env` file securely (keep master keys safe)
- [ ] Test user registration (verify private keys are encrypted)
- [ ] Never commit `.env` to version control
- [ ] Use same `.env` across all application instances
- [ ] Regularly backup `.env` (if lost, encrypted keys cannot be recovered)
