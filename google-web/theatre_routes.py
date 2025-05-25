import subprocess
import json
import os
import base64
from datetime import datetime, timedelta
import random

class GongleDataProtector:
    """
    Ironically over-engineered data protection for harvested user data.
    Because nothing says "we care about your privacy" like military-grade
    encryption on data we're actively selling!
    """
    
    def __init__(self, rust_binary_path="/path/to/wofl_obs-defuscrypt"):
        self.rust_binary = rust_binary_path
        self.encryption_levels = {
            "basic": {"passes": 1, "points": 100},
            "premium": {"passes": 3, "points": 500},
            "paranoid": {"passes": 7, "points": 1000},
            "tinfoil": {"passes": 13, "points": 5000}
        }
    
    def encrypt_user_data(self, user_id, data_type, data_value, protection_level="basic"):
        """
        Encrypt user data with varying levels of 'protection'
        Higher levels = more points spent = more theatrical security
        """
        # Create temporary file with data
        temp_file = f"/tmp/gongle_{user_id}_{data_type}.tmp"
        with open(temp_file, 'w') as f:
            json.dump({
                "type": data_type,
                "value": data_value,
                "harvested_at": datetime.now().isoformat(),
                "sold_to": "highest_bidder",
                "protection_level": protection_level
            }, f)
        
        # Call rust encryption tool
        encrypted_file = f"{temp_file}.enc"
        try:
            # Use a "secure" password based on user ID (totally not predictable!)
            password = f"user_{user_id}_super_secure_pwd"
            
            result = subprocess.run([
                self.rust_binary,
                "encrypt",
                temp_file,
                "-o", encrypted_file,
                "--force"
            ], input=password.encode(), capture_output=True)
            
            if result.returncode == 0:
                # Read encrypted data
                with open(encrypted_file, 'rb') as f:
                    encrypted_data = base64.b64encode(f.read()).decode()
                
                # Clean up with secure deletion if user paid for it
                if protection_level != "basic":
                    passes = self.encryption_levels[protection_level]["passes"]
                    subprocess.run([
                        self.rust_binary,
                        "shred",
                        temp_file,
                        f"--passes={passes}"
                    ])
                else:
                    os.remove(temp_file)
                
                os.remove(encrypted_file)
                return encrypted_data
            else:
                raise Exception(f"Encryption failed: {result.stderr.decode()}")
                
        except Exception as e:
            # Clean up on failure
            for f in [temp_file, encrypted_file]:
                if os.path.exists(f):
                    os.remove(f)
            raise e
    
    def schedule_data_funeral(self, user_id, data_ids, funeral_type="viking"):
        """
        Schedule dramatic deletion of user data
        funeral_type options:
        - 'viking': Burn with fire (35 passes) 
        - 'space': Launch into void (random passes 1-100)
        - 'quantum': Superposition deletion (deletes and doesn't delete)
        """
        funeral_config = {
            "viking": {
                "passes": 35,
                "message": "Your data sails to Valhalla! 🔥⛵",
                "points": 10000
            },
            "space": {
                "passes": random.randint(1, 100),
                "message": "Your data has achieved escape velocity! 🚀",
                "points": 7500  
            },
            "quantum": {
                "passes": random.choice([0, 999]),  # Schrödinger's shred
                "message": "Your data both exists and doesn't exist! 🎲",
                "points": 15000
            }
        }
        
        config = funeral_config[funeral_type]
        
        # Create memorial file
        memorial = {
            "user_id": user_id,
            "data_ids": data_ids,
            "funeral_type": funeral_type,
            "scheduled_for": (datetime.now() + timedelta(hours=24)).isoformat(),
            "epitaph": f"Here lies {len(data_ids)} pieces of data. {config['message']}",
            "shred_passes": config['passes']
        }
        
        return memorial
    
    def generate_security_theater_report(self, user_id):
        """
        Generate an impressive-looking but meaningless security report
        """
        buzz_words = [
            "blockchain", "AI-powered", "quantum-resistant", "zero-knowledge",
            "military-grade", "NSA-approved", "holographic", "5D encrypted"
        ]
        
        report = {
            "user_id": user_id,
            "security_score": random.randint(900, 999),  # Always impressively high
            "encryption_layers": random.randint(7, 13),
            "protection_level": random.choice(buzz_words) + " " + random.choice(buzz_words),
            "vulnerabilities_found": 0,  # Always zero, we're "perfect"!
            "recommendation": "Sell more data for enhanced protection!",
            "next_audit": "When pigs fly",
            "certificate": self._generate_fake_certificate()
        }
        
        return report
    
    def _generate_fake_certificate(self):
        """Generate a completely legitimate security certificate"""
        return f"""
        ========================================
        CERTIFICATE OF MAXIMUM SECURITY™
        ========================================
        This certifies that your data is protected by:
        ✓ {random.randint(2, 9)} layers of encryption
        ✓ {random.choice(['Alien', 'Time-traveling', 'Interdimensional'])} technology
        ✓ At least {random.randint(3, 7)} prayers to the data gods
        ✓ One (1) very good password: ********
        
        Signed: Dr. Totally Real Security Expert
        Date: {datetime.now().strftime('%Y-%m-%d')}
        ========================================
        """

# Integration with Flask app
def add_encryption_routes(app, db):
    """Add encryption-related routes to the Gongle app"""
    protector = GongleDataProtector()
    
    @app.route('/api/encrypt_my_data', methods=['POST'])
    def encrypt_my_data():
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        data = request.json
        protection_level = data.get('level', 'basic')
        
        # Check if user has enough points
        required_points = protector.encryption_levels[protection_level]['points']
        user = User.query.get(user_id)
        
        if user.points < required_points:
            return jsonify({
                'error': f'Not enough points! Need {required_points}, you have {user.points}'
            }), 400
        
        # Deduct points
        user.points -= required_points
        
        # "Encrypt" all their data
        encrypted_count = 0
        for data_sold in DataSold.query.filter_by(user_id=user_id).all():
            try:
                encrypted = protector.encrypt_user_data(
                    user_id, 
                    data_sold.data_type,
                    data_sold.data_value,
                    protection_level
                )
                # Store encrypted version
                data_sold.data_value = f"ENCRYPTED:{encrypted[:32]}..."  # Just show a snippet
                encrypted_count += 1
            except Exception as e:
                print(f"Failed to encrypt {data_sold.data_type}: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'encrypted_count': encrypted_count,
            'points_remaining': user.points,
            'message': f'Your data is now {protection_level}-level protected! Sleep tight!'
        })
    
    @app.route('/api/data_funeral', methods=['POST'])
    def schedule_data_funeral():
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        data = request.json
        funeral_type = data.get('type', 'viking')
        
        # Get all user's data IDs
        data_ids = [d.id for d in DataSold.query.filter_by(user_id=user_id).all()]
        
        memorial = protector.schedule_data_funeral(user_id, data_ids, funeral_type)
        
        # Store the memorial
        funeral_data = DataSold(
            user_id=user_id,
            data_type='funeral_scheduled',
            data_value=json.dumps(memorial),
            points=0
        )
        db.session.add(funeral_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'memorial': memorial,
            'message': 'Your data funeral has been scheduled. Dress code: Black.'
        })
    
    @app.route('/api/security_theater', methods=['GET'])
    def security_theater():
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        report = protector.generate_security_theater_report(session['user_id'])
        
        return jsonify({
            'success': True,
            'report': report,
            'disclaimer': 'This report is for entertainment purposes only. Your data is still being sold.'
        })
    
    return app