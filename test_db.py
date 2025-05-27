import sys
sys.path.insert(0, '/app/gongle-web')

print("Testing database configuration...")

try:
    from app import app
    print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')}")
    print(f"All config keys: {list(app.config.keys())}")
except Exception as e:
    print(f"Error importing app: {e}")

try:
    from app import db
    print("Database object imported successfully")
except Exception as e:
    print(f"Error importing db: {e}")
