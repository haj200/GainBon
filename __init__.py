from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    
    # --- Configuration ---
    app.config['SECRET_KEY'] = 'scjmkdntln trpoytkfdp'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:12345678@localhost:5432/bdc'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Avoids warnings

    # --- Init DB ---
    db.init_app(app)

    # --- Blueprints ---
    from routes.auth import auth
    from routes.bdc import bdc
    from routes.notif import notif_bp
    from routes.explore import main
    from routes.recherche import search
    from routes.favouris import favouris
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(bdc, url_prefix='/bdc')
    app.register_blueprint(notif_bp, url_prefix='/notif')
    app.register_blueprint(main, url_prefix='/main')
    app.register_blueprint(search, url_prefix='/search')
    app.register_blueprint(favouris, url_prefix='/favouris')


    # --- Login manager ---
    from models.user import User
    login_manager = LoginManager()
    login_manager.login_message = "S'il vous plaît connectez-vous, notre plateforme n'est plus la même sans vous"
    login_manager.login_view = 'auth.sign_up'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Optional: Reset database ---
    with app.app_context():
        from models.user import User
        from models.new_BDC import new_BDC
        from models.old_BDC import old_BDC
        from models.result_BDC import result_BDC
        from models.temp_BDC import temp_BDC
        from models.nature import nature
        from models.user import Consultation
        
        # db.drop_all()
        # db.create_all()
        # print("✅ Toutes les tables ont été supprimées et recréées.")

    return app
