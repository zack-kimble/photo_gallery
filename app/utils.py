import glob
import os

def build_image_paths(directory_path):
    last_common_dir = os.path.basename(directory_path)
    files = glob.glob(directory_path + '/**/*.JPG', recursive=True) #TODO: look for lowercase .jpg  also
    files = [file.replace(directory_path,f'{last_common_dir}') for file in files]
    return files