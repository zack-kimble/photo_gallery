from datetime import datetime
from flask import render_template, flash, redirect, url_for, request,  send_from_directory, session,jsonify
from flask import current_app as app
from flask_login import current_user, login_required

from app import db
from app.main.forms import PhotoDirectoryForm, CreateSearchForm, LoadSearchForm, FaceProcessingForm
from app.models import User, Photo, PhotoFace, SavedSearch, SearchResults, PhotoMetadata, Task
from app.utils import add_jpeg_symlinks, convert_copy_tiffs
from app.main import bp
from sqlalchemy import and_, or_, not_, text
from sqlalchemy.orm.attributes import flag_modified

#from app.tasks import identify_faces_task, create_embeddings_task, detect_faces_task

from werkzeug.http import HTTP_STATUS_CODES

import os
import warnings
import json
import boolean
import random

@bp.before_app_first_request
def complete_zombie_tasks():
    print("before_app_first_request function ran")
    zombie_tasks = Task.query.filter_by(complete=False).all()
    if len(zombie_tasks) > 0:
        app.logger.info(f"cleaning up {len(zombie_tasks)} zombie tasks")
        for task in zombie_tasks:
            task.complete = True
            task.meta.update({'Zombie task set to complete on restart': True})
            task.meta = task.meta
            flag_modified(task, "meta")
        db.session.commit()

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
@login_required
def index():

    path_form = PhotoDirectoryForm()
    create_search_form = CreateSearchForm()
    search_name_list = db.session.query(SavedSearch.id, SavedSearch.name).all()
    load_search_form = LoadSearchForm()
    load_search_form.search_name.choices = search_name_list
    load_search_form_submitted = (load_search_form.slideshow.data or load_search_form.browse.data or
                                  load_search_form.label_faces.data or load_search_form.delete.data)

    face_processing_form = FaceProcessingForm()
    face_processing_form_submitted = (face_processing_form.detect.data or face_processing_form.embed.data or
                                      face_processing_form.identify.data)

    if path_form.submit.data and path_form.validate():
        #Todo: Handle duplicates. Currently just errors
        source_full_path = path_form.path.data
        # #when running in docker, os seems to still see host path names, but shutils sees the docker ones.
        # if photo_source := app.config['PHOTO_SOURCE']:
        #     app.logger.info(f"replacing {photo_source} in user supplied path for tiffs")
        #     tiff_source_full_path = source_full_path.replace(photo_source, 'photo_source')
        upload_directory = app.config['UPLOAD_FOLDER']
        link_directory = os.path.join(upload_directory, 'linked')
        copy_directory = os.path.join(upload_directory, 'jpg_copy')
        for directory in (link_directory,copy_directory):
            if not os.path.exists(directory):
                os.mkdir(directory)
        photo_paths = add_jpeg_symlinks(source_full_path, link_directory)
        photo_paths.extend(convert_copy_tiffs(source_full_path, copy_directory))
        for photo_path in photo_paths:
            photo = Photo(location=photo_path)

            keywords = photo_path.split('/')
            for keyword in keywords:
                metadata = PhotoMetadata(key='path_keyword',
                                         value=keyword)
                photo.photo_metadata.append(metadata)
            db.session.add(photo)
        db.session.commit()
        flash('Photos added!')
        return redirect(url_for('main.index'))
    elif create_search_form.create.data and create_search_form.validate():
        #run_now = create_search_form.run_now.data
        name = create_search_form.name.data
        people = create_search_form.people.data
        keywords = create_search_form.keywords.data
        search = SavedSearch(name=name, people=people, keywords=keywords)
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
        selected_search_id = load_search_form.search_name.data
        ordering = load_search_form.ordering.data
        #delete button
        if load_search_form.delete.data:
            SavedSearch.query.filter_by(id=selected_search_id).delete()
            db.session.commit()
            flash('search deleted')
            return redirect(url_for('main.index'))
        #all other buttons
        else:
            if not(SearchResults.query.filter_by(search_id=selected_search_id).first() and load_search_form.use_cache.data):
                execute_search(selected_search_id, ordering=ordering)

            if load_search_form.slideshow.data:
                return redirect(url_for('main.slideshow', search_id=selected_search_id))
            elif load_search_form.browse.data:
                pass
                #return redirect(url_for('main.browse', search_results=search_results))
            elif load_search_form.label_faces.data:
                return redirect(url_for('main.label_faces', search_id=selected_search_id))
    elif face_processing_form_submitted and face_processing_form.validate():
        if face_processing_form.detect.data:
            return redirect(url_for('main.detect_faces'))
        elif face_processing_form.embed.data:
            return redirect(url_for('main.create_embeddings'))
        elif face_processing_form.identify.data:
            return redirect(url_for('main.identify_faces'))

    page = request.args.get('page', 1, type=int)
    tasks = current_user.tasks.order_by(Task.date_created.desc()).paginate(1, 10, False)
    next_url = url_for('main.index', page=tasks.next_num) \
        if tasks.has_next else None
    prev_url = url_for('main.index', page=tasks.prev_num) \
        if tasks.has_prev else None

    return render_template('index.html', path_form=path_form, create_search_form=create_search_form,
                           load_search_form=load_search_form, face_processing_form=face_processing_form, tasks=tasks.items,
                           next_url=next_url, prev_url=prev_url)

def parse_values(input):
    input = input.replace(', ', ' and ')
    algebra = boolean.BooleanAlgebra()
    expression = algebra.parse(input).simplify()
    return expression

def boolean_algebra_to_slqalchemy(expression,  child_object, child_table_column):
    '''A bit ugly, converts boolean expression to a sqla BooleanClauseList where each symbol is replaced with .any(child_table_column=symbol)'''
    #TODO: either make this more generic and/or make into a method for Photo
    operator_map = {'AND': and_, 'OR': or_, 'NOT': not_}
    func_for_map = lambda x: boolean_algebra_to_slqalchemy(x, child_object=child_object, child_table_column=child_table_column)
    if isinstance(expression, boolean.boolean.Symbol):
        obj = expression.obj if isinstance(expression.obj, str) else repr(expression.obj)
        return child_object.any(child_table_column.like(f"%{obj}%"))
        #return child_object.any(child_table_column == obj)
    else:
        return operator_map[expression.__class__.__name__](*map(func_for_map, expression.args))

def execute_search(saved_search_id, ordering):
    saved_search = SavedSearch.query.get(saved_search_id)
    #will return all photos if no keywords match
    #TODO make this less ugly and support more possible filters without long list of if/then
    search_filter = and_()
    if saved_search.people:
        people_expression = parse_values(saved_search.people)
        people_filter = boolean_algebra_to_slqalchemy(people_expression, child_object=Photo.photo_faces, child_table_column=PhotoFace.name)
        search_filter = and_(search_filter, people_filter)
    if saved_search.keywords:
        keyword_expression = parse_values(saved_search.keywords)
        keyword_filter = boolean_algebra_to_slqalchemy(expression=keyword_expression, child_object=Photo.photo_metadata, child_table_column=PhotoMetadata.value)
        search_filter = and_(search_filter, keyword_filter)

    #TODO: support something other than random order.
    search_query = Photo.query.with_entities(f"'{saved_search.id}'", Photo.id, "row_number() over(order by random())-1 as order_by").filter(search_filter)
    #Delete existing results for this search_id
    SearchResults.query.filter_by(search_id=saved_search.id).delete()
    #Write results to SearchResults table
    res = db.session.execute(
            SearchResults.__table__
            .insert().from_select(
                names=['search_id', 'photo_id','order_by'],
                select=search_query.selectable))

    db.session.commit()


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


@bp.route('/static_photo')
@login_required
def static_photo():
    return render_template('static_photo.html')



@bp.route('/slideshow')
@login_required
def slideshow():
    search_id = request.args.get('search_id')
    return render_template('slideshow.html', search_id=search_id)

@bp.route('/galleria1')
@login_required
def galleria1():
    return render_template('galleria1.html')

@bp.route('/detect_faces')
@login_required
def detect_faces():
    # flash('Detect faces task started')
    # detect_faces_task(storage_root='app/static/faces')
    # flash("Detect faces task complete")
    if current_user.get_task_in_progress('detect_faces_task'):
        flash('Detection task is currently in progress')
    else:
        current_user.launch_task('detect_faces_task', 'Detecting Faces...', storage_root='app/static/faces')
        db.session.commit()
        flash('Detection task started')
    return redirect(url_for('main.index'))

@bp.route('/create_embeddings')
def create_embeddings():
    # flash('Embedding task started')
    # create_embeddings_task()
    # flash("Embedding task complete")
    if current_user.get_task_in_progress('create_embeddings_task'):
        flash('Embedding task is currently in progress')
    else:
        current_user.launch_task('create_embeddings_task', 'Embedding Faces...')
        db.session.commit()
        flash('Embedding task started')
    return redirect(url_for('main.index'))


@bp.route('/identify_faces')
def identify_faces():
    # flash('Identify faces task started')
    # identify_faces_task()
    # flash("Identify faces task complete")
    if current_user.get_task_in_progress('identify_faces_task'):
        flash('Identify faces task is currently in progress')
    else:
        current_user.launch_task('identify_faces_task', 'Identify faces...')
        db.session.commit()
        flash('Identify faces task started')
    return redirect(url_for('main.index'))

@bp.route('/test_task')
def test_task():
    if current_user.get_task_in_progress('test_task'):
        flash('Test task is currently in progress')
    else:
        current_user.launch_task('test_task', 'Testing..')
        db.session.commit()
        flash('Test task started')
    return redirect(url_for('main.index'))

@bp.route('/label_faces')
@login_required
def label_faces():
    search_id = request.args.get('search_id')
    page = request.args.get('page', 1, type=int)
    # random_order = request.args.get('random', type=bool)
    # if random_order:
    #     next_page =
    #TODO handle no results and add control of ordering
    photos = Photo.query.join(SearchResults).filter_by(search_id=search_id).order_by(SearchResults.order_by).paginate(page, 1, False)
    photo = photos.items[0]
    #photo_faces = PhotoFace.query.filter_by(photo_id=photo.id).all()
    next_url = url_for('main.label_faces', search_id=search_id, page=photos.next_num) \
        if photos.has_next else None
    prev_url = url_for('main.label_faces', search_id=search_id, page=photos.prev_num) \
        if photos.has_prev else None
    face_dictionaries =[]
    #convert the information stored in photo_faces into json friendly dictionaries
    #TODO: figure out better way of preparing for serialization. This fixes numbers but causes booleans become 'True'. Also should maybe add to_dict() mehtod to photo_faces
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

@bp.route('/search/<int:search_id>/results', methods=['GET'])
@login_required
def get_search_results(search_id):
    if request.args.get('get_range'):
        start = int(request.args.get('start'))
        stop = int(request.args.get('stop'))
        app.logger.info(f"search results for range start: {start}, stop: {stop}")
        photos = SearchResults.query.filter_by(search_id=search_id).filter(SearchResults.order_by.between(start, stop)).all()
        app.logger.info(f"{len(photos)} results")
        data = [photo.to_dict() for photo in photos]
        galleria_name_map = {'image': 'url', 'title': 'location'}
        for photo in data:
            for k, v in galleria_name_map.items():
                photo[k] = photo.pop(v)
        return jsonify(data)
    else:
        return bad_request("only works for request for get_range with start and stop values")

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

def error_response(status_code, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response

def bad_request(message):
    return error_response(400, message)
