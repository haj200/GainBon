from models.old_BDC import old_BDC
from services.scraper.full_scrap_for_initialization import load_natures, merge_temp_with_results
from models.nature import nature
from __init__ import create_app, db  # on importe create_app pour initialiser Flask

def initialization_job():
    print('Lancement du job d\'initialization...')

    # 1️⃣ Scraper les nouveaux BDC
    resultats = [r for r in merge_temp_with_results() if r is not None]
    natures = [n for n in load_natures() if n is not None]

    
    for bdc in resultats:
        bon = old_BDC.query.filter_by(id=bdc.id).first()
        if not bon:
            db.session.add(bdc)
        

    db.session.commit()  # commit après ajout des BDC
    for n in natures:
        natu = nature.query.filter_by(id=n.id).first()
        if not natu:
            db.session.add(n)
    
    db.session.commit()
    print(f"✅ {len(resultats)} anciens BDC insérés")
    print(f"✅ {len(natures)} natures insérés")
    


if __name__ == "__main__":
    app = create_app()
    with app.app_context():  # contexte nécessaire pour utiliser db
        initialization_job()
