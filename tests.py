#!/usr/bin/env python
from datetime import datetime, timedelta
import unittest, pytest, tempfile, os, glob, shutil
os.environ["PYTEST"] = 'true'

from app import create_app, db
from app.models import User, Photo, PhotoFace, Task, SavedSearch, SearchResults
from config import Config
from app.tasks import detect_faces_task, create_embeddings_task, identify_faces_task
from flask import session, g
from flask_login import current_user
from app.main.routes import detect_faces
import shutil
from webtest import TestApp
from app.utils import ignore
#from pytest_mock import mocker
from sqlalchemy import text

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    ELASTICSEARCH_URL = None
    UPLOAD_FOLDER = 'test_assets/uploads'
    USERNAME = 'test'
    PASSWORD = 'test'
    #LOGIN_DISABLED = True
    WTF_CSRF_ENABLED = False



@pytest.fixture(scope='module')
def app():

    app = create_app(TestConfig)
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.app_context().push()
    print(app.config['DATABASE'])
    app.logger.info(f"testing db location: {app.config['DATABASE']}")

    yield app

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()

@pytest.fixture(scope='module')
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(scope='module')
def testapp(app, init_database):
    """Create Webtest app."""
    testapp = TestApp(app)
    #testapp = TestApp(app, extra_environ=dict(REMOTE_USE='test'))
    # testapp.set_authorization(('Basic', (app.config['USERNAME'],app.config['PASSWORD'])))
    # testapp.get_authorization()
    return testapp


@pytest.fixture(scope='module')
def init_database(app):
    # Create the database and the database table
    db.create_all()

    # Insert user data
    test_user = User(email='test@nowhere.nowhere', username=app.config['USERNAME'])
    test_user.set_password(app.config['PASSWORD'])
    db.session.add(test_user)
    db.session.commit()

    yield db  # this is where the testing happens!

    db.drop_all()

#@pytest.fixture(scope='module')
def test_PhotoDirectoryForm(testapp, init_database, login):
    #testapp.get_authorization()
    rv = testapp.get('/')
    form = rv.forms['photo_directory_form'] #can't figure out where to name the form so it shows up here.
    form['path'] = '/home/zack/PycharmProjects/photo_gallery/test_assets/client_files'
    result = form.submit(name='submit')
    assert Photo.query.count() == 246
    assert Photo.query.filter(Photo.location.like("%0456%")).first().location=='jpg_copy/client_files/test_tiff_directory/test_dir/DSC_0456.JPG'
    for root, dirs, files in os.walk('test_assets/uploads'):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
    Photo.query.delete()
    db.session.commit()

    #todo: test skipping existing tiffs

@pytest.fixture(scope='module')
def create_test_search(testapp, init_database):
    rv = testapp.get('/')
    form = rv.forms[2]  # can't figure out where to name the form so it shows up here
    form['name'] = 'Kacey'
    form['people'] = 'Kacey'
    result = form.submit(name='create')
    assert SavedSearch.query.filter_by(name='Kacey').first()

@pytest.fixture(scope='module')
def populate_test_photos(init_database):
    shutil.copytree('test_assets/face_processing_tests','test_assets/uploads', dirs_exist_ok =True)
    photo1 = Photo(location='Kacey_Musgraves.jpg')
    photo2 = Photo(location='Tom_Petty.jpg')
    photo3 = Photo(location='Twin.jpg')
    photo4 = Photo(location='Kacey_Musgraves_2.jpg')
    db.session.add_all([photo1, photo2, photo3, photo4])
    db.session.commit()

    yield db
    Photo.query.delete()
    db.session.commit()

@pytest.fixture(scope='module')
def login(testapp):
    res = testapp.get("/auth/login")
    form = res.forms[0]
    form["username"] = 'test'
    form["password"] = "test"
    # Submits
    res = form.submit()


@pytest.fixture(scope='module')
def test_detect_faces_route(testapp, client, init_database, login):
    result = testapp.get('/detect_faces')
    assert Task.query.filter_by(name='detect_faces_task').count() == 1
    result = testapp.get('/detect_faces')
    assert Task.query.filter_by(name='detect_faces_task').count() == 1

#these tests need to be executed in a particular order.  Right now pytest-order would work, but I went with chaining them as fixtures so the dependencies would be explicit if things become less linear.
@pytest.fixture(scope='module')
def test_detect_faces_task(app, init_database, populate_test_photos):
    detect_faces_task(storage_root='test_assets/faces', outer_batch_size=2)
    assert PhotoFace.query.count() == 5

@pytest.fixture(scope='module')
def test_photo_face(testapp,init_database, login, test_detect_faces_task):
    rv = testapp.put_json('/photo_face/1', dict(name='Kacey', name_auto=False))
    rv = testapp.put_json('/photo_face/2', dict(name='Tom', name_auto=False))
    assert PhotoFace.query.get(1).name == 'Kacey'
    assert PhotoFace.query.get(2).name == 'Tom'

@pytest.fixture(scope='module')
def test_create_embeddings_route(testapp, login, init_database, test_detect_faces_task):
    result = testapp.get('/create_embeddings')
    assert Task.query.filter_by(name='create_embeddings_task').count() == 1
    result = testapp.get('/create_embeddings')
    assert Task.query.filter_by(name='create_embeddings_task').count() == 1

@pytest.fixture(scope='module')
def test_create_embeddings_task(client, init_database, populate_test_photos, test_detect_faces_task):
    create_embeddings_task()
    assert len(PhotoFace.query.first().embedding) > 0

@pytest.fixture(scope='module')
def test_identify_faces_task(client, init_database, populate_test_photos, test_create_embeddings_task, test_photo_face):
    #Create manual labels moved to test_photo_face
    # kacey = Photo.query.filter(text("photo.location like '%Kacey%'")).first().photo_faces
    # tom = Photo.query.filter(text("photo.location like '%Tom%'")).first().photo_faces
    # kacey.name = 'Kacey'
    # tom.name = 'Tom'

    identify_faces_task()
    assert PhotoFace.query.get(5).name == 'Kacey'

#TODO: need to either run after identify or create setup to add matching photofaces
@pytest.fixture()
def test_search_execution(testapp, create_test_search,test_identify_faces_task):
    rv = testapp.get('/')
    form = rv.forms[3]  # can't figure out where to name the form so it shows up here
    form['search_name'] = 1
    form['use_cache'] = False
    form['ordering'] = 'c'
    result = form.submit(name='browse')
    assert SearchResults.query.filter_by(search_id=1).first()


#def test_label_page(testapp, )

def test_get_search_results(testapp, test_search_execution):
    rv = testapp.get('/search/1/results?start=1&stop=2&get_range=true')

# couldn't find a way to check for access .Trashes properly in the ignore function. Just try/except copytree now, so this test doesn't matter anymore
# def test_ignore_function():
#     shutil.copytree('test_assets/copytree_test', 'test_assets/copytree_test_output', ignore=ignore, dirs_exist_ok=True)
#     assert len(os.listdir('test_assets/copytree_test_output'))==1