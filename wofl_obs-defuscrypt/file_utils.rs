use anyhow::Result;
use console::style;
use std::{
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
};
use walkdir::WalkDir;

use crate::{
    config::Config,
    crypto::{decrypt_file, encrypt_file, get_password, is_encrypted_file},
    secure_delete::{
        clean_empty_directories, confirm_secure_deletion, get_overwrite_confirmation,
        secure_delete_file, OverwriteAction,
    },
    ui::ensure_directory,
};

/// Process a single file (encrypt or decrypt)
pub fn process_file(
    file_path: &Path,
    output_path: &Path,
    config: &Config,
    is_encrypt: bool,
    password: Option<String>,
    overwrite_all: &AtomicBool,
) -> Result<bool> {
    // Skip files that are already in the target format
    if is_encrypt && file_path.extension().map_or(false, |ext| ext == "enc") {
        println!(
            "{} Skipped (already encrypted): {}",
            style("[INFO]").yellow().bold(),
            file_path.display()
        );
        return Ok(false);
    } else if !is_encrypt && !is_encrypted_file(file_path) {
        println!(
            "{} Skipped (not an encrypted file): {}",
            style("[INFO]").yellow().bold(),
            file_path.display()
        );
        return Ok(false);
    }

    // Check if output file exists and handle overwrite
    if output_path.exists() && !config.force {
        if overwrite_all.load(Ordering::Relaxed) {
            // Skip confirmation if overwrite_all is set
        } else {
            let action = get_overwrite_confirmation(output_path)?;
            match action {
                OverwriteAction::Yes => {
                    // Continue with overwrite for this file
                }
                OverwriteAction::No => {
                    println!(
                        "{} Skipped (output file exists): {}",
                        style("[INFO]").yellow().bold(),
                        file_path.display()
                    );
                    return Ok(false);
                }
                OverwriteAction::All => {
                    // Set the atomic flag to overwrite all future files
                    overwrite_all.store(true, Ordering::Relaxed);
                }
            }
        }
    }

    // Ensure output directory exists
    if let Some(parent) = output_path.parent() {
        ensure_directory(parent)?;
    }

    // Process the file
    if is_encrypt {
        println!(
            "{} Encrypting: {}",
            style("[PROCESS]").blue().bold(),
            file_path.display()
        );
        encrypt_file(file_path, output_path, password.clone())?;
    } else {
        println!(
            "{} Decrypting: {}",
            style("[PROCESS]").blue().bold(),
            file_path.display()
        );
        decrypt_file(file_path, output_path, password.clone())?;
    }

    // Handle secure deletion if requested
    if config.secure_delete {
        secure_delete_file(file_path, config.shred_passes)?;
    }

    Ok(true)
}

/// Process a directory (encrypt or decrypt all files)
pub fn process_directory(
    dir_path: &Path,
    output_dir: &Path,
    config: &Config,
    is_encrypt: bool,
    password: Option<String>,
) -> Result<(usize, usize)> {
    let mut success_count = 0;
    let mut failure_count = 0;
    let overwrite_all = AtomicBool::new(false);

    // Ensure output directory exists
    ensure_directory(output_dir)?;

    // Walk through directory
    let walker = if config.recursive {
        WalkDir::new(dir_path).into_iter()
    } else {
        WalkDir::new(dir_path).max_depth(1).into_iter()
    };

    // Track files to process
    let files: Vec<PathBuf> = walker
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file())
        .map(|e| e.path().to_path_buf())
        .collect();

    let total_files = files.len();
    println!(
        "{} Processing {} files in {}",
        style("[INFO]").blue().bold(),
        total_files,
        dir_path.display()
    );

    // Process each file
    for file_path in files {
        // Determine output path
        let relative_path = file_path
            .strip_prefix(dir_path)
            .unwrap_or_else(|_| file_path.as_path());
        let mut output_path = output_dir.join(relative_path);

        // Adjust extension for encryption/decryption
        if is_encrypt {
            output_path.set_extension("enc");
        } else if output_path.extension().map_or(false, |ext| ext == "enc") {
            output_path.set_extension("");
        }

        // Process the file
        match process_file(
            &file_path,
            &output_path,
            config,
            is_encrypt,
            password.clone(),
            &overwrite_all,
        ) {
            Ok(true) => success_count += 1,
            Ok(false) => {} // File was skipped
            Err(e) => {
                eprintln!(
                    "{} Failed to process file {}: {}",
                    style("[ERROR]").red().bold(),
                    file_path.display(),
                    e
                );
                failure_count += 1;
            }
        }
    }

    // Clean up empty directories if requested
    if config.clean_empty_folders && config.secure_delete {
        println!("{}", style("\nCleaning up empty directories...").blue().bold());
        let deleted_folders = clean_empty_directories(dir_path, config.recursive)?;
        println!(
            "{} Removed {} empty directories",
            style("[INFO]").green().bold(),
            deleted_folders
        );
    }

    Ok((success_count, failure_count))
}

/// Process a path (file or directory)
pub fn process_path(path: &Path, config: &Config, is_encrypt: bool) -> Result<()> {
    // Check if path exists
    if !path.exists() {
        anyhow::bail!("Path does not exist: {}", path.display());
    }

    // Confirm secure deletion if requested
    let perform_secure_delete = if config.secure_delete {
        confirm_secure_deletion(path, path.is_dir(), config.clean_empty_folders)?
    } else {
        false
    };

    // Update config with secure deletion decision
    let mut modified_config = config.clone();
    modified_config.secure_delete = perform_secure_delete;

    // Get password once (will be reused for all files)
    let password = Some(get_password(is_encrypt)?);

    // Process based on path type
    if path.is_dir() {
        // Process directory
        let output_dir = match &config.output_path {
            Some(output) => output.clone(),
            None => path.to_path_buf(),
        };

        let (success_count, failure_count) =
            process_directory(path, &output_dir, &modified_config, is_encrypt, password)?;

        // Print summary
        println!("\n{}", style("Directory processing complete").green().bold());
        println!("Total files: {}", success_count + failure_count);
        println!("{} {}", style("Successfully processed:").green(), success_count);
        println!("{} {}", style("Failed:").red(), failure_count);
    } else {
        // Process single file
        let output_path = config.get_output_path(&path.to_path_buf(), is_encrypt);

        // Ensure output directory exists
        if let Some(parent) = output_path.parent() {
            ensure_directory(parent)?;
        }

        let result = process_file(
            path,
            &output_path,
            &modified_config,
            is_encrypt,
            password,
            &AtomicBool::new(false),
        )?;

        if result {
            println!("{}", style("\nFile processing completed successfully").green().bold());
        } else {
            println!("{}", style("\nFile processing skipped").yellow().bold());
        }
    }

    Ok(())
}

/// List all encrypted files in a directory
pub fn list_encrypted_files(dir_path: &Path, recursive: bool) -> Result<Vec<PathBuf>> {
    if !dir_path.exists() || !dir_path.is_dir() {
        anyhow::bail!("Invalid directory path: {}", dir_path.display());
    }

    let walker = if recursive {
        WalkDir::new(dir_path).into_iter()
    } else {
        WalkDir::new(dir_path).max_depth(1).into_iter()
    };

    let encrypted_files: Vec<PathBuf> = walker
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file() && is_encrypted_file(e.path()))
        .map(|e| e.path().to_path_buf())
        .collect();

    Ok(encrypted_files)
}