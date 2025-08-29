
from __init__ import db
from sqlalchemy.dialects.postgresql import JSONB

class result_BDC(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.Text)
    montant_str = db.Column(db.Text)
    montant = db.Column(db.Float)
    objet = db.Column(db.Text)
    acheteur = db.Column(db.Text)
    date_publication_str = db.Column(db.Text)
    date_publication = db.Column(db.DateTime)
    entreprise_attributaire = db.Column(db.Text)
    nombre_devis = db.Column(db.Text)
    lien_resultat = db.Column(db.Text)
    

