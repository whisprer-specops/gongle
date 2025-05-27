"""
Rust Bridge - Python interface to the wofl_obs-defuscrypt theatrical features
Handles subprocess communication and data marshalling between Flask and Rust
"""

import subprocess
import json
import asyncio
import os
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import msgpack
import logging

logger = logging.getLogger(__name__)

class RustEncryptionBridge:
    """Bridge between Flask app and Rust encryption binary"""
    
    def __init__(self, rust_binary_path: str = None):
        """
        Initialize the bridge
        
        Args:
            rust_binary_path: Path to the compiled Rust binary
        """
        if rust_binary_path is None:
            # Try to find the binary in common locations
            possible_paths = [
                "../wofl_obs-defuscrypt/target/release/wofl_obs-defuscrypt",
                "../wofl_obs-defuscrypt/target/debug/wofl_obs-defuscrypt",
                "./wofl_obs-defuscrypt",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    rust_binary_path = path
                    break
            else:
                raise RuntimeError("Could not find Rust binary. Please compile it first.")
        
        self.rust_binary = os.path.abspath(rust_binary_path)
        self.temp_dir = tempfile.mkdtemp(prefix="gongle_")
        logger.info(f"Rust bridge initialized with binary at: {self.rust_binary}")
    
    async def encrypt_theatrical(
        self, 
        data: str, 
        user_id: int, 
        level: str,
        password: Optional[str] = None
    ) -> Dict:
        """
        Encrypt data with theatrical flair
        
        Args:
            data: The data to encrypt
            user_id: User ID for password generation
            level: Encryption level (basic, premium, paranoid, etc.)
            password: Optional custom password
        
        Returns:
            Dictionary with encryption results and theatrical elements
        """
        # Create temporary file with data
        input_file = os.path.join(self.temp_dir, f"input_{user_id}_{level}.txt")
        output_file = os.path.join(self.temp_dir, f"output_{user_id}_{level}.enc")
        
        try:
            # Write data to temp file
            with open(input_file, 'w') as f:
                f.write(data)
            
            # Generate theatrical password if not provided
            if password is None:
                password = self._generate_theatrical_password(user_id, level)
            
            # Build command based on level
            cmd = [
                self.rust_binary,
                "encrypt",
                input_file,
                "-o", output_file,
                "--force"
            ]
            
            # Add level-specific parameters
            if level in ["paranoid", "tinfoil", "eldritch"]:
                # These levels use multiple passes
                passes = {"paranoid": 3, "tinfoil": 7, "eldritch": 13}
                cmd.extend(["--passes", str(passes.get(level, 3))])
            
            # Run encryption
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send password via stdin
            stdout, stderr = await process.communicate(input=password.encode())
            
            if process.returncode != 0:
                raise RuntimeError(f"Encryption failed: {stderr.decode()}")
            
            # Read encrypted file
            with open(output_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Generate theatrical response
            result = {
                "success": True,
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "data_size": len(encrypted_data),
                "compression_ratio": len(encrypted_data) / len(data.encode()),
                "theatrical_elements": self._get_theatrical_elements(level),
                "password_hint": self._get_password_hint(level),
                "encryption_time_ms": self._get_theatrical_time(level)
            }
            
            return result
            
        finally:
            # Cleanup temp files
            for f in [input_file, output_file]:
                if os.path.exists(f):
                    os.remove(f)
    
    async def shred_theatrical(
        self,
        file_path: str,
        shred_type: str = "standard"
    ) -> Dict:
        """
        Theatrically shred a file
        
        Args:
            file_path: Path to file to shred
            shred_type: Type of shredding (standard, military, nuclear, blackhole)
        
        Returns:
            Dictionary with shredding results
        """
        # Map shred types to passes
        shred_config = {
            "standard": 3,
            "military": 7,
            "nuclear": 35,
            "blackhole": 99
        }
        
        passes = shred_config.get(shred_type, 3)
        
        cmd = [
            self.rust_binary,
            "shred",
            file_path,
            f"--passes={passes}"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "passes": passes,
            "message": self._get_shred_message(shred_type),
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    
    def _generate_theatrical_password(self, user_id: int, level: str) -> str:
        """Generate a theatrical password based on user and level"""
        passwords = {
            "basic": f"user_{user_id}_password123",
            "premium": f"user_{user_id}_premiumpassword!",
            "paranoid": f"user_{user_id}_they_are_watching",
            "tinfoil": f"user_{user_id}_5g_cant_penetrate_this",
            "quantum": f"user_{user_id}_schrodingers_password",
            "alien": f"user_{user_id}_area51_clearance",
            "eldritch": f"user_{user_id}_ph_nglui_mglw_nafh"
        }
        return passwords.get(level, f"user_{user_id}_default")
    
    def _get_theatrical_elements(self, level: str) -> List[str]:
        """Get theatrical elements for each level"""
        elements = {
            "basic": [
                "Applied ROT13 (just kidding)",
                "Added blockchain dust",
                "Sprinkled with cyber-salt"
            ],
            "premium": [
                "Double-encrypted for safety",
                "Blessed by cyber-monks",
                "Wrapped in digital silk",
                "Premium particles added"
            ],
            "paranoid": [
                "Wrapped in digital tin foil",
                "Hidden from government satellites",
                "5G-proof coating applied",
                "Illuminati-resistant layer added",
                "Birds aren't real protection enabled"
            ],
            "tinfoil": [
                "Compressed with anxiety",
                "Encrypted with conspiracy theories",
                "Chemtrail-resistant layer added",
                "Flat-earth approved encryption",
                "Lizard people can't read this"
            ],
            "quantum": [
                "Quantum entangled with parallel universe",
                "Schrödinger's encryption applied",
                "Observed by quantum cats",
                "Superposition achieved",
                "Heisenberg would be uncertain"
            ],
            "alien": [
                "Applied Area 51 technology",
                "Translated to alien language",
                "UFO cloaking activated",
                "Crop circle pattern applied",
                "Roswell-grade protection"
            ],
            "eldritch": [
                "C̸͎̈ť̶̰h̷̺̎u̸̮̇l̴̰̈h̴̬̆ṳ̶̈ ̷͇̈́f̸̱̈h̶̺̄t̶̜̔ä̶́ͅg̷̱̈ñ̶̬",
                "Reality.exe has stopped responding",
                "S̵̱̈́a̷̤̐n̶̜̈́i̷̦̇t̸̰̄y̷̺̌ ̸̜̇c̸̣̈h̶̰̄ë̶́ͅc̷̱̈k̸̜̇ ̷̤̈f̶̰̄ä̶́ͅi̷̦̇ḷ̸̈ë̶́ͅď̷̺",
                "Tentacles deployed",
                "Non-Euclidean geometry applied"
            ]
        }
        return elements.get(level, ["Magic happened"])
    
    def _get_password_hint(self, level: str) -> str:
        """Get password hint for each level"""
        hints = {
            "basic": "It's literally 'password123' with your user ID",
            "premium": "Same as basic but with an exclamation mark!",
            "paranoid": "They. Are. Watching. (with underscores)",
            "tinfoil": "5G can't penetrate this password",
            "quantum": "The cat knows the password (or doesn't)",
            "alien": "Check your Area 51 clearance badge",
            "eldritch": "Ph'nglui mglw'nafh... you know the rest"
        }
        return hints.get(level, "The password is hidden in plain sight")
    
    def _get_theatrical_time(self, level: str) -> int:
        """Get theatrical encryption time in milliseconds"""
        import random
        base_times = {
            "basic": 100,
            "premium": 500,
            "paranoid": 1000,
            "tinfoil": 2000,
            "quantum": 3000,
            "alien": 4000,
            "eldritch": 6666
        }
        base = base_times.get(level, 1000)
        # Add some randomness for realism
        return base + random.randint(-base//4, base//4)
    
    def _get_shred_message(self, shred_type: str) -> str:
        """Get shredding complete message"""
        messages = {
            "standard": "Data overwritten with cat videos",
            "military": "Data destroyed with military precision",
            "nuclear": "Data atomized at the molecular level",
            "blackhole": "Data consumed by artificial black hole"
        }
        return messages.get(shred_type, "Data has been shredded")
    
    def cleanup(self):
        """Clean up temporary directory"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


# Singleton instance
_bridge_instance = None

def get_rust_bridge() -> RustEncryptionBridge:
    """Get or create the Rust bridge singleton"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = RustEncryptionBridge()
    return _bridge_instance


# Async wrapper functions for Flask routes
async def encrypt_data_theatrical(data: str, user_id: int, level: str) -> Dict:
    """Async wrapper for theatrical encryption"""
    bridge = get_rust_bridge()
    return await bridge.encrypt_theatrical(data, user_id, level)


async def shred_data_theatrical(file_path: str, shred_type: str) -> Dict:
    """Async wrapper for theatrical shredding"""
    bridge = get_rust_bridge()
    return await bridge.shred_theatrical(file_path, shred_type)