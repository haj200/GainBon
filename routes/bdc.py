import math
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from psycopg2 import IntegrityError
from sqlalchemy import func, cast, String, and_, or_
from models.new_BDC import new_BDC
from models.old_BDC import old_BDC
from models.user import Consultation, Favouris
from models.nature import nature
from __init__ import db

bdc = Blueprint('bdc', __name__)

@bdc.route('/details/<int:bon_id>', methods=['GET'])
@login_required
def details(bon_id):
    # Récupération du bon
    bon = new_BDC.query.get(bon_id)
    is_new = True
    if not bon:
        bon = old_BDC.query.get(bon_id)
        is_new = False
    if not bon:
        flash("Le bon de commande demandé n'existe pas.", "warning")
        return redirect(request.referrer or url_for('main.explore_route'))

    # Gestion consultations/favoris
    if is_new:
        consultation = Consultation.query.filter_by(user_id=current_user.id, bon_id=bon.id).first()
        if consultation:
            consultation.nbr_de_fois += 1
        else:
            consultation = Consultation(user_id=current_user.id, bon_id=bon.id, nbr_de_fois=1)
            db.session.add(consultation)
        if consultation.nbr_de_fois > 4:
            if not Favouris.query.filter_by(user_id=current_user.id, bon_id=bon.id).first():
                db.session.add(Favouris(
                    bon_id=bon_id,
                    user_id=current_user.id,
                    defined_by_user=False,
                    expired=False
                ))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    return render_template(
        'details_general.html',
        user=current_user,
        bon=bon,
        is_new=is_new,
    )


@bdc.route('/details/<int:bon_id>/similaires', methods=['GET'])
@login_required
def details_similaires(bon_id):
    # Récupération du bon
    bon = new_BDC.query.get(bon_id)
    is_new = True
    if not bon:
        flash("Le bon de commande demandé n'existe pas.", "warning")
        return redirect(request.referrer or url_for('main.explore_route'))

    bons_similaires = []
    if is_new and getattr(bon, 'bons_similaires', None):
        bons_similaires = old_BDC.query.filter(old_BDC.id.in_(bon.bons_similaires)).all()

    return render_template(
        'details_similaires.html',
        user=current_user,
        bon=bon,
        is_new=is_new,
        bons_similaires=bons_similaires,
    )


@bdc.route('/details/<int:bon_id>/recherche', methods=['GET'])
@login_required
def details_recherche(bon_id):
    # Récupération du bon
    bon = new_BDC.query.get(bon_id)
    is_new = True
    if not bon:
        flash("Le bon de commande demandé n'existe pas.", "warning")
        return redirect(request.referrer or url_for('main.explore_route'))

    # Recherche
    query = request.args.get('q', '').strip()
    min_montant = request.args.get('min_montant')
    max_montant = request.args.get('max_montant')
    search_in = request.args.get('search_in', 'both')
    nature_prestation = bon.nature.strip() if getattr(bon, 'nature', None) else ''
    categorie = bon.categorie.strip() if getattr(bon, 'categorie', None) else ''
    page = request.args.get('page', 1, type=int)
    per_page = 20

    def build_filters(model):
        filters = []

        if query:
            like_query = f"%{query.lower()}%"
            if any(c.isdigit() for c in query) and len(query) >= 5:
                filters.append(func.lower(model.reference).like(like_query))
            else:
                filters.append(or_(
                    func.lower(model.lieu).like(like_query),
                    func.lower(model.objet).like(like_query),
                    func.lower(model.acheteur).like(like_query),
                    func.lower(cast(model.articles, String)).like(like_query),
                ))
        if min_montant:
            filters.append(model.montant >= float(min_montant))
        if max_montant:
            filters.append(model.montant <= float(max_montant))
        if nature_prestation:
            filters.append(func.lower(model.nature).like(f"%{nature_prestation.lower()}%"))
        if categorie:
            filters.append(func.lower(model.categorie) == categorie.lower())

        return filters

    # Récupérer tous les résultats filtrés (pas paginés)
    if search_in in ['new', 'both']:
        q_new = new_BDC.query.filter(and_(*build_filters(new_BDC))).order_by(new_BDC.date_mise_en_ligne.desc())
        results_new = q_new.all()
    else:
        results_new = []

    if search_in in ['old', 'both']:
        q_old = old_BDC.query.filter(and_(*build_filters(old_BDC))).order_by(old_BDC.date_mise_en_ligne.desc())
        results_old = q_old.all()
    else:
        results_old = []

    # Fusionner les deux listes, triées par date_mise_en_ligne décroissante
    combined = []
    for item in results_new:
        combined.append((item.date_mise_en_ligne, item, 'new'))
    for item in results_old:
        combined.append((item.date_mise_en_ligne, item, 'old'))

    # Tri décroissant par date_mise_en_ligne
    combined.sort(key=lambda x: x[0], reverse=True)

    total = len(combined)
    total_pages = math.ceil(total / per_page)

    # Paginer manuellement
    start = (page - 1) * per_page
    end = start + per_page
    page_items = combined[start:end]

    # Ne garder que les objets (items) pour l'affichage
    bons_recherche = [x[1] for x in page_items]

    return render_template(
        'details_recherche.html',
        user=current_user,
        bon=bon,
        is_new=is_new,
        bons_recherche=bons_recherche,
        search_in=search_in,
        min_montant=min_montant,
        max_montant=max_montant,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
    )
