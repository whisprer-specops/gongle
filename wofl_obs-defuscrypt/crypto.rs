use anyhow::{Context, Result};
use chacha20poly1305::{
    aead::{Aead, KeyInit},
    ChaCha20Poly1305, Nonce,
};
use dialoguer::{theme::ColorfulTheme, Password};
use pbkdf2::{
    password_hash::{PasswordHasher, SaltString},
    Pbkdf2,
};
use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use std::{
    fs,
    io::{Read, Write},
    path::Path,
};
use thiserror::Error;
use zeroize::Zeroize;

// Number of PBKDF2 iterations for key derivation
const PBKDF2_ITERATIONS: u32 = 600_000;
// Length of the salt in bytes
const SALT_LENGTH: usize = 32;
// Length of the nonce in bytes
const NONCE_LENGTH: usize = 12;
// Header version for encryption format
const HEADER_VERSION: u8 = 1;

/// Encryption-specific errors
#[derive(Error, Debug)]
pub enum CryptoError {
    #[error("Failed to derive encryption key")]
    KeyDerivationError,
    
    #[error("Failed to encrypt data")]
    EncryptionError,
    
    #[error("Failed to decrypt data: {0}")]
    DecryptionError(String),
    
    #[error("Invalid file format")]
    InvalidFileFormat,
    
    #[error("Unsupported version: {0}")]
    UnsupportedVersion(u8),
    
    #[error("Password mismatch")]
    PasswordMismatch,
}

/// Metadata stored in encrypted files
#[derive(Debug, Serialize, Deserialize)]
struct FileHeader {
    version: u8,
    salt: Vec<u8>,
    nonce: Vec<u8>,
}

/// Gets a password interactively from the user
pub fn get_password(confirm: bool) -> Result<String> {
    let password = if confirm {
        Password::with_theme(&ColorfulTheme::default())
            .with_prompt("Enter encryption password")
            .with_confirmation("Confirm password", "Passwords don't match")
            .interact()?
    } else {
        Password::with_theme(&ColorfulTheme::default())
            .with_prompt("Enter decryption password")
            .interact()?
    };

    Ok(password)
}

/// Derives an encryption key from a password and salt
fn derive_key(password: &str, salt: &[u8]) -> Result<[u8; 32]> {
    let mut key = [0u8; 32];
    
    // Create salt
    let salt = SaltString::encode_b64(salt)
        .map_err(|_| CryptoError::KeyDerivationError)?;
    
    // Derive key using PBKDF2-HMAC-SHA256
    let hash = Pbkdf2
        .hash_password_customized(
            password.as_bytes(),
            None,
            None,
            pbkdf2::Params {
                rounds: PBKDF2_ITERATIONS,
                output_length: 32,
            },
            &salt,
        )
        .map_err(|_| CryptoError::KeyDerivationError)?;
    
    // Extract the hash value - FIX: Create a binding for the unwrapped hash
    let hash_unwrapped = hash.hash.unwrap();
    let hash_value = hash_unwrapped.as_bytes();
    key.copy_from_slice(&hash_value[0..32]);
    
    Ok(key)
}

/// Encrypts file content with ChaCha20-Poly1305
pub fn encrypt_file<P: AsRef<Path>>(
    input_path: P,
    output_path: P,
    password: Option<String>,
) -> Result<()> {
    // Read file content
    let mut file_content = fs::read(&input_path)
        .with_context(|| format!("Failed to read file: {}", input_path.as_ref().display()))?;
    
    // Get password either from parameter or by prompting
    let password = match password {
        Some(pwd) => pwd,
        None => get_password(true)?,
    };
    
    // Generate a random salt
    let mut salt = vec![0u8; SALT_LENGTH];
    OsRng.fill_bytes(&mut salt);
    
    // Derive encryption key
    let key = derive_key(&password, &salt)
        .context("Failed to derive encryption key")?;
    
    // Create cipher
    let cipher = ChaCha20Poly1305::new(&key.into());
    
    // Generate a random nonce
    let mut nonce_bytes = [0u8; NONCE_LENGTH];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);
    
    // Encrypt the data
    let encrypted_data = cipher
        .encrypt(nonce, file_content.as_ref())
        .map_err(|_| CryptoError::EncryptionError)?;
    
    // Create header with metadata
    let header = FileHeader {
        version: HEADER_VERSION,
        salt,
        nonce: nonce_bytes.to_vec(),
    };
    
    // Serialize header
    let header_json = serde_json::to_vec(&header)
        .context("Failed to serialize encryption header")?;
    
    // Write header length (4 bytes) + header + encrypted data
    let mut output_file = fs::File::create(&output_path)
        .with_context(|| format!("Failed to create output file: {}", output_path.as_ref().display()))?;
    
    // Write header length as 4 bytes in little-endian
    let header_len = header_json.len() as u32;
    output_file.write_all(&header_len.to_le_bytes())
        .context("Failed to write header length")?;
    
    // Write header
    output_file.write_all(&header_json)
        .context("Failed to write header")?;
    
    // Write encrypted data
    output_file.write_all(&encrypted_data)
        .context("Failed to write encrypted data")?;
    
    // Zeroize sensitive data
    let mut password = password;
    password.zeroize();
    file_content.zeroize();
    
    Ok(())
}

/// Decrypts file content with ChaCha20-Poly1305
pub fn decrypt_file<P: AsRef<Path>>(
    input_path: P,
    output_path: P,
    password: Option<String>,
) -> Result<()> {
    // Open encrypted file
    let mut file = fs::File::open(&input_path)
        .with_context(|| format!("Failed to open encrypted file: {}", input_path.as_ref().display()))?;
    
    // Read header length (first 4 bytes)
    let mut header_len_bytes = [0u8; 4];
    file.read_exact(&mut header_len_bytes)
        .context("Failed to read header length")?;
    let header_len = u32::from_le_bytes(header_len_bytes) as usize;
    
    // Read header
    let mut header_bytes = vec![0u8; header_len];
    file.read_exact(&mut header_bytes)
        .context("Failed to read header")?;
    
    // Deserialize header
    let header: FileHeader = serde_json::from_slice(&header_bytes)
        .map_err(|_| CryptoError::InvalidFileFormat)?;
    
    // Check version
    if header.version != HEADER_VERSION {
        return Err(CryptoError::UnsupportedVersion(header.version).into());
    }
    
    // Get password
    let password = match password {
        Some(pwd) => pwd,
        None => get_password(false)?,
    };
    
    // Derive decryption key
    let key = derive_key(&password, &header.salt)
        .context("Failed to derive decryption key")?;
    
    // Create cipher
    let cipher = ChaCha20Poly1305::new(&key.into());
    
    // Read encrypted data
    let mut encrypted_data = Vec::new();
    file.read_to_end(&mut encrypted_data)
        .context("Failed to read encrypted data")?;
    
    // Create nonce from header
    let nonce = Nonce::from_slice(&header.nonce);
    
    // Decrypt the data
    let decrypted_data = cipher
        .decrypt(nonce, encrypted_data.as_ref())
        .map_err(|e| CryptoError::DecryptionError(e.to_string()))?;
    
    // Write decrypted data to output file
    fs::write(&output_path, &decrypted_data)
        .with_context(|| format!("Failed to write decrypted file: {}", output_path.as_ref().display()))?;
    
    // Zeroize sensitive data
    let mut password = password;
    password.zeroize();
    
    Ok(())
}

/// Check if file is in our encrypted format
pub fn is_encrypted_file<P: AsRef<Path>>(path: P) -> bool {
    if !path.as_ref().is_file() {
        return false;
    }
    
    // Check file extension
    if let Some(ext) = path.as_ref().extension() {
        if ext != "enc" {
            return false;
        }
    } else {
        return false;
    }
    
    // Try to read header length
    if let Ok(mut file) = fs::File::open(path) {
        let mut header_len_bytes = [0u8; 4];
        if file.read_exact(&mut header_len_bytes).is_err() {
            return false;
        }
        
        let header_len = u32::from_le_bytes(header_len_bytes) as usize;
        
        // Sanity check - header should be reasonable size
        if header_len < 10 || header_len > 1024 {
            return false;
        }
        
        // Try to read and parse header
        let mut header_bytes = vec![0u8; header_len];
        if file.read_exact(&mut header_bytes).is_err() {
            return false;
        }
        
        if let Ok(header) = serde_json::from_slice::<FileHeader>(&header_bytes) {
            return header.version == HEADER_VERSION;
        }
    }
    
    false
}