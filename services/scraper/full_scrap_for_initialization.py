import json
import re
from string import punctuation
from datetime import datetime, timedelta
from models.new_BDC import new_BDC
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from models.result_BDC import result_BDC
from models.old_BDC import old_BDC
from models.nature import nature
from models.user import Favouris, Notification
from typing import List, Tuple
import json
from pathlib import Path
from models.user import Notification
##scrap all details of bdcs

# Configuration
MAX_WORKERS = 8
RETRIES = 10
TIMEOUT = 120
PAGE_SIZE = 50

BASE_URL = "https://www.marchespublics.gov.ma"
SEARCH_URL = BASE_URL + "/bdc/entreprise/consultation/resultat"

FIXED_URL_PART_1 = (
    "search_consultation_resultats%5Bkeyword%5D="
    "&search_consultation_resultats%5Breference%5D="
    "&search_consultation_resultats%5Bobjet%5D="
)
FIXED_URL_PART_2 = (
    "&search_consultation_resultats%5BdateMiseEnLigneStart%5D="
    "&search_consultation_resultats%5BdateMiseEnLigneEnd%5D="
    "&search_consultation_resultats%5Bcategorie%5D="
)
FIXED_URL_PART_3 = (
    "&search_consultation_resultats%5Bacheteur%5D="
    "&search_consultation_resultats%5Bservice%5D="
    "&search_consultation_resultats%5BlieuExecution%5D="
    f"&search_consultation_resultats%5BpageSize%5D={PAGE_SIZE}"
)

headers = {"User-Agent": "Mozilla/5.0"}
session = requests.Session()
session.headers.update(headers)


def normalize_text(text: Optional[str]) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    punctuation_without_apostrophe = punctuation.replace("'", "")
    text = re.sub(rf"[{re.escape(punctuation_without_apostrophe)}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_field(d, key):
    for k in d:
        if k.lower().replace("é", "e").replace("è", "e") == key.lower().replace("é", "e").replace("è", "e"):
            return d[k]
    return ""

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None

def create_new_bdc_from_json_line(line: str) -> new_BDC:
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
        id=id,
        reference=reference,
        nature=normalize_text(nature),
        montant_str='',
        montant=None,
        objet=normalize_text(objet),
        acheteur=normalize_text(acheteur),
        lieu=lieu,
        date_limite_str=date_limite_str,
        date_limite=parse_date(date_limite_str),
        date_mise_en_ligne_str=date_mise_en_ligne_str,
        date_mise_en_ligne=parse_date(date_mise_en_ligne_str),
        categorie=normalize_text(categorie),
        intervalle_prevision='',
        articles=articles_clean
    )
    return bdc

def fetch_url_with_retry(url, session=None) -> Optional[str]:
    session = session or requests.Session()
    session.headers.update(headers)

    for attempt in range(1, RETRIES + 1):
        try:
            print(f"Essai {attempt} pour {url}")
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.Timeout:
            print(f"Timeout lors de la lecture de {url}, tentative {attempt}/{RETRIES}")
        except requests.ConnectionError:
            print(f"Erreur de connexion pour {url}, tentative {attempt}/{RETRIES}")
        except requests.HTTPError as e:
            code = e.response.status_code
            print(f"Erreur HTTP {code} pour {url}")
            if code == 404:
                break
        except Exception as e:
            print(f"Erreur inattendue lors de la requête {url} : {e}")

        wait_time = 2 ** attempt
        print(f"Attente {wait_time}s avant nouvelle tentative...")
        time.sleep(wait_time)

    print(f"Échec après {RETRIES} tentatives pour {url}")
    return None

def fetch_and_parse(id_: int) -> Optional[dict]:
    url = f"{BASE_URL}/bdc/entreprise/consultation/show/{id_}"
    session = requests.Session()
    session.headers.update(headers)

    for attempt in range(1, RETRIES + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            h4 = soup.find("h4")
            objet_tag = soup.find("span", class_="text-black")
            if not h4 or not objet_tag:
                print(f"Échec parsing : éléments manquants pour id={id_}")
                return None

            reference = h4.text.strip()
            objet = objet_tag.text.strip()

            details = soup.find_all("div", class_="d-flex flex-column")
            if len(details) < 6:
                print(f"Détails insuffisants pour id={id_}")
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

        except requests.RequestException as e:
            print(f"Erreur requête id={id_}: {e}")
            time.sleep(1)

    print(f"Échec après {RETRIES} tentatives pour id={id_}")
    return None



def build_url_for_today(page=1, date_str=None) -> str:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"{BASE_URL}/bdc/entreprise/consultation/"
        f"?search_consultation_entreprise%5Bkeyword%5D="
        f"&search_consultation_entreprise%5Breference%5D="
        f"&search_consultation_entreprise%5Bobjet%5D="
        f"&search_consultation_entreprise%5BdateLimiteStart%5D="
        f"&search_consultation_entreprise%5BdateLimiteEnd%5D="
        f"&search_consultation_entreprise%5BdateMiseEnLigneStart%5D={date_str}"
        f"&search_consultation_entreprise%5BdateMiseEnLigneEnd%5D={date_str}"
        f"&search_consultation_entreprise%5Bcategorie%5D="
        f"&search_consultation_entreprise%5BnaturePrestation%5D="
        f"&search_consultation_entreprise%5Bacheteur%5D="
        f"&search_consultation_entreprise%5Bservice%5D="
        f"&search_consultation_entreprise%5BlieuExecution%5D="
        f"&search_consultation_entreprise%5BpageSize%5D=50"
        f"&page={page}")
    return (
        f"{BASE_URL}/bdc/entreprise/consultation/"
        f"?search_consultation_entreprise%5Bkeyword%5D="
        f"&search_consultation_entreprise%5Breference%5D="
        f"&search_consultation_entreprise%5Bobjet%5D="
        f"&search_consultation_entreprise%5BdateLimiteStart%5D="
        f"&search_consultation_entreprise%5BdateLimiteEnd%5D="
        f"&search_consultation_entreprise%5BdateMiseEnLigneStart%5D={date_str}"
        f"&search_consultation_entreprise%5BdateMiseEnLigneEnd%5D={date_str}"
        f"&search_consultation_entreprise%5Bcategorie%5D="
        f"&search_consultation_entreprise%5BnaturePrestation%5D="
        f"&search_consultation_entreprise%5Bacheteur%5D="
        f"&search_consultation_entreprise%5Bservice%5D="
        f"&search_consultation_entreprise%5BlieuExecution%5D="
        f"&search_consultation_entreprise%5BpageSize%5D=50"
        f"&page={page}"
    )


def get_total_results_and_first_id(date_str) :
    url = build_url_for_today(page=1, date_str=date_str)
    session = requests.Session()
    session.headers.update(headers)
    try:
        res = session.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')

        # Total résultats
        total = 0
        div = soup.find('div', class_='content__resultat')
        if div:
            match = re.search(r'Nombre de résultats\s*:\s*(\d+)', div.get_text(strip=True))
            if match:
                total = int(match.group(1))

        # Premier ID
        first_id = None
        link = soup.select_one("a[href^='/bdc/entreprise/consultation/show/']")
        if link:
            href = link.get("href")
            if href:
                try:
                    first_id = int(href.strip().split("/")[-1])
                except ValueError:
                    first_id = None

        return total, first_id
    except Exception as e:
        print(f"[get_total_results_and_first_id] Erreur: {e}")
    return 0, None

def scrape_all_bdc() -> List[new_BDC]:
    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    total, first_id = get_total_results_and_first_id(date_str)
    if not first_id or total == 0:
        print("Aucun résultat trouvé ou problème pour récupérer l'ID du premier bon.")
        return []

    print(f"Nombre total de résultats : {total}")
    print(f"Premier ID détecté : {first_id}")

    bons = []
    for current_id in range(1, first_id + total):
        print(f"Scraping ID {current_id} / {first_id + total - 1}")
        bon = fetch_and_parse(current_id)
        if bon:
            try:
                line_json = json.dumps(bon, ensure_ascii=False)
                new_bdc_obj = create_new_bdc_from_json_line(line_json)
                bons.append(new_bdc_obj)
            except Exception as e:
                print(f"Erreur traitement bon ID {current_id}: {e}")
        else:
            print(f"Pas de données pour l'ID {current_id}")
        time.sleep(0.5)  # pause pour ne pas surcharger

    print(f"Total bons récupérés : {len(bons)}")
    return bons

##scrap results

def parse_montant(montant_str):
    if not isinstance(montant_str, str):
        return 0.0
    montant_str = montant_str.replace("MAD", "").replace("Dhs", "").replace(" ", "").replace(",", ".")
    try:
        return float(montant_str)
    except ValueError:
        return 0.0

def get_max_page():
    
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D=&"
        f"search_consultation_resultats%5BdateLimitePublicationEnd%5D="
        f"{FIXED_URL_PART_2}"
        f"&search_consultation_resultats%5BnaturePrestation%5D="
        f"{FIXED_URL_PART_3}"
    )
    url = f"{SEARCH_URL}?{query}"
    try:
        res = session.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'lxml')
        div = soup.find('div', class_='content__resultat')
        if div:
            match = re.search(r'Nombre de résultats\s*:\s*(\d+)', div.get_text(strip=True))
            if match:
                total = int(match.group(1))
                pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
                return pages, total
    except Exception as e:
        print(f"[get_max_page] Erreur: {e}")
    return 1, 0

def extract_card_data(card, url):
    try:
        ref = card.select_one('.font-bold.table__links')
        objet = card.select_one('[data-bs-toggle="tooltip"]')
        buyer = card.find('span', string=lambda s: s and "Acheteur" in s)
        pub_date = card.find('span', string=lambda s: s and "Date de publication" in s)

        reference = ref.text.strip().replace('Référence :', '') if ref else None
        obj = objet.text.strip().replace('Objet :', '') if objet else None
        acheteur = buyer.parent.text.replace('Acheteur :', '').strip() if buyer else None
        date_pub = pub_date.parent.text.replace('Date de publication du résultat :', '').strip() if pub_date else None

        right = card.select_one('.entreprise__rightSubCard--top')
        if right:
            devis = right.find(string=lambda s: "Nombre de devis reçus" in s)
            nombre_devis = right.select_one("span span.font-bold").text.strip() if devis else None

            spans = right.find_all('span', recursive=False)
            attribue = False
            entreprise = montant = None

            if len(spans) >= 3:
                entreprise = spans[1].find('span', class_='font-bold')
                montant = spans[2].find('span', class_='font-bold')
                entreprise = entreprise.text.strip() if entreprise else None
                montant = montant.text.strip() if montant else None
                attribue = entreprise is not None

            if attribue and montant:
                r = result_BDC()
                r.reference = reference
                r.objet = obj
                r.acheteur = acheteur
                r.date_publication_str = date_pub
                r.date_publication = parse_date(date_pub)
                r.nombre_devis = nombre_devis
                r.entreprise_attributaire = entreprise
                r.montant_str = montant
                r.montant = parse_montant(montant)
                r.lien_resultat = url
                return r

        
    except Exception as e:
        print(f"[extract_card_data] Erreur: {e}")
    return None

def fetch_page(page):
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D=&"
        f"search_consultation_resultats%5BdateLimitePublicationEnd%5D="
        f"{FIXED_URL_PART_2}"
        f"&search_consultation_resultats%5BnaturePrestation%5D="
        f"{FIXED_URL_PART_3}"
        f"&page={page}"
    )
    url = f"{SEARCH_URL}?{query}"
    for attempt in range(RETRIES):
        try:
            time.sleep(random.uniform(0.25, 0.35))
            res = session.get(url, timeout=TIMEOUT)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'lxml')
            cards = soup.select('.entreprise__card')
            return [extract_card_data(card ,url) for card in cards if card]
        except requests.RequestException as e:
            print(f"[fetch_page] Tentative {attempt+1}/{RETRIES} - Erreur page {page}: {e}")
            time.sleep(0.3)
    return []

def scrape_all_objects():
    max_pages, total_results = get_max_page()
    print(f"{total_results} résultats sur {max_pages} pages")
    all_data = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_page, page ): page
            for page in range(1, max_pages + 1)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_data.extend(result)
    return [obj for obj in all_data if obj is not None]

def scrapeAllresults(today: datetime):
    """
    Scrape les résultats publiés entre hier et les 6 jours précédents.
    Retourne une liste d'objets `result_BDC`.
    """
    results = []
    
    All_results = scrape_all_objects()
    results.extend(All_results)
    print(f"✅ Total résultats attribués récupérés : {len(results)}")
    return results



def clean(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"^[\s#:]+|[\s#:]+$", "", text.strip().lower())

##fusionner:
def merge_temp_with_results(current_date=None):
    if current_date is None:
        current_date = datetime.now()
    #scraper all détails
    bons = scrape_all_bdc()
    # Scraper les résultats récents
    results = scrapeAllresults(current_date) 
    results_with_montant = [r for r in results if r.montant and r.montant > 0]

    # Indexer par clef (reference, objet, acheteur) nettoyée
    results_index = {
        (clean(r.reference), clean(r.objet), clean(r.acheteur)): r
        for r in results_with_montant
    }

    seen_keys = set()
    unique_temp_bdc = []
    for temp in bons:
        key = (clean(temp.reference), clean(temp.objet), clean(temp.acheteur))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_temp_bdc.append(temp)

    matched_old_bdcs = []
    

    for temp in unique_temp_bdc:
        key = (clean(temp.reference), clean(temp.objet), clean(temp.acheteur))
        result = results_index.get(key)
        if result:
            old = old_BDC(
                reference=temp.reference,
                nature=temp.nature,
                objet=temp.objet,
                acheteur=temp.acheteur,
                lieu=temp.lieu,
                date_limite=temp.date_limite,
                date_limite_str=temp.date_limite_str,
                date_mise_en_ligne=temp.date_mise_en_ligne,
                date_mise_en_ligne_str=temp.date_mise_en_ligne_str,
                categorie=temp.categorie,
                articles=temp.articles,
                montant=result.montant,
                montant_str=result.montant_str,
            )
            # Ajout d'un attribut dynamique pour url du résultat (utile après)
            old.lien_resultat = result.lien_resultat
            matched_old_bdcs.append(old)
        

    return matched_old_bdcs


##natures

def load_natures():
    """
    Charge les natures depuis le fichier natures.jsonl
    et retourne une liste d'objets nature (SQLAlchemy).
    """
    NATURES_FILE = Path("C:/Users/pc/Desktop/site/services/prediction/natures.jsonl")

    if not NATURES_FILE.exists():
        print("⚠️ Fichier natures.jsonl introuvable, liste vide retournée.")
        return []

    natures_list = []

    try:
        with open(NATURES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    name = obj.get("name", "").strip()
                    id_ = obj.get("id")

                    if name and id_ is not None:
                        natures_list.append(nature(id=id_, nom=name))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Ligne JSON invalide : {line.strip()} ({e})")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier natures.jsonl : {e}")

    return natures_list


    