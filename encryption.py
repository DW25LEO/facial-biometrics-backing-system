import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
import json
import numpy as np

class AESBiometricEncryption:
    """AES-256-GCM encryption for facial biometric templates"""
    
    def __init__(self, master_key=None):
        if master_key:
            self.master_key = base64.b64decode(master_key)
        else:
            self.master_key = self._load_master_key()
    
    def _load_master_key(self):
        key = os.environ.get('AES_MASTER_KEY')
        if not key:
            key = base64.b64encode(get_random_bytes(32)).decode()
            with open('master_key.key', 'w') as f:
                f.write(key)
            os.environ['AES_MASTER_KEY'] = key
        return base64.b64decode(key)
    
    def derive_user_key(self, user_id, salt=None):
        if not salt:
            salt = get_random_bytes(32)
        user_key = PBKDF2(
            self.master_key + user_id.encode(),
            salt,
            dkLen=32,
            count=100000
        )
        return user_key, salt
    
    def encrypt_face_template(self, face_encoding, user_id):
        face_bytes = face_encoding.tobytes()
        user_key, salt = self.derive_user_key(user_id)
        iv = get_random_bytes(12)
        cipher = AES.new(user_key, AES.MODE_GCM, nonce=iv)
        cipher.update(user_id.encode())
        ciphertext, tag = cipher.encrypt_and_digest(face_bytes)
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'iv': base64.b64encode(iv).decode(),
            'tag': base64.b64encode(tag).decode(),
            'salt': base64.b64encode(salt).decode(),
            'algorithm': 'AES-256-GCM'
        }
    
    def decrypt_face_template(self, encrypted_data, user_id):
        try:
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            iv = base64.b64decode(encrypted_data['iv'])
            tag = base64.b64decode(encrypted_data['tag'])
            salt = base64.b64decode(encrypted_data['salt'])
            
            user_key, _ = self.derive_user_key(user_id, salt)
            cipher = AES.new(user_key, AES.MODE_GCM, nonce=iv)
            cipher.update(user_id.encode())
            face_bytes = cipher.decrypt_and_verify(ciphertext, tag)
            return np.frombuffer(face_bytes, dtype=np.float64)
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def get_encrypted_data_string(self, encrypted_data):
        return json.dumps(encrypted_data)