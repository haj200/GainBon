from datetime import datetime
from models.new_BDC import new_BDC
from models.temp_BDC import temp_BDC
from models.user import Favouris, Notification
from __init__ import db


def extract_expired_bdcs(new_bdcs):
    """Retourne tuple : (liste des new_BDC expirés, liste des temp_BDC correspondants)"""
    expired_new_bdcs = []
    expired_temp_bdcs = []

    for bdc in new_bdcs:
        if bdc.date_limite and bdc.date_limite < datetime.utcnow():
            expired_new_bdcs.append(bdc)
            temp = temp_BDC(
                reference=bdc.reference,
                nature=bdc.nature,
                objet=bdc.objet,
                acheteur=bdc.acheteur,
                lieu=bdc.lieu,
                date_limite_str=bdc.date_limite_str,
                date_limite=bdc.date_limite,
                date_mise_en_ligne_str=bdc.date_mise_en_ligne_str,
                date_mise_en_ligne=bdc.date_mise_en_ligne,
                categorie=bdc.categorie,
                articles=bdc.articles
            )
            expired_temp_bdcs.append(temp)

    return expired_new_bdcs, expired_temp_bdcs


def update_favoris_and_generate_alerts(new_bdcs, favoris_list):
    notifications = []
    now = datetime.utcnow()
    bdc_map = {bdc.id: bdc for bdc in new_bdcs}

    for fav in favoris_list:
        if fav.expired:
            continue

        bdc = bdc_map.get(fav.bon_id)
        if not bdc or not bdc.date_limite:
            continue

        jours_restants = (bdc.date_limite - now).days

        if jours_restants < 0:
            fav.expired = True
        elif 0 <= jours_restants <= 3:
            if jours_restants == 0:
                contenu_msg = f"Le bon de commande {bdc.reference} expire aujourd'hui."
                fav.expired = True
            else:
                contenu_msg = f"Le bon de commande {bdc.reference} expire dans {jours_restants} jour(s)."

            notif = Notification(
                is_new=True,
                is_read=False,
                type='alerte',
                contenu=contenu_msg,
                temps_restant_jours=jours_restants,
                date=now,
                bon_id=bdc.id,
                user_id=fav.user_id
            )
            notifications.append(notif)

    for notif in notifications:
        db.session.add(notif)
    db.session.commit()

    return notifications, favoris_list
