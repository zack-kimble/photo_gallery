import glob, os, warnings, shutil, pathlib

from PIL import Image

def ignore(dir, files):
    return [f for f in files if os.path.isfile(os.path.join(dir, f)) or not os.access(os.path.join(dir, f), os.R_OK)]

#Todo: honestly just need to diagram both these functions and probably completely rebuild using os.walk and indexes
def add_jpeg_symlinks(source_directory, target_directory):
    pathlib.Path(target_directory).mkdir(exist_ok=True)
    last_common_dir = os.path.basename(source_directory)
    new_root = os.path.basename(target_directory)
    try:
        os.symlink(source_directory, f'{target_directory}/{last_common_dir}')
    except FileExistsError as e:
        warnings.warn(message=f'caught error:{e}')
    #Todo: make this less redundant or at least less messy. From what I could find online, there's not a good way to make glob case insensitive
    sym_paths = glob.glob(source_directory + '/**/*.JPG', recursive=True)
    sym_paths.extend(glob.glob(source_directory + '/**/*.jpg', recursive=True))
    sym_paths.extend(glob.glob(source_directory + '/**/*.JPEG', recursive=True))
    sym_paths.extend(glob.glob(source_directory + '/**/*.jpeg', recursive=True))
    sym_paths = [path.replace(source_directory, os.path.join(new_root,last_common_dir))for path in sym_paths]

    return sym_paths

def convert_copy_tiffs(source_directory, target_directory):
    pathlib.Path(target_directory).mkdir(exist_ok=True)
    last_common_dir = os.path.basename(source_directory)
    new_root = os.path.basename(target_directory)
    files = glob.glob(source_directory + '/**/*.TIFF', recursive=True)
    files.extend(glob.glob(source_directory + '/**/*.tiff', recursive=True))
    files.extend(glob.glob(source_directory + '/**/*.TIF', recursive=True))
    files.extend(glob.glob(source_directory + '/**/*.tif', recursive=True))
    shutil.copytree(source_directory, os.path.join(target_directory,last_common_dir), ignore=ignore, dirs_exist_ok=True, ignore_dangling_symlinks=True)

    target_paths = [os.path.splitext(path)[0].replace(source_directory, last_common_dir)+'.JPG' for path in files]
    for file, target in zip(files, target_paths):
        save_path = os.path.join(target_directory, target)
        im = Image.open(file)
        out = im.convert("RGB")
        out.save(save_path, "JPEG", quality=95)

    db_locations = [os.path.join(new_root,path) for path in target_paths]
    return db_locations

def get_keywords_from_path(photo_path):
    keywords = photo_path.split('/')

def search_creation(name, people):
    pass