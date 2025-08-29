#imports
from datetime import datetime
from flask import Blueprint, render_template,request, flash, redirect, session, url_for
from models.nature import nature
from models.user import Favouris, User
from models.new_BDC import new_BDC
from werkzeug.security import generate_password_hash, check_password_hash
from __init__ import db
from flask_login import login_user, login_required, logout_user, current_user
from flask import jsonify
from models.old_BDC import old_BDC
#fonctions utiles

#fonction pour vérifier la force du mot de passe
def is_password_strong(password):
            """
            Vérifie la force du mot de passe
            
            Critères :
            - Au moins 8 caractères
            - Au moins une majuscule
            - Au moins une minuscule
            - Au moins un chiffre
            - Au moins un caractère spécial
            """
            if len(password) < 8:
                return False, "Le mot de passe doit contenir au moins 8 caractères."
            elif not any(c.isupper() for c in password):
                return False, "Le mot de passe doit contenir au moins une majuscule."
            elif not any(c.islower() for c in password):
                return False, "Le mot de passe doit contenir au moins une minuscule."
            elif not any(c.isdigit() for c in password):
                return False, "Le mot de passe doit contenir au moins un chiffre."
            elif not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
                return False, "Le mot de passe doit contenir au moins un caractère spécial."
            return True, "Le mot de passe est fort."
        





auth = Blueprint('auth', __name__)
# index route
@auth.route('/')
def index():
    return render_template("index.html")


@auth.route('/profile-data')
@login_required
def profile_data():
    # Natures
    natures = [
        {"id": n.id, "nom": n.nom}
        for n in nature.query.all()
    ]
    # Villes distinctes
    MAX_CITY_NAME_LENGTH = 30  # par exemple

    cities = [
    row[0]
    for row in db.session.query(old_BDC.lieu).distinct().all()
    if row[0] and len(row[0]) <= MAX_CITY_NAME_LENGTH
    ]

    # Catégories distinctes
    
    categories = [
        'travaux', 'services', 'fournitures'
    ]
    
    return jsonify({
        "natures": natures,
        "cities": cities,
        "categories": categories
    })
#logout route
@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.sign_up'))

#register and login route
@auth.route('/auth', methods = ['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        if request.form.get('action') == 'sign-up':
            nom = request.form.get('nom')
            email = request.form.get('email')
            mdp = request.form.get('mdp')
            is_strong, message = is_password_strong(mdp)
            if not is_strong:
                flash(message, category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            user = User.query.filter_by(username=nom).first()
            if user:
                flash('Ce username est déjà utilisé.', category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Cet email est déjà utilisé.', category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            if not nom or not email or not mdp:
                flash('Veuillez remplir tous les champs.',category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            elif len(nom)<5:
                flash('le nom doit dépasser cinq caractères.',category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            elif len(email)<4:
                flash('l\'email doit dépasser quatres caractères.',category='error')
                session['form_type'] = 'sign-up'
                return redirect(url_for('auth.sign_up'))
            else:
                new_user = User(username=nom, email=email, password_hash=generate_password_hash(mdp))
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user, remember=True)
                return redirect(url_for('main.explore_route'))
        else :
            nom = request.form.get('nom')
            mdp = request.form.get('mdp')
            user = User.query.filter_by(username=nom).first() 
            if user:
                if check_password_hash(user.password_hash, mdp):
                    login_user(user, remember=True)
                    return redirect(url_for('main.explore_route')) 
                else:
                    flash('Mot de passe incorrect.', category='error')
                    session['form_type'] = 'sign-in'
                    return redirect(url_for('auth.sign_up'))
            flash('Ce nom n\'existe pas.', category='error')
            session['form_type'] = 'sign-in'
            return redirect(url_for('auth.sign_up'))
    form_type = session.pop('form_type', 'sign-up')
    return render_template("sign-up.html", user=current_user, form_type=form_type)




@auth.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        ville = request.form.get('ville')
        favourite_cities = request.form.getlist('favourite_cities')
        favourite_prices = request.form.get('favourite_prices')
        categories = request.form.getlist('categories')
        natures = request.form.getlist('natures')
        telephone = request.form.get('telephone')
        adresse = request.form.get('adresse')
        profession = request.form.get('profession')
        sexe = request.form.get('sexe')
        user = User.query.filter_by(username=current_user.username).first()
        # Vérifier l'unicité du téléphone
        existing_user = User.query.filter(User.telephone == telephone, User.id != user.id).first()
        if existing_user:
            flash('Ce numéro de téléphone est déjà utilisé.', category='error')
            return redirect(url_for('auth.complete_profile'))
        user.nom = nom
        user.prenom = prenom
        user.ville = ville
        user.telephone = telephone
        user.adresse = adresse
        user.profession = profession
        if not sexe or sexe in ('[null]', 'null', '', None):
            sexe = None
        user.sexe = sexe

        user.preferences_user = {
            "favourite_cities": favourite_cities,
            "favourite_prices": favourite_prices,
            "favourites_categories": categories,
            "favourites_natures_de_prestation": natures
        }
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la mise à jour du profil: {str(e)}", category='error')
            return redirect(url_for('auth.complete_profile'))

        flash("Profil mis à jour avec succès.", category='success')
        if current_user.is_profile_complete():
            return redirect(url_for('main.explore_route'))
        else:
            return redirect(url_for('main.explore_skip_route'))
        

    return render_template('complete_profile.html', user=current_user)


