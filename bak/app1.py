from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
import traceback
import random
import time

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gongle.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    current_page = db.Column(db.Integer, default=1)
    last_login = db.Column(db.DateTime)

class DataSold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    data_type = db.Column(db.String(50))
    data_value = db.Column(db.String(500))
    points = db.Column(db.Integer)

class Bonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    page = db.Column(db.String(50))
    points = db.Column(db.Integer)

class SessionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    session_start = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # In seconds
    pages_visited = db.Column(db.String(500))

# Create tables
try:
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
except Exception as e:
    print(f"Error creating database: {str(e)}")

@app.route('/')
def index():
    print("Serving index.html")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/create_account', methods=['POST'])
def create_account():
    try:
        data = request.json
        email = data.get('email')
        print(f"Received create_account request with email: {email}")

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            return jsonify({'success': True, 'message': 'Logged in', 'current_page': user.current_page})

        new_user = User(email=email, points=0, current_page=1)
        db.session.add(new_user)
        db.session.commit()
        print(f"Created new user with email: {email}")

        session['user_id'] = new_user.id
        data_sold = DataSold(user_id=new_user.id, data_type='email', data_value=email, points=50)
        new_user.points += 50
        db.session.add(data_sold)
        db.session.commit()
        print("Awarded 50 points for email")

        return jsonify({'success': True, 'message': 'Account created', 'current_page': new_user.current_page})
    except Exception as e:
        print(f"Error in create_account: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/sell', methods=['POST'])
def sell_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        user_id = session['user_id']
        data = request.json
        type = data.get('type')
        value = data.get('value')

        if DataSold.query.filter_by(user_id=user_id, data_type=type).first():
            return jsonify({'error': 'You already sold that, greedy!'}), 400

        points_map = {
            'ip_address': 10, 'browser': 5, 'location': 20, 'favorite_food': 60, 'favorite_movie': 70,
            'phone_number': 100, 'twitter_handle': 80, 'instagram_username': 85,
            'credit_card_last4': 200, 'medical_conditions': 500, 'week_location': 500,
            'ssn_full': 10000, 'dna_results': 1000, 'bank_account': 3000,
            'first_pet': 2000, 'mothers_maiden': 2500, 'street_grew_up': 3000,
            'childhood_friend': 3500, 'mothers_birthday': 4000, 'favorite_teacher': 4500,
            'city_born': 5000, 'mothers_city_born': 5000,
            'facebook_name': 1000, 'youtube_channel': 1000, 'fb_messenger': 1200,
            'whatsapp': 1200, 'telegram': 1200, 'tiktok': 1500, 'discord': 1500,
            'gender': 50, 'marital_status': 75, 'occupation': 100, 'education_level': 75,
            'nationality': 50, 'passport_number': 500, 'driver_license_number': 500,
            'reddit': 100, 'linkedin': 120, 'snapchat': 80,
            'full_credit_card_number': 5000, 'credit_card_expiry_date': 2500, 'credit_card_cvv': 7500,
            'bank_account_sort_code': 3500, 'paypal_email': 150, 'crypto_wallet_address': 300,
            'annual_income': 250, 'credit_score': 500, 'investment_portfolio': 1000,
            'favorite_book': 70, 'hobbies': 80, 'political_affiliation': 1850,
            'religious_beliefs': 1650, 'sexual_orientation': 2000, 'dating_preferences': 750,
            'shopping_habits': 100, 'travel_history': 200,
            'blood_type': 400, 'allergies': 350, 'insurance_provider': 150,
            'prescription_medications': 450, 'vaccination_records': 300,
            'mental_health_history': 4000, 'home_location': 500, 'work_location': 2500,
            'favorite_hangout_spots': 250, 'travel_destinations': 100,
            'favorite_childhood_memory': 50, 'pet_name': 50, 'favorite_sport': 50,
            'favorite_date_activity': 50, 'favorite_school_subject': 50,
            'favorite_sex_position': 1000, 'favorite_jolly_rancher_color': 1000,
            'current_video_game_addiction': 1000
        }

        if type == 'ip_address':
            value = request.remote_addr

        data_sold = DataSold(user_id=user_id, data_type=type, data_value=value, points=points_map.get(type, 0))
        user = User.query.get(user_id)
        user.points += points_map.get(type, 0)
        db.session.add(data_sold)
        db.session.commit()

        # Handle travel_destinations as a list
        if type == 'travel_destinations':
            try:
                destinations = value.split(',')
                user.points += points_map.get(type, 0) * len(destinations)
                for dest in destinations:
                    if dest.strip():
                        db.session.add(DataSold(user_id=user_id, data_type=type, data_value=dest.strip(), points=100))
                db.session.commit()
            except:
                pass

        return jsonify({'success': True, 'points': user.points})
    except Exception as e:
        print(f"Error in sell_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/claim_bonus', methods=['POST'])
def claim_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        user_id = session['user_id']
        data = request.json
        page = data.get('page')
        points = data.get('points')

        if Bonus.query.filter_by(user_id=user_id, page=page).first():
            return jsonify({'error': 'Bonus already claimed'}), 400

        user = User.query.get(user_id)
        user.points += points
        if page != 'page6':  # Updated to handle Page 6
            user.current_page += 1
        bonus = Bonus(user_id=user_id, page=page, points=points)
        db.session.add(bonus)
        db.session.commit()

        return jsonify({'success': True, 'points': user.points})
    except Exception as e:
        print(f"Error in claim_bonus: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/social_bonus', methods=['POST'])
def social_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        user_id = session['user_id']
        data = request.json
        page = data.get('page')
        points = data.get('points')

        user = User.query.get(user_id)
        user.points += points
        db.session.commit()

        return jsonify({'success': True, 'points': user.points})
    except Exception as e:
        print(f"Error in social_bonus: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/daily_bonus', methods=['POST'])
def daily_bonus():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        user_id = session['user_id']
        user = User.query.get(user_id)
        now = datetime.utcnow()

        if user.last_login and (now - user.last_login).days < 1:
            return jsonify({'success': True, 'points': user.points, 'points_added': 0})

        ip = request.remote_addr
        if not DataSold.query.filter_by(user_id=user_id, data_type='daily_ip').first():
            data_sold = DataSold(user_id=user_id, data_type='daily_ip', data_value=ip, points=100)
            user.points += 100
            db.session.add(data_sold)

        user.last_login = now
        db.session.commit()
        return jsonify({'success': True, 'points': user.points, 'points_added': 100})
    except Exception as e:
        print(f"Error in daily_bonus: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/session_data', methods=['POST'])
def session_data():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        user_id = session['user_id']
        data = request.json
        duration = data.get('duration')
        pages_visited = data.get('pages_visited')

        session_data = SessionData(user_id=user_id, session_start=datetime.utcnow(), duration=duration, pages_visited=pages_visited)
        db.session.add(session_data)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in session_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/leaderboard')
def leaderboard():
    try:
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
                    socials[data.data_type] = data.data_value
            result.append({'name': user.email, 'points': user.points, 'socials': socials})

        # Add fake bot users
        bot_names = ['BotMaster3000', 'DataHoarderX', 'PointKing999', 'ShadowCollector']
        for bot in bot_names:
            result.append({'name': bot, 'points': random.randint(50000, 100000), 'socials': {}})

        return jsonify(sorted(result, key=lambda x: x['points'], reverse=True)[:10])
    except Exception as e:
        print(f"Error in leaderboard: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)