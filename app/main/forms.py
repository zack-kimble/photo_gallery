from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, StringField, BooleanField, SelectField
from wtforms.validators import DataRequired
from app.models import SavedSearch

class PhotoDirectoryForm(FlaskForm):
    path = TextAreaField('Path for photo directory', validators=[DataRequired()])
    submit = SubmitField('Submit')

class CreateSearchForm(FlaskForm):
    name = StringField('Create Search',validators=[DataRequired()])
    #search_by_people = BooleanField()
    people = StringField('People')
    #search_by_metadata_keywords = BooleanField()
    keywords = StringField('Keywords')
    create = SubmitField('Create')

class LoadSearchForm(FlaskForm):
    search_name = SelectField(coerce=int)
    use_cache = BooleanField()
    ordering = SelectField(choices=[('r','Random'), ('c','Chronological'), ('f','Filename')])
      # [zip(SavedSearch.query.id.all(), SavedSearch.query.name.all())])
    slideshow = SubmitField('Slideshow')
    browse = SubmitField('Browse')
    label_faces = SubmitField('Label')
    delete = SubmitField('Delete')

