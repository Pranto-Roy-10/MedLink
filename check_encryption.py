"""Check if private keys are encrypted in database"""
import sqlite3

conn = sqlite3.connect('medlink.db')
cursor = conn.cursor()

print('=' * 60)
print('DATABASE CHECK: PRIVATE KEY ENCRYPTION')
print('=' * 60)

# Get all users
cursor.execute('SELECT username, rsa_private_key, ecc_private_key FROM user')
rows = cursor.fetchall()

for username, rsa_key, ecc_key in rows:
    print(f'\n👤 User: {username}')
    
    # Check RSA key
    if rsa_key:
        is_rsa_encrypted = rsa_key.startswith('rsa:')
        rsa_preview = rsa_key[:60]
        print(f'  RSA Private Key:')
        print(f'    Format: {"🔒 ENCRYPTED (rsa:)" if is_rsa_encrypted else "❌ PLAINTEXT"}')
        print(f'    First 60 chars: {rsa_preview}...')
    
    # Check ECC key
    if ecc_key:
        is_ecc_encrypted = ecc_key.startswith('rsa:')
        ecc_preview = ecc_key[:60]
        print(f'  ECC Private Key:')
        print(f'    Format: {"🔒 ENCRYPTED (rsa:)" if is_ecc_encrypted else "❌ PLAINTEXT"}')
        print(f'    First 60 chars: {ecc_preview}...')

print('\n' + '=' * 60)
conn.close()
