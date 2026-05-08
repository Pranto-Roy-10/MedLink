# 🔐 CSE447 Security Setup Guide

## CRITICAL: Encryption Key Generation

This project implements **ASYMMETRIC-ONLY encryption** per CSE447 requirements. Private keys in the database are encrypted using a master RSA key pair.

### ⚠️ IMPORTANT SECURITY NOTES

1. **NEVER commit .env file to git** - It contains encryption keys!
2. **Keep .env file private** - If leaked, all encrypted data can be decrypted
3. **Generate new keys for each environment** (dev, staging, production)
4. **Back up .env file securely** - If lost, cannot decrypt data

---

## Setup Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
pip install cryptography
```

### Step 2: Generate Master Encryption Key

This key is used to encrypt/decrypt ALL private keys in the database.

```bash
python -c "import os; print(os.urandom(32).hex())"
```

**Output example:**
```
a1b2c3d4e5f6...7890abcdef (64 hex characters)
```

**Save this! You'll need it in .env**

### Step 3: Generate Master RSA Key Pair

This key pair is used to encrypt private keys before storing in database.

```bash
python
>>> from security.rsa import generate_keys
>>> pub, priv = generate_keys(2048)
>>> print("PUBLIC KEY:")
>>> print(pub)
>>> print("\nPRIVATE KEY:")
>>> print(priv)
>>> exit()
```

**Output example:**
```
PUBLIC KEY:
(1234567890..., 65537)

PRIVATE KEY:
(9876543210..., 1234567890...)
```

**Copy both! You'll need them in .env**

### Step 4: Create .env File

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///medlink.db

# Master Encryption Key (from Step 2)
MASTER_ENCRYPTION_KEY=a1b2c3d4e5f6...7890abcdef

# Master RSA Keys (from Step 3)
MASTER_RSA_PUBLIC_KEY=(1234567890..., 65537)
MASTER_RSA_PRIVATE_KEY=(9876543210..., 1234567890...)
```

### Step 5: Verify Setup

```bash
python -c "
import os
from dotenv import load_dotenv

load_dotenv()

# Check all required keys
required_keys = [
    'MASTER_ENCRYPTION_KEY',
    'MASTER_RSA_PUBLIC_KEY', 
    'MASTER_RSA_PRIVATE_KEY'
]

for key in required_keys:
    value = os.getenv(key)
    if value:
        print(f'✓ {key}: Found')
    else:
        print(f'✗ {key}: MISSING')
"
```

---

## Security Architecture

### How Private Keys Are Protected

```
┌─ USER REGISTRATION ─────────────────────────┐
│                                              │
│ 1. Generate RSA key pair for user           │
│    └─ Public key: stored plaintext          │
│    └─ Private key: TO BE ENCRYPTED          │
│                                              │
│ 2. Generate ECC key pair for user           │
│    └─ Public key: stored plaintext          │
│    └─ Private key: TO BE ENCRYPTED          │
│                                              │
│ 3. Encrypt private keys with master RSA     │
│    ├─ Private key → JSON                    │
│    ├─ JSON → Encrypted with master pub key  │
│    └─ Ciphertext: stored in database        │
│                                              │
│ 4. Database stores:                         │
│    ├─ username, email (plaintext)           │
│    ├─ password_hash (hashed)                │
│    ├─ rsa_public_key (plaintext - public!)  │
│    ├─ rsa_private_key_encrypted (ciphertext)│
│    ├─ ecc_public_key (plaintext - public!)  │
│    └─ ecc_private_key_encrypted (ciphertext)│
│                                              │
└─────────────────────────────────────────────┘

┌─ USER DECRYPTION (When Needed) ─────────────┐
│                                              │
│ 1. Fetch encrypted private key from DB      │
│                                              │
│ 2. Decrypt with master RSA private key      │
│    ├─ Ciphertext → Decrypt                  │
│    ├─ Result: JSON                          │
│    └─ Parse: Get private key                │
│                                              │
│ 3. Use private key for:                     │
│    ├─ Decrypting messages                   │
│    ├─ Signing documents                     │
│    └─ Other cryptographic operations        │
│                                              │
│ 4. Keep decrypted key in memory only        │
│    └─ Never write to disk                   │
│                                              │
└─────────────────────────────────────────────┘
```

### What Happens If Database is Hacked

**BEFORE (Vulnerable):**
```
Hacker accesses database:
  ├─ Sees plaintext private keys ✗
  ├─ Can decrypt all messages ✗
  ├─ Can impersonate users ✗
  └─ Complete system compromise ✗
```

**AFTER (Secure):**
```
Hacker accesses database:
  ├─ Sees encrypted private keys (garbage) ✓
  ├─ Needs master RSA private key ✗
  ├─ Cannot decrypt without it ✓
  ├─ Server is only one with master key ✓
  └─ Messages remain secure ✓
```

---

## CSE447 Compliance

This implementation satisfies all requirements:

✅ **Requirement #7:** All critical data encrypted (private keys encrypted with master RSA)

✅ **Requirement #9:** ASYMMETRIC ONLY (no XOR, no AES)
   - RSA used for: private key encryption
   - ECC used for: message encryption
   - No symmetric algorithms

✅ **Requirement #10:** Two asymmetric algorithms
   - RSA (1024-bit, 2048-bit)
   - ECC (SECP256K1)

---

## Key Management Operations

### Rotating Keys (Admin Function)

```python
# 1. Generate new master RSA key pair
from security.rsa import generate_keys
new_pub, new_priv = generate_keys(2048)

# 2. Re-encrypt all private keys
from models import User
users = User.query.all()
for user in users:
    if user.rsa_private_key_encrypted:
        # Decrypt with old master key
        old_decrypted = decrypt_with_old_master_key(user.rsa_private_key_encrypted)
        # Encrypt with new master key
        new_encrypted = encrypt_private_key_with_new_master_key(old_decrypted)
        user.rsa_private_key = new_encrypted

# 3. Update .env with new master key
# Update MASTER_RSA_PUBLIC_KEY
# Update MASTER_RSA_PRIVATE_KEY
```

### Emergency: Lost Master Key

If master encryption key is lost:
1. **All encrypted private keys become inaccessible**
2. **Users must reset passwords and regenerate keys**
3. **Historical encrypted data cannot be recovered**

**Prevention:**
- Back up .env file in secure location
- Store in password manager or HSM
- Replicate across secure servers

---

## Troubleshooting

### Error: "MASTER_ENCRYPTION_KEY not set"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Check .env has correct variable
grep MASTER_ENCRYPTION_KEY .env

# If missing, generate new key and add to .env
python -c "import os; print(os.urandom(32).hex())"
```

### Error: "Cannot decrypt private key"

**Causes:**
1. Wrong MASTER_RSA_PRIVATE_KEY in .env
2. Private key was encrypted with different master key
3. .env file modified

**Solution:**
```bash
# Verify .env is correct
cat .env

# Check database for encrypted key format
sqlite3 medlink.db "SELECT rsa_private_key FROM users LIMIT 1;"

# Should see: rsa:...hex...
```

### Error: "Private key JSON decode error"

**Cause:** Decryption produced garbage (wrong key)

**Solution:**
```bash
# Verify MASTER_RSA_PRIVATE_KEY is correct
python -c "
from security.rsa import generate_keys
import os

# The tuple you stored should match this format
pub, priv = generate_keys(2048)
print('Expected format:')
print(f'PUBLIC: {pub}')
print(f'PRIVATE: {priv}')

# Check .env
import os
from dotenv import load_dotenv
load_dotenv()
print('\nYour .env has:')
print(f\"MASTER_RSA_PRIVATE_KEY: {os.getenv('MASTER_RSA_PRIVATE_KEY')}\")
"
```

---

## Testing Encryption/Decryption

```bash
python
>>> from security.asymmetric_encryption import AsymmetricEncryption
>>> import os
>>> from dotenv import load_dotenv
>>> load_dotenv()
>>>
>>> # Test RSA encryption of a private key
>>> test_key = '{"k": 12345}'
>>> encrypted = AsymmetricEncryption.encrypt_private_key_with_master_key(test_key)
>>> print(f"Encrypted: {encrypted}")
>>>
>>> # Test decryption
>>> decrypted = AsymmetricEncryption.decrypt_private_key_with_master_key(encrypted)
>>> print(f"Decrypted: {decrypted}")
>>> print(f"Match: {decrypted == test_key}")
>>> exit()
```

**Expected Output:**
```
Encrypted: rsa:a1b2c3d4e5f6...
Decrypted: {"k": 12345}
Match: True
```

---

## Security Best Practices

1. **Minimize decryption time** - Decrypt only when needed
2. **Protect decrypted keys in memory** - Never log them
3. **Use constant-time operations** - Prevent timing attacks
4. **Rotate keys regularly** - At least annually
5. **Monitor access logs** - Track who decrypts keys
6. **Use HSM in production** - Hardware Security Module for master keys
7. **Separate environments** - Different keys for dev/staging/prod
8. **Secure backups** - Encrypt .env file even in backups

---

For questions about this implementation, contact your instructor.

**Remember: Encryption is only as strong as your key management! 🔐**
