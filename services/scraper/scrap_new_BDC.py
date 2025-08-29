import json
import re
from string import punctuation
from datetime import datetime, timedelta
from models.new_BDC import new_BDC
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Optional

# Configuration
BASE_URL = "https://www.marchespublics.gov.ma"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
TIMEOUT = 120
MAX_RETRIES = 10

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
    session.headers.update(HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Essai {attempt} pour {url}")
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.Timeout:
            print(f"Timeout lors de la lecture de {url}, tentative {attempt}/{MAX_RETRIES}")
        except requests.ConnectionError:
            print(f"Erreur de connexion pour {url}, tentative {attempt}/{MAX_RETRIES}")
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

    print(f"Échec après {MAX_RETRIES} tentatives pour {url}")
    return None

def fetch_and_parse(id_: int) -> Optional[dict]:
    url = f"{BASE_URL}/bdc/entreprise/consultation/show/{id_}"
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):
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

    print(f"Échec après {MAX_RETRIES} tentatives pour id={id_}")
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
    session.headers.update(HEADERS)
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

def scrape_today_bdc() -> List[new_BDC]:
    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    total, first_id = get_total_results_and_first_id(date_str)
    if not first_id or total == 0:
        print("Aucun résultat trouvé ou problème pour récupérer l'ID du premier bon.")
        return []

    print(f"Nombre total de résultats : {total}")
    print(f"Premier ID détecté : {first_id}")

    bons = []
    for current_id in range(first_id, first_id + total):
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
