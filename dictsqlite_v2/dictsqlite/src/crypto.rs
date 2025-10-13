//! 暗号化モジュール - AES-256-GCM による高性能暗号化
//!
//! v1 の暗号化機能を Rust で最適化・高速化した実装
//! - AES-256-GCM (認証付き暗号化)
//! - PBKDF2-HMAC-SHA256 によるパスワードベースの鍵導出
//! - 高速化のため、鍵をキャッシュ

use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use pbkdf2::pbkdf2_hmac;
use rand::RngCore;
use sha2::Sha256;
use std::sync::Arc;
use thiserror::Error;

/// 暗号化関連のエラー
#[derive(Error, Debug)]
pub enum CryptoError {
    #[error("暗号化に失敗しました: {0}")]
    EncryptionFailed(String),

    #[error("復号化に失敗しました: {0}")]
    DecryptionFailed(String),

    #[error("無効なパスワード")]
    InvalidPassword,

    #[error("無効なデータ形式")]
    InvalidFormat,
}

/// 暗号化エンジン
pub struct CryptoEngine {
    /// 導出済みの鍵（キャッシュ）
    cipher: Arc<Aes256Gcm>,
}

impl CryptoEngine {
    /// 新しい暗号化エンジンを作成
    ///
    /// # Arguments
    /// * `password` - パスワード
    /// * `salt` - ソルト（オプション、Noneの場合は固定ソルトを使用）
    pub fn new(password: &str, salt: Option<&[u8]>) -> Result<Self, CryptoError> {
        let salt = salt.unwrap_or(b"DictSQLite_v4_default_salt_16b");

        // PBKDF2 で鍵を導出（100,000回の反復）
        let mut key = [0u8; 32];
        pbkdf2_hmac::<Sha256>(password.as_bytes(), salt, 100_000, &mut key);

        let cipher = Aes256Gcm::new(&key.into());

        Ok(CryptoEngine {
            cipher: Arc::new(cipher),
        })
    }

    /// データを暗号化
    ///
    /// # Arguments
    /// * `plaintext` - 平文データ
    ///
    /// # Returns
    /// `Vec<u8>` - マーカー(4) + nonce(12) + 暗号文 + タグ(16)
    #[allow(deprecated)]
    pub fn encrypt(&self, plaintext: &[u8]) -> Result<Vec<u8>, CryptoError> {
        // ランダムなnonceを生成（12バイト）
        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        // 暗号化
        let ciphertext = self
            .cipher
            .encrypt(nonce, plaintext)
            .map_err(|e| CryptoError::EncryptionFailed(e.to_string()))?;

        // マーカー(4バイト) + nonce + 暗号文を結合
        // マーカー: "ENC\0" - 暗号化データであることを示す
        let mut result = Vec::with_capacity(4 + nonce_bytes.len() + ciphertext.len());
        result.extend_from_slice(b"ENC\0");
        result.extend_from_slice(&nonce_bytes);
        result.extend_from_slice(&ciphertext);

        Ok(result)
    }

    /// データを復号化
    ///
    /// # Arguments
    /// * `encrypted` - 暗号化データ (マーカー + nonce + 暗号文 + タグ)
    ///
    /// # Returns
    /// `Vec<u8>` - 平文データ
    #[allow(deprecated)]
    pub fn decrypt(&self, encrypted: &[u8]) -> Result<Vec<u8>, CryptoError> {
        // 最小サイズチェック: マーカー(4) + nonce(12) + 最小暗号文(16 for GCM tag)
        if encrypted.len() < 32 {
            return Err(CryptoError::InvalidFormat);
        }

        // マーカーをチェック
        if &encrypted[0..4] != b"ENC\0" {
            return Err(CryptoError::InvalidFormat);
        }

        // マーカーをスキップして nonce と暗号文を分離
        let data = &encrypted[4..];
        let (nonce_bytes, ciphertext) = data.split_at(12);
        let nonce = Nonce::from_slice(nonce_bytes);

        // 復号化
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext)
            .map_err(|e| CryptoError::DecryptionFailed(e.to_string()))?;

        Ok(plaintext)
    }

    /// 暗号化されたデータかどうかをチェック
    pub fn is_encrypted(data: &[u8]) -> bool {
        data.len() >= 4 && &data[0..4] == b"ENC\0"
    }
}

/// 高速化のためのユーティリティ関数

#[cfg(test)]
mod tests {
    use super::*;
    use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};

    /// Base64エンコード（URL-safe）
    pub fn encode_base64(data: &[u8]) -> String {
        URL_SAFE_NO_PAD.encode(data)
    }

    /// Base64デコード（URL-safe）
    pub fn decode_base64(encoded: &str) -> Result<Vec<u8>, CryptoError> {
        URL_SAFE_NO_PAD
            .decode(encoded)
            .map_err(|_| CryptoError::InvalidFormat)
    }

    #[test]
    fn test_encrypt_decrypt() {
        let engine = CryptoEngine::new("test_password", None).unwrap();
        let plaintext = b"Hello, World!";

        let encrypted = engine.encrypt(plaintext).unwrap();
        let decrypted = engine.decrypt(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted.as_slice());
    }

    #[test]
    fn test_different_passwords() {
        let engine1 = CryptoEngine::new("password1", None).unwrap();
        let engine2 = CryptoEngine::new("password2", None).unwrap();

        let plaintext = b"Secret data";
        let encrypted = engine1.encrypt(plaintext).unwrap();

        // 異なるパスワードでは復号化に失敗するはず
        assert!(engine2.decrypt(&encrypted).is_err());
    }

    #[test]
    fn test_base64_encoding() {
        let data = b"test data";
        let encoded = encode_base64(data);
        let decoded = decode_base64(&encoded).unwrap();

        assert_eq!(data, decoded.as_slice());
    }
}
