#!/usr/bin/env python
from datetime import datetime, timedelta
import unittest, pytest
from app import create_app, db
from app.models import User, Photo, PhotoFace
from config import Config
from app.tasks import detect_faces_task


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    ELASTICSEARCH_URL = None
    UPLOAD_FOLDER = 'test_assets/uploads'

class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


    def test_password_hashing(self):
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

# if __name__ == '__main__':
#     unittest.main(verbosity=2)

@pytest.fixture(scope='module')
def test_client():
    app = create_app(TestConfig)
    testing_client = app.test_client()

    app_context = app.app_context()
    app_context.push()

    yield testing_client  # this is where the testing happens!

    app_context.pop()


@pytest.fixture(scope='module')
def init_database():
    # Create the database and the database table
    db.create_all()

    # Insert user data
    test_user = User(email='test@nowhere.nowhere',username='test')
    test_user.set_password('password')
    db.session.add(test_user)
    db.session.commit()

    yield db  # this is where the testing happens!

    db.drop_all()

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

def test_fixtures(test_client, init_database, populate_test_photos):
    assert Photo.query.filter_by(id=1).first().location == 'Kacey_Musgraves.jpg'

def test_detect_faces_task(test_client, init_database, populate_test_photos):
    detect_faces_task(storage_root='test_assets/faces')
    assert PhotoFace.query.count() == 4