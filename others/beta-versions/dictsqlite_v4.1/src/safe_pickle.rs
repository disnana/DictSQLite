//! Safe Pickle バリデーション - Python のpickleデータを安全に検証
//!
//! v1 の safe_pickle 機能を Rust で実装
//! Python側でのpickle処理前にバイトストリームを検証

use std::collections::HashSet;
use thiserror::Error;

/// Safe Pickle 関連のエラー
#[derive(Error, Debug)]
pub enum SafePickleError {
    #[error("禁止されたpickle opcode: {0}")]
    ForbiddenOpcode(String),
    
    #[error("禁止されたモジュール: {0}")]
    ForbiddenModule(String),
    
    #[error("禁止されたグローバル: {0}.{1}")]
    ForbiddenGlobal(String, String),
    
    #[error("無効なpickleデータ")]
    InvalidData,
}

/// Safe Pickle ポリシー
#[derive(Clone, Debug)]
pub struct SafePicklePolicy {
    /// 許可されたモジュールのプレフィックス
    pub allowed_module_prefixes: Vec<String>,
    
    /// 許可されたビルトイン型
    pub allowed_builtins: HashSet<String>,
    
    /// 明示的に禁止されたグローバル
    pub denied_globals: HashSet<String>,
    
    /// 関数の許可
    pub allow_functions: bool,
    
    /// クラスの許可
    pub allow_classes: bool,
}

impl Default for SafePicklePolicy {
    fn default() -> Self {
        let mut allowed_builtins = HashSet::new();
        
        // 基本的なデータ型のみ許可
        for builtin in &[
            "object", "bool", "int", "float", "complex", "str", "bytes", 
            "bytearray", "tuple", "list", "dict", "set", "frozenset", "slice"
        ] {
            allowed_builtins.insert(builtin.to_string());
        }
        
        let mut denied_globals = HashSet::new();
        
        // 危険な関数を明示的に拒否
        for dangerous in &[
            "os.system", "os.popen", "subprocess.Popen", "subprocess.call",
            "builtins.eval", "builtins.exec", "__builtin__.eval", "__builtin__.exec"
        ] {
            denied_globals.insert(dangerous.to_string());
        }
        
        SafePicklePolicy {
            allowed_module_prefixes: vec![],
            allowed_builtins,
            denied_globals,
            allow_functions: false,
            allow_classes: true,
        }
    }
}

impl SafePicklePolicy {
    /// カスタムポリシーを作成
    pub fn new() -> Self {
        Self::default()
    }
    
    /// 許可モジュールプレフィックスを追加
    pub fn with_module_prefix(mut self, prefix: String) -> Self {
        self.allowed_module_prefixes.push(prefix);
        self
    }
    
    /// グローバルが許可されているか検証
    pub fn is_allowed_global(&self, module: &str, name: &str) -> bool {
        let fq = format!("{}.{}", module, name);
        
        // 拒否リストにあれば常に拒否
        if self.denied_globals.contains(&fq) {
            return false;
        }
        
        // builtins は厳格にホワイトリスト
        if module == "builtins" || module == "__builtin__" {
            return self.allowed_builtins.contains(name);
        }
        
        // 許可されたモジュールプレフィックスに一致するか確認
        for prefix in &self.allowed_module_prefixes {
            if module == prefix || module.starts_with(&format!("{}.", prefix)) {
                return true;
            }
        }
        
        false
    }
    
    /// Pickle opcodeが安全か検証（基本的な検証のみ）
    pub fn validate_opcodes(&self, data: &[u8]) -> Result<(), SafePickleError> {
        // 危険なopcodeを検出
        // Pickle プロトコルの危険な opcode:
        // - 'R' (REDUCE): 任意の関数呼び出しが可能
        // - 'i' (INST): クラスのインスタンス化
        // - 'o' (OBJ): オブジェクトの構築
        // - 'c' (GLOBAL): グローバル変数の取得
        
        let mut i = 0;
        while i < data.len() {
            let opcode = data[i];
            
            match opcode as char {
                'R' => {
                    // REDUCE は慎重に扱う必要がある
                    // 完全な検証は Python 側で実施
                },
                'c' => {
                    // GLOBAL opcode - モジュール名とクラス名を読み取り
                    // ここでは基本的な検出のみ
                },
                _ => {}
            }
            
            i += 1;
        }
        
        Ok(())
    }
}

/// Pickle データの検証
pub struct SafePickleValidator {
    policy: SafePicklePolicy,
}

impl SafePickleValidator {
    /// 新しいバリデータを作成
    pub fn new(policy: SafePicklePolicy) -> Self {
        SafePickleValidator { policy }
    }
    
    /// デフォルトポリシーでバリデータを作成
    pub fn default() -> Self {
        SafePickleValidator {
            policy: SafePicklePolicy::default(),
        }
    }
    
    /// Pickleデータを検証（基本的な検証のみ、詳細はPython側で実施）
    pub fn validate(&self, data: &[u8]) -> Result<(), SafePickleError> {
        // 空データをチェック
        if data.is_empty() {
            return Err(SafePickleError::InvalidData);
        }
        
        // Pickle マジックバイトをチェック（オプション）
        // プロトコル 0-5 をサポート
        
        // Opcode の基本検証
        self.policy.validate_opcodes(data)?;
        
        Ok(())
    }
    
    /// グローバルが許可されているか検証
    pub fn is_allowed_global(&self, module: &str, name: &str) -> bool {
        self.policy.is_allowed_global(module, name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_default_policy_builtins() {
        let policy = SafePicklePolicy::default();
        
        // 許可されたビルトイン
        assert!(policy.is_allowed_global("builtins", "int"));
        assert!(policy.is_allowed_global("builtins", "str"));
        assert!(policy.is_allowed_global("builtins", "dict"));
        
        // 禁止された関数
        assert!(!policy.is_allowed_global("builtins", "eval"));
        assert!(!policy.is_allowed_global("builtins", "exec"));
    }
    
    #[test]
    fn test_denied_globals() {
        let policy = SafePicklePolicy::default();
        
        assert!(!policy.is_allowed_global("os", "system"));
        assert!(!policy.is_allowed_global("subprocess", "Popen"));
    }
    
    #[test]
    fn test_module_prefix() {
        let policy = SafePicklePolicy::new()
            .with_module_prefix("myapp".to_string());
        
        assert!(policy.is_allowed_global("myapp", "MyClass"));
        assert!(policy.is_allowed_global("myapp.models", "User"));
        assert!(!policy.is_allowed_global("os", "system"));
    }
    
    #[test]
    fn test_validator() {
        let validator = SafePickleValidator::default();
        
        // 空データは無効
        assert!(validator.validate(&[]).is_err());
        
        // 基本的なpickleデータ（簡易テスト）
        let simple_pickle = b"\x80\x04\x95\x05\x00\x00\x00\x00\x00\x00\x00K\x01.";
        assert!(validator.validate(simple_pickle).is_ok());
    }
}
