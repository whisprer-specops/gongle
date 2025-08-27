from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import platform
from datetime import datetime, timedelta
import traceback
import random
import time

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Fix database path for cross-platform compatibility
def get_database_path():
    """Get appropriate database path for the current platform"""
    if platform.system() == 'Windows':
        # On Windows, use the current directory or AppData
        db_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Gongle')
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, 'gongle.db')
    else:
        # On Unix-like systems, try to use a writable directory
        possible_dirs = [
            '/tmp',
            os.path.expanduser('~/tmp'),
            os.path.expanduser('~/.local/share/gongle'),
            os.getcwd()  # Fallback to current directory
        ]
        
        for dir_path in possible_dirs:
            try:
                os.makedirs(dir_path, exist_ok=True)
                test_file = os.path.join(dir_path, 'test_write.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return os.path.join(dir_path, 'gongle.db')
            except (OSError, PermissionError):
                continue
        
        # Ultimate fallback
        return os.path.join(os.getcwd(), 'gongle.db')

# Set database configuration
db_path = get_database_path()
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"🎭 Gongle Database will be created at: {db_path}")

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    current_page = db.Column(db.Integer, default=1)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DataSold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    data_type = db.Column(db.String(50))
    data_value = db.Column(db.String(500))
    points = db.Column(db.Integer)
    sold_at = db.Column(db.DateTime, default=datetime.utcnow)

class Bonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    page = db.Column(db.String(50))
    points = db.Column(db.Integer)
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)

class SessionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    session_start = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # In seconds
    pages_visited = db.Column(db.String(500))

# Create tables with proper error handling
def initialize_database():
    """Initialize the database with proper error handling"""
    try:
        with app.app_context():
            # Check if database file exists and is writable
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Create all tables
            db.create_all()
            
            print("🎉 Database tables created successfully!")
            print(f"📊 Database location: {db_path}")
            
            # Test database by creating a test query
            test_user_count = User.query.count()
            print(f"👥 Current users in database: {test_user_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating database: {str(e)}")
        print(f"🔍 Database path attempted: {db_path}")
        print(f"📝 Error details: {traceback.format_exc()}")
        return False

# Initialize database
db_initialized = initialize_database()
if not db_initialized:
    print("⚠️  Database initialization failed, but server will still start")

@app.route('/')
def index():
    print("🏠 Serving index.html")
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        return f"""
        <html>
        <head><title>Gongle - Temporary Landing</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: #4285f4;">G<span style="color: #ea4335;">o</span><span style="color: #fbbc05;">n</span><span style="color: #34a853;">g</span><span style="color: #ea4335;">l</span><span style="color: #4285f4;">e</span></h1>
            <p>🎭 Where your data goes to party before being sold!</p>
            <p style="color: #666;">Static files not found. Please create static/index.html</p>
            <p style="font-size: 12px; color: #999;">Database: {db_path}</p>
            <p style="font-size: 12px; color: #999;">Error: {str(e)}</p>
        </body>
        </html>
        """

@app.route('/api/health')
def health_check():
    """Health check endpoint to verify everything is working"""
    try:
        # Test database connection
        user_count = User.query.count()
        data_count = DataSold.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'database_path': db_path,
            'users': user_count,
            'data_sold_entries': data_count,
            'message': '🎭 Gongle Theater is operational!'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'error',
            'database_path': db_path,
            'error': str(e),
            'message': '💥 Database connection failed'
        }), 500

@app.route('/api/create_account', methods=['POST'])
def create_account():
    try:
        if not db_initialized:
            return jsonify({'error': 'Database not initialized'}), 500
            
        data = request.json
        email = data.get('email')
        print(f"📧 Received create_account request with email: {email}")

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            bonus = Bonus.query.filter_by(user_id=user.id, page=f'page{user.current_page}').first()
            if bonus and user.current_page < 6:
                user.current_page += 1
                db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Welcome back to the data circus!', 
                'current_page': user.current_page,
                'points': user.points
            })

        # Create new user
        new_user = User(email=email, points=0, current_page=1)
        db.session.add(new_user)
        db.session.commit()
        print(f"✨ Created new user with email: {email}")

        # Set session
        session['user_id'] = new_user.id
        
        # Award points for email data
        data_sold = DataSold(
            user_id=new_user.id, 
            data_type='email', 
            data_value=email, 
            points=50
        )
        new_user.points += 50
        db.session.add(data_sold)
        db.session.commit()
        print("🎯 Awarded 50 points for email submission")

        return jsonify({
            'success': True, 
            'message': 'Account created! Welcome to the data marketplace!', 
            'current_page': new_user.current_page,
            'points': new_user.points
        })
        
    except Exception as e:
        print(f"💥 Error in create_account: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/get_sold_data', methods=['GET'])
def get_sold_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        sold_data = DataSold.query.filter_by(user_id=user_id).all()
        sold_types = [data.data_type for data in sold_data]
        
        return jsonify({
            'success': True, 
            'sold_data': sold_types,
            'total_entries': len(sold_data)
        })
        
    except Exception as e:
        print(f"💥 Error in get_sold_data: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sell', methods=['POST'])
def sell_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        data = request.json
        data_type = data.get('type')
        data_value = data.get('value')

        print(f"💰 User {user_id} wants to sell: {data_type}")

        # Check if already sold
        existing = DataSold.query.filter_by(user_id=user_id, data_type=data_type).first()
        if existing:
            return jsonify({'error': 'You already sold that, greedy! 😏'}), 400

        # Auto-collect server-side data
        auto_collect_types = {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'http_accept': request.headers.get('Accept', 'Unknown'),
            'http_accept_language': request.headers.get('Accept-Language', 'Unknown'),
            'http_accept_encoding': request.headers.get('Accept-Encoding', 'Unknown'),
            'http_referer': request.headers.get('Referer', 'Unknown'),
            'proxy_x_forwarded': request.headers.get('X-Forwarded-For', 'None'),
            'proxy_via': request.headers.get('Via', 'None'),
        }

        # Points mapping - the psychological pricing of privacy!
        points_map = {
            # Basic technical data
            'ip_address': 10, 'browser': 5, 'user_agent': 5,
            'http_accept': 5, 'http_accept_language': 5, 'http_accept_encoding': 5,
            'http_referer': 10, 'proxy_x_forwarded': 15, 'proxy_via': 15,
            'browser_details': 10, 'screen_size': 10, 'plugins': 15, 'canvas_fingerprint': 20,
            
            # Personal preferences (low-medium value)
            'favorite_food': 60, 'favorite_movie': 70, 'favorite_book': 70,
            'hobbies': 80, 'favorite_sport': 50, 'favorite_school_subject': 50,
            'favorite_childhood_memory': 50, 'pet_name': 50,
            
            # Contact & Social (medium value)
            'phone_number': 100, 'location': 20,
            'twitter_handle': 80, 'instagram_username': 85, 'facebook_name': 1000,
            'youtube_channel': 1000, 'fb_messenger': 1200, 'whatsapp': 1200,
            'telegram': 1200, 'tiktok': 1500, 'discord': 1500,
            'reddit': 100, 'linkedin': 120, 'snapchat': 80,
            
            # Demographics (medium value)
            'gender': 50, 'marital_status': 75, 'occupation': 100,
            'education_level': 75, 'nationality': 50,
            
            # Beliefs & Identity (high value - controversial data)
            'political_affiliation': 1850, 'religious_beliefs': 1650,
            'sexual_orientation': 2000, 'dating_preferences': 750,
            
            # Financial (very high value)
            'credit_card_last4': 200, 'full_credit_card_number': 5000,
            'credit_card_expiry_date': 2500, 'credit_card_cvv': 7500,
            'bank_account': 3000, 'bank_account_sort_code': 3500,
            'paypal_email': 150, 'crypto_wallet_address': 300,
            'annual_income': 250, 'credit_score': 500, 'investment_portfolio': 1000,
            
            # Health & Medical (very high value)
            'medical_conditions': 500, 'blood_type': 400, 'allergies': 350,
            'insurance_provider': 150, 'prescription_medications': 450,
            'vaccination_records': 300, 'mental_health_history': 4000,
            
            # Identity Documents (extremely high value)
            'ssn_full': 10000, 'passport_number': 500, 'driver_license_number': 500,
            'dna_results': 1000,
            
            # Security Questions (very high value)
            'first_pet': 2000, 'mothers_maiden': 2500, 'street_grew_up': 3000,
            'childhood_friend': 3500, 'mothers_birthday': 4000,
            'favorite_teacher': 4500, 'city_born': 5000, 'mothers_city_born': 5000,
            
            # Location Data (high value)
            'week_location': 500, 'home_location': 500, 'work_location': 2500,
            'favorite_hangout_spots': 250, 'travel_history': 200,
            'travel_destinations': 100,
            
            # Behavioral (medium-high value)
            'shopping_habits': 100,
            
            # Fun/Weird (medium value - for engagement)
            'favorite_date_activity': 50, 'favorite_sex_position': 1000,
            'favorite_jolly_rancher_color': 1000, 'current_video_game_addiction': 1000,
            'surprise_data': 1000,
        }

        user = User.query.get(user_id)
        
        # Auto-collect server data
        for auto_type, auto_value in auto_collect_types.items():
            if not DataSold.query.filter_by(user_id=user_id, data_type=auto_type).first():
                auto_points = points_map.get(auto_type, 0)
                if auto_points > 0:
                    data_sold = DataSold(
                        user_id=user_id, 
                        data_type=auto_type, 
                        data_value=auto_value, 
                        points=auto_points
                    )
                    user.points += auto_points
                    db.session.add(data_sold)
                    print(f"🎁 Auto-collected {auto_type} for {auto_points} points")

        # Handle the requested data sale
        if data_type in auto_collect_types:
            data_value = auto_collect_types[data_type]

        points_earned = points_map.get(data_type, 10)  # Default 10 points
        
        data_sold = DataSold(
            user_id=user_id, 
            data_type=data_type, 
            data_value=data_value, 
            points=points_earned
        )
        user.points += points_earned
        db.session.add(data_sold)
        
        # Special handling for travel destinations (multiple entries)
        if data_type == 'travel_destinations' and data_value:
            try:
                destinations = [d.strip() for d in data_value.split(',') if d.strip()]
                bonus_points = 50 * (len(destinations) - 1)  # Bonus for multiple destinations
                user.points += bonus_points
                print(f"🌍 Travel bonus: {bonus_points} points for {len(destinations)} destinations")
            except:
                pass

        db.session.commit()
        print(f"✅ Sold {data_type} for {points_earned} points")

        return jsonify({
            'success': True, 
            'points': user.points,
            'points_earned': points_earned,
            'message': f'Thanks for selling your {data_type.replace("_", " ")}! 🎉'
        })
        
    except Exception as e:
        print(f"💥 Error in sell_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/collect_client_data', methods=['POST'])
def collect_client_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        data = request.json
        user = User.query.get(user_id)
        points_added = 0

        # Client-side data collection
        client_data_map = {
            'browser_details': 10,
            'screen_size': 10,
            'plugins': 15,
            'canvas_fingerprint': 20,
            'timezone': 5,
            'language': 5,
            'platform': 5
        }

        for data_key, points in client_data_map.items():
            data_value = data.get(data_key)
            if data_value and not DataSold.query.filter_by(user_id=user_id, data_type=data_key).first():
                data_sold = DataSold(
                    user_id=user_id, 
                    data_type=data_key, 
                    data_value=str(data_value), 
                    points=points
                )
                user.points += points
                points_added += points
                db.session.add(data_sold)
                print(f"🔍 Collected {data_key} for {points} points")

        db.session.commit()
        
        return jsonify({
            'success': True, 
            'points': user.points, 
            'points_added': points_added
        })
        
    except Exception as e:
        print(f"💥 Error in collect_client_data: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/leaderboard')
def leaderboard():
    try:
        # Get real users
        users = User.query.order_by(User.points.desc()).limit(10).all()
        result = []
        
        social_types = [
            'twitter_handle', 'instagram_username', 'facebook_name', 'youtube_channel',
            'fb_messenger', 'whatsapp', 'telegram', 'tiktok', 'discord', 'reddit',
            'linkedin', 'snapchat'
        ]
        
        for user in users:
            socials = {}
            for data in DataSold.query.filter_by(user_id=user.id).all():
                if data.data_type in social_types:
                    socials[data.data_type] = data.data_value[:20]  # Truncate for display
                    
            result.append({
                'name': user.email.split('@')[0] + '***',  # Partially hide email
                'points': user.points, 
                'socials': socials,
                'data_sold_count': DataSold.query.filter_by(user_id=user.id).count()
            })

        # Add some "bot" competition
        bot_names = [
            'DataHoarder_Supreme', 'PrivacyDestroyer_9000', 'InfoGoblin_X', 
            'ByteHunter_Pro', 'MetricsMonster', 'TelemetryTitan',
            'AnalyticsAnarchist', 'BigBrotherBot', 'SurveillanceSpecialist'
        ]
        
        for bot in bot_names[:3]:  # Add 3 bots
            result.append({
                'name': bot, 
                'points': random.randint(75000, 150000), 
                'socials': {'note': '[BOT]'},
                'data_sold_count': random.randint(500, 1000)
            })

        # Sort by points and return top 10
        result.sort(key=lambda x: x['points'], reverse=True)
        return jsonify(result[:10])
        
    except Exception as e:
        print(f"💥 Error in leaderboard: {str(e)}")
        return jsonify([])  # Return empty list on error

# Additional utility endpoints
@app.route('/api/user_stats')
def user_stats():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        user = User.query.get(user_id)
        data_sold = DataSold.query.filter_by(user_id=user_id).all()
        
        stats = {
            'total_points': user.points,
            'data_items_sold': len(data_sold),
            'member_since': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown',
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            'current_page': user.current_page,
            'data_categories': {}
        }
        
        # Categorize sold data
        for data in data_sold:
            category = data.data_type.split('_')[0]  # Simple categorization
            if category not in stats['data_categories']:
                stats['data_categories'][category] = 0
            stats['data_categories'][category] += 1
            
        return jsonify(stats)
        
    except Exception as e:
        print(f"💥 Error in user_stats: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Development/debug endpoints
@app.route('/api/debug/database')
def debug_database():
    """Debug endpoint to check database status"""
    try:
        return jsonify({
            'database_path': db_path,
            'database_exists': os.path.exists(db_path),
            'database_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
            'total_users': User.query.count(),
            'total_data_sold': DataSold.query.count(),
            'total_bonuses': Bonus.query.count(),
            'session_data_entries': SessionData.query.count(),
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'database_path': db_path,
            'database_exists': os.path.exists(db_path) if 'db_path' in locals() else False
        })

@app.route('/api/claim_bonus', methods=['POST'])
def claim_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        data = request.json
        page = data.get('page')
        points = data.get('points')

        print(f"🎁 User {user_id} claiming bonus for {page}: {points} points")

        # Check if bonus already claimed
        if Bonus.query.filter_by(user_id=user_id, page=page).first():
            return jsonify({'error': 'Bonus already claimed for this page'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Award bonus points
        user.points += points
        
        # Advance to next page if not final page
        if page != 'page6':
            user.current_page += 1
            
        # Record bonus claim
        bonus = Bonus(user_id=user_id, page=page, points=points)
        db.session.add(bonus)
        db.session.commit()

        print(f"✅ Bonus claimed: {points} points, new total: {user.points}")

        return jsonify({
            'success': True, 
            'points': user.points,
            'current_page': user.current_page,
            'message': f'Bonus claimed! +{points} points!'
        })
        
    except Exception as e:
        print(f"💥 Error in claim_bonus: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/session_data', methods=['POST'])
def session_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        data = request.json
        duration = data.get('duration', 0)
        pages_visited = data.get('pages_visited', '')

        print(f"📊 Session data for user {user_id}: {duration}s, pages: {pages_visited}")

        # Store session data
        session_entry = SessionData(
            user_id=user_id, 
            session_start=datetime.utcnow(), 
            duration=duration, 
            pages_visited=pages_visited
        )
        db.session.add(session_entry)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Session data recorded'})
        
    except Exception as e:
        print(f"💥 Error in session_data: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Also add this bonus route for social sharing
@app.route('/api/social_bonus', methods=['POST'])
def social_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        data = request.json
        page = data.get('page')
        points = data.get('points')

        print(f"📱 User {user_id} claiming social bonus for {page}: {points} points")

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Award social bonus points
        user.points += points
        db.session.commit()

        print(f"✅ Social bonus awarded: {points} points, new total: {user.points}")

        return jsonify({
            'success': True, 
            'points': user.points,
            'message': f'Social sharing bonus! +{points} points!'
        })
        
    except Exception as e:
        print(f"💥 Error in social_bonus: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/daily_bonus', methods=['POST'])
def daily_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        user = User.query.get(user_id)
        now = datetime.utcnow()

        # Check if user already got daily bonus today
        if user.last_login and (now - user.last_login).days < 1:
            return jsonify({
                'success': True, 
                'points': user.points, 
                'points_added': 0,
                'message': 'Daily bonus already claimed today'
            })

        # Award daily bonus
        daily_bonus_points = 100
        user.points += daily_bonus_points
        user.last_login = now

        # Also collect daily IP as data
        ip = request.remote_addr
        existing_daily_ip = DataSold.query.filter_by(user_id=user_id, data_type='daily_ip').first()
        if not existing_daily_ip:
            daily_ip_data = DataSold(
                user_id=user_id, 
                data_type='daily_ip', 
                data_value=ip, 
                points=50
            )
            user.points += 50
            db.session.add(daily_ip_data)
            daily_bonus_points += 50

        db.session.commit()

        print(f"🌅 Daily bonus awarded to user {user_id}: {daily_bonus_points} points")

        return jsonify({
            'success': True, 
            'points': user.points, 
            'points_added': daily_bonus_points,
            'message': f'Daily login bonus: {daily_bonus_points} points!'
        })
        
    except Exception as e:
        print(f"💥 Error in daily_bonus: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/theater/encrypt', methods=['POST'])
def theatrical_encrypt():
    """Theatrical encryption with maximum drama"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        data = request.json
        level = data.get('level', 'basic')
        
        # Encryption costs
        costs = {
            'basic': 1000,
            'paranoid': 5000,
            'quantum': 15000,
            'eldritch': 66666
        }
        
        cost = costs.get(level, 1000)
        user = User.query.get(user_id)
        
        if user.points < cost:
            return jsonify({
                'error': f'Insufficient points! Need {cost}, you have {user.points}'
            }), 400
        
        # Deduct points
        user.points -= cost
        
        # Generate theatrical elements
        elements = {
            'basic': ['Applied ROT13 (just kidding)', 'Added blockchain dust', 'Sprinkled with cyber-salt'],
            'paranoid': ['Wrapped in digital tin foil', 'Hidden from government satellites', '5G-proof coating applied'],
            'quantum': ['Quantum entangled with parallel universe', 'Schrödinger\'s encryption applied', 'Observed by quantum cats'],
            'eldritch': ['C̸͎̈ť̶̰h̷̺̎u̸̮̇l̴̰̈h̴̬̆ṳ̶̈ ̷͇̈́f̸̱̈h̶̺̄t̶̜̔ä̶́ͅg̷̱̈ñ̶̬', 'Reality.exe has stopped responding', 'Tentacles deployed']
        }
        
        # "Encrypt" user's data
        user_data = DataSold.query.filter_by(user_id=user_id).all()
        for data_item in user_data:
            if not data_item.data_value.startswith('ENCRYPTED:'):
                data_item.data_value = f'ENCRYPTED:{level.upper()}:{data_item.data_value[:20]}...'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Data encrypted with {level.upper()} protection!',
            'theatrical_elements': elements.get(level, ['Magic happened']),
            'points': user.points,
            'encrypted_count': len(user_data)
        })
        
    except Exception as e:
        print(f"💥 Error in theatrical_encrypt: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/theater/funeral', methods=['POST'])
def schedule_data_funeral():
    """Schedule a dramatic data funeral"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        data = request.json
        funeral_type = data.get('type', 'viking')
        
        # Funeral costs
        costs = {
            'viking': 10000,
            'space': 7500,
            'quantum': 15000,
            'eldritch': 66666
        }
        
        cost = costs.get(funeral_type, 10000)
        user = User.query.get(user_id)
        
        if user.points < cost:
            return jsonify({
                'error': f'Insufficient points for {funeral_type} funeral! Need {cost} points'
            }), 400
        
        # Deduct points
        user.points -= cost
        
        # Generate epitaphs
        epitaphs = {
            'viking': 'Your data sails to digital Valhalla! ⚔️⛵',
            'space': 'Data has achieved escape velocity! 🚀🌌',
            'quantum': 'Data both exists and doesn\'t exist. Schrödinger is confused. 🎲',
            'eldritch': 'D̸a̷t̶a̷ ̸c̶o̷n̶s̷u̸m̷e̶d̸ ̷b̶y̷ ̸t̶h̷e̸ ̷v̶o̷i̶d̸ 🐙'
        }
        
        # Store funeral record
        funeral_data = DataSold(
            user_id=user_id,
            data_type='funeral_scheduled',
            data_value=f'FUNERAL:{funeral_type.upper()}:SCHEDULED',
            points=0
        )
        db.session.add(funeral_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'epitaph': epitaphs.get(funeral_type, 'Your data has been scheduled for destruction'),
            'scheduled_time': '24 hours from now',
            'points': user.points
        })
        
    except Exception as e:
        print(f"💥 Error in schedule_data_funeral: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/theater/certificate', methods=['GET'])
def generate_certificate():
    """Generate a security certificate"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Count user's data
        data_count = DataSold.query.filter_by(user_id=user_id).count()
        
        import random
        
        certificate = {
            'user_name': user.email,
            'security_score': random.randint(900, 999),
            'encrypted_items': data_count,
            'technology': random.choice(['Alien', 'Quantum', 'Blockchain', 'AI-powered']),
            'certificate_id': f'CERT-{user_id}-{random.randint(1000, 9999)}'
        }
        
        return jsonify({
            'success': True,
            'certificate': certificate
        })
        
    except Exception as e:
        print(f"💥 Error in generate_certificate: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Add this debug endpoint to your app.py (temporary fix)

@app.route('/api/debug/reset_bonus', methods=['POST'])
def reset_bonus():
    """Debug endpoint to reset bonus state for stuck users"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        page = request.json.get('page', 'page1')
        
        # Delete existing bonus record for this page
        existing_bonus = Bonus.query.filter_by(user_id=user_id, page=page).first()
        if existing_bonus:
            db.session.delete(existing_bonus)
            db.session.commit()
            print(f"🔄 Reset bonus for user {user_id}, page {page}")
            
        return jsonify({
            'success': True, 
            'message': f'Bonus reset for {page}. You can claim it again now!'
        })
        
    except Exception as e:
        print(f"💥 Error in reset_bonus: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/debug/user_state', methods=['GET'])
def debug_user_state():
    """Debug endpoint to check current user state"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
            
        user_id = session['user_id']
        user = User.query.get(user_id)
        bonuses = Bonus.query.filter_by(user_id=user_id).all()
        sold_data = DataSold.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'user_id': user_id,
            'points': user.points,
            'current_page': user.current_page,
            'bonuses_claimed': [{'page': b.page, 'points': b.points} for b in bonuses],
            'data_sold_count': len(sold_data),
            'data_types_sold': [d.data_type for d in sold_data]
        })
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("🎭 Starting Gongle Data Theater...")
    print(f"📍 Database: {db_path}")
    print("🌐 Server starting on http://127.0.0.1:5000")
    print("💡 Visit /api/health to check if everything is working")
    print("🔍 Visit /api/debug/database for database info")
    
    app.run(debug=True, host='127.0.0.1', port=5000)