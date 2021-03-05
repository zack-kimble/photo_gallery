from datetime import datetime
from hashlib import md5
from time import time

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import redis
import rq
from app import db, login
# from app.search import add_to_index, remove_from_index, query_index
from sqlalchemy import types
import numpy as np
import io


class ArrayType(types.TypeDecorator):
    impl = types.BLOB

    # def __repr__(self):
    #     return self.impl.__repr__()

    def process_bind_param(self, value, dialect):
        out = io.BytesIO()
        np.save(out, value)
        out.seek(0)
        return out.read()

    def process_result_value(self, value, dialect):
        out = io.BytesIO(value)
        out.seek(0)
        return np.load(out)





class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def launch_task(self, name, description, *args, **kwargs):
        print(name, description)
        print(*args)
        # for k,v in kwargs.items():
        #     print(k,':',v)

        rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# class SearchableMixin(object):
#     @classmethod
#     def search(cls, expression, page, per_page):
#         ids, total = query_index(cls.__tablename__, expression, page, per_page)
#         if total == 0:
#             return cls.query.filter_by(id=0), 0
#         when = []
#         for i in range(len(ids)):
#             when.append((ids[i], i))
#         return cls.query.filter(cls.id.in_(ids)).order_by(
#             db.case(when, value=cls.id)), total
#
#     @classmethod
#     def before_commit(cls, session):
#         session._changes = {
#             'add': list(session.new),
#             'update': list(session.dirty),
#             'delete': list(session.deleted)
#         }
#
#     @classmethod
#     def after_commit(cls, session):
#         for obj in session._changes['add']:
#             if isinstance(obj, SearchableMixin):
#                 add_to_index(obj.__tablename__, obj)
#         for obj in session._changes['update']:
#             if isinstance(obj, SearchableMixin):
#                 add_to_index(obj.__tablename__, obj)
#         for obj in session._changes['delete']:
#             if isinstance(obj, SearchableMixin):
#                 remove_from_index(obj.__tablename__, obj)
#         session._changes = None
#
#     @classmethod
#     def reindex(cls):
#         for obj in cls.query:
#             add_to_index(cls.__tablename__, obj)


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String, unique=True, index=True)
    photo_metadata = db.relationship('PhotoMetadata')
    photo_faces = db.relationship('PhotoFace')


class PhotoMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    photo = db.relationship("Photo", back_populates='photo_metadata')
    key = db.Column(db.String, index=True)
    value = db.Column(db.String, index=True)


class PhotoFace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.Integer, unique=True, nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    bb_x1 = db.Column(db.NUMERIC, nullable=False)
    bb_y1 = db.Column(db.NUMERIC, nullable=False)
    bb_x2 = db.Column(db.NUMERIC, nullable=False)
    bb_y2 = db.Column(db.NUMERIC, nullable=False)
    bb_prob = db.Column(db.NUMERIC, nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    photo = db.relationship("Photo", back_populates='photo_faces')
    bb_auto = db.Column(db.BOOLEAN)
    name = db.Column(db.VARCHAR)
    name_auto = db.Column(db.BOOLEAN)
    embedding = db.relationship('FaceEmbedding')

    def from_dict(self, data):
        for field in data:
            setattr(self, field, data[field])


class FaceEmbedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # embedding = db.Column(db.JSON)
    embedding = db.Column(ArrayType)
    photo_face_id = db.Column(db.Integer, db.ForeignKey('photo_face.id'), unique=True)


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    progress = db.Column(db.NUMERIC)
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

class SavedSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    people = db.Column(db.String)

class SearchResults(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('saved_search.id'))
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    order_by = db.Column(db.Integer, index=True)