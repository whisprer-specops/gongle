use anyhow::{Context, Result};
use console::style;
use dialoguer::{theme::ColorfulTheme, Confirm};
use indicatif::{ProgressBar, ProgressStyle};
use rand::{rngs::OsRng, RngCore};
use std::{
    fs::{self, File, OpenOptions},
    io::{Seek, SeekFrom, Write},
    path::{Path, PathBuf},
    thread,
    time::Duration,
};
use thiserror::Error;

/// Possible patterns for overwriting
pub enum OverwritePattern {
    /// All zeros (0x00)
    Zeros,
    /// All ones (0xFF)
    Ones,
    /// Random data
    Random,
}

/// Secure deletion errors
#[derive(Error, Debug)]
pub enum SecureDeleteError {
    #[error("Failed to open file for secure deletion")]
    OpenError,

    #[error("Failed during overwrite pass")]
    OverwriteError,

    #[error("Failed to delete file after overwriting")]
    DeleteError,
}

/// Confirmation for secure deletion
pub fn confirm_secure_deletion(path: &Path, is_dir: bool, clean_folders: bool) -> Result<bool> {
    let descriptor = if is_dir { "all files in directory" } else { "file" };
    let folder_note = if clean_folders {
        " Empty folders will also be deleted after processing."
    } else {
        ""
    };

    let message = format!(
        "{}{}{}",
        style("WARNING: You are about to SECURELY DELETE the original ")
            .red()
            .bold(),
        style(descriptor).yellow().bold(),
        style(format!(
            " after processing.\nThis operation CANNOT be undone!{}",
            folder_note
        ))
        .red()
        .bold()
    );

    println!("{}", message);
    println!("{}", style("Path: ").bold().yellow().to_string() + &path.display().to_string());

    let confirm = Confirm::with_theme(&ColorfulTheme::default())
        .with_prompt("Are you sure you want to proceed?")
        .default(false)
        .interact()?;

    Ok(confirm)
}

/// Securely delete a file using multiple overwrite passes
pub fn secure_delete_file(path: &Path, passes: u8) -> Result<()> {
    // Check if file exists
    if !path.exists() {
        println!(
            "{} File not found for secure deletion: {}",
            style("[WARNING]").yellow().bold(),
            path.display()
        );
        return Ok(());
    }

    // Get file size
    let metadata = fs::metadata(path).context("Failed to get file metadata")?;
    let file_size = metadata.len();

    // If file is empty, just delete it
    if file_size == 0 {
        fs::remove_file(path).context("Failed to delete empty file")?;
        println!(
            "{} Deleted empty file: {}",
            style("[INFO]").green().bold(),
            path.display()
        );
        return Ok(());
    }

    println!(
        "{} Securely deleting file with {} passes: {}",
        style("[INFO]").blue().bold(),
        passes,
        path.display()
    );

    // Setup progress bar
    let progress_bar = ProgressBar::new(file_size * u64::from(passes));
    progress_bar.set_style(
        ProgressStyle::default_bar()
            .template("[{elapsed_precise}] {bar:40.green/red} {pos:>7}/{len:7} {msg}")
            .unwrap()
            .progress_chars("##-"),
    );

    // Open file for writing
    let mut file = OpenOptions::new()
        .write(true)
        .open(path)
        .map_err(|_| SecureDeleteError::OpenError)?;

    // Buffer for writing (8 KB)
    const BUFFER_SIZE: usize = 8192;
    let mut buffer = vec![0u8; BUFFER_SIZE];

    // For random data generation
    let mut rng = OsRng;

    // Perform overwrite passes
    for pass in 1..=passes {
        // Determine pattern based on pass number
        let pattern = match pass % 3 {
            1 => OverwritePattern::Zeros,
            2 => OverwritePattern::Ones,
            0 => OverwritePattern::Random,
            _ => unreachable!(),
        };

        // Set message for progress bar
        progress_bar.set_message(format!(
            "Pass {}/{}: {}",
            pass,
            passes,
            match pattern {
                OverwritePattern::Zeros => "Writing zeros",
                OverwritePattern::Ones => "Writing ones",
                OverwritePattern::Random => "Writing random data",
            }
        ));

        // Prepare buffer based on pattern
        match pattern {
            OverwritePattern::Zeros => {
                for i in 0..BUFFER_SIZE {
                    buffer[i] = 0x00;
                }
            }
            OverwritePattern::Ones => {
                for i in 0..BUFFER_SIZE {
                    buffer[i] = 0xFF;
                }
            }
            OverwritePattern::Random => {
                // Random pattern buffer is regenerated for each write
            }
        };

        // Seek to beginning of file
        file.seek(SeekFrom::Start(0))
            .map_err(|_| SecureDeleteError::OverwriteError)?;

        // Write data in chunks
        let mut bytes_written = 0;
        while bytes_written < file_size {
            let remaining = file_size - bytes_written;
            let to_write = std::cmp::min(remaining, BUFFER_SIZE as u64) as usize;

            // For random pattern, regenerate buffer each time
            if let OverwritePattern::Random = pattern {
                rng.fill_bytes(&mut buffer[0..to_write]);
            }

            file.write_all(&buffer[0..to_write])
                .map_err(|_| SecureDeleteError::OverwriteError)?;

            bytes_written += to_write as u64;
            progress_bar.inc(to_write as u64);
        }

        // Sync changes to disk after each pass
        file.sync_all().map_err(|_| SecureDeleteError::OverwriteError)?;

        // Small delay to prevent CPU hammering
        thread::sleep(Duration::from_millis(10));
    }

    // Finish progress
    progress_bar.finish_with_message("Overwriting complete");

    // Close file handle
    drop(file);

    // Finally delete the file
    fs::remove_file(path).map_err(|_| SecureDeleteError::DeleteError)?;

    println!(
        "{} Successfully securely deleted: {}",
        style("[SUCCESS]").green().bold(),
        path.display()
    );

    Ok(())
}

/// Clean up empty directories
pub fn clean_empty_directories(dir_path: &Path, recursive: bool) -> Result<usize> {
    if !dir_path.is_dir() {
        println!(
            "{} Not a directory: {}",
            style("[WARNING]").yellow().bold(),
            dir_path.display()
        );
        return Ok(0);
    }

    let mut deleted_count = 0;

    // If recursive, process subdirectories bottom-up
    if recursive {
        // Get all subdirectories sorted by depth (deepest first)
        let mut subdirs: Vec<PathBuf> = walkdir::WalkDir::new(dir_path)
            .min_depth(1)
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| e.path().is_dir())
            .map(|e| e.path().to_path_buf())
            .collect();

        // Sort directories by depth (deepest first)
        subdirs.sort_by(|a, b| {
            let a_components = a.components().count();
            let b_components = b.components().count();
            b_components.cmp(&a_components)
        });

        // Process each subdirectory
        for subdir in subdirs {
            // Check if directory is empty
            let is_empty = fs::read_dir(&subdir)
                .map(|entries| entries.count() == 0)
                .unwrap_or(false);

            if is_empty {
                println!(
                    "{} Removing empty directory: {}",
                    style("[INFO]").blue().bold(),
                    subdir.display()
                );

                fs::remove_dir(&subdir)
                    .with_context(|| format!("Failed to remove directory: {}", subdir.display()))?;

                deleted_count += 1;
            }
        }
    }

    // Check if the root directory is now empty and should be deleted
    let is_empty = fs::read_dir(dir_path)
        .map(|entries| entries.count() == 0)
        .unwrap_or(false);

    if is_empty {
        println!(
            "{} Removing empty root directory: {}",
            style("[INFO]").blue().bold(),
            dir_path.display()
        );

        fs::remove_dir(dir_path)
            .with_context(|| format!("Failed to remove directory: {}", dir_path.display()))?;

        deleted_count += 1;
    }

    Ok(deleted_count)
}

/// Handles overwrite confirmation with "All" option
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OverwriteAction {
    /// Overwrite this file only
    Yes,
    /// Skip this file
    No,
    /// Overwrite all files
    All,
}

/// Get confirmation for overwriting a file
pub fn get_overwrite_confirmation(file_path: &Path) -> Result<OverwriteAction> {
    let prompt = format!(
        "File '{}' already exists. Overwrite?",
        file_path.display()
    );

    let options = &["Yes (this file)", "No (skip file)", "All (all files)"];

    let selection = dialoguer::Select::with_theme(&ColorfulTheme::default())
        .with_prompt(prompt)
        .default(0)
        .items(options)
        .interact()?;

    match selection {
        0 => Ok(OverwriteAction::Yes),
        1 => Ok(OverwriteAction::No),
        2 => Ok(OverwriteAction::All),
        _ => Ok(OverwriteAction::No), // Default to No for safety
    }
}
