"""
MedLink Security Package
Provides modular cryptographic implementations for RSA, ECC, SHA-256, and HMAC.

This package contains manual implementations of cryptographic algorithms
for educational purposes and MedLink's secure medical referral system.

Modules:
- rsa.py: RSA encryption with 6-step key generation
- ecc.py: Elliptic Curve Cryptography for key exchange
- hashing.py: SHA-256 and HMAC implementations

Usage:
    from security.rsa import generate_keys, encrypt, decrypt
    from security.ecc import EllipticCurve, Point
    from security.hashing import manual_sha256, hmac_sha256, generate_mac
"""

# Import key functions from submodules for convenience
from .rsa import (
    generate_keys,
    encrypt,
    decrypt,
    rsa_encrypt_hex,
    rsa_decrypt_hex,
    is_prime,
    get_prime,
    extended_gcd,
    mod_inverse
)

from .ecc import (
    EllipticCurve,
    Point,
    create_curve_secp256k1_demo,
    create_test_curve
)

from .hashing import (
    manual_sha256,
    hmac_sha256,
    generate_mac,
    verify_mac,
    hmac_verify,
    hash_password,
    verify_password
)

from .encryption_utils import (
    ecc_encrypt_message,
    ecc_decrypt_message,
    encrypt_email_rsa,
    decrypt_email_rsa,
    encrypt_sensitive_data,
    decrypt_sensitive_data
)

__all__ = [
    # RSA
    'generate_keys',
    'encrypt',
    'decrypt',
    'rsa_encrypt_hex',
    'rsa_decrypt_hex',
    'is_prime',
    'get_prime',
    'extended_gcd',
    'mod_inverse',
    
    # ECC
    'EllipticCurve',
    'Point',
    'create_curve_secp256k1_demo',
    'create_test_curve',
    
    # Hashing
    'manual_sha256',
    'hmac_sha256',
    'generate_mac',
    'verify_mac',
    'hmac_verify',
    'hash_password',
    'verify_password',
    
    # Encryption Utils
    'ecc_encrypt_message',
    'ecc_decrypt_message',
    'encrypt_email_rsa',
    'decrypt_email_rsa',
    'encrypt_sensitive_data',
    'decrypt_sensitive_data'
]

__version__ = '1.0.0'
__author__ = 'MedLink Security Team'
__description__ = 'Cryptographic implementations for MedLink medical platform'
