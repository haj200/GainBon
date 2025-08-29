import re
import unicodedata
from string import punctuation


# === Paramètres ===
STOPWORDS = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "à", "a", "en",
    "d", "dans", "pour", "par", "avec", "sans", "sur", "au", "aux", "ce",
    "ces", "cette", "se", "sa", "son", "leurs", "leurs", "lui", "elle",
    "qui", "que", "quoi", "dont", "où", "ne", "pas", "plus", "moins", "comme"
}

def normalize_text(text):
    """
    Normalise un texte en le convertissant en minuscules, supprimant les accents,
    les caractères spéciaux et les chiffres.
    
    Args:
        text (str): Le texte à normaliser
        
    Returns:
        str: Le texte normalisé
    """
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(rf"[{punctuation}]", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_keywords(text):
    """
    Extrait les mots-clés d'un texte en supprimant les stopwords français
    et en gardant seulement les mots de plus de 2 caractères.
    
    Args:
        text (str): Le texte à analyser
        
    Returns:
        set: Ensemble des mots-clés extraits
    """
    text = normalize_text(text)
    return set(w for w in text.split() if w not in STOPWORDS and len(w) > 2)

def build_full_text(bdc):
    """
    Construit le texte complet d'un BDC en combinant tous les champs pertinents
    (référence, objet, acheteur, lieu, catégorie et articles).
    
    Args:
        bdc: L'objet BDC contenant les informations
        
    Returns:
        str: Le texte complet combiné
    """
    articles_text = []
    for art in bdc.articles or []:
        titre = art.get("titre", "")
        garanties = art.get("garanties", "")
        caracteristiques = art.get("caractéristiques", "")
        articles_text.append(f"{titre} {garanties} {caracteristiques}")
    
    return " ".join([
        str(bdc.reference or ""), str(bdc.objet or ""), str(bdc.acheteur or ""),
        str(bdc.lieu or ""), str(bdc.categorie or ""), " ".join(articles_text)
    ]).strip()
