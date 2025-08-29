from services.prediction.bdc_predictor import normalize_nature
from .text_utils import extract_keywords, build_full_text

def fill_similar_bons(bdc, old_bdcs):
    """
    Remplit bdc.bons_similaires avec les IDs des 20 anciens bons similaires les plus proches,
    triés par ordre décroissant de similarité basée sur les mots-clés communs.
    """
    try:
        if not bdc:
            print("❌ Erreur : bdc est vide ou None.")
            return None

        if not old_bdcs:
            print(f"⚠️ Aucun ancien bon fourni pour comparaison avec {getattr(bdc, 'id', 'inconnu')}.")
            bdc.bons_similaires = []
            return bdc

        print(f"\n📌 Traitement du BDC ID={getattr(bdc, 'id', 'inconnu')} "
              f"Nature='{bdc.nature}' Catégorie='{bdc.categorie}'")

        # Extraction mots-clés BDC principal
        try:
            bdc_keywords = extract_keywords(build_full_text(bdc))
            print(f"🔑 Mots-clés BDC ({len(bdc_keywords)}): {list(bdc_keywords)[:10]}{'...' if len(bdc_keywords) > 10 else ''}")
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction des mots-clés du BDC: {e}")
            bdc_keywords = set()

        similars = []
        for old in old_bdcs:
            try:
                same_nature = normalize_nature(old.nature) == normalize_nature(bdc.nature)
                same_categorie = (old.categorie or "").strip().lower() == (bdc.categorie or "").strip().lower()

                if not same_nature or not same_categorie:
                    continue

                old_keywords = extract_keywords(build_full_text(old))
                intersection = bdc_keywords & old_keywords
                score = len(intersection) / len(bdc_keywords) if bdc_keywords else 0

                if score > 0:
                    similars.append((old.id, score))

            except Exception as e:
                print(f"⚠️ Erreur sur ancien BDC ID={getattr(old, 'id', 'inconnu')}: {e}")

        # Trier par score décroissant
        similars.sort(key=lambda x: x[1], reverse=True)
        print(f"📊 {len(similars)} bons similaires trouvés avant limitation.")

        # Garder seulement les 20 premiers
        top_similars = similars[:20]

        # Remplir bons_similaires avec uniquement les IDs
        bdc.bons_similaires = [sid for sid, _ in top_similars]
        print(f"✅ Bons similaires sélectionnés (IDs): {bdc.bons_similaires}")

        return bdc

    except Exception as e:
        print(f"💥 Erreur critique dans fill_similar_bons: {e}")
        return bdc
