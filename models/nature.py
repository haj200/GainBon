from __init__ import db

class nature(db.Model):
    __tablename__ = 'nature'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Nature {self.nom}>"
