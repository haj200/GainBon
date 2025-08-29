def interval_to_float(interval_str):
    """
    Convertit un intervalle sous forme de chaîne (ex: "1000-2000") 
    en valeur flottante représentant le milieu de l'intervalle.
    
    Args:
        interval_str (str): L'intervalle au format "min-max"
        
    Returns:
        float: La valeur moyenne de l'intervalle, ou 0.0 si erreur
    """
    try:
        min_, max_ = map(float, interval_str.split("-"))
        return (min_ + max_) / 2
    except:
        return 0.0

def format_montant_str(value):
    """
    Formate un montant en chaîne de caractères avec le format français
    (espaces pour les milliers, virgule pour les décimales, suffixe MAD).
    
    Args:
        value (float): Le montant à formater
        
    Returns:
        str: Le montant formaté (ex: "1 234,56 MAD")
    """
    return f"{value:,.2f} MAD".replace(",", " ").replace(".", ",")

def prix_label(montant):
    """
    Retourne une étiquette de prix selon le montant pour catégoriser
    les BDC par tranche de prix.
    
    Args:
        montant (float): Le montant du BDC
        
    Returns:
        list: Liste contenant l'étiquette de prix ("bas", "moyen", ou "haut")
    """
    if montant < 1000:
        return ["bas"]
    elif montant < 10000:
        return ["moyen"]
    else:
        return ["haut"]
