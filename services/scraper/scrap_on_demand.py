import json
import re
from string import punctuation
from datetime import datetime
from models.new_BDC import new_BDC 
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time 
from urllib.parse import urlparse
from typing import List



# Configuration
BASE_URL = "https://www.marchespublics.gov.ma"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
TIMEOUT = 10
MAX_RETRIES = 3

def parse_date(date_str):
    """Convertit une date du format 'DD/MM/YYYY HH:MM' en datetime"""
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None

def normalize_text(text):
    """Nettoie et normalise un texte sans supprimer les accents ni les apostrophes"""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    punctuation_without_apostrophe = punctuation.replace("'", "")
    text = re.sub(rf"[{re.escape(punctuation_without_apostrophe)}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_field(d, key):
    """Gère les variations de clés avec accents ou casse"""
    for k in d:
        if k.lower().replace("é", "e").replace("è", "e") == key.lower().replace("é", "e").replace("è", "e"):
            return d[k]
    return ""
def create_new_bdc_from_json_line(line: str):
    """Prend une ligne JSON et retourne un objet new_BDC avec montant = None"""
    data = json.loads(line)

    id = get_field(data, "id")
    reference = get_field(data, "référence")
    objet = get_field(data, "objet")
    acheteur = get_field(data, "acheteur")
    lieu = get_field(data, "lieu")
    categorie = get_field(data, "catégorie")
    nature = get_field(data, "nature")
    date_limite_str = get_field(data, "date_limite")
    date_mise_en_ligne_str = get_field(data, "date_mise_en_ligne")
    articles = data.get("articles", [])

    articles_clean = []
    for art in articles:
        article_data = {
            "titre": normalize_text(get_field(art, "Titre")),
            "garanties": normalize_text(get_field(art, "Garanties")),
            "caracteristiques": normalize_text(get_field(art, "Caractéristiques"))
        }
        articles_clean.append(article_data)

    bdc = new_BDC(
        id= id,
        reference=reference,
        nature=normalize_text(nature),
        montant_str='',
        montant=None,  # Montant prédit ultérieurement
        objet=normalize_text(objet),
        acheteur=normalize_text(acheteur),
        lieu=lieu,
        date_limite_str=date_limite_str,
        date_limite=parse_date(date_limite_str),
        date_mise_en_ligne_str=date_mise_en_ligne_str,
        date_mise_en_ligne=parse_date(date_mise_en_ligne_str),
        categorie=normalize_text(categorie),
        intervalle_prevision = '',
        articles=articles_clean
    )

    return bdc
def extract_id_from_url(url):
    path = urlparse(url).path
    parts = path.strip("/").split("/")
    if len(parts) >= 5 and parts[-2] == "show":
        return parts[-1]
    return None

def fetch_and_parse_bdc(id_):
    url = f"{BASE_URL}/bdc/entreprise/consultation/show/{id_}"
    session = requests.Session()
    session.headers.update(HEADERS)

    for _ in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            h4 = soup.find("h4")
            objet_tag = soup.find("span", class_="text-black")
            if not h4 or not objet_tag:
                return None

            reference = h4.text.strip()
            objet = objet_tag.text.strip()
            details = soup.find_all("div", class_="d-flex flex-column")
            if len(details) < 6:
                return None

            acheteur = details[0].find_all("span")[1].text.strip()
            date_mise_en_ligne = details[1].find_all("span")[1].text.strip()
            date_limite = details[2].find_all("span")[1].text.strip()
            lieu = details[3].find_all("span")[1].text.strip()
            categorie = details[4].find_all("span")[1].text.strip()
            nature = details[5].find_all("span")[1].text.strip()

            articles = []
            for item in soup.select(".accordion-item"):
                button = item.select_one("button.accordion-button")
                if not button:
                    continue
                titre = button.get_text(strip=True)

                caract_span = item.select_one(".accordion-body__flex .col-8 span.text-black")
                caracteristiques = caract_span.get_text(strip=True) if caract_span else "N/A"

                champs = {
                    "Unité de mesure": "N/A",
                    "Quantité": "N/A",
                    "TVA (%)": "N/A",
                    "Garanties exigées": "N/A"
                }

                for bloc in item.select(".content__article__miniCard .d-flex"):
                    label = bloc.select_one("span")
                    valeur = bloc.select_one(".content__article--subMiniCard")
                    if label and valeur:
                        champs[label.text.strip()] = valeur.text.strip()

                article = {
                    "titre": titre,
                    "quantité": champs["Quantité"],
                    "unité": champs["Unité de mesure"],
                    "tva": champs["TVA (%)"],
                    "garanties": champs["Garanties exigées"],
                    "caractéristiques": caracteristiques
                }
                articles.append(article)

            return {
                "id": id_,
                "référence": reference,
                "objet": objet,
                "acheteur": acheteur,
                "date_mise_en_ligne": date_mise_en_ligne,
                "date_limite": date_limite,
                "lieu": lieu,
                "catégorie": categorie,
                "nature": nature,
                "articles": articles
            }

        except requests.RequestException:
            time.sleep(1)

    return None


def scrape_bdc_from_url(url: str) -> new_BDC | None:
    """
    Reçoit un lien complet d’un bon de commande, scrape les données,
    les nettoie et retourne un objet `new_BDC` (avec montant=None).
    """
    id_ = extract_id_from_url(url)
    if not id_:
        print("❌ URL invalide ou ID non trouvé")
        return None

    data_dict = fetch_and_parse_bdc(id_)
    if not data_dict:
        print("❌ Échec du scraping pour ce lien")
        return None

    try:
        line_json = json.dumps(data_dict, ensure_ascii=False)
        bdc = create_new_bdc_from_json_line(line_json)
        return bdc
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage des données : {e}")
        return None
