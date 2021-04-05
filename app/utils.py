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

#TODO this function is way too messy. As coded if something fails between saving the file and registering, then subsequent runs will skip those photos, adn they can't be added to the db. To prevent this requires a list of all files in the db, which could be huge and just doesn't belong here\
# Frankly this just needs to be moved out of routes and done from command line
def convert_copy_tiffs(source_directory, target_directory):
    pathlib.Path(target_directory).mkdir(exist_ok=True)
    last_common_dir = os.path.basename(source_directory)
    new_root = os.path.basename(target_directory)
    files = glob.glob(source_directory + '/**/*.TIFF', recursive=True)
    files.extend(glob.glob(source_directory + '/**/*.tiff', recursive=True))
    files.extend(glob.glob(source_directory + '/**/*.TIF', recursive=True))
    files.extend(glob.glob(source_directory + '/**/*.tif', recursive=True))
    #TODO figure this out
    #somehow this is still causing errors on directories where it doesn't have permissions despite ignore, but only on mac. Checked the .Trashes and other hidden directories and they are -rwxrwxrwx, so not sure what the deal is.
    #Anyway, wrapping in try except. Will just log the shutil.Errors at end.
    try:
        shutil.copytree(source_directory, os.path.join(target_directory,last_common_dir), ignore=ignore, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    except shutil.Error as e:
        Warning(f'copytree completed, but ran into some errors:{e}')
    target_paths = [os.path.splitext(path)[0].replace(source_directory, last_common_dir)+'.JPG' for path in files]
    #db_locations = [os.path.join(new_root, path) for path in target_paths]
    db_locations = []
    for i, (file, target) in enumerate(zip(files, target_paths)):
        try:
            save_path = os.path.join(target_directory, target)
            if os.path.exists(save_path):
                continue
            im = Image.open(file)
            out = im.convert("RGB")
            out.save(save_path, "JPEG", quality=95)
            db_locations.append(os.path.join(new_root, target))
        except Exception as e:
            warnings.warn(f'could not convert {file} to jpg. Error: {e}')
    return db_locations

def get_keywords_from_path(photo_path):
    keywords = photo_path.split('/')

def search_creation(name, people):
    pass