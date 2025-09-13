"""暗号ユーティリティ: AES(対称)とRSA(非対称)の簡易ヘルパー群。"""

from __future__ import annotations

import os
from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding as sym_padding, serialization
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
    padding as asym_padding,
)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# パスワードを基にしたキーの生成
def derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC(SHA-256) でパスワードから32バイトの鍵を導出する。

    Args:
        password: パスワード（UTF-8エンコードして使用）。
        salt: 16バイト程度のソルト。
    Returns:
        派生済みの鍵（32バイト）。
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256に対応する32バイトのキー
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


# データの暗号化
def encrypt_aes(data: bytes, password: str) -> bytes:
    """AES-CBC + PKCS7 でデータを暗号化し、salt|iv|ciphertext をURL-safeなBase64で返す。

    Args:
        data: 平文データ（バイト列）。
        password: パスワード。
    Returns:
        URL-safe Base64でエンコードされたバイト列。
    """
    salt = os.urandom(16)  # ソルトの生成
    key = derive_key(password, salt)

    # 初期化ベクトル（IV）の生成
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # データにパディングを追加
    padder = sym_padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()

    # データの暗号化
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # ソルト、IV、および暗号化されたデータを結合して返す
    return urlsafe_b64encode(salt + iv + ciphertext)


# データの復号化
def decrypt_aes(encrypted_data: bytes | str, password: str) -> bytes:
    """encrypt_aes の逆操作を行い、元の平文データ（バイト列）を返す。

    Args:
        encrypted_data: URL-safe Base64の文字列またはバイト列。
        password: パスワード。
    Returns:
        復号した元のバイト列。
    """
    encrypted_bytes = urlsafe_b64decode(encrypted_data)

    # ソルト、IV、および暗号化されたデータを分割
    salt, iv, ciphertext = (
        encrypted_bytes[:16],
        encrypted_bytes[16:32],
        encrypted_bytes[32:],
    )
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # データの復号化
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    # パディングの削除
    unpadder = sym_padding.PKCS7(algorithms.AES.block_size).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data


# 鍵読み書きユーティリティ

def load_private_key(pem_file_path: str, password: str | None = None) -> rsa.RSAPrivateKey:
    """暗号化保存されたPEM秘密鍵を復号して読み込む。"""
    with open(pem_file_path, "rb") as pem_file:
        private_key_pem = pem_file.read()

    private_key = serialization.load_pem_private_key(
        decrypt_aes(private_key_pem, password or ""),
        backend=default_backend(),
        password=None,
    )
    return private_key


def load_public_key(pem_file_path: str, password: str) -> rsa.RSAPublicKey:
    """暗号化保存されたPEM公開鍵を復号して読み込む。"""
    with open(pem_file_path, "rb") as pem_file:
        public_key_pem = pem_file.read()

    public_key = serialization.load_pem_public_key(
        decrypt_aes(public_key_pem, password),
        backend=default_backend(),
    )
    return public_key


def key_create(
    password: str = "test",
    pubkey_path: str = "./pubkey.pem",
    private_key_path: str = "./key.pem",
) -> None:
    """RSA鍵ペアを生成し、AESで暗号化してPEMファイルとして保存する。"""
    # 4096ビットのRSA鍵ペアの生成
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # 公開鍵の取得
    public_key = private_key.public_key()

    # 秘密鍵のPEMフォーマットへのシリアライズ
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # 公開鍵のPEMフォーマットへのシリアライズ
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # 秘密鍵と公開鍵をファイルに保存
    with open(private_key_path, "wb") as f:
        f.write(encrypt_aes(private_pem, password))

    with open(pubkey_path, "wb") as f:
        f.write(encrypt_aes(public_pem, password))


# RSAユーティリティ

def encrypt_rsa(key: rsa.RSAPublicKey, message: bytes) -> bytes:
    """RSA-OAEP(SHA-256)でメッセージを暗号化する。"""
    ciphertext = key.encrypt(
        message,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext


def decrypt_rsa(key: rsa.RSAPrivateKey, message: bytes) -> bytes:
    """RSA-OAEP(SHA-256)で暗号文を復号する。"""
    # データの復号化
    plaintext = key.decrypt(
        message,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext


# 結果の表示用のサンプルコードは不要なためコメントアウトのまま保持
# key_create()
# test_ct = encrypt_rsa(load_public_key("./public_key.pem", "test"), b"Very sensitive data")
# print(f"暗号化されたデータ: {test_ct}")
# print(f"復号化されたデータ: {decrypt_rsa(load_private_key('./private_key.pem', 'test'), test_ct)}")
