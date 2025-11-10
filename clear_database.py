"""
Clear all data from the database (delete all users and scores).
Use this to reset your database to a clean state.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from models import db, User, Score

def clear_all_data():
    """Delete all users and scores from the database."""
    with app.app_context():
        try:
            # Delete all scores first (because of foreign key constraint)
            num_scores = Score.query.delete()
            
            # Delete all users
            num_users = User.query.delete()
            
            # Commit the changes
            db.session.commit()
            
            print(f"✅ Successfully cleared database:")
            print(f"   - Deleted {num_scores} score(s)")
            print(f"   - Deleted {num_users} user(s)")
            print(f"\n🎉 Database is now empty and ready for fresh data!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {e}")

if __name__ == "__main__":
    response = input("⚠️  This will delete ALL users and scores. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        clear_all_data()
    else:
        print("❌ Operation cancelled.")
