from app import create_app, db
from app.models import User, Photo, Task, PhotoFace, FaceEmbedding

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Photo': Photo, 'Task': Task, 'PhotoFace':PhotoFace, 'FaceEmbedding': FaceEmbedding}
