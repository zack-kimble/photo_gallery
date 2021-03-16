import glob
import os
from boolean_parser import parse

def build_image_paths(directory_path):
    last_common_dir = os.path.basename(directory_path)
    files = glob.glob(directory_path + '/**/*.JPG', recursive=True) #TODO: look for lowercase .jpg  also
    files.extend(glob.glob(directory_path + '/**/*.jpg', recursive=True) )
    files = [file.replace(directory_path,f'{last_common_dir}') for file in files]
    return files

def get_keywords_from_path(photo_path):
    keywords = photo_path.split('/')

def search_creation(name, people):
    pass