from datetime import datetime
from __init__ import create_app, db
from models.new_BDC import new_BDC
from models.temp_BDC import temp_BDC
from models.user import Favouris
from models.result_BDC import result_BDC
from services.scraper.scrap_results import clean, create_notifications_for_expired_favoris_with_results, merge_temp_with_results
from services.updates.new_bdc_to_temp_bdc import extract_expired_bdcs, update_favoris_and_generate_alerts

def test_merge_and_notifications():
    app = create_app()
    with app.app_context():
        temp_bdcs = db.session.query(temp_BDC).all()
        favoris_list = db.session.query(Favouris).all()
        old_resultats = db.session.query(result_BDC).all()
        # 1. Fusionner temp_bdc avec résultats
        old_bdcs_matched, non_matched_ids, results = merge_temp_with_results(temp_bdcs,old_resultats, datetime.now())
        print(f"BDCs fusionnés (old_bdcs) : {len(old_bdcs_matched)}")
        print(f"Temp_BDC non fusionnés (ids) : {non_matched_ids}")

        # --- SUPPRESSION des temp_bdc fusionnés ---
        for old in old_bdcs_matched:
            temp_bdc = temp_BDC.query.filter_by(id=old.id).first()
            print(f"Suppression temp_BDC id={temp_bdc.id} ref={temp_bdc.reference}")
            db.session.delete(temp_bdc)

        for re in results:
            db.session.add(re)

        

        # --- INSERTION des bons fusionnés dans old_bdc ---
        for old in old_bdcs_matched:
            db.session.add(old)

        db.session.commit()
        print(f"Suppression et insertion commités en base.")

        # 2. Création notifications pour favoris expirés avec résultats publiés
        notifications = create_notifications_for_expired_favoris_with_results(old_bdcs_matched, temp_bdcs, favoris_list)
        print(f"Notifications créées : {len(notifications)}")

        for notif in notifications:
            print(f"- Utilisateur {notif.user_id} : {notif.contenu}")

        for notif in notifications:
            db.session.add(notif)
        db.session.commit()
        print("Notifications insérées en base avec succès.")


if __name__ == "__main__":
    test_merge_and_notifications()