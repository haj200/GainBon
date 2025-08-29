from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.new_BDC import new_BDC
from models.old_BDC import old_BDC
from services.prediction.bdc_predictor import predict_bdc_montant
from services.prediction.similarity_finder import fill_similar_bons
from services.scraper.scrap_on_demand import  scrape_bdc_from_url
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models.user import Favouris
from __init__ import db 

main = Blueprint('main', __name__)

def explore(lien, old_bdcs):
    bon = scrape_bdc_from_url(lien)
    bdc_with_montant = predict_bdc_montant(bon)
    bdc_with_similars = fill_similar_bons(bdc_with_montant, old_bdcs)
    return bdc_with_similars


@main.route('/explore', methods=['GET', 'POST'])
@login_required
def explore_route():
    if request.method == 'GET':
        if current_user.is_admin():
            return render_template('admin/admin.html', user=current_user)
        elif not current_user.is_profile_complete():
            return render_template("complete_profile.html", user=current_user)
        else:
            return render_template('explore_form.html', user=current_user)
    else:
        lien = request.form.get('lien')
        if not lien:
            flash("Veuillez entrer un lien valide.", "error")
            return redirect(url_for('main.explore_route'))
        
        old_bdcs = old_BDC.query.all()
        
        new_bdc = explore(lien, old_bdcs)
        
        if not new_bdc:
            flash("Aucun bon de commande trouvé ou problème dans le traitement.", "error")
            return redirect(url_for('main.explore_route'))
        
        # Vérifie si le new_bdc existe déjà en base (par exemple par référence)
        existing_bdc = new_BDC.query.filter_by(reference=new_bdc.reference).first()
        
        if not existing_bdc:
            # Nouveau bdc, on l'ajoute
            db.session.add(new_bdc)
            db.session.commit()
            existing_bdc = new_bdc  # pour la suite
        
        # Vérifie s'il existe déjà un favoris pour ce user et ce bon
        favoris = Favouris.query.filter_by(user_id=current_user.id, bon_id=existing_bdc.id).first()
        
        if not favoris:
            # Crée un favoris non défini par l'utilisateur (defined_by_user=False)
            favoris = Favouris(
                defined_by_user=False,
                expired=False,
                bon_id=existing_bdc.id,
                user_id=current_user.id
            )
            db.session.add(favoris)
            db.session.commit()
        
        # Prépare les bons similaires complets pour affichage
        similar_bons = []
        if existing_bdc.bons_similaires:
            similar_bons = old_BDC.query.filter(old_BDC.id.in_(existing_bdc.bons_similaires)).all()
        
        return render_template('explore_result.html', bdc=existing_bdc, similars=similar_bons, user=current_user)
    
@main.route('/skip/explore', methods=['GET', 'POST'])
@login_required
def explore_skip_route():
    if request.method == 'GET':
        if current_user.is_admin():
            return render_template('admin/admin.html', user=current_user)
        elif current_user.is_profile_complete():
            return redirect(url_for('main.explore_route'))
        else:
            return render_template('explore_form.html', user=current_user)
    else:
        lien = request.form.get('lien')
        if not lien:
            flash("Veuillez entrer un lien valide.", "error")
            return redirect(url_for('main.explore_route'))
        
        old_bdcs = old_BDC.query.all()
        
        new_bdc = explore(lien, old_bdcs)
        
        if not new_bdc:
            flash("Aucun bon de commande trouvé ou problème dans le traitement.", "error")
            return redirect(url_for('main.explore_route'))
        
        # Vérifie si le new_bdc existe déjà en base (par exemple par référence)
        existing_bdc = new_BDC.query.filter_by(reference=new_bdc.reference).first()
        
        if not existing_bdc:
            # Nouveau bdc, on l'ajoute
            db.session.add(new_bdc)
            db.session.commit()
            existing_bdc = new_bdc  # pour la suite
        
        # Vérifie s'il existe déjà un favoris pour ce user et ce bon
        favoris = Favouris.query.filter_by(user_id=current_user.id, bon_id=existing_bdc.id).first()
        
        if not favoris:
            # Crée un favoris non défini par l'utilisateur (defined_by_user=False)
            favoris = Favouris(
                defined_by_user=False,
                expired=False,
                bon_id=existing_bdc.id,
                user_id=current_user.id
            )
            db.session.add(favoris)
            db.session.commit()
        
        # Prépare les bons similaires complets pour affichage
        similar_bons = []
        if existing_bdc.bons_similaires:
            similar_bons = old_BDC.query.filter(old_BDC.id.in_(existing_bdc.bons_similaires)).all()
        
        return render_template('explore_result.html', bdc=existing_bdc, similars=similar_bons, user=current_user)
    
    

    
