from math import ceil
from flask import Blueprint, request, render_template
from sqlalchemy import or_, and_, func, cast, String
from models.new_BDC import new_BDC
from models.old_BDC import old_BDC
from models.nature import nature
from flask_login import login_required, current_user

search = Blueprint('search', __name__)

@search.route('/search', methods=['GET'])
@login_required
def recherche():
    natures = [{"id": n.id, "nom": n.nom} for n in nature.query.all()]
    nature_names = [n["nom"] for n in natures]

    query = request.args.get('q', '').strip()
    min_montant = request.args.get('min_montant')
    max_montant = request.args.get('max_montant')
    date_min = request.args.get('date_min')
    date_max = request.args.get('date_max')
    search_in = request.args.get('search_in', 'both')  # 'new', 'old', 'both'
    nature_prestation = request.args.get('nature', '').strip()
    categorie = request.args.get('categorie', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Préparation filtres texte
    text_filters_new = []
    text_filters_old = []
    if query:
        like_query = f"%{query.lower()}%"
        if any(c.isdigit() for c in query) and len(query) >= 5:
            text_filters_new.append(func.lower(new_BDC.reference).like(like_query))
            text_filters_old.append(func.lower(old_BDC.reference).like(like_query))
        else:
            text_filters_new.extend([
                func.lower(new_BDC.lieu).like(like_query),
                func.lower(new_BDC.objet).like(like_query),
                func.lower(new_BDC.acheteur).like(like_query),
                func.lower(cast(new_BDC.articles, String)).like(like_query),
            ])
            text_filters_old.extend([
                func.lower(old_BDC.lieu).like(like_query),
                func.lower(old_BDC.objet).like(like_query),
                func.lower(old_BDC.acheteur).like(like_query),
                func.lower(cast(old_BDC.articles, String)).like(like_query),
            ])

    # Préparation filtres montants, dates, nature, catégorie
    def build_filters(model, text_filters):
        filters = []
        if text_filters:
            filters.append(or_(*text_filters))
        if min_montant:
            filters.append(model.montant >= float(min_montant))
        if max_montant:
            filters.append(model.montant <= float(max_montant))
        if date_min:
            filters.append(model.date_limite >= date_min)
        if date_max:
            filters.append(model.date_limite <= date_max)
        if nature_prestation:
            filters.append(func.lower(model.nature).like(f"%{nature_prestation.lower()}%"))
        if categorie:
            filters.append(func.lower(model.categorie) == categorie.lower())
        return filters

    filters_new = build_filters(new_BDC, text_filters_new)
    filters_old = build_filters(old_BDC, text_filters_old)

    results_all = []

    # Charger tous les résultats (avec un max raisonnable pour éviter surcharge)
    max_results = 1000  # par exemple

    if search_in in ['new', 'both']:
        q_new = new_BDC.query.filter(and_(*filters_new)).order_by(new_BDC.date_mise_en_ligne.desc()).limit(max_results)
        results_all.extend(q_new.all())

    if search_in in ['old', 'both']:
        q_old = old_BDC.query.filter(and_(*filters_old)).order_by(old_BDC.date_mise_en_ligne.desc()).limit(max_results)
        results_all.extend(q_old.all())

    # Tri global (ex: par date_mise_en_ligne décroissante)
    results_all.sort(key=lambda bdc: bdc.date_mise_en_ligne or '', reverse=True)

    # Pagination manuelle
    total_results = len(results_all)
    total_pages = ceil(total_results / per_page)

    start = (page - 1) * per_page
    end = start + per_page
    results_paginated = results_all[start:end]

    return render_template(
        'search_results.html',
        natures=nature_names,
        results=results_paginated,
        query=query,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        user=current_user
    )
