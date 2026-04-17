# MedLink Security Module Documentation

## Project Overview

The MedLink cryptographic security package has been reorganized into a modular architecture containing manual implementations of RSA, ECC, SHA-256, and HMAC for educational and laboratory purposes.

## Folder Structure

```
MedLink/
├── security/                 # Cryptographic package
│   ├── __init__.py          # Package initialization and exports
│   ├── rsa.py               # RSA encryption implementation
│   ├── ecc.py               # Elliptic Curve Cryptography
│   └── hashing.py           # SHA-256 and HMAC implementations
├── app.py                   # Flask application (updated)
├── models.py                # Database models (updated)
├── medlink.db               # SQLite database
├── requirements.txt         # Dependencies
└── templates/               # HTML templates
```

---

## Module Descriptions

### 1. security/rsa.py - RSA Encryption

**Purpose:** Complete RSA cryptographic implementation with the 6-step key generation algorithm.

#### Key Functions:

**`generate_keys(key_size=512) → (public_key, private_key)`**
- **Algorithm Steps:**
  1. Generate two distinct large prime numbers $p$ and $q$ using Miller-Rabin
  2. Calculate $N = p \times q$ (modulus)
  3. Calculate $\phi(N) = (p-1) \times (q-1)$ (Euler's totient)
  4. Choose $e$ such that $1 < e < \phi(N)$ and $\gcd(e, \phi(N)) = 1$
  5. Calculate $d \equiv e^{-1} \pmod{\phi(N)}$ (modular inverse)
  6. Return public key $(e, N)$ and private key $(d, N)$
- **Mathematical Property:** $M^{ed} \equiv M \pmod{N}$ (RSA correctness)

**`is_prime(n, k=40) → bool`**
- **Miller-Rabin Primality Test**
- **Formula:** For $n-1 = 2^r \times d$ where $d$ is odd:
  - Test: $x = a^d \bmod n$
  - Iterate: $x = x^2 \bmod n$ up to $r-1$ times
  - Accept if $x = 1$ or $x = n-1$ (repeat $k$ times)
- **Complexity:** $O(k \log^3 n)$ with probability $4^{-k}$ error

**`extended_gcd(a, b) → (gcd, x, y)`**
- **Euclidean Algorithm:** Finds $x, y$ such that $ax + by = \gcd(a, b)$
- **Used for:** Computing modular inverse $d = e^{-1} \bmod \phi(n)$
- **Formula:** $e \cdot d \equiv 1 \pmod{\phi(n)}$

**`encrypt(message_int, public_key) → ciphertext_int`**
- **Formula:** $C \equiv M^e \pmod{N}$
- **Uses:** Python's built-in `pow(M, e, N)` for fast modular exponentiation

**`decrypt(ciphertext_int, private_key) → message_int`**
- **Formula:** $M \equiv C^d \pmod{N}$
- **Uses:** Python's built-in `pow(C, d, N)` for fast modular exponentiation

#### Example Usage:
```python
from security.rsa import generate_keys, encrypt, decrypt

# Generate 512-bit keys
public_key, private_key = generate_keys(512)  # (e, N), (d, N)

# Encrypt a number
message = 12345
ciphertext = encrypt(message, public_key)     # C = M^e mod N

# Decrypt
plaintext = decrypt(ciphertext, private_key)  # M = C^d mod N
assert plaintext == message
```

---

### 2. security/ecc.py - Elliptic Curve Cryptography

**Purpose:** Manual implementation of point arithmetic on elliptic curves.

**Curve Equation:** $y^2 \equiv x^3 + ax + b \pmod{p}$

#### Key Classes:

**`class Point(x, y, curve)`**
- Represents a point on an elliptic curve
- **Special point:** Point at infinity $O$ (additive identity)

**`class EllipticCurve(a, b, p)`**
- Defines an elliptic curve over finite field $\mathbb{F}_p$
- **Validation:** Discriminant $4a^3 + 27b^2 \not\equiv 0 \pmod{p}$

#### Point Operations:

**`point_addition(P, Q) → R`**
- **Formula (when $P \neq Q$):**
  - $\lambda = \frac{y_Q - y_P}{x_Q - x_P} \bmod p$ (slope)
  - $x_R = \lambda^2 - x_P - x_Q \bmod p$
  - $y_R = \lambda(x_P - x_R) - y_P \bmod p$
- **Special cases:**
  - $P = O \Rightarrow P + Q = Q$
  - $Q = O \Rightarrow P + Q = P$
  - $P.x = Q.x, P.y = -Q.y \Rightarrow P + Q = O$

**`point_doubling(P) → 2P`**
- **Formula (when $y \neq 0$):**
  - $\lambda = \frac{3x^2 + a}{2y} \bmod p$ (derivative slope)
  - $x_R = \lambda^2 - 2x \bmod p$
  - $y_R = \lambda(x - x_R) - y \bmod p$

**`scalar_multiplication(k, P) → kP`**
- **Double-and-Add Algorithm** for efficiency
- **Formula:** $kP = P + P + \cdots + P$ ($k$ times)
- **Complexity:** $O(\log k)$ using binary representation
- **Algorithm:**
  1. Write $k$ in binary: $k = \sum b_i 2^i$
  2. For each bit from LSB to MSB:
     - If bit is 1, add $P$ to result
     - Double $P$ for next iteration

#### Example Usage:
```python
from security.ecc import EllipticCurve, Point

# Create a test curve: y² = x³ + x + 1 (mod 1009)
curve = EllipticCurve(a=1, b=1, p=1009)

# Define a point on the curve
P = Point(2, 2, curve)

# Point operations
Q = Point(3, 6, curve)
R = curve.point_addition(P, Q)      # P + Q

double_P = curve.point_doubling(P)  # 2P

# Scalar multiplication
result = curve.scalar_multiplication(5, P)  # 5P (efficient)
```

---

### 3. security/hashing.py - SHA-256 and HMAC

**Purpose:** Complete SHA-256 implementation from scratch with bitwise operations and HMAC.

#### SHA-256 Implementation:

**`manual_sha256(data) → hex_digest`**

**Complete Algorithm (FIPS 180-4):**

**Step 1: Preprocessing (Padding)**
- Append bit '1' to message
- Append $k$ zero bits where $k$ is minimum such that $(msg\_len + 1 + k) \equiv 448 \pmod{512}$
- Append 64-bit block with original message length in bits

**Step 2: Parse into 512-bit blocks**

**Step 3: Initialize hash values**
- $H_0, H_1, \ldots, H_7$ from first 32 bits of square roots of first 8 primes

**Step 4: For each 512-bit block:**
- **Message Schedule:** Generate 64-word schedule
  - $W[0:16]$ = 512-bit block as 16 32-bit words
  - $W[16:64] = \gamma_1(W[i-2]) + W[i-7] + \gamma_0(W[i-15]) + W[i-16]$
  
- **Bitwise Operations Used:**
  - $\text{Ch}(x,y,z) = (x \land y) \oplus (\neg x \land z)$ (choice)
  - $\text{Maj}(x,y,z) = (x \land y) \oplus (x \land z) \oplus (y \land z)$ (majority)
  - $\Sigma_0(x) = \text{ROTR}(2,x) \oplus \text{ROTR}(13,x) \oplus \text{ROTR}(22,x)$
  - $\Sigma_1(x) = \text{ROTR}(6,x) \oplus \text{ROTR}(11,x) \oplus \text{ROTR}(25,x)$
  - $\gamma_0(x) = \text{ROTR}(7,x) \oplus \text{ROTR}(18,x) \oplus \text{SHR}(3,x)$
  - $\gamma_1(x) = \text{ROTR}(17,x) \oplus \text{ROTR}(19,x) \oplus \text{SHR}(10,x)$

- **Compression Loop (64 rounds):**
  - $T_1 = H + \Sigma_1(E) + \text{Ch}(E,F,G) + K[i] + W[i]$
  - $T_2 = \Sigma_0(A) + \text{Maj}(A,B,C)$
  - Update: $A \leftarrow T_1 + T_2$, shift others right

**Step 5: Produce final hash**
- Concatenate 8 hash values as 64-character hex string

**Example:**
```python
from security.hashing import manual_sha256

# Compute SHA-256
message = "MedLink Security"
digest = manual_sha256(message)  # 64-char hex string
```

#### HMAC-SHA256 Implementation:

**`hmac_sha256(key, message) → mac`**

**RFC 2104 Algorithm:**
- **Block size:** 64 bytes (512 bits)
- **Key preprocessing:** If $|key| > 64$: $key = \text{SHA256}(key)$
- **Padding:** If $|key| < 64$: $key = key \| 0x00\ldots00$
- **Inner/Outer pads:**
  - $\text{ipad} = 0x36 \text{ repeated } 64 \text{ times}$
  - $\text{opad} = 0x5c \text{ repeated } 64 \text{ times}$
- **Formula:** $\text{HMAC}(K,M) = \text{SHA256}((K \oplus \text{opad}) \| \text{SHA256}((K \oplus \text{ipad}) \| M))$

**XOR Operations:** $\oplus$ (bitwise exclusive OR) for byte-level operations

**Example:**
```python
from security.hashing import hmac_sha256, verify_mac

# Generate MAC
key = "secret_key"
message = "Medical Record"
mac = hmac_sha256(key, message)

# Verify MAC
is_valid = verify_mac(key, message, mac)
```

#### Password Hashing:

**`hash_password(password, salt=None) → hashed`**
- **Algorithm:**
  1. Generate random 16-byte salt if not provided
  2. Hash: $H = \text{SHA256}(\text{salt} \| \text{password})$
  3. Return: base64($\text{salt} \| H$)
- **Protection against:**
  - Dictionary attacks (via salt)
  - Rainbow tables (unique salt per user)
  - Same password patterns (different salts)

**`verify_password(password, hashed) → bool`**
- **Constant-time comparison** to prevent timing attacks
- **Algorithm:**
  1. Decode base64 hash
  2. Extract salt (first 16 bytes) and expected hash
  3. Recompute: $H' = \text{SHA256}(\text{salt} \| \text{password})$
  4. Compare: $H == H'$ (bitwise XOR, prevent short-circuit)

**Example:**
```python
from security.hashing import hash_password, verify_password

# Hash a password
hashed = hash_password("user_password")
# Output: base64-encoded "salt||sha256_hash"

# Verify password
is_correct = verify_password("user_password", hashed)
```

---

### 4. security/__init__.py - Package Initialization

**Purpose:** Export all security functions for convenient importing.

**Exported Functions:**
```python
from security.rsa import (
    generate_keys, encrypt, decrypt,
    rsa_encrypt_hex, rsa_decrypt_hex,
    is_prime, get_prime, extended_gcd, mod_inverse
)

from security.ecc import (
    EllipticCurve, Point,
    create_curve_secp256k1_demo, create_test_curve
)

from security.hashing import (
    manual_sha256, hmac_sha256,
    generate_mac, verify_mac, hmac_verify,
    hash_password, verify_password
)
```

---

## Integration with MedLink Application

### models.py Changes

**Password Hashing:**
```python
from security.hashing import hash_password, verify_password

class User(db.Model):
    def set_password(self, password):
        """Hash password using SHA-256 + salt"""
        self.password_hash = hash_password(password)
    
    def check_password(self, password):
        """Verify password using constant-time comparison"""
        return verify_password(password, self.password_hash)
```

**MAC Tag Generation and Verification:**
```python
from security.hashing import generate_mac, verify_mac

class Referral(db.Model):
    def verify_integrity(self):
        """Verify HMAC-SHA256 MAC tag"""
        if not self.mac_tag or not self.encrypted_content:
            return False
        
        hmac_key = f"referral_{self.sender_id}"
        if verify_mac(hmac_key, self.encrypted_content, self.mac_tag):
            self.is_verified = True
            return True
        return False
```

### app.py Changes

**Sample Data Initialization:**
```python
from security.hashing import generate_mac

def init_sample_data():
    # Hash passwords using security module
    patient.set_password('patient123')  # Uses SHA-256 + salt
    
    # Generate MAC tags using HMAC
    referral_content = 'Patient needs cardiology consultation'
    referral_mac = generate_mac(f"referral_{doctor.id}", referral_content)
    
    referral = Referral(
        ...,
        mac_tag=referral_mac  # Real HMAC-SHA256 tag
    )
```

---

## Mathematical Formulas for Lab Defense

### RSA
- **Encryption:** $C \equiv M^e \pmod{N}$
- **Decryption:** $M \equiv C^d \pmod{N}$
- **Key Property:** $e \cdot d \equiv 1 \pmod{\phi(N)}$ where $\phi(N) = (p-1)(q-1)$

### ECC
- **Curve:** $y^2 \equiv x^3 + ax + b \pmod{p}$
- **Point Addition:** $\lambda = \frac{y_Q - y_P}{x_Q - x_P} \bmod p$
- **Scalar Multiplication:** $kP = \sum_{i=0}^{\log_2 k} b_i \cdot 2^i \cdot P$

### SHA-256
- **Padding:** $(M \| 1 \| 0^k \| L) \bmod 512 = 0$ where $L$ is message length
- **Message Schedule:** $W[i] = \gamma_1(W[i-2]) + W[i-7] + \gamma_0(W[i-15]) + W[i-16]$
- **Compression:** $T_1 = H + \Sigma_1(E) + \text{Ch}(E,F,G) + K[i] + W[i]$

### HMAC
- **Formula:** $\text{HMAC}(K,M) = H((K \oplus \text{opad}) \| H((K \oplus \text{ipad}) \| M))$
- **ipad:** $0x36$ repeated 64 times
- **opad:** $0x5c$ repeated 64 times

---

## Testing and Verification

**Test the security module:**
```bash
python -c "
from security.rsa import generate_keys, encrypt, decrypt
from security.hashing import manual_sha256, hmac_sha256
from security.ecc import EllipticCurve, Point

# RSA test
pub, priv = generate_keys(256)
msg = 12345
enc = encrypt(msg, pub)
dec = decrypt(enc, priv)
print(f'RSA Test: {msg == dec}')  # True

# SHA-256 test
hash1 = manual_sha256('test')
print(f'SHA256 Test: {len(hash1) == 64}')  # True

# HMAC test
mac = hmac_sha256('key', 'message')
print(f'HMAC Test: {len(mac) == 64}')  # True
"
```

---

## Security Considerations

⚠️ **For Production Use:**
- This implementation is for **educational purposes only**
- Use established cryptography libraries (cryptography.io, PyCryptodome) for production
- Implement proper key management and storage
- Use TLS/SSL for network communication
- Implement secure random number generation
- Add additional authentication factors

✅ **Lab Defense Features:**
- Complete algorithm documentation with mathematical formulas
- Manual implementation demonstrating algorithm understanding
- Bitwise operations explicitly shown (no library shortcuts)
- Modular design showing cryptographic components
- Integrated authentication and integrity verification

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `security/rsa.py` | 250+ | RSA with Miller-Rabin, Extended GCD, 6-step key generation |
| `security/ecc.py` | 350+ | ECC point arithmetic, scalar multiplication |
| `security/hashing.py` | 400+ | SHA-256 from scratch, HMAC, password hashing |
| `security/__init__.py` | 60 | Package exports and documentation |
| `models.py` | 175 | Updated with security module integration |
| `app.py` | 350+ | Updated with HMAC-based MAC tag generation |

---

## Version Information

- **MedLink Version:** 2.0 (Cryptographic Reorganization)
- **Python:** 3.8+
- **Flask:** 2.3.3
- **SQLAlchemy:** 3.0.5
- **Security Package Version:** 1.0.0

---

## Next Steps

1. ✅ **Reorganize into modular structure** - COMPLETE
2. ✅ **Implement RSA 6-step algorithm** - COMPLETE
3. ✅ **Implement ECC point arithmetic** - COMPLETE
4. ✅ **Implement SHA-256 from scratch** - COMPLETE
5. ✅ **Implement HMAC** - COMPLETE
6. ✅ **Integrate into MedLink** - COMPLETE
7. 🔲 **Lab Defense Presentation**
8. 🔲 **Production hardening** (optional future)
