# app/create_db.py
from app import create_app, db
from app.models import User, Score, UserSet, Group, GroupMembership

app = create_app()

with app.app_context():
    print("🗑️ Dropping old tables...")
    db.drop_all()
    print("📦 Creating new tables...")
    db.create_all()
    print("✅ Database has been created/reset.")
