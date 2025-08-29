from __init__ import db
from sqlalchemy.dialects.postgresql import JSONB

class new_BDC(db.Model):
    __tablename__ = 'new_bdc'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.Text)
    nature = db.Column(db.Text)
    montant_str = db.Column(db.Text, nullable=True)
    montant = db.Column(db.Float, nullable=True)
    objet = db.Column(db.Text)
    acheteur = db.Column(db.Text)
    lieu = db.Column(db.Text)
    date_limite_str = db.Column(db.Text)
    date_limite = db.Column(db.DateTime)
    date_mise_en_ligne_str = db.Column(db.Text)
    date_mise_en_ligne = db.Column(db.DateTime)
    categorie = db.Column(db.Text)
    articles = db.Column(JSONB)
    intervalle_prevision = db.Column(db.Text, nullable=True)
    bons_similaires = db.Column(JSONB, nullable=True)  # Store list of integers ids


    