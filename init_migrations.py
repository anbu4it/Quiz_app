"""
Initialize Flask-Migrate for database migrations.
Run this script once to set up migrations for your project.
"""
import os
import sys

# Ensure we can import from the parent directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from flask_migrate import init, migrate, upgrade

def initialize_migrations():
    """Initialize migration repository and create initial migration."""
    with app.app_context():
        print("🔧 Initializing Flask-Migrate...")
        
        # Check if migrations folder already exists
        if os.path.exists('migrations'):
            print("⚠️  Migrations folder already exists. Skipping init.")
        else:
            print("📁 Creating migrations folder...")
            os.system('flask db init')
        
        print("\n📝 Creating initial migration...")
        os.system('flask db migrate -m "Initial migration"')
        
        print("\n✅ Applying migration to database...")
        os.system('flask db upgrade')
        
        print("\n🎉 Migration setup complete!")
        print("\nNext steps:")
        print("1. For production, set DATABASE_URL environment variable")
        print("2. Run 'flask db upgrade' in your production environment")

if __name__ == "__main__":
    initialize_migrations()
