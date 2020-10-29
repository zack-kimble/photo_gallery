from datetime import datetime
from flask import render_template, flash, redirect, url_for, request,  send_from_directory
from flask import current_app as app
from flask_login import current_user, login_required
from app import db
from app.main.forms import PhotoDirectoryForm
from app.models import User, Photo
from app.utils import build_image_paths
from app.main import bp

import os
import warnings

@bp.route('/manage')
def manage():
    pass

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    path_form = PhotoDirectoryForm()
    if path_form.validate_on_submit():
        full_path = path_form.path.data
        upload_folder = app.config['UPLOAD_FOLDER']
        try:
            os.symlink(full_path, f'{upload_folder}/{os.path.basename(full_path)}')
        except FileExistsError as e:
            warnings.warn(message=e)
        photo_paths = build_image_paths(full_path)
        for photo_path in photo_paths:
            photo = Photo(location=photo_path)
            db.session.add(photo)
            db.session.commit()
        flash('Photos added!')
        return redirect(url_for('main.index'))
    return render_template('index.html', path_form=path_form)

@bp.route('/photos/<path:filename>')
@login_required
def photos(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# #TODO: reminder this is completely unsafe other than when running locally
# @bp.route('/slideshow', methods=['GET','POST'])
# @login_required
# def slideshow():
#     img = request.args.get('img', type=str)
#     if not img:
#         img = Photo.query.first().location
#     return send_from_directory(os.path.dirname(img), os.path.basename(img))

@bp.route('/slideshow', methods=['GET','POST'])
@login_required
def slideshow():
    img = request.args.get('img', type=str)
    if not img:
        img = Photo.query.first().location
    return render_template('slideshow.html', img=img)

@bp.route('/galleria')
@login_required
def galleria():
    return render_template('galleria.html')

@bp.route('/galleria1')
@login_required
def galleria1():
    return render_template('galleria1.html')

@bp.route('/detect_faces')
@login_required
def detect_faces():
    if current_user.get_task_in_progress('detect_faces_task'):
        flash('Detection task is currently in progress')
    else:

        current_user.launch_task('detect_faces_task', 'Detecting Faces...', storage_root='app/static/faces')
        db.session.commit()
        flash('Detection task started')
    return redirect(url_for('main.index'))

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
