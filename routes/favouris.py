import math
from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from psycopg2 import IntegrityError
from sqlalchemy import func, cast, String, and_, or_
from models.new_BDC import new_BDC
from models.old_BDC import old_BDC
from models.user import Consultation, Favouris
from models.nature import nature
from __init__ import db
from datetime import datetime

favouris = Blueprint('favouris', __name__)

@favouris.route('/toggle_favourite', methods=['POST'])
@login_required
def toggle_favourite():
    data = request.get_json()
    bon = data.get('bon')

    if bon is None or 'id' not in bon:
        return jsonify({'success': False, 'error': 'Missing or invalid bon'}), 400

    bon_id = bon['id']

    # Chercher un favori existant pour cet utilisateur et ce bon
    favouri = Favouris.query.filter_by(user_id=current_user.id, bon_id=bon_id).first()

    if favouri:
        # Supprimer des favoris
        db.session.delete(favouri)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed'})
    else:
        # Ajouter aux favoris
        new_favouri = Favouris(
            bon_id=bon_id,
            user_id=current_user.id,
            defined_by_user=True,
            expired=False
        )
        db.session.add(new_favouri)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added'})


@favouris.route('/favouris', methods=['GET'])
@login_required
def get_favouris():
    page = request.args.get('page', 1, type=int)
    per_page = 18

    # Préférences utilisateur
    prefs_user = current_user.preferences_user or {}

    # Extraction sécurisée des préférences nature
    preferred_nature_ids_str = prefs_user.get("favourites_natures_de_prestation", "")
    if isinstance(preferred_nature_ids_str, str):
        nature_ids_str = preferred_nature_ids_str
    elif isinstance(preferred_nature_ids_str, list) and preferred_nature_ids_str:
        nature_ids_str = preferred_nature_ids_str[0]
    else:
        nature_ids_str = ""

    preferred_nature_ids = [int(id.strip()) for id in nature_ids_str.split(",") if id.strip().isdigit()] if prefs_user else []
    preferred_categories = prefs_user.get("favourites_categories", [])  # Liste des catégories préférées
    preferred_cities = []
    if prefs_user and "favourite_cities" in prefs_user:
        if isinstance(prefs_user["favourite_cities"], list) and prefs_user["favourite_cities"]:
            preferred_cities = prefs_user["favourite_cities"][0].split(", ")
        elif isinstance(prefs_user["favourite_cities"], str):
            preferred_cities = prefs_user["favourite_cities"].split(", ")
    # print(preferred_cities)
    # print(preferred_categories)

    # Mapping nature ID -> nom
    nature_mapping = {n.id: n.nom for n in nature.query.all()}
    preferred_natures_text = [nature_mapping[id].strip('"\'') for id in preferred_nature_ids if id in nature_mapping]
    # print(preferred_natures_text)

    # Récupérer les favoris de l'utilisateur depuis la table Favouris
    user_favs = {fav.bon_id for fav in Favouris.query.filter_by(user_id=current_user.id).all()}
    user_favs_defined_by_user = {fav.bon_id for fav in Favouris.query.filter_by(user_id=current_user.id).all() if fav.defined_by_user}

    # Tous les bons de commande, triés par date mise en ligne
    all_bdcs = new_BDC.query.order_by(new_BDC.date_mise_en_ligne.desc()).all()

    # Normalisation des préférences en minuscules pour comparaison rapide
    preferred_natures_lower = {n.lower() for n in preferred_natures_text}
    preferred_cities_lower = {c.lower() for c in preferred_cities}
    preferred_categories_lower = {cat.lower() for cat in preferred_categories}

    # Score de similarité basé sur les correspondances (0..3)
    def compute_similarity(bdc):
        nature_match = 1 if (bdc.nature and bdc.nature.lower() in preferred_natures_lower) else 0
        city_match = 1 if (bdc.lieu and bdc.lieu.lower() in preferred_cities_lower) else 0
        category_match = 1 if (bdc.categorie and bdc.categorie.lower() in preferred_categories_lower) else 0
        return nature_match + city_match + category_match

    # Tri global: favoris d'abord, puis par similarité décroissante, puis par date décroissante
    def sort_key(bdc):
        is_fav = 1 if bdc.id in user_favs else 0
        similarity = compute_similarity(bdc)
        date_value = bdc.date_mise_en_ligne or datetime.min
        return (is_fav, similarity, date_value)

    sorted_bdcs = sorted(all_bdcs, key=sort_key, reverse=True)

    # Pagination manuelle
    total = len(sorted_bdcs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_bdcs = sorted_bdcs[start:end]
    has_more = end < total

    all_natures_json = [{"id": id, "nom": nom} for id, nom in nature_mapping.items()]

    return render_template(
        "home.html",
        user_favs_ids = user_favs_defined_by_user,
        user=current_user,
        bdcs=paginated_bdcs,
        page=page,
        has_more=has_more,
        all_natures=all_natures_json
    )  
    