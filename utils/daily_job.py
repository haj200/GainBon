from models.old_BDC import old_BDC
from services.prediction.bdc_predictor import predict_bdc_montant
from services.prediction.notification_generator import generer_notifications_suggestions
from services.prediction.similarity_finder import fill_similar_bons
from services.scraper.scrap_new_BDC import scrape_today_bdc
from models.new_BDC import new_BDC
from models.user import User
from models.nature import nature
from __init__ import create_app, db  # on importe create_app pour initialiser Flask

def daily_job():
    print('Lancement du job quotidien...')

    # 1️⃣ Scraper les nouveaux BDC
    resultats = [r for r in scrape_today_bdc() if r is not None]


    # Récupérer les BDC déjà existants pour comparaison de similarité
    old_bdcs = db.session.query(old_BDC).all()

    # 2️⃣ Prédire le montant et remplir les bons similaires
    processed_results = []
    for resultat in resultats:
        if not resultat:
            continue

        bdc_with_montant = predict_bdc_montant(resultat)
        if not bdc_with_montant:
            print("⚠️ Skipping: montant prediction returned None")
            continue

        bdc_with_similars = fill_similar_bons(bdc_with_montant, old_bdcs)
        if not bdc_with_similars:
            print("⚠️ Skipping: similarity filling returned None")
            continue

        processed_results.append(bdc_with_similars)

    resultats = processed_results

    # 3️⃣ Sauvegarder les nouveaux BDC dans la base
    for bdc in resultats:
        bon = new_BDC.query.filter_by(id=bdc.id).first()
        if not bon:
            db.session.add(bdc)
        

    db.session.commit()  # commit après ajout des BDC

    # 4️⃣ Générer les suggestions (notifications)
    users = db.session.query(User).all()
    natures = db.session.query(nature).all()

    suggestions = generer_notifications_suggestions(resultats, users, natures)

    # 5️⃣ Sauvegarder les notifications dans la base
    for notif in suggestions:
        db.session.add(notif)

    db.session.commit()  # commit final après ajout des notifications

    print(f"✅ {len(resultats)} nouveaux BDC insérés")
    print(f"✅ {len(suggestions)} notifications générées")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():  # contexte nécessaire pour utiliser db
        daily_job()
