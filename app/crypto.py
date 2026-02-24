from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os

# In production, use a secure key from environment variable
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'default_key_32_chars_long!!!').encode()[:32].ljust(32, b'\0')

def encrypt_file(input_path: str, output_path: str):
    """Encrypt a file using AES-256-CBC"""
    # Generate a random IV
    iv = os.urandom(16)

    # Create cipher
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Read input file
    with open(input_path, 'rb') as f:
        data = f.read()

    # Pad the data
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    # Encrypt
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Write IV + encrypted data
    with open(output_path, 'wb') as f:
        f.write(iv + encrypted_data)

def decrypt_file(input_path: str, output_path: str):
    """Decrypt a file using AES-256-CBC"""
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()

    # Extract IV
    iv = encrypted_data[:16]
    encrypted_data = encrypted_data[16:]

    # Create cipher
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    # Write decrypted data
    with open(output_path, 'wb') as f:
        f.write(data)

def decrypt_to_memory(input_path: str) -> bytes:
    """Decrypt a file and return the bytes in memory"""
    with open(input_path, 'rb') as f:
        encrypted_data = f.read()

    # Extract IV
    iv = encrypted_data[:16]
    encrypted_data = encrypted_data[16:]

    # Create cipher
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data