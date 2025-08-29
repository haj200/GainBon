from __init__ import db
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import Enum
from sqlalchemy.ext.mutable import MutableList

#user class
class User(db.Model, UserMixin):
    #auth info
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(10000), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    #client informations
    ville = db.Column(db.String(80), nullable=True)
    nom = db.Column(db.String(80), nullable=True)
    prenom = db.Column(db.String(80), nullable=True)
    telephone = db.Column(db.String(80), nullable=True, unique=True)
    adresse = db.Column(db.String(80), nullable=True)
    profession = db.Column(db.String(80), nullable=True)
    sexe = db.Column(Enum('homme', 'femme', 'autre', name='sexe_enum'), nullable=True)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    preferences_user = db.Column(JSONB, nullable=True, default=dict)    # Renseignées par l'utilisateur
    """
    example
            {
        "favourites_natures_de prestation": [1, 100],
        "favourite_cities": ["Casablanca", "Rabat"]
        "favourite_prices": [moyen, haut],
        "favourites_categories": ["Fournitures", "Services"]
        }
     """ 
    favouris = db.relationship('Favouris')
    notifications = db.relationship('Notification')
    def is_admin(self):
            """Vérifie si l'utilisateur est admin"""
            return self.role == 'admin'

    def is_profile_complete(self):
            """Vérifie si le profil utilisateur est complet"""
            if self.is_admin():
                return True
            champs = [self.nom, self.prenom, self.ville, self.telephone, self.adresse, self.profession, self.sexe]
            prefs = self.preferences_user or {}
            fav_natures = prefs.get("favourites_natures_de_prestation", [])
            fav_cities = prefs.get("favourite_cities", [])
            fav_prices = prefs.get("favourite_prices", [])
            fav_categories = prefs.get("favourites_categories", [])
            return all(champs) and fav_natures and fav_cities and fav_prices and fav_categories
        
class Favouris(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    defined_by_user = db.Column(db.Boolean, default=False, nullable=True)
    expired = db.Column(db.Boolean, default=False, nullable=True)
    bon_id = db.Column(db.Integer)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    is_new = db.Column(db.Boolean, default=False, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=True)
    type = db.Column(Enum('alerte', 'info', 'suggestion', name='notification_enum'), default= 'info', nullable=True)
    contenu = db.Column(db.Text)
    temps_restant_jours = db.Column(db.Integer)
    date = db.Column(db.DateTime)
    bon_id = db.Column(db.Integer)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    nbr_de_fois = db.Column(db.Integer)
    bon_id = db.Column(db.Integer)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
         
    