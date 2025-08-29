
from __init__ import db
from sqlalchemy.dialects.postgresql import JSONB

class old_BDC(db.Model):
    __tablename__ = 'old_bdc'
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.Text)
    nature = db.Column(db.Text)
    montant_str = db.Column(db.Text)
    montant = db.Column(db.Float)
    objet = db.Column(db.Text)
    acheteur = db.Column(db.Text)
    lieu = db.Column(db.Text)
    date_limite_str = db.Column(db.Text)
    date_limite = db.Column(db.DateTime)
    date_mise_en_ligne_str = db.Column(db.Text)
    date_mise_en_ligne = db.Column(db.DateTime)
    categorie = db.Column(db.Text)
    articles = db.Column(JSONB)
    lien_resultat = db.Column(db.Text, default = 'https://www.marchespublics.gov.ma/bdc/entreprise/consultation/resultat')

