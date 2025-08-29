from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests
import re
import time
import random
from models.new_BDC import new_BDC
from models.result_BDC import result_BDC
from models.old_BDC import old_BDC
from models.user import Favouris, Notification
from datetime import datetime
from typing import List, Tuple

from models.user import Notification


# --- Configuration ---
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

def parse_date(date_str):
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None

def parse_montant(montant_str):
    if not isinstance(montant_str, str):
        return 0.0
    montant_str = montant_str.replace("MAD", "").replace("Dhs", "").replace(" ", "").replace(",", ".")
    try:
        return float(montant_str)
    except ValueError:
        return 0.0

def get_max_page(date_str):
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    date_formattee = date_obj.strftime("%Y-%m-%d")
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D={date_formattee}&"
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

def fetch_page(page, date_str):
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    date_formattee = date_obj.strftime("%Y-%m-%d")
    query = (
        f"{FIXED_URL_PART_1}"
        f"&search_consultation_resultats%5BdateLimitePublicationStart%5D={date_formattee}&"
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

def scrape_day_objects(date_str):
    max_pages, total_results = get_max_page(date_str)
    print(f"📅 {date_str} : {total_results} résultats sur {max_pages} pages")
    all_data = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_page, page, date_str): page
            for page in range(1, max_pages + 1)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_data.extend(result)
    return [obj for obj in all_data if obj is not None]

def scrape_last_week_results(today: datetime):
    """
    Scrape les résultats publiés entre hier et les 6 jours précédents.
    Retourne une liste d'objets `result_BDC`.
    """
    results = []
    for i in range(1, 8):  # De 1 à 7 (hier à -6)
        day = today - timedelta(days=i)
        date_str = day.strftime("%d/%m/%Y")
        print(f"🔍 Scraping {date_str}")
        daily_results = scrape_day_objects(date_str)
        results.extend(daily_results)
    print(f"✅ Total résultats attribués récupérés : {len(results)}")
    return results



def clean(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"^[\s#:]+|[\s#:]+$", "", text.strip().lower())

def merge_temp_with_results(temp_bdc_list, old_results, current_date=None):
    if current_date is None:
        current_date = datetime.now()
    # Scraper les résultats récents
    results = scrape_last_week_results(current_date) + old_results
    results_with_montant = [r for r in results if r.montant and r.montant > 0]

    # Indexer par clef (reference, objet, acheteur) nettoyée
    results_index = {
        (clean(r.reference), clean(r.objet), clean(r.acheteur)): r
        for r in results_with_montant
    }

    seen_keys = set()
    unique_temp_bdc = []
    for temp in temp_bdc_list:
        key = (clean(temp.reference), clean(temp.objet), clean(temp.acheteur))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_temp_bdc.append(temp)

    matched_old_bdcs = []
    non_matched_ids = []

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
        else:
            non_matched_ids.append(temp.id)

    return matched_old_bdcs, non_matched_ids, results


def create_notifications_for_expired_favoris_with_results(old_bdcs, temp_bdc_list, favoris_list):
    notifications = []

    # Indexer old_bdcs par clé simplifiée
    old_bdc_map = {
        (clean(old.reference), clean(old.objet), clean(old.acheteur)): old
        for old in old_bdcs
    }

    # Indexer temp_bdc_list par id pour accès rapide (dict id -> temp_bdc)
    temp_bdc_map = {temp.id: temp for temp in temp_bdc_list}

    for fav in favoris_list:
        if not fav.expired:
            continue  # on ne traite que favoris expirés

        temp_bdc_obj = temp_bdc_map.get(fav.bon_id)
        if not temp_bdc_obj:
            continue

        key = (clean(temp_bdc_obj.reference), clean(temp_bdc_obj.objet), clean(temp_bdc_obj.acheteur))
        old_bdc = old_bdc_map.get(key)

        if old_bdc:
            contenu_msg = (
                f"Le résultat du bon de commande {old_bdc.reference} est publié. "
                f"Consultez-le ici : {getattr(old_bdc, 'lien_resultat', 'Lien non disponible')}"
            )
            notif = Notification(
                is_new=True,
                is_read=False,
                type='info',
                contenu=contenu_msg,
                temps_restant_jours=None,
                date=datetime.utcnow(),
                bon_id=fav.bon_id,
                user_id=fav.user_id
            )
            notifications.append(notif)

  

    return notifications
