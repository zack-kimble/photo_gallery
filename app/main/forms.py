from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired

class PhotoDirectoryForm(FlaskForm):
    path = TextAreaField('Path for photo directory', validators=[DataRequired()])
    submit = SubmitField('Submit')