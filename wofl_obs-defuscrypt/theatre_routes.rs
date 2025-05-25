# theater_routes.py - Flask routes for data protection theater

from flask import Blueprint, jsonify, request, session
import subprocess
import json
import asyncio
import random
import time
from datetime import datetime, timedelta
import base64

theater_bp = Blueprint('theater', __name__)

# Mock encryption levels with costs
ENCRYPTION_LEVELS = {
    'basic': {'cost': 100, 'name': 'Basic', 'rust_level': 'Basic'},
    'premium': {'cost': 500, 'name': 'Premium', 'rust_level': 'Premium'},
    'paranoid': {'cost': 1000, 'name': 'Paranoid', 'rust_level': 'Paranoid'},
    'tinfoil': {'cost': 5000, 'name': 'Tinfoil Supreme', 'rust_level': 'Tinfoil'},
    'quantum': {'cost': 10000, 'name': 'Quantum', 'rust_level': 'Quantum'},
    'alien': {'cost': 25000, 'name': 'Alien Technology', 'rust_level': 'Alien'},
    'eldritch': {'cost': 66666, 'name': 'Eldritch Horror', 'rust_level': 'Eldritch'}
}

# Loot box algorithms
LOOT_BOX_ALGORITHMS = [
    {'name': 'ROT13 Supreme Edition', 'rarity': 'common', 'bonus': 100},
    {'name': 'Caesar Cipher Deluxe', 'rarity': 'common', 'bonus': 150},
    {'name': 'Base64 Premium', 'rarity': 'common', 'bonus': 200},
    {'name': 'XOR with Password "password"', 'rarity': 'uncommon', 'bonus': 300},
    {'name': 'Pig Latin Encryption', 'rarity': 'uncommon', 'bonus': 400},
    {'name': 'Reverse String Technology', 'rarity': 'rare', 'bonus': 500},
    {'name': 'UPPERCASE ONLY MODE', 'rarity': 'rare', 'bonus': 600},
    {'name': 'Emoji Substitution Cipher 🔐', 'rarity': 'epic', 'bonus': 1000},
    {'name': 'Blockchain-ish Algorithm', 'rarity': 'legendary', 'bonus': 2500},
    {'name': 'AI-Powered Nonsense', 'rarity': 'mythic', 'bonus': 5000},
    {'name': 'Quantum Entangled ROT26', 'rarity': 'mythic', 'bonus': 10000}
]

# Global dictionary to store encryption races
active_races = {}

@theater_bp.route('/api/theater/encrypt', methods=['POST'])
def theatrical_encrypt():
    """Encrypt user data with maximum drama"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    data = request.json
    level = data.get('level', 'basic')
    
    if level not in ENCRYPTION_LEVELS:
        return jsonify({'error': 'Invalid encryption level'}), 400
    
    # Check if user has enough points
    from app import User, DataSold, db
    user = User.query.get(user_id)
    cost = ENCRYPTION_LEVELS[level]['cost']
    
    if user.points < cost:
        return jsonify({
            'error': f'Insufficient points! Need {cost}, you have {user.points}'
        }), 400
    
    # Deduct points
    user.points -= cost
    
    # Get all user's data
    user_data = DataSold.query.filter_by(user_id=user_id).all()
    
    # Call Rust encryption theater (mock for now)
    theatrical_response = {
        'success': True,
        'message': f'Your data has been encrypted with {ENCRYPTION_LEVELS[level]["name"]} protection!',
        'data_id': f'GONGLE-{user_id}-{int(time.time())}',
        'encryption_time_ms': random.randint(1000, 10000),
        'theatrical_elements': generate_theatrical_elements(level),
        'points_earned': 0,
        'achievement_unlocked': check_achievement(user_id, level),
        'encrypted_count': len(user_data)
    }
    
    # "Encrypt" the data in database
    for data_item in user_data:
        if not data_item.data_value.startswith('ENCRYPTED:'):
            # Generate fake encrypted preview
            fake_encrypted = base64.b64encode(data_item.data_value.encode()).decode()[:32]
            data_item.data_value = f'ENCRYPTED:{fake_encrypted}...'
    
    db.session.commit()
    
    return jsonify(theatrical_response)

@theater_bp.route('/api/theater/funeral', methods=['POST'])
def schedule_data_funeral():
    """Schedule a dramatic data funeral"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    data = request.json
    funeral_type = data.get('type', 'viking')
    
    from app import User, DataSold, db
    user = User.query.get(user_id)
    
    # Funeral costs
    funeral_costs = {
        'viking': 10000,
        'space': 7500,
        'quantum': 15000,
        'eldritch': 66666
    }
    
    cost = funeral_costs.get(funeral_type, 10000)
    
    if user.points < cost:
        return jsonify({
            'error': f'Insufficient points for {funeral_type} funeral! Need {cost} points'
        }), 400
    
    # Deduct points
    user.points -= cost
    
    # Get all user data IDs
    data_ids = [str(d.id) for d in DataSold.query.filter_by(user_id=user_id).all()]
    
    # Generate funeral details
    funeral_details = generate_funeral_details(funeral_type, len(data_ids))
    
    # Store funeral record
    funeral_record = DataSold(
        user_id=user_id,
        data_type='funeral_scheduled',
        data_value=json.dumps({
            'type': funeral_type,
            'data_count': len(data_ids),
            'scheduled_time': (datetime.now() + timedelta(days=1)).isoformat(),
            'details': funeral_details
        }),
        points=0
    )
    db.session.add(funeral_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'funeral_id': f'FUNERAL-{user_id}-{int(time.time())}',
        'message': funeral_details['epitaph'],
        'scheduled_time': funeral_record.data_value,
        'special_effects': funeral_details['effects'],
        'guest_list': funeral_details['guests']
    })

@theater_bp.route('/api/theater/race/start', methods=['POST'])
def start_encryption_race():
    """Start an encryption race"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    race_id = f'RACE-{user_id}-{int(time.time())}'
    
    # Create race participants
    participants = [
        {'name': f'User_{user_id}', 'speed': random.uniform(0.8, 1.2), 'vehicle': '🏎️'},
        {'name': 'CryptoBot3000', 'speed': random.uniform(0.9, 1.3), 'vehicle': '🚗'},
        {'name': 'QuantumRacer', 'speed': random.uniform(0.7, 1.4), 'vehicle': '🚙'},
        {'name': 'BlockchainBurner', 'speed': random.uniform(0.85, 1.25), 'vehicle': '🏍️'}
    ]
    
    # Calculate finish times
    for p in participants:
        p['finish_time'] = random.uniform(2, 5) / p['speed']
    
    # Sort by finish time
    participants.sort(key=lambda x: x['finish_time'])
    
    # Store race results
    active_races[race_id] = {
        'participants': participants,
        'winner': participants[0]['name'],
        'started_at': time.time()
    }
    
    # Award points to user if they won
    if participants[0]['name'] == f'User_{user_id}':
        from app import User, db
        user = User.query.get(user_id)
        user.points += 1000
        db.session.commit()
        winner_bonus = 1000
    else:
        winner_bonus = 0
    
    return jsonify({
        'success': True,
        'race_id': race_id,
        'participants': participants,
        'winner': participants[0]['name'],
        'winner_bonus': winner_bonus,
        'victory_cry': random.choice([
            'ENCRYPTED TO THE MOON!',
            'EAT MY CIPHER DUST!',
            'CHACHA20 GO BRRRRR!',
            'WITNESS MY ENTROPY!',
            'QUANTUM SUPREMACY ACHIEVED!',
            'I AM THE KEY MASTER!'
        ])
    })

@theater_bp.route('/api/theater/lootbox', methods=['POST'])
def open_loot_box():
    """Open an encryption algorithm loot box"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    from app import User, DataSold, db
    user = User.query.get(user_id)
    
    # Loot box cost
    LOOT_BOX_COST = 1000
    
    if user.points < LOOT_BOX_COST:
        return jsonify({
            'error': f'Insufficient points! Need {LOOT_BOX_COST} points'
        }), 400
    
    # Deduct points
    user.points -= LOOT_BOX_COST
    
    # Roll for algorithm with weighted probabilities
    roll = random.random()
    if roll < 0.4:  # 40% common
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'common']
    elif roll < 0.7:  # 30% uncommon
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'uncommon']
    elif roll < 0.85:  # 15% rare
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'rare']
    elif roll < 0.95:  # 10% epic
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'epic']
    elif roll < 0.99:  # 4% legendary
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'legendary']
    else:  # 1% mythic
        algorithms = [a for a in LOOT_BOX_ALGORITHMS if a['rarity'] == 'mythic']
    
    algorithm = random.choice(algorithms)
    
    # Award bonus points
    user.points += algorithm['bonus']
    
    # Store the algorithm "collection"
    collection = DataSold(
        user_id=user_id,
        data_type='algorithm_collected',
        data_value=json.dumps(algorithm),
        points=algorithm['bonus']
    )
    db.session.add(collection)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'algorithm': algorithm,
        'points_awarded': algorithm['bonus'],
        'total_points': user.points,
        'rarity_color': get_rarity_color(algorithm['rarity'])
    })

@theater_bp.route('/api/theater/certificate', methods=['GET'])
def generate_certificate():
    """Generate a security certificate"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    from app import User, DataSold
    user = User.query.get(user_id)
    
    # Count encrypted items
    encrypted_count = DataSold.query.filter_by(user_id=user_id)\
        .filter(DataSold.data_value.like('ENCRYPTED:%')).count()
    
    # Generate certificate data
    tech_options = ['Alien', 'Time-traveling', 'Interdimensional', 'Blockchain', 'AI-powered', 'Quantum', 'Holographic']
    bonus_items = ['A rubber duck', 'Good vibes', 'Thoughts and prayers', 'A lucky penny', 'Mercury in retrograde', 'Essential oils', 'Crystal healing']
    
    certificate = {
        'user_name': user.email,
        'layers': random.randint(3, 13),
        'technology': random.choice(tech_options),
        'prayers': random.randint(1, 10),
        'bonus_protection': random.choice(bonus_items),
        'security_score': random.randint(900, 999),
        'encrypted_items': encrypted_count,
        'certificate_id': f'CERT-{user_id}-{int(time.time())}',
        'issued_date': datetime.now().isoformat(),
        'expiry_date': 'When the sun explodes',
        'signed_by': 'Dr. Totally Real Security Expert',
        'quantum_signature': generate_quantum_signature()
    }
    
    return jsonify({
        'success': True,
        'certificate': certificate
    })

@theater_bp.route('/api/theater/shred', methods=['POST'])
def shred_data():
    """Dramatically shred user data"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    data = request.json
    shred_type = data.get('type', 'standard')
    
    from app import User, DataSold, db
    user = User.query.get(user_id)
    
    # Shredding costs
    shred_costs = {
        'standard': 500,
        'military': 2000,
        'nuclear': 5000,
        'blackhole': 10000
    }
    
    cost = shred_costs.get(shred_type, 500)
    
    if user.points < cost:
        return jsonify({
            'error': f'Insufficient points for {shred_type} shredding! Need {cost} points'
        }), 400
    
    # Deduct points
    user.points -= cost
    
    # Get shredding details
    shred_details = get_shred_details(shred_type)
    
    # "Shred" some data
    data_to_shred = DataSold.query.filter_by(user_id=user_id).limit(5).all()
    shredded_count = 0
    
    for item in data_to_shred:
        if not item.data_value.startswith('SHREDDED:'):
            item.data_value = f'SHREDDED:{shred_type.upper()}'
            shredded_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'shredded_count': shredded_count,
        'shred_type': shred_type,
        'message': shred_details['message'],
        'passes': shred_details['passes'],
        'special_effects': shred_details['effects']
    })

@theater_bp.route('/api/theater/threat_level', methods=['GET'])
def get_threat_level():
    """Get current "threat level" """
    threat_levels = [
        {'level': 'RAINBOW UNICORN', 'color': '#FF69B4', 'severity': 1},
        {'level': 'DOUBLE RAINBOW', 'color': '#FF1493', 'severity': 2},
        {'level': 'NEON PINK', 'color': '#FF00FF', 'severity': 3},
        {'level': 'GLITTER BOMB', 'color': '#FFD700', 'severity': 4},
        {'level': 'JAZZ HANDS', 'color': '#00CED1', 'severity': 5},
        {'level': 'DISCO INFERNO', 'color': '#FF4500', 'severity': 6},
        {'level': 'PLAID ALERT', 'color': '#8B4513', 'severity': 7},
        {'level': 'PAISLEY PANIC', 'color': '#9370DB', 'severity': 8},
        {'level': 'COSMIC HORROR', 'color': '#4B0082', 'severity': 9},
        {'level': 'BEIGE NIGHTMARE', 'color': '#F5F5DC', 'severity': 10}
    ]
    
    current_threat = random.choice(threat_levels)
    
    return jsonify({
        'success': True,
        'threat_level': current_threat,
        'recommended_action': get_threat_recommendation(current_threat['severity'])
    })

# Helper functions

def generate_theatrical_elements(level):
    """Generate theatrical elements based on encryption level"""
    elements = {
        'basic': [
            'Applied ROT13 (just kidding)',
            'Added blockchain dust',
            'Sprinkled with cyber-salt'
        ],
        'premium': [
            'Double-encrypted for safety',
            'Blessed by cyber-monks',
            'Wrapped in digital silk'
        ],
        'paranoid': [
            'Wrapped in digital tin foil',
            'Hidden from government satellites',
            '5G-proof coating applied',
            'Illuminati-resistant layer added'
        ],
        'tinfoil': [
            'Compressed with anxiety',
            'Encrypted with conspiracy theories',
            'Chemtrail-resistant layer added',
            'Flat-earth approved encryption'
        ],
        'quantum': [
            'Quantum entangled with parallel universe',
            'Schrödinger\'s encryption applied',
            'Observed by quantum cats',
            'Superposition achieved'
        ],
        'alien': [
            'Applied Area 51 technology',
            'Translated to alien language',
            'UFO cloaking activated',
            'Crop circle pattern applied'
        ],
        'eldritch': [
            'C̸͎̈ť̶̰h̷̺̎u̸̮̇l̴̰̈h̴̬̆ṳ̶̈ ̷͇̈́f̸̱̈h̶̺̄t̶̜̔ä̶́ͅg̷̱̈ñ̶̬',
            'Reality.exe has stopped responding',
            'S̵̱̈́a̷̤̐n̶̜̈́i̷̦̇t̸̰̄y̷̺̌ ̸̜̇c̸̣̈h̶̰̄ë̶́ͅc̷̱̈k̸̜̇ ̷̤̈f̶̰̄ä̶́ͅi̷̦̇ḷ̸̈ë̶́ͅď̷̺',
            'Tentacles deployed'
        ]
    }
    
    return elements.get(level, ['Magic happened'])

def check_achievement(user_id, level):
    """Check if user unlocked an achievement"""
    achievements = {
        'basic': 'Baby\'s First Encryption!',
        'premium': 'Premium Member!',
        'paranoid': 'They\'re Watching!',
        'tinfoil': 'Conspiracy Theorist!',
        'quantum': 'Quantum Entangled!',
        'alien': 'Area 51 Clearance!',
        'eldritch': 'M̸̰̈ä̷̤̐d̶̜̈́ṅ̷̦ḛ̸̄š̷̺ṡ̸̜ ̸̣̈Ḛ̶̄m̷̺̌ḃ̸̜r̷̤̈ā̶̰c̷̱̈ė̸̜d̷̤̈!'
    }
    
    # Simple check - in real implementation would track if first time
    if random.random() < 0.3:  # 30% chance
        return achievements.get(level)
    return None

def generate_funeral_details(funeral_type, data_count):
    """Generate funeral details based on type"""
    details = {
        'viking': {
            'epitaph': f'Here lies {data_count} pieces of data. They sail to digital Valhalla!',
            'effects': ['🔥', '⚔️', '🛡️', '⛵'],
            'guests': ['Odin', 'Thor', 'Your Viking Ancestors', 'Spam Bots']
        },
        'space': {
            'epitaph': f'{data_count} data points achieved escape velocity!',
            'effects': ['🚀', '🌟', '🌌', '👨‍🚀'],
            'guests': ['Elon Musk', 'Neil deGrasse Tyson', 'Alien Observers', 'Space Force']
        },
        'quantum': {
            'epitaph': f'Data both exists and doesn\'t exist. Schrödinger is confused.',
            'effects': ['🎲', '📊', '🔬', '❓'],
            'guests': ['Schrödinger\'s Cat', 'Werner Heisenberg', 'Quantum Physicists', 'Parallel Universe You']
        },
        'eldritch': {
            'epitaph': f'D̸a̷t̶a̷ ̸c̶o̷n̶s̷u̸m̷e̶d̸ ̷b̶y̷ ̸t̶h̷e̸ ̷v̶o̷i̶d̸',
            'effects': ['🐙', '🌀', '👁️', '🕸️'],
            'guests': ['Cthulhu', 'Nyarlathotep', 'The Old Ones', 'Your Sanity (departed)']
        }
    }
    
    return details.get(funeral_type, details['viking'])

def get_rarity_color(rarity):
    """Get color for loot box rarity"""
    colors = {
        'common': '#808080',
        'uncommon': '#00FF00',
        'rare': '#0080FF',
        'epic': '#B000B0',
        'legendary': '#FF8000',
        'mythic': '#FF0080'
    }
    return colors.get(rarity, '#FFFFFF')

def generate_quantum_signature():
    """Generate a quantum signature"""
    chars = '0123456789ABCDEF'
    signature = ''
    for _ in range(8):
        signature += ''.join(random.choices(chars, k=4)) + '-'
    return signature[:-1] + ' (QUANTUM VERIFIED)'

def get_shred_details(shred_type):
    """Get shredding details"""
    details = {
        'standard': {
            'message': 'Data overwritten with cat videos',
            'passes': 3,
            'effects': ['📄', '✂️', '🗑️']
        },
        'military': {
            'message': 'Data destroyed with military precision',
            'passes': 7,
            'effects': ['💣', '🔥', '💥']
        },
        'nuclear': {
            'message': 'Data atomized at the molecular level',
            'passes': 35,
            'effects': ['☢️', '💥', '🔥']
        },
        'blackhole': {
            'message': 'Data consumed by artificial black hole',
            'passes': 999,
            'effects': ['🕳️', '🌌', '🌀']
        }
    }
    return details.get(shred_type, details['standard'])

def get_threat_recommendation(severity):
    """Get recommendation based on threat level"""
    recommendations = {
        1: 'No action needed. Pet a unicorn.',
        2: 'Consider wearing sunglasses indoors.',
        3: 'Apply glitter-resistant coating.',
        4: 'Jazz hands defense protocol activated.',
        5: 'Disco ball deflection shields up.',
        6: 'Switch to plaid camouflage.',
        7: 'Paisley pattern scrambler engaged.',
        8: 'Cosmic horror insurance recommended.',
        9: 'Reality anchor deployment suggested.',
        10: 'PANIC! Then have some beige tea.'
    }
    return recommendations.get(severity, 'Run in circles screaming.')