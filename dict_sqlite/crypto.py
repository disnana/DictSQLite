# パスワードを基にしたキーの生成
def derive_key(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from base64 import urlsafe_b64encode, urlsafe_b64decode
    import os
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256に対応する32バイトのキー
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


# データの暗号化
def encrypt_aes(data: str, password: str) -> str:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from base64 import urlsafe_b64encode, urlsafe_b64decode
    import os
    salt = os.urandom(16)  # ソルトの生成
    key = derive_key(password, salt)

    # 初期化ベクトル（IV）の生成
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # データにパディングを追加
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()

    # データの暗号化
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # ソルト、IV、および暗号化されたデータを結合して返す
    return urlsafe_b64encode(salt + iv + ciphertext)


# データの復号化
def decrypt_aes(encrypted_data: str, password: str) -> str:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from base64 import urlsafe_b64encode, urlsafe_b64decode
    import os
    encrypted_data = urlsafe_b64decode(encrypted_data)

    # ソルト、IV、および暗号化されたデータを分割
    salt, iv, ciphertext = encrypted_data[:16], encrypted_data[16:32], encrypted_data[32:]
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # データの復号化
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    # パディングの削除
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data


from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def load_private_key(pem_file_path: str, password: str = None) -> rsa.RSAPrivateKey:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from base64 import urlsafe_b64encode, urlsafe_b64decode
    import os
    with open(pem_file_path, 'rb') as pem_file:
        private_key_pem = pem_file.read()

    private_key = serialization.load_pem_private_key(
        decrypt_aes(private_key_pem, password),
        backend=default_backend(),
        password=None
    )
    return private_key


from cryptography.hazmat.primitives.asymmetric import rsa


def load_public_key(pem_file_path: str, password) -> rsa.RSAPublicKey:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from base64 import urlsafe_b64encode, urlsafe_b64decode
    import os
    with open(pem_file_path, 'rb') as pem_file:
        public_key_pem = pem_file.read()

    public_key = serialization.load_pem_public_key(
        decrypt_aes(public_key_pem, password),
        backend=default_backend()
    )
    return public_key


def key_create():
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
        encryption_algorithm=serialization.NoEncryption()  # パスワードで暗号化したい場合は適切なオプションを設定
    )

    # 公開鍵のPEMフォーマットへのシリアライズ
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # 秘密鍵と公開鍵をファイルに保存（オプション）
    with open('private_key.pem', 'wb') as f:
        f.write(encrypt_aes(private_pem, "test"))

    with open('public_key.pem', 'wb') as f:
        f.write(encrypt_aes(public_pem, "test"))


# データの暗号化
message = b"Very sensitive data"


def encrypt_rsa(key, message):
    ciphertext = key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext


def decrypt_rsa(key, message):
    # データの復号化
    plaintext = key.decrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext


# 結果の表示
key_create()
test = encrypt_rsa(load_public_key("./public_key.pem", "test"), message)
print(f"暗号化されたデータ: {test}")
print(f"復号化されたデータ: {decrypt_rsa(load_private_key('./private_key.pem', 'test'), test)}")
