import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from string import punctuation
from nltk.corpus import stopwords

STOPWORDS = set(stopwords.words('french'))

# === PARAMÈTRES ===
INTERVALS_FILE = Path("C:/Users/pc/Desktop/site/services/prediction/intervals.json")
NATURES_FILE = Path("C:/Users/pc/Desktop/site/services/prediction/natures.jsonl")
OUTPUT_DIR = Path("C:/Users/pc/Desktop/site/services/prediction/mot_clefs")

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(rf"[{punctuation}]", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_keywords(text):
    text = normalize_text(text)
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]

def load_intervals(path):
    if not path.exists():
        print(f"❌ Fichier introuvable : {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture intervals.json : {e}")
        return []

    intervals = []
    for bloc in config:
        try:
            min_, max_, step = bloc["min"], bloc["max"], bloc["step"]
            val = min_
            while val < max_:
                intervals.append((val, val + step))
                val += step
        except KeyError as e:
            print(f"⚠️ Bloc interval invalide (clé manquante {e}) : {bloc}")
    return intervals

def get_interval(montant, intervals):
    for interval in intervals:
        if interval[0] <= montant < interval[1]:
            return f"{interval[0]}-{interval[1]}"
    return None

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

def load_natures_map():
    if not NATURES_FILE.exists():
        print(f"⚠️ Fichier natures.jsonl introuvable, création à vide.")
        return {}, set()
    natures_map = {}
    existing_ids = set()
    try:
        with open(NATURES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    name = normalize_nature(obj.get("name", ""))
                    id_ = obj.get("id")
                    if name and id_ is not None:
                        natures_map[name] = id_
                        existing_ids.add(id_)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Ligne JSON invalide dans natures.jsonl : {line.strip()} ({e})")
    except Exception as e:
        print(f"❌ Erreur lecture natures.jsonl : {e}")
    return natures_map, existing_ids

def add_nature_to_file(nature_name, new_id):
    try:
        with open(NATURES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": new_id, "name": nature_name}, ensure_ascii=False) + "\n")
        print(f"➕ Nature ajoutée : {nature_name} (ID {new_id})")
    except Exception as e:
        print(f"❌ Impossible d'ajouter la nature '{nature_name}' : {e}")

def retrain_predictive_model_from_db(old_bdc_list):
    print("🔁 Début re-entraînement du modèle prédictif...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in OUTPUT_DIR.glob("data_nature_*.jsonl"):
        try:
            f.unlink()
            print(f"🗑️ Fichier supprimé : {f}")
        except Exception as e:
            print(f"⚠️ Erreur suppression {f} : {e}")

    intervals = load_intervals(INTERVALS_FILE)
    if not intervals:
        print("❌ Aucun interval chargé, arrêt du traitement.")
        return

    nature_id_map, existing_ids = load_natures_map()
    regroupement = defaultdict(lambda: defaultdict(list))

    for bdc in old_bdc_list:
        try:
            nature = normalize_nature(getattr(bdc, "nature", "") or "")
            montant = getattr(bdc, "montant", None)
            if not nature or montant is None:
                continue

            if nature not in nature_id_map:
                new_id = max(existing_ids) + 1 if existing_ids else 1
                add_nature_to_file(getattr(bdc, "nature", "").strip(), new_id)
                nature_id_map[nature] = new_id
                existing_ids.add(new_id)

            interval = get_interval(montant, intervals)
            if not interval:
                continue

            articles_text = []
            for art in getattr(bdc, "articles", []) or []:
                titre = art.get("titre", "")
                garanties = art.get("garanties", "")
                caracteristiques = art.get("caractéristiques", "")
                articles_text.append(f"{titre} {garanties} {caracteristiques}")

            full_text = " ".join([
                str(getattr(bdc, "reference", "")),
                str(getattr(bdc, "objet", "")),
                str(getattr(bdc, "acheteur", "")),
                str(getattr(bdc, "lieu", "")),
                str(getattr(bdc, "categorie", "")),
                " ".join(articles_text)
            ]).strip()

            regroupement[nature][interval].append(full_text)

        except Exception as e:
            print(f"⚠️ Erreur traitement BDC {getattr(bdc, 'id', '?')} : {e}")

    for nature, data_by_interval in regroupement.items():
        nature_id = nature_id_map[nature]
        resultats = {}
        for interval, textes in data_by_interval.items():
            mots = set()
            for t in textes:
                mots.update(extract_keywords(t))
            if mots:
                resultats[interval] = sorted(mots)

        if resultats:
            filename = OUTPUT_DIR / f"data_nature_{nature_id}.json"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(resultats, f, ensure_ascii=False, indent=2)
                print(f"✅ Keywords enregistrés : {filename}")
            except Exception as e:
                print(f"❌ Erreur écriture {filename} : {e}")
        else:
            print(f"⚠️ Aucun mot trouvé pour {nature}")

    print("🏁 Fin de l'entraînement.\n")
