#!/usr/bin/env python
from datetime import datetime, timedelta
import unittest, pytest, tempfile, os
from app import create_app, db
from app.models import User, Photo, PhotoFace, Task
from config import Config
from app.tasks import detect_faces_task, create_embeddings_task
from flask import session, g
from flask_login import current_user
from app.main.routes import detect_faces

from webtest import TestApp
#from pytest_mock import mocker

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

    yield app

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])

@pytest.fixture(scope='module')
def client(app):
    return app.test_client()

@pytest.fixture(scope='module')
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def testapp(app):
    """Create Webtest app."""
    return TestApp(app)


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

def test_PhotoDirectoryForm(testapp, init_database):
    rv = testapp.get('/')
    form = rv.forms[0] #can't figure out where to name the form so it shows up here
    form['path'] = '/home/zack/PycharmProjects/photo_gallery/test_assets/client_files'
    result = form.submit()
    assert Photo.query.count() == 243
    Photo.query.delete()
    db.session.commit()

@pytest.fixture(scope='module')
def populate_test_photos(init_database):
    photo1 = Photo(location='Kacey_Musgraves.jpg')
    photo2 = Photo(location='Tom_Petty.jpg')
    photo3 = Photo(location='Twin.jpg')
    db.session.add_all([photo1, photo2, photo3])
    db.session.commit()
    yield db
    Photo.query.delete()
    db.session.commit()

@pytest.fixture()
def login(testapp):
    res = testapp.get("/auth/login")
    form = res.forms[0]
    form["username"] = 'test'
    form["password"] = "test"
    # Submits
    res = form.submit()

def test_detect_faces_route(testapp, client, login, init_database):
    result = testapp.get('/detect_faces')
    assert Task.query.filter_by(name='detect_faces_task').count() == 1
    result = testapp.get('/detect_faces')
    assert Task.query.filter_by(name='detect_faces_task').count() == 1

def test_detect_faces_task(client, init_database, populate_test_photos):
    detect_faces_task(storage_root='test_assets/faces')
    assert PhotoFace.query.count() == 4

def test_photo_face(testapp,login,init_database):
    rv = testapp.put_json('/photo_face/1', dict(name='Erin', name_auto=False))
    assert PhotoFace.query.get(1).name == 'Erin'

def test_create_faces_route(testapp, login, init_database):
    result = testapp.get('/create_embeddings')
    assert Task.query.filter_by(name='create_embeddings_task').count() == 1
    result = testapp.get('/create_embeddings')
    assert Task.query.filter_by(name='create_embeddings_task').count() == 1

def test_create_embeddings_task(client, init_database, populate_test_photos):
    create_embeddings_task()
    assert PhotoFace.query.first().embedding is not None