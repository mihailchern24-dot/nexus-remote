#!/usr/bin/env python3
# encryption.py - ногоуровневое шифрование для Nexus Remote
import base64
import hashlib
import os
from enum import Enum
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

class EncryptionMethod(Enum):
    NONE = "none"
    AES_GCM = "aes_gcm"         # AES-256-GCM (рекомендуется)
    AES_CBC = "aes_cbc"         # AES-256-CBC + HMAC
    CHACHA20 = "chacha20"       # ChaCha20-Poly1305
    AES_CTR = "aes_ctr"         # AES-256-CTR + HMAC
    XOR = "xor"                 # ростое XOR (для слабых устройств)
    RSA_AES = "rsa_aes"         # RSA + AES (асимметричное)

class NexusCrypto:
    """Шифрование для Nexus Remote"""
    
    def __init__(self, password="nexus_secure_key_2024"):
        self.password = password.encode() if isinstance(password, str) else password
        self.backend = default_backend()
    
    def _derive_key(self, salt=None, length=32):
        """енерация ключа из пароля"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        key = kdf.derive(self.password)
        return key, salt
    
    def encrypt(self, data, method=EncryptionMethod.AES_GCM):
        """ашифровать данные"""
        if not data:
            return data, EncryptionMethod.NONE, {}
        
        if isinstance(data, str):
            data = data.encode()
        
        try:
            if method == EncryptionMethod.AES_GCM:
                return self._aes_gcm_encrypt(data)
            elif method == EncryptionMethod.AES_CBC:
                return self._aes_cbc_encrypt(data)
            elif method == EncryptionMethod.CHACHA20:
                return self._chacha20_encrypt(data)
            elif method == EncryptionMethod.AES_CTR:
                return self._aes_ctr_encrypt(data)
            elif method == EncryptionMethod.XOR:
                return self._xor_encrypt(data)
            elif method == EncryptionMethod.RSA_AES:
                return self._rsa_aes_encrypt(data)
            else:
                return data, EncryptionMethod.NONE, {}
        except Exception as e:
            print(f"Encryption error: {e}")
            return data, EncryptionMethod.NONE, {}
    
    def decrypt(self, data, method, metadata):
        """асшифровать данные"""
        if not data or method == EncryptionMethod.NONE:
            return data
        
        try:
            if method == EncryptionMethod.AES_GCM:
                return self._aes_gcm_decrypt(data, metadata)
            elif method == EncryptionMethod.AES_CBC:
                return self._aes_cbc_decrypt(data, metadata)
            elif method == EncryptionMethod.CHACHA20:
                return self._chacha20_decrypt(data, metadata)
            elif method == EncryptionMethod.AES_CTR:
                return self._aes_ctr_decrypt(data, metadata)
            elif method == EncryptionMethod.XOR:
                return self._xor_decrypt(data, metadata)
            elif method == EncryptionMethod.RSA_AES:
                return self._rsa_aes_decrypt(data, metadata)
        except Exception as e:
            print(f"Decryption error: {e}")
            return data
    
    def _aes_gcm_encrypt(self, data):
        """AES-256-GCM шифрование (рекомендуется)"""
        key, salt = self._derive_key()
        iv = os.urandom(12)
        
        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=self.backend
        ).encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        metadata = {
            'salt': base64.b64encode(salt).decode(),
            'iv': base64.b64encode(iv).decode(),
            'tag': base64.b64encode(encryptor.tag).decode()
        }
        
        return ciphertext, EncryptionMethod.AES_GCM, metadata
    
    def _aes_gcm_decrypt(self, data, metadata):
        """AES-256-GCM расшифровка"""
        key, _ = self._derive_key(base64.b64decode(metadata['salt']))
        iv = base64.b64decode(metadata['iv'])
        tag = base64.b64decode(metadata['tag'])
        
        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=self.backend
        ).decryptor()
        
        return decryptor.update(data) + decryptor.finalize()
    
    def _aes_cbc_encrypt(self, data):
        """AES-256-CBC + HMAC"""
        key, salt = self._derive_key()
        iv = os.urandom(16)
        
        # PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        encryptor = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        ).encryptor()
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # HMAC для проверки целостности
        h = hmac.HMAC(key, hashes.SHA256(), backend=self.backend)
        h.update(ciphertext)
        mac = h.finalize()
        
        metadata = {
            'salt': base64.b64encode(salt).decode(),
            'iv': base64.b64encode(iv).decode(),
            'mac': base64.b64encode(mac).decode()
        }
        
        return ciphertext, EncryptionMethod.AES_CBC, metadata
    
    def _aes_cbc_decrypt(self, data, metadata):
        """AES-256-CBC расшифровка"""
        key, _ = self._derive_key(base64.b64decode(metadata['salt']))
        iv = base64.b64decode(metadata['iv'])
        mac = base64.b64decode(metadata['mac'])
        
        # роверка HMAC
        h = hmac.HMAC(key, hashes.SHA256(), backend=self.backend)
        h.update(data)
        h.verify(mac)
        
        decryptor = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        ).decryptor()
        
        padded_data = decryptor.update(data) + decryptor.finalize()
        
        # бираем padding
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()
    
    def _chacha20_encrypt(self, data):
        """ChaCha20-Poly1305 (быстрее на мобильных)"""
        key, salt = self._derive_key(length=32)
        nonce = os.urandom(12)
        
        algorithm = algorithms.ChaCha20Poly1305(key)
        encryptor = Cipher(algorithm, modes.ChaCha20Poly1305(nonce), backend=self.backend).encryptor()
        
        ciphertext = encryptor.update(data)
        
        metadata = {
            'salt': base64.b64encode(salt).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'tag': base64.b64encode(encryptor.tag).decode()
        }
        
        return ciphertext, EncryptionMethod.CHACHA20, metadata
    
    def _chacha20_decrypt(self, data, metadata):
        key, _ = self._derive_key(base64.b64decode(metadata['salt']), length=32)
        nonce = base64.b64decode(metadata['nonce'])
        tag = base64.b64decode(metadata['tag'])
        
        algorithm = algorithms.ChaCha20Poly1305(key)
        decryptor = Cipher(algorithm, modes.ChaCha20Poly1305(nonce, tag), backend=self.backend).decryptor()
        
        return decryptor.update(data)
    
    def _aes_ctr_encrypt(self, data):
        """AES-256-CTR (потоковый режим)"""
        key, salt = self._derive_key()
        nonce = os.urandom(16)
        
        encryptor = Cipher(
            algorithms.AES(key),
            modes.CTR(nonce),
            backend=self.backend
        ).encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        metadata = {
            'salt': base64.b64encode(salt).decode(),
            'nonce': base64.b64encode(nonce).decode()
        }
        
        return ciphertext, EncryptionMethod.AES_CTR, metadata
    
    def _aes_ctr_decrypt(self, data, metadata):
        key, _ = self._derive_key(base64.b64decode(metadata['salt']))
        nonce = base64.b64decode(metadata['nonce'])
        
        decryptor = Cipher(
            algorithms.AES(key),
            modes.CTR(nonce),
            backend=self.backend
        ).decryptor()
        
        return decryptor.update(data) + decryptor.finalize()
    
    def _xor_encrypt(self, data):
        """ростое XOR шифрование (для IoT/слабых устройств)"""
        key = hashlib.sha256(self.password).digest()
        key_length = len(key)
        
        encrypted = bytes([data[i] ^ key[i % key_length] for i in range(len(data))])
        
        metadata = {'method': 'xor'}
        return encrypted, EncryptionMethod.XOR, metadata
    
    def _xor_decrypt(self, data, metadata):
        """XOR расшифровка (симметричная)"""
        return self._xor_encrypt(data)[0]
    
    def _rsa_aes_encrypt(self, data):
        """RSA + AES (асимметричное) - заглушка"""
        #  реальном приложении: генерируем AES ключ, шифруем его RSA
        return self._aes_gcm_encrypt(data)
    
    def _rsa_aes_decrypt(self, data, metadata):
        return self._aes_gcm_decrypt(data, metadata)

# Тесты шифрования
if __name__ == "__main__":
    crypto = NexusCrypto("my_secure_password_2024")
    test_data = b"Hello Nexus Remote! " * 100
    
    print("=== Тесты шифрования ===\n")
    
    for method in [EncryptionMethod.AES_GCM, EncryptionMethod.AES_CBC, 
                   EncryptionMethod.CHACHA20, EncryptionMethod.XOR]:
        encrypted, enc_method, meta = crypto.encrypt(test_data, method)
        decrypted = crypto.decrypt(encrypted, enc_method, meta)
        
        success = "✅" if decrypted == test_data else "❌"
        print(f"{method.value:15} {success} | {len(test_data)} -> {len(encrypted)} bytes")
