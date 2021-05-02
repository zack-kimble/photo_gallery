from app import create_app, db
from app.models import User, Photo, Task, PhotoFace, FaceEmbedding, SavedSearch, SearchResults

app = create_app()
app.run()
print('running photo_gallery.py')

@app.shell_context_processor
def make_shell_context():
    print('importing context')
    return {'db': db, 'User': User, 'Photo': Photo, 'Task': Task, 'PhotoFace':PhotoFace, 'FaceEmbedding': FaceEmbedding,\
            'SavedSearch': SavedSearch, 'SearchResults': SearchResults, 'Task': Task}
