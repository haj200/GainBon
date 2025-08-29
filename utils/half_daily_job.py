from __init__ import create_app, db
from models.new_BDC import new_BDC
from models.user import Favouris
from services.updates.new_bdc_to_temp_bdc import extract_expired_bdcs, update_favoris_and_generate_alerts

def half_daily_job():
    app = create_app()
    with app.app_context():
        new_bdcs = db.session.query(new_BDC).all()
        print(f"Total new BDCs en base: {len(new_bdcs)}")

        # Extraction BDC expirés (liste de new_BDC + liste temp_BDC)
        expired_new_bdcs, expired_temp_bdcs = extract_expired_bdcs(new_bdcs)
        print(f"Nombre de BDC expirés extraits: {len(expired_new_bdcs)}")

        for b in expired_new_bdcs:
            print(f"  - {b.reference} expiré le {b.date_limite}")

        # Supprimer les BDC expirés de new_bdc
        for b in expired_new_bdcs:
            db.session.delete(b)

        # Ajouter les BDC expirés dans temp_bdc
        for temp_bdc in expired_temp_bdcs:
            db.session.add(temp_bdc)

        db.session.commit()  # Commit suppression + insertion

        # Recharger la liste de new_bdcs (actualisée)
        new_bdcs = db.session.query(new_BDC).all()

        favoris_list = db.session.query(Favouris).all()
        print(f"Total favoris en base: {len(favoris_list)}")

        notifications, favoris_updated = update_favoris_and_generate_alerts(new_bdcs, favoris_list)
        print(f"Notifications générées: {len(notifications)}")

        # Mettre à jour les favoris expirés dans la base
        for fav in favoris_updated:
            db.session.add(fav)

        db.session.commit()

        print("Job terminé avec succès.")

if __name__ == "__main__":
    half_daily_job()