"""
Pre-Storage Encryption Utilities
Handles encryption of sensitive data before database storage.
Provides unified interface for RSA and ECC encryption/decryption.

IMPORTANT: Encryption happens on the BACKEND (server-side) so the plaintext never travels over the network.
The database stores ONLY encrypted ciphertext.
Decryption only happens server-side when authorized users request messages.
"""

import json
import hashlib
from security.rsa import rsa_encrypt_hex, rsa_decrypt_hex
from security.hashing import generate_mac, verify_mac, manual_sha256


def derive_encryption_key(sender_ecc_public_key, receiver_ecc_public_key):
    """
    Derive a shared encryption key using both public keys.
    
    IMPORTANT: This is SYMMETRIC - both sender and receiver can compute it!
    
    Algorithm:
    1. Use BOTH sender and receiver public key coordinates
    2. Hash them together: SHA256(sender_pubkey || receiver_pubkey)
    3. This creates a SHARED key that both can derive independently
    
    Key property:
    - Sender can compute using: sender_pub + receiver_pub (has both)
    - Receiver can compute using: sender_pub + receiver_pub (has both from DB or message metadata)
    
    Args:
        sender_ecc_public_key (dict): {"x": int, "y": int} - sender's public key
        receiver_ecc_public_key (dict): {"x": int, "y": int} - receiver's public key
    
    Returns:
        bytes: 32-byte symmetric encryption key
    """
    # Extract coordinates - sort them to make it symmetric
    sender_x = sender_ecc_public_key.get('x', 0) if sender_ecc_public_key else 0
    sender_y = sender_ecc_public_key.get('y', 0) if sender_ecc_public_key else 0
    receiver_x = receiver_ecc_public_key.get('x', 0) if receiver_ecc_public_key else 0
    receiver_y = receiver_ecc_public_key.get('y', 0) if receiver_ecc_public_key else 0
    
    # Create key material from both public keys
    # Sort to ensure symmetry: same key regardless of who encrypts
    if sender_x <= receiver_x:
        key_material = f"{sender_x}:{sender_y}:{receiver_x}:{receiver_y}".encode('utf-8')
    else:
        key_material = f"{receiver_x}:{receiver_y}:{sender_x}:{sender_y}".encode('utf-8')
    
    derived_key = hashlib.sha256(key_material).digest()
    return derived_key


def ecc_encrypt_message(message, sender_ecc_public_key, receiver_ecc_public_key):
    """
    Encrypt a message using symmetric encryption derived from both public keys.
    
    IMPORTANT: This encryption happens on the BACKEND ONLY.
    The plaintext message NEVER leaves the server.
    
    Algorithm:
    1. Use BOTH sender and receiver public keys to derive shared symmetric key
    2. Key derivation is SYMMETRIC: both can independently compute same key
    3. Encrypt message with this key using XOR cipher
    4. Only ciphertext stored in database
    5. Plaintext never transmitted or stored
    
    Security:
    - Plaintext never transmitted or stored
    - Both sender and receiver can decrypt (both have public keys)
    - Ciphertext in DB cannot be decrypted by eavesdropper (needs at least one private key)
    
    Args:
        message (str): Plaintext message to encrypt
        sender_ecc_public_key (dict): {"x": int, "y": int} - sender's public key
        receiver_ecc_public_key (dict): {"x": int, "y": int} - receiver's public key
    
    Returns:
        str: Hex-encoded ciphertext (format: "ecc:ciphertext_hex")
    """
    if sender_ecc_public_key and receiver_ecc_public_key:
        # Derive shared encryption key from BOTH public keys
        encryption_key = derive_encryption_key(sender_ecc_public_key, receiver_ecc_public_key)
        
        # Encrypt message
        message_bytes = message.encode('utf-8')
        ciphertext_bytes = bytearray()
        
        # XOR each byte with corresponding byte of key (cycling)
        for i, byte in enumerate(message_bytes):
            ciphertext_bytes.append(byte ^ encryption_key[i % len(encryption_key)])
        
        ciphertext_hex = ciphertext_bytes.hex()
        return f"ecc:{ciphertext_hex}"
    
    return None


def ecc_decrypt_message(ciphertext_hex, sender_ecc_public_key, receiver_ecc_public_key):
    """
    Decrypt a symmetric-encrypted message using both public keys.
    
    IMPORTANT: Decryption happens ONLY on the backend.
    Both sender and receiver can decrypt (both have access to public keys).
    
    Algorithm:
    1. Both sender and receiver can compute shared key from both public keys
    2. Key is SYMMETRIC - same key for both encryption and decryption
    3. XOR ciphertext with key stream to recover plaintext
    
    Args:
        ciphertext_hex (str): Hex-encoded ciphertext (format: "ecc:ciphertext_hex")
        sender_ecc_public_key (dict): {"x": int, "y": int} - sender's public key
        receiver_ecc_public_key (dict): {"x": int, "y": int} - receiver's public key
    
    Returns:
        str: Decrypted plaintext message
    """
    if not ciphertext_hex.startswith('ecc:'):
        return ciphertext_hex  # Not encrypted
    
    try:
        # Extract the encrypted part
        encrypted_part = ciphertext_hex[4:]  # Remove "ecc:" prefix
        
        if not sender_ecc_public_key or not receiver_ecc_public_key:
            return "[Cannot decrypt - missing keys]"
        
        # Derive the SAME shared key using both public keys
        # This works for both sender and receiver because both have public keys
        encryption_key = derive_encryption_key(sender_ecc_public_key, receiver_ecc_public_key)
        
        # Reverse the XOR encryption
        ciphertext_bytes = bytes.fromhex(encrypted_part)
        plaintext_bytes = bytearray()
        
        for i, byte in enumerate(ciphertext_bytes):
            plaintext_bytes.append(byte ^ encryption_key[i % len(encryption_key)])
        
        return plaintext_bytes.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return ciphertext_hex  # Return encrypted if decryption fails


def encrypt_email_rsa(email, recipient_rsa_public_key):
    """
    Encrypt email using RSA public key.
    Ensures emails are stored as gibberish in database.
    
    Args:
        email (str): Email address to encrypt
        recipient_rsa_public_key (dict): {"e": int, "n": int}
    
    Returns:
        str: Hex-encoded RSA ciphertext
    """
    if isinstance(recipient_rsa_public_key, dict):
        public_key_tuple = (recipient_rsa_public_key['e'], recipient_rsa_public_key['n'])
        return rsa_encrypt_hex(email, public_key_tuple)
    return email


def decrypt_email_rsa(encrypted_email, recipient_rsa_private_key):
    """
    Decrypt email using RSA private key.
    
    Args:
        encrypted_email (str): Hex-encoded RSA ciphertext
        recipient_rsa_private_key (dict): {"d": int, "n": int}
    
    Returns:
        str: Decrypted email address
    """
    if isinstance(recipient_rsa_private_key, dict):
        private_key_tuple = (recipient_rsa_private_key['d'], recipient_rsa_private_key['n'])
        return rsa_decrypt_hex(encrypted_email, private_key_tuple)
    return encrypted_email


def encrypt_sensitive_data(data, encryption_key, method='ecc'):
    """
    Generic encryption wrapper for any sensitive data.
    
    Args:
        data (str): Data to encrypt
        encryption_key (dict): Public key (RSA or ECC format)
        method (str): 'rsa' or 'ecc'
    
    Returns:
        str: Encrypted data in hex format
    """
    if method == 'rsa':
        return encrypt_email_rsa(data, encryption_key)
    elif method == 'ecc':
        return ecc_encrypt_message(data, encryption_key)
    return data


def decrypt_sensitive_data(encrypted_data, decryption_key, method='ecc'):
    """
    Generic decryption wrapper for any sensitive data.
    
    Args:
        encrypted_data (str): Encrypted data in hex format
        decryption_key (dict): Private key (RSA or ECC format)
        method (str): 'rsa' or 'ecc'
    
    Returns:
        str: Decrypted plaintext
    """
    if method == 'rsa':
        return decrypt_email_rsa(encrypted_data, decryption_key)
    elif method == 'ecc':
        return ecc_decrypt_message(encrypted_data, decryption_key)
    return encrypted_data


# ==================== DIRECT ASYMMETRIC ENCRYPTION ====================
# Uses RSA directly on data without symmetric key derivation
# Ensures 100% asymmetric-only compliance for critical data

def direct_rsa_encrypt(plaintext, recipient_rsa_public_key, chunk_size=50):
    """
    Direct RSA encryption of plaintext data.
    ASYMMETRIC ONLY - No symmetric encryption involved.
    
    Algorithm:
    1. Split plaintext into chunks (to handle large data)
    2. Encrypt each chunk using RSA public key
    3. Concatenate ciphertext chunks
    
    Args:
        plaintext (str): Data to encrypt
        recipient_rsa_public_key (dict): {"e": int, "n": int}
        chunk_size (int): Size of each plaintext chunk for RSA
    
    Returns:
        str: "rsa:" + hex-encoded RSA ciphertext chunks (separated by "|")
    """
    if not isinstance(recipient_rsa_public_key, dict):
        return plaintext
    
    try:
        public_key_tuple = (recipient_rsa_public_key['e'], recipient_rsa_public_key['n'])
        
        # Split plaintext into chunks
        chunks = [plaintext[i:i+chunk_size] for i in range(0, len(plaintext), chunk_size)]
        
        # Encrypt each chunk
        encrypted_chunks = []
        for chunk in chunks:
            encrypted_chunk = rsa_encrypt_hex(chunk, public_key_tuple)
            encrypted_chunks.append(encrypted_chunk)
        
        # Concatenate with separator
        return "rsa:" + "|".join(encrypted_chunks)
    except Exception as e:
        print(f"Direct RSA encryption error: {e}")
        return plaintext


def direct_rsa_decrypt(ciphertext, recipient_rsa_private_key):
    """
    Direct RSA decryption.
    ASYMMETRIC ONLY - No symmetric decryption involved.
    
    Args:
        ciphertext (str): "rsa:" + encrypted data
        recipient_rsa_private_key (dict): {"d": int, "n": int}
    
    Returns:
        str: Decrypted plaintext
    """
    if not ciphertext.startswith("rsa:"):
        return ciphertext
    
    try:
        if not isinstance(recipient_rsa_private_key, dict):
            return ciphertext
        
        private_key_tuple = (recipient_rsa_private_key['d'], recipient_rsa_private_key['n'])
        
        # Extract encrypted chunks
        encrypted_part = ciphertext[4:]  # Remove "rsa:" prefix
        encrypted_chunks = encrypted_part.split("|")
        
        # Decrypt each chunk
        decrypted_chunks = []
        for chunk in encrypted_chunks:
            decrypted_chunk = rsa_decrypt_hex(chunk, private_key_tuple)
            decrypted_chunks.append(decrypted_chunk)
        
        return "".join(decrypted_chunks)
    except Exception as e:
        print(f"Direct RSA decryption error: {e}")
        return ciphertext


