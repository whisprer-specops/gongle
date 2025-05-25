from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
import traceback

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
            return jsonify({'success': True, 'message': 'Logged in'})

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

        return jsonify({'success': True, 'message': 'Account created'})
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
            'ssn_full': 10000, 'dna_results': 1000, 'bank_account': 3000
        }

        if type == 'ip_address':
            value = request.remote_addr

        data_sold = DataSold(user_id=user_id, data_type=type, data_value=value, points=points_map.get(type, 0))
        user = User.query.get(user_id)
        user.points += points_map.get(type, 0)
        db.session.add(data_sold)
        db.session.commit()

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
        if page != 'page4':
            user.current_page += 1
        bonus = Bonus(user_id=user_id, page=page, points=points)
        db.session.add(bonus)
        db.session.commit()

        return jsonify({'success': True, 'points': user.points})
    except Exception as e:
        print(f"Error in claim_bonus: {str(e)}")
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

@app.route('/api/leaderboard')
def leaderboard():
    try:
        users = User.query.order_by(User.points.desc()).limit(10).all()
        return jsonify([{'name': u.email, 'points': u.points} for u in users])
    except Exception as e:
        print(f"Error in leaderboard: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)