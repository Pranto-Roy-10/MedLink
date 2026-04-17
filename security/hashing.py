"""
SHA-256 and HMAC Cryptographic Implementation
Implements SHA-256 from scratch with bitwise operations and HMAC for message authentication.

Mathematical Foundation:
SHA-256: Secure Hash Algorithm producing 256-bit (32-byte) output
HMAC: Hash-based Message Authentication Code for data integrity verification

References:
FIPS 180-4: Secure Hash Standard (SHS)
RFC 2104: HMAC definition
"""


# ==================== SHA-256 Constants ====================

# SHA-256 K Constants (first 32 bits of fractional parts of cube roots of first 64 primes)
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

# SHA-256 Initial Hash Values (first 32 bits of fractional parts of square roots of first 8 primes)
H_INIT = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]


# ==================== Bitwise Operations ====================

def rightrotate(n, d):
    """
    Right rotate an unsigned 32-bit integer by d bits.
    
    Formula: (n >> d) | ((n << (32 - d)) & 0xffffffff)
    
    Args:
        n: 32-bit integer
        d: Number of positions to rotate
    
    Returns:
        int: Rotated value
    """
    return ((n >> d) | (n << (32 - d))) & 0xffffffff


def rightshift(n, d):
    """
    Right shift an unsigned 32-bit integer by d bits.
    
    Formula: n >> d
    
    Args:
        n: 32-bit integer
        d: Number of positions to shift
    
    Returns:
        int: Shifted value
    """
    return n >> d


# ==================== SHA-256 Functions ====================

def sha256_ch(x, y, z):
    """
    SHA-256 Choice function: Ch(x,y,z) = (x & y) ⊕ (¬x & z)
    
    Selects bits from y if x bit is 1, from z if x bit is 0.
    
    Formula: (x ∧ y) ⊕ (¬x ∧ z)
    Where ∧ = AND, ⊕ = XOR, ¬ = NOT
    
    Args:
        x, y, z: 32-bit integers
    
    Returns:
        int: Result of choice function
    """
    return (x & y) ^ ((~x & 0xffffffff) & z)


def sha256_maj(x, y, z):
    """
    SHA-256 Majority function: Maj(x,y,z) = (x & y) ⊕ (x & z) ⊕ (y & z)
    
    Outputs the majority bit among the three inputs.
    
    Formula: (x ∧ y) ⊕ (x ∧ z) ⊕ (y ∧ z)
    
    Args:
        x, y, z: 32-bit integers
    
    Returns:
        int: Result of majority function
    """
    return (x & y) ^ (x & z) ^ (y & z)


def sha256_sigma0(x):
    """
    SHA-256 Σ0(x) = ROTR(2,x) ⊕ ROTR(13,x) ⊕ ROTR(22,x)
    
    Upper case sigma for H_t update.
    
    Formula: rightrotate(x, 2) ⊕ rightrotate(x, 13) ⊕ rightrotate(x, 22)
    
    Args:
        x: 32-bit integer
    
    Returns:
        int: Result
    """
    return rightrotate(x, 2) ^ rightrotate(x, 13) ^ rightrotate(x, 22)


def sha256_sigma1(x):
    """
    SHA-256 Σ1(x) = ROTR(6,x) ⊕ ROTR(11,x) ⊕ ROTR(25,x)
    
    Upper case sigma for carry/temp calculation.
    
    Formula: rightrotate(x, 6) ⊕ rightrotate(x, 11) ⊕ rightrotate(x, 25)
    
    Args:
        x: 32-bit integer
    
    Returns:
        int: Result
    """
    return rightrotate(x, 6) ^ rightrotate(x, 11) ^ rightrotate(x, 25)


def sha256_gamma0(x):
    """
    SHA-256 γ0(x) = ROTR(7,x) ⊕ ROTR(18,x) ⊕SHR(3,x)
    
    Lower case gamma for message schedule.
    
    Formula: rightrotate(x, 7) ⊕ rightrotate(x, 18) ⊕ rightshift(x, 3)
    
    Args:
        x: 32-bit integer
    
    Returns:
        int: Result
    """
    return rightrotate(x, 7) ^ rightrotate(x, 18) ^ rightshift(x, 3)


def sha256_gamma1(x):
    """
    SHA-256 γ1(x) = ROTR(17,x) ⊕ ROTR(19,x) ⊕ SHR(10,x)
    
    Lower case gamma for message schedule.
    
    Formula: rightrotate(x, 17) ⊕ rightrotate(x, 19) ⊕ rightshift(x, 10)
    
    Args:
        x: 32-bit integer
    
    Returns:
        int: Result
    """
    return rightrotate(x, 17) ^ rightrotate(x, 19) ^ rightshift(x, 10)


# ==================== SHA-256 Main Implementation ====================

def manual_sha256(data):
    """
    SHA-256 Hash Function Implementation
    
    Complete Algorithm (FIPS 180-4):
    
    Step 1: Preprocessing (Padding)
    - Append bit '1' to message
    - Append k zero bits where k is minimum non-negative integer
      such that (message_length + 1 + k) ≡ 448 (mod 512)
    - Append 64-bit block with original message length
    
    Step 2: Parse into 512-bit blocks
    
    Step 3: Initialize 8 hash values with H_INIT constants
    
    Step 4: For each 512-bit message block:
    - Copy hash values to working variables (a, b, c, d, e, f, g, h)
    - Generate 64-word schedule W[0..63]:
      W[0..15] = 512-bit block parsed as 16 32-bit words
      W[16..63] = γ1(W[i-2]) + W[i-7] + γ0(W[i-15]) + W[i-16]
    - Run 64 compression rounds with T1, T2 calculations
    - Add results back to hash values
    
    Step 5: Produce final hash value (concatenate 8 hash values)
    
    Args:
        data: Message as bytes or string
    
    Returns:
        str: 64-character hexadecimal SHA-256 hash
    """
    # Convert input to bytes
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Step 1: Preprocessing - Create padded message
    msg_len = len(data) * 8  # Message length in bits
    msg = bytearray(data)
    msg.append(0x80)  # Append '1' bit (0x80 = 10000000)
    
    # Append zero bytes until message length ≡ 448 (mod 512)
    while (len(msg) * 8) % 512 != 448:
        msg.append(0x00)
    
    # Append original message length as 64-bit big-endian
    msg += msg_len.to_bytes(8, byteorder='big')
    
    # Step 2: Initialize working hash variables
    h = H_INIT.copy()  # h0, h1, ..., h7
    
    # Step 3: Process each 512-bit block
    for block_start in range(0, len(msg), 64):
        block = msg[block_start:block_start + 64]
        
        # Step 4a: Create message schedule array W
        w = [0] * 64
        
        # W[0..15] = 512-bit block parsed as 16 32-bit words (big-endian)
        for i in range(16):
            w[i] = int.from_bytes(block[i*4:(i+1)*4], byteorder='big')
        
        # W[16..63] = γ1(W[i-2]) + W[i-7] + γ0(W[i-15]) + W[i-16]
        for i in range(16, 64):
            w[i] = (sha256_gamma1(w[i-2]) + w[i-7] + sha256_gamma0(w[i-15]) + w[i-16]) & 0xffffffff
        
        # Step 4b: Initialize working variables
        a, b, c, d, e, f, g, h_var = h
        
        # Step 4c: Compression loop (64 rounds)
        for i in range(64):
            # T1 = h + Σ1(e) + Ch(e,f,g) + K[i] + W[i]
            T1 = (h_var + sha256_sigma1(e) + sha256_ch(e, f, g) + K[i] + w[i]) & 0xffffffff
            
            # T2 = Σ0(a) + Maj(a,b,c)
            T2 = (sha256_sigma0(a) + sha256_maj(a, b, c)) & 0xffffffff
            
            # Update working variables
            h_var = g
            g = f
            f = e
            e = (d + T1) & 0xffffffff
            d = c
            c = b
            b = a
            a = (T1 + T2) & 0xffffffff
        
        # Step 4d: Add compressed chunk to hash values
        h[0] = (h[0] + a) & 0xffffffff
        h[1] = (h[1] + b) & 0xffffffff
        h[2] = (h[2] + c) & 0xffffffff
        h[3] = (h[3] + d) & 0xffffffff
        h[4] = (h[4] + e) & 0xffffffff
        h[5] = (h[5] + f) & 0xffffffff
        h[6] = (h[6] + g) & 0xffffffff
        h[7] = (h[7] + h_var) & 0xffffffff
    
    # Step 5: Produce final hash value (convert to hex)
    hash_hex = ''.join(f'{value:08x}' for value in h)
    return hash_hex


# ==================== HMAC Implementation ====================

def hmac_sha256(key, message):
    """
    HMAC-SHA256: Hash-based Message Authentication Code
    
    RFC 2104 Algorithm:
    
    Step 1: If key length > block size (64 bytes for SHA-256):
            key = SHA256(key)
    
    Step 2: Pad key to block size:
            If key length < block size:
              key = key || 0x00...00
    
    Step 3: Generate inner and outer padding:
            ipad = 0x36 repeated block_size times
            opad = 0x5c repeated block_size times
    
    Step 4: Compute HMAC:
            HMAC(key, msg) = SHA256((key ⊕ opad) || SHA256((key ⊕ ipad) || msg))
    
    Step 5: Return first 32 bytes of result as MAC tag
    
    Mathematical Property:
    - Secure if hash function is collision-resistant
    - Provides authentication + integrity
    - Detects any modification to message or key
    
    Args:
        key: Secret key (bytes or string)
        message: Message to authenticate (bytes or string)
    
    Returns:
        str: 64-character hexadecimal HMAC-SHA256
    """
    # Convert inputs to bytes
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(message, str):
        message = message.encode('utf-8')
    
    block_size = 64  # SHA-256 block size in bytes
    
    # Step 1: If key is longer than block size, hash it
    if len(key) > block_size:
        key = bytes.fromhex(manual_sha256(key))
    
    # Step 2: Pad key to block size
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))
    
    # Step 3: Create inner and outer padding
    ipad = b'\x36' * block_size  # Inner pad constant
    opad = b'\x5c' * block_size  # Outer pad constant
    
    # Step 4: Compute HMAC
    # Inner: SHA256((key ⊕ ipad) || message)
    key_ipad = bytes(a ^ b for a, b in zip(key, ipad))
    inner_hash = manual_sha256(key_ipad + message)
    
    # Outer: SHA256((key ⊕ opad) || inner_hash)
    key_opad = bytes(a ^ b for a, b in zip(key, opad))
    outer_hash = manual_sha256(key_opad + bytes.fromhex(inner_hash))
    
    return outer_hash


def generate_mac(key, message):
    """
    Generate Message Authentication Code for data integrity.
    
    Alias for hmac_sha256 - used in models for MAC tag generation.
    
    Args:
        key: Secret key for MAC generation
        message: Data to authenticate
    
    Returns:
        str: 64-character hexadecimal MAC tag
    """
    return hmac_sha256(key, message)


def verify_mac(key, message, mac_tag):
    """
    Verify Message Authentication Code.
    
    Compares computed MAC with provided MAC using constant-time comparison
    to prevent timing attacks.
    
    Args:
        key: Secret key used to generate MAC
        message: Original message
        mac_tag: MAC tag to verify
    
    Returns:
        bool: True if MAC is valid, False otherwise
    """
    expected_mac = generate_mac(key, message)
    
    # Constant-time comparison (prevents timing attacks)
    if len(expected_mac) != len(mac_tag):
        return False
    
    result = 0
    for a, b in zip(expected_mac, mac_tag):
        result |= ord(a) ^ ord(b)
    
    return result == 0


def hmac_verify(key, message, mac_tag):
    """
    Alias for verify_mac - verifies data integrity using HMAC.
    
    Args:
        key: Secret key
        message: Original message
        mac_tag: MAC tag to verify
    
    Returns:
        bool: True if valid, False otherwise
    """
    return verify_mac(key, message, mac_tag)


# ==================== Password Hashing ====================

import os
import base64


def hash_password(password, salt=None):
    """
    Hash a password using SHA-256 with salt for user authentication.
    
    Algorithm:
    1. If no salt provided, generate random 16-byte salt
    2. Hash password: H = SHA256(salt || password)
    3. Return: salt || H (base64 encoded for storage)
    
    This provides protection against:
    - Dictionary attacks (via salt)
    - Rainbow table attacks (unique salt per user)
    - Multiple users with same password (different salts)
    
    Args:
        password: Plain text password to hash
        salt: Optional salt (bytes). If None, generates random 16-byte salt
    
    Returns:
        str: Base64-encoded "salt||hash" string for database storage
    """
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Generate salt if not provided
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = salt.encode('utf-8')
    
    # Hash password with salt: H = SHA256(salt || password)
    salted_password = salt + password
    password_hash = bytes.fromhex(manual_sha256(salted_password))
    
    # Return base64-encoded "salt||hash"
    combined = salt + password_hash
    return base64.b64encode(combined).decode('utf-8')


def verify_password(password, hashed):
    """
    Verify a password against its hash.
    
    Algorithm:
    1. Base64 decode stored hash
    2. Extract salt (first 16 bytes) and expected hash (remaining 32 bytes)
    3. Hash provided password with extracted salt
    4. Constant-time comparison of hashes
    
    Args:
        password: Plain text password to verify
        hashed: Base64-encoded "salt||hash" from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Decode base64 hash
        combined = base64.b64decode(hashed.encode('utf-8'))
        
        # Extract salt and expected hash
        salt = combined[:16]
        expected_hash = combined[16:]
        
        # Hash provided password with extracted salt
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        salted_password = salt + password
        computed_hash = bytes.fromhex(manual_sha256(salted_password))
        
        # Constant-time comparison
        if len(expected_hash) != len(computed_hash):
            return False
        
        result = 0
        for a, b in zip(expected_hash, computed_hash):
            result |= a ^ b
        
        return result == 0
    
    except Exception:
        return False
