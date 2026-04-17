"""
RSA Cryptographic Implementation
Implements the 6-step RSA algorithm with manual primality testing and modular arithmetic.

Mathematical Foundation:
- Public Key: (e, N)
- Private Key: (d, N)
- Encryption: C ≡ M^e (mod N)
- Decryption: M ≡ C^d (mod N)
- Security: N = p × q (product of two large primes)
"""

import random


def is_prime(n, k=40):
    """
    Miller-Rabin Primality Test
    
    Algorithm:
    1. Write n - 1 as 2^r × d where d is odd
    2. Repeat k times:
       - Pick random a: 1 < a < n - 1
       - Compute x = a^d mod n
       - If x = 1 or x = n - 1, continue
       - Repeat r-1 times: x = x^2 mod n
         If x = n - 1, continue outer loop
       - Return COMPOSITE
    3. Return PROBABLY PRIME
    
    Args:
        n: Integer to test for primality
        k: Number of iterations (higher k = higher confidence)
    
    Returns:
        bool: True if probably prime, False if composite
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    
    # Write n - 1 as 2^r × d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    # Witness loop - repeat k times
    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)  # a^d mod n using fast modular exponentiation
        
        if x == 1 or x == n - 1:
            continue
        
        for _ in range(r - 1):
            x = pow(x, 2, n)  # x^2 mod n
            if x == n - 1:
                break
        else:
            return False
    
    return True


def get_prime(bit_length):
    """
    Generate a random prime number of specified bit length.
    
    Algorithm:
    1. Generate random odd number of bit_length
    2. Test for primality using Miller-Rabin
    3. Repeat until prime found
    
    Args:
        bit_length: Desired bit length of prime
    
    Returns:
        int: A prime number with bit_length bits
    """
    while True:
        num = random.getrandbits(bit_length)
        num |= (1 << bit_length - 1) | 1  # Set MSB and make odd
        if is_prime(num):
            return num


def extended_gcd(a, b):
    """
    Extended Euclidean Algorithm
    
    Finds integers x, y such that: a·x + b·y = gcd(a, b)
    
    Mathematical Formulation:
    1. If b = 0: return (a, 1, 0)
    2. Otherwise: recursively compute gcd(b, a mod b)
    3. Back-substitute to find coefficients
    
    Used to find modular inverse: d = e^(-1) mod φ(n)
    where e·d ≡ 1 (mod φ(n))
    
    Args:
        a: First integer
        b: Second integer
    
    Returns:
        tuple: (gcd, x, y) where a·x + b·y = gcd
    """
    if b == 0:
        return a, 1, 0
    else:
        gcd, x, y = extended_gcd(b, a % b)
        return gcd, y, x - (a // b) * y


def mod_inverse(e, phi):
    """
    Compute modular multiplicative inverse.
    
    Finds d such that: e·d ≡ 1 (mod φ)
    
    Uses extended GCD: e·d = 1 + k·φ for some integer k
    Therefore: e·d ≡ 1 (mod φ)
    
    Args:
        e: The exponent (public exponent)
        phi: Euler's totient function value φ(n) = (p-1)(q-1)
    
    Returns:
        int: Modular inverse d such that e·d ≡ 1 (mod φ)
    
    Raises:
        ValueError: If e and phi are not coprime
    """
    gcd, x, _ = extended_gcd(e, phi)
    if gcd != 1:
        raise ValueError("Modular inverse does not exist")
    return (x % phi + phi) % phi


def generate_keys(key_size=512):
    """
    Generate RSA Key Pair - The 6-Step Algorithm
    
    Step 1: Choose two distinct large prime numbers p and q
    Step 2: Calculate N = p × q (modulus for encryption/decryption)
    Step 3: Calculate φ(N) = (p-1) × (q-1) (Euler's totient)
    Step 4: Choose e such that 1 < e < φ(N) and gcd(e, φ(N)) = 1
    Step 5: Calculate d ≡ e^(-1) (mod φ(N)) (modular inverse)
    Step 6: Public key is (e, N), Private key is (d, N)
    
    Mathematical Verification:
    For any message M: M^(e·d) ≡ M (mod N)
    Proof: e·d ≡ 1 (mod φ(N)) → e·d = 1 + k·φ(N)
           M^(e·d) = M^(1 + k·φ(N)) = M · (M^φ(N))^k ≡ M · 1^k ≡ M (mod N)
           by Euler's theorem: M^φ(N) ≡ 1 (mod N) when gcd(M, N) = 1
    
    Args:
        key_size: Bit length of each prime (total N will be ~2x this size)
    
    Returns:
        tuple: ((e, N), (d, N)) - (public_key, private_key)
    """
    # Step 1: Generate two distinct large primes
    p = get_prime(key_size)
    q = get_prime(key_size)
    while p == q:
        q = get_prime(key_size)
    
    # Step 2: Calculate N = p × q
    N = p * q
    
    # Step 3: Calculate φ(N) = (p-1) × (q-1)
    phi = (p - 1) * (q - 1)
    
    # Step 4: Choose e (commonly 65537 for efficiency)
    e = 65537
    while e >= phi or gcd_simple(e, phi) != 1:
        e = random.randint(2, phi - 1)
    
    # Step 5: Calculate d = e^(-1) mod φ(N)
    d = mod_inverse(e, phi)
    
    # Step 6: Return public and private keys
    public_key = (e, N)
    private_key = (d, N)
    
    return public_key, private_key


def gcd_simple(a, b):
    """
    Simple GCD using Euclidean algorithm (for step 4 check).
    
    Algorithm: gcd(a, b) = gcd(b, a mod b) until b = 0
    
    Args:
        a, b: Integers
    
    Returns:
        int: Greatest common divisor
    """
    while b:
        a, b = b, a % b
    return a


def encrypt(message_int, public_key):
    """
    RSA Encryption
    
    Formula: C ≡ M^e (mod N)
    
    Args:
        message_int: Message as integer M
        public_key: Tuple (e, N) - public key pair
    
    Returns:
        int: Ciphertext C
    """
    e, N = public_key
    return pow(message_int, e, N)  # Uses fast modular exponentiation


def decrypt(ciphertext_int, private_key):
    """
    RSA Decryption
    
    Formula: M ≡ C^d (mod N)
    
    Args:
        ciphertext_int: Ciphertext as integer C
        private_key: Tuple (d, N) - private key pair
    
    Returns:
        int: Decrypted message M
    """
    d, N = private_key
    return pow(ciphertext_int, d, N)  # Uses fast modular exponentiation


def rsa_encrypt_hex(message, public_key):
    """
    Convenience function: Encrypt string message and return hex.
    
    Args:
        message: String message to encrypt
        public_key: RSA public key tuple (e, N)
    
    Returns:
        str: Hexadecimal representation of ciphertext
    """
    message_int = int(message.encode('utf-8').hex(), 16)
    ciphertext_int = encrypt(message_int, public_key)
    return hex(ciphertext_int)[2:]


def rsa_decrypt_hex(ciphertext_hex, private_key):
    """
    Convenience function: Decrypt hex ciphertext and return string.
    
    Args:
        ciphertext_hex: Hexadecimal representation of ciphertext
        private_key: RSA private key tuple (d, N)
    
    Returns:
        str: Decrypted message
    """
    ciphertext_int = int(ciphertext_hex, 16)
    message_int = decrypt(ciphertext_int, private_key)
    return bytes.fromhex(hex(message_int)[2:]).decode('utf-8')
