from datetime import datetime
from flask import render_template, flash, redirect, url_for, request,  send_from_directory, session,jsonify
from flask import current_app as app
from flask_login import current_user, login_required
from app import db
from app.main.forms import PhotoDirectoryForm, CreateSearchForm, LoadSearchForm
from app.models import User, Photo, PhotoFace, SavedSearch
from app.utils import build_image_paths
from app.main import bp

import os
import warnings
import json


@bp.route('/manage')
def manage():
    pass

# @bp.before_request
# def before_request():
#     if current_user.is_authenticated:
#         current_user.last_seen = datetime.utcnow()
#         db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    path_form = PhotoDirectoryForm()
    create_search_form = CreateSearchForm()
    search_name_list = db.session.query(SavedSearch.id, SavedSearch.name).all()
    load_search_form = LoadSearchForm()
    load_search_form.search_name.choices = search_name_list
    load_search_form_submitted = (load_search_form.slideshow.data or load_search_form.browse.data or
                                  load_search_form.label_faces.data or load_search_form.delete.data)

    if path_form.submit.data and path_form.validate():
        full_path = path_form.path.data
        upload_folder = app.config['UPLOAD_FOLDER']
        try:
            os.symlink(full_path, f'{upload_folder}/{os.path.basename(full_path)}')
        except FileExistsError as e:
            warnings.warn(message=f'caught error:{e}')
        photo_paths = build_image_paths(full_path)
        for photo_path in photo_paths:
            photo = Photo(location=photo_path)
            db.session.add(photo)
        db.session.commit()
        flash('Photos added!')
        return redirect(url_for('main.index'))
    elif create_search_form.create.data and create_search_form.validate():
        #run_now = create_search_form.run_now.data
        name = create_search_form.name.data
        if create_search_form.search_by_people.data:
            people = create_search_form.people.data
        else:
            people = None
        search = SavedSearch(name=name, people=people)
        db.session.add(search)
        db.session.commit()
        flash('Search saved')
        return redirect(url_for('main.index'))
        # if run_now:
        #     if current_user.get_task_in_progress('search_task'):
        #         flash('Search task is currently in progress')
        #     else:
        #         current_user.launch_task('identify_faces_task', 'Identify faces...', name, people, save=True)
        #         db.session.commit()
        #         search_task(search_id)
        #         flash('Search is running. Results will be cached.')
        # else:

    elif load_search_form_submitted and load_search_form.validate():
        selected_search = load_search_form.search_name.data
        if load_search_form.delete.data:
            SavedSearch.query.filter_by(id=selected_search).delete()
            db.session.commit()
            flash('search deleted')
            return redirect(url_for('main.index'))
        else:
            if load_search_form.use_cache.data:
                search_results = SearchResult.get(selected_search)
            else:
                search_results = run_search(SavedSearch.get(selected_search))
            if load_search_form.slideshow.data:
                return redirect(url_for('main.slideshow', search_results=search_results))
            elif load_search_form.browse.data:
                pass
                #return redirect(url_for('main.browse', search_results=search_results))
            elif load_search_form.label_faces.data:
                return redirect(url_for('main.label_faces', search_results=search_results))


    return render_template('index.html', path_form=path_form, create_search_form=create_search_form, load_search_form=load_search_form)

from boolean_parser import parse
def run_search(saved_search):
    saved_search.people
    Photo.query.join(Photo.photo_faces, aliased=False).filter(
        or_(PhotoFace.name.in_(['Zack', 'Erin']), PhotoFace.name.in_(['Z', 'e']))).count()


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
    return render_template('detect_faces.html')

@bp.route('/create_embeddings')
def create_embeddings():
    if current_user.get_task_in_progress('create_embeddings_task'):
        flash('Embedding task is currently in progress')
    else:
        current_user.launch_task('create_embeddings_task', 'Embedding Faces...')
        db.session.commit()
        flash('Embedding task started')
    return redirect(url_for('main.index'))


@bp.route('/identify_faces')
def identify_faces():
    if current_user.get_task_in_progress('identify_faces_task'):
        flash('Identify faces task is currently in progress')
    else:
        current_user.launch_task('identify_faces_task', 'Identify faces...')
        db.session.commit()
        flash('Identify faces task started')
    return redirect(url_for('main.index'))


@bp.route('/label_faces')
@login_required
def label_faces():
    page = request.args.get('page', 1, type=int)
    #TODO make this get list from search or something
    photos = Photo.query.order_by(Photo.id).paginate(page, 1, False)
    photo = photos.items[0]
    #photo_faces = PhotoFace.query.filter_by(photo_id=photo.id).all()
    next_url = url_for('main.label_faces', page=photos.next_num) \
        if photos.has_next else None
    prev_url = url_for('main.label_faces', page=photos.prev_num) \
        if photos.has_prev else None
    face_dictionaries =[]
    #convert the information stored in photo_faces into json friendly dictionaries
    #TODO: figure out better way of preparing for serialization. This fixes numbers but causes booleans become 'True'
    for face in photo.photo_faces:
        face_dictionary = {}
        for column in face.__table__.columns:
            face_dictionary[column.name] = str(getattr(face, column.name))
        face_dictionaries.append(face_dictionary)
    face_json = json.dumps(face_dictionaries)

    return render_template('label_faces.html', photo=photo, face_json=face_json, next_url=next_url, prev_url=prev_url)


@bp.route('/photo_face/<int:id>', methods=['PUT'])
@login_required
def update_photo_face(id):
    photo_face = PhotoFace.query.get(id)
    data = request.get_json()
    #print(request.form)
    photo_face.from_dict(data)
    db.session.commit()
    resp = jsonify(success=True)
    return resp


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


