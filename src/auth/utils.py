from .models import db, User

def setup_auth_db(app):
    with app.app_context():
        db.create_all()
            
        if not User.query.filter_by(email="email@example6.com").first():
            user = User(email="email@example6.com", role="user", password="password123")
            db.session.add(user)
            
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(email="admin@example.com", role="admin", password="password123")
            db.session.add(admin)
            
        db.session.commit()