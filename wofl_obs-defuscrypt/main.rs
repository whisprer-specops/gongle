use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use console::style;
use std::path::PathBuf;

mod config;
mod crypto;
mod file_utils;
mod secure_delete;
mod ui;

use crate::config::Config;
use file_utils::{list_encrypted_files, process_path};

#[derive(Parser)]
#[command(
    name = "secure-crypt",
    author = "RYO Modular",
    version,
    about = "Secure file encryption and shredding utility",
    long_about = "A tool for encrypting files with strong cryptography and securely deleting originals."
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Output directory [default: same as input]
    #[arg(short, long, value_name = "DIR")]
    output: Option<PathBuf>,

    /// Process directories recursively
    #[arg(short, long)]
    recursive: bool,

    /// Force overwrite without prompting
    #[arg(short, long)]
    force: bool,

    /// Securely delete original files
    #[arg(short, long)]
    secure_delete: bool,

    /// Number of passes for secure deletion [default: 3]
    #[arg(short = 'p', long, default_value_t = 3)]
    passes: u8,

    /// Remove empty folders after processing
    #[arg(short = 'c', long)]
    clean_folders: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Encrypt file(s) or folder(s)
    Encrypt {
        /// Path to file or directory to encrypt
        path: PathBuf,
    },

    /// Decrypt file(s) or folder(s)
    Decrypt {
        /// Path to file or directory to decrypt
        path: PathBuf,
    },

    /// List encrypted files in a directory
    List {
        /// Path to directory to list encrypted files from
        path: PathBuf,
    },
}

fn main() -> Result<()> {
    // Initialize logger
    env_logger::init_from_env(
        env_logger::Env::default().filter_or(env_logger::DEFAULT_FILTER_ENV, "info"),
    );

    // Parse command line arguments
    let cli = Cli::parse();

    // Create config from CLI arguments
    let config = Config {
        output_path: cli.output,
        recursive: cli.recursive,
        force: cli.force,
        secure_delete: cli.secure_delete,
        shred_passes: cli.passes,
        clean_empty_folders: cli.clean_folders,
    };

    // Handle commands
    match &cli.command {
        Commands::Encrypt { path } => {
            println!(
                "{} files at {}",
                style("Encrypting").green().bold(),
                path.display()
            );
            
            process_path(path, &config, true)
                .context("Failed to encrypt files")?;
                
            println!("{}", style("Encryption completed").green().bold());
        }

        Commands::Decrypt { path } => {
            println!(
                "{} files at {}",
                style("Decrypting").blue().bold(),
                path.display()
            );
            
            process_path(path, &config, false)
                .context("Failed to decrypt files")?;
                
            println!("{}", style("Decryption completed").blue().bold());
        }

        Commands::List { path } => {
            println!(
                "{} encrypted files in {}",
                style("Listing").yellow().bold(),
                path.display()
            );
            
            let files = list_encrypted_files(path, cli.recursive)
                .context("Failed to list encrypted files")?;
                
            println!("Found {} encrypted files:", files.len());
            
            for file in files {
                println!("  {}", file.display());
            }
        }
    }

    Ok(())
}