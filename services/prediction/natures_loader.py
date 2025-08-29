import json
import re
import unicodedata
# === Paramètres ===
NATURES_MAP_FILE = "C:/Users/pc/Desktop/site/services/prediction/natures.jsonl"

def normalize_nature(text):
    if not text:
        return ""

    # Minuscule
    text = text.lower()

    # Remplacer les apostrophes typographiques par des simples
    text = text.replace("’", "'").replace("‘", "'").replace("ʼ", "'")

    # Supprimer les accents
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')

    # Remplacer les caractères de ponctuation / séparation par des espaces
    text = re.sub(r"[-,;:.!?()/]", " ", text)

    # Remplacer les apostrophes restantes par rien
    text = text.replace("'", " ")

    # Remplacer les espaces multiples par un seul
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def load_natures_map():
    """
    Charge le fichier natures.jsonl et crée un mapping entre les noms
    des natures (en minuscules) et leurs objets complets.
    
    Returns:
        dict: Dictionnaire {nom_nature: objet_nature} pour accès rapide
    """
    natures_map = {}
    with open(NATURES_MAP_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            nature_obj = json.loads(line)
            name = normalize_nature(nature_obj.get("name", ""))
            if name:
                natures_map[name] = nature_obj
    return natures_map
