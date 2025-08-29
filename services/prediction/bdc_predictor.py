import json
from pathlib import Path
import re
import unicodedata

from .text_utils import extract_keywords, build_full_text
from .format_utils import interval_to_float, format_montant_str
from .natures_loader import load_natures_map

# === Paramètres ===
RESULTS_DIR = "C:/Users/pc/Desktop/site/services/prediction/mot_clefs"

def normalize_nature(text):
    if not text:
        return ""

    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'").replace("ʼ", "'")
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r"[-,;:.!?()/]", " ", text)
    text = text.replace("'", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def predict_bdc_montant(bdc):
    """
    Prédit le montant d'un BDC en analysant ses mots-clés et en les comparant
    avec les données d'entraînement stockées par nature et intervalle de prix.
    """
    try:
        if not bdc or not getattr(bdc, "nature", None):
            print("❌ BDC invalide ou nature manquante.")
            return bdc

        print(f"\n📌 Prédiction montant pour BDC ID={getattr(bdc, 'id', 'inconnu')} "
              f"Réf='{getattr(bdc, 'reference', '')}' Nature='{bdc.nature}'")

        # Charger mapping des natures
        try:
            natures_map = load_natures_map()
        except Exception as e:
            print(f"💥 Erreur lors du chargement de natures_map: {e}")
            return bdc

        nature = normalize_nature(bdc.nature) or ""
        nature_id = natures_map.get(nature, {}).get("id", None)

        if not nature_id:
            print(f"❌ Nature inconnue : '{bdc.nature}' (normalisée: '{nature}')")
            return bdc

        # Charger fichier des mots-clés
        nature_file = Path(RESULTS_DIR) / f"data_nature_{nature_id}.json"
        if not nature_file.exists():
            print(f"❌ Fichier introuvable : {nature_file}")
            return bdc

        try:
            with open(nature_file, "r", encoding="utf-8") as f:
                intervals_keywords = json.load(f)
        except json.JSONDecodeError as e:
            print(f"💥 Erreur JSON dans {nature_file}: {e}")
            return bdc
        except Exception as e:
            print(f"💥 Erreur ouverture {nature_file}: {e}")
            return bdc

        # Construire texte et extraire mots-clés
        try:
            full_text = build_full_text(bdc)
            keywords = extract_keywords(full_text)
            print(f"🔑 {len(keywords)} mots-clés extraits.")
        except Exception as e:
            print(f"💥 Erreur extraction mots-clés: {e}")
            keywords = set()

        # Trouver intervalle le plus proche
        best_interval, max_overlap = None, 0
        for interval, kws in intervals_keywords.items():
            overlap = len(keywords & set(kws))
            if overlap > max_overlap:
                max_overlap = overlap
                best_interval = interval

        if not best_interval:
            print(f"❌ Aucun intervalle trouvé pour BDC '{getattr(bdc, 'reference', '')}'")
            return bdc

        # Calculer montant
        try:
            predicted_amount = interval_to_float(best_interval)
            predicted_str = format_montant_str(predicted_amount)
        except Exception as e:
            print(f"💥 Erreur calcul montant: {e}")
            return bdc

        # Mise à jour BDC
        bdc.montant = predicted_amount
        bdc.montant_str = predicted_str
        bdc.intervalle_prevision = best_interval

        print(f"✅ Intervalle retenu: {best_interval} | Montant estimé: {predicted_str} "
              f"(overlap={max_overlap})")

        return bdc

    except Exception as e:
        print(f"💥 Erreur critique dans predict_bdc_montant: {e}")
        return bdc
