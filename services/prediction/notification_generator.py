from datetime import datetime
from models.user import Notification
from .format_utils import prix_label

def generer_notifications_suggestions(new_bdcs, users, natures):
    """
    Génère des notifications de suggestions pour les utilisateurs basées sur
    leurs préférences et les nouveaux BDC disponibles.
    """
    try:
        if not new_bdcs:
            print("⚠️ Aucun nouveau BDC à analyser.")
            return []

        if not users:
            print("⚠️ Aucun utilisateur à notifier.")
            return []

        # Création mapping natures
        try:
            nature_mapping = {n.id: n.nom for n in natures}
            print(f"📄 {len(nature_mapping)} natures chargées.")
        except Exception as e:
            print(f"💥 Erreur création mapping natures : {e}")
            return []

        notifications = []

        for user in users:
            try:
                prefs = user.preferences_user or {}
                print(f"\n👤 Utilisateur {user.id} — analyse des préférences...")

                # Préférences utilisateur (normalisées en minuscule)
                pref_nature_ids = prefs.get("favourites_natures_de_prestation", [])
                pref_natures_text = [
                    nature_mapping.get(nid, "").lower()
                    for nid in pref_nature_ids
                    if nid in nature_mapping
                ]
                pref_cats = [c.lower() for c in prefs.get("favourites_categories", [])]
                pref_cities = [c.lower() for c in prefs.get("favourite_cities", [])]
                pref_prices = [p.lower() for p in prefs.get("favourite_prices", [])]

                print(f"   📌 Natures préférées: {pref_natures_text}")
                print(f"   📌 Catégories préférées: {pref_cats}")
                print(f"   📌 Villes préférées: {pref_cities}")
                print(f"   📌 Gammes de prix préférées: {pref_prices}")

                # Fonction de scoring
                def score_bdc(bdc):
                    score = 0
                    raisons = []

                    if bdc.nature and bdc.nature.lower() in pref_natures_text:
                        score += 1
                        raisons.append("Nature")
                    if bdc.categorie and bdc.categorie.lower() in pref_cats:
                        score += 1
                        raisons.append("Catégorie")
                    if bdc.lieu and bdc.lieu.lower() in pref_cities:
                        score += 1
                        raisons.append("Ville")
                    if bdc.montant and any(price in pref_prices for price in prix_label(bdc.montant)):
                        score += 1
                        raisons.append("Prix")

                    return score, raisons

                # Filtrer et trier les BDC
                scored_bdcs = []
                for bdc in new_bdcs:
                    score, raisons = score_bdc(bdc)
                    if score > 0:
                        scored_bdcs.append((bdc, score, raisons))

                scored_bdcs.sort(key=lambda x: x[1], reverse=True)

                print(f"   🔍 {len(scored_bdcs)} BDC correspondent aux préférences.")

                # Limite à 5 BDC
                for bdc, score, raisons in scored_bdcs[:5]:
                    print(f"      ➕ BDC {bdc.id} retenu (score={score}, raisons={raisons})")
                    notif = Notification(
                        type="suggestion",
                        date=datetime.utcnow(),
                        contenu="Vous pouvez être intéressé(e) par ce bon de commande aligné avec vos préférences",
                        bon_id=bdc.id,
                        user_id=user.id,
                        is_new=True,
                        is_read=False
                    )
                    notifications.append(notif)

            except Exception as e:
                print(f"💥 Erreur traitement utilisateur {getattr(user, 'id', 'inconnu')}: {e}")

        print(f"\n✅ {len(notifications)} notifications générées au total.")
        return notifications

    except Exception as e:
        print(f"💥 Erreur critique dans generer_notifications_suggestions: {e}")
        return []
