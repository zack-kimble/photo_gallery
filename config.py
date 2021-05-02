import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'database/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    POSTS_PER_PAGE = 25
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    #TODO Need better way to handle this. RQ doesn't get env from .flaskenv, so probably need to control env elsewhere
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.getcwd(),'uploads') #'/photo_gallery/uploads'
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    #PHOTO_SOURCE = os.environ.get('PHOTO_SOURCE')
    #SQLALCHEMY_ECHO = True