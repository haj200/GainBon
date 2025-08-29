from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from __init__ import db
from models.user import Notification

notif_bp = Blueprint('notif', __name__)

@notif_bp.route('/notifications')
@login_required
def liste():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date.desc()).all()
    return render_template('newsletter.html', notifications=notifications)

