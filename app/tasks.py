import os
import sys

import torch
from PIL import Image
from facenet_pytorch import MTCNN, training
from facenet_pytorch.models.utils.detect_face import save_img
from rq import get_current_job
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.datasets.folder import pil_loader

from app import create_app, Config
from app import db
from app.models import Photo, PhotoFace, Task, FaceEmbedding


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    ELASTICSEARCH_URL = None
    UPLOAD_FOLDER = 'test_assets/uploads'


if os.environ.get('PYTEST'):
    app = create_app(TestConfig)
    app.app_context().push()
else:
    app = create_app()
    app.app_context().push()


# Making dataset return image and path instead of image and label. Probably better to just stop using Dataset and Dataloader at some point, but whatever
class ImagePathsDataset(Dataset):
    def __init__(self, data, loader=pil_loader, transform=lambda x: x):
        self.data = data
        self.loader = loader
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        orig_path = self.data[idx]
        img = self.loader(orig_path)
        if self.transform is not None:
            img = self.transform(img)
        return img, orig_path


def exif_rotate_pil_loader(path):
    with open(path, 'rb') as f:
        image = Image.open(f)
        image = reorient_image(image)
        image = image.convert('RGB')  # replicates pil_loader from torchvision. Copies to convert to PIL
    return image


def reorient_image(im):
    try:
        image_exif = im._getexif()
        image_orientation = image_exif[274]
        if image_orientation in (2, '2'):
            return im.transpose(Image.FLIP_LEFT_RIGHT)
        elif image_orientation in (3, '3'):
            return im.transpose(Image.ROTATE_180)
        elif image_orientation in (4, '4'):
            return im.transpose(Image.FLIP_TOP_BOTTOM)
        elif image_orientation in (5, '5'):
            return im.transpose(Image.ROTATE_90).transpose(Image.FLIP_TOP_BOTTOM)
        elif image_orientation in (6, '6'):
            return im.transpose(Image.ROTATE_270)
        elif image_orientation in (7, '7'):
            return im.transpose(Image.ROTATE_270).transpose(Image.FLIP_TOP_BOTTOM)
        elif image_orientation in (8, '8'):
            return im.transpose(Image.ROTATE_90)
        else:
            return im
    except (KeyError, AttributeError, TypeError, IndexError):
        return im


def mtcnn_detect_faces(images):
    batch_size = 16
    workers = 0 if os.name == 'nt' else 8

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    mtcnn = MTCNN(
        image_size=112,
        margin=10,
        min_face_size=20,
        thresholds=[0.6, 0.7, 0.7],
        factor=0.709,
        post_process=False,
        keep_all=True,
        device=device
    )

    img_ds = ImagePathsDataset(images, loader=exif_rotate_pil_loader, transform=transforms.Resize((1024, 1024)))

    loader = DataLoader(
        img_ds,
        num_workers=workers,
        batch_size=batch_size,
        collate_fn=training.collate_pil
    )

    paths = []
    boxes = []
    box_probs = []
    faces = []

    for i, (x, b_paths) in enumerate(loader):
        # save_paths = [photo_path.replace('test_assets/uploads', storage_root) for photo_path in b_paths]
        # face_path = [p.replace(os.path.basename(p), os.path.basename(p) + '_face') for p in b_paths]
        b_boxes, b_box_probs, points = mtcnn.detect(x, landmarks=True)

        b_faces = mtcnn.extract(x, b_boxes, save_path=None)

        boxes.extend(b_boxes)
        box_probs.extend(b_box_probs)
        paths.extend(b_paths)
        faces.extend(b_faces)

    return paths, boxes, box_probs, faces


def get_arcface_embeddings(images):
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    print('Running on device: {}'.format(device))
    batch_size = 16
    workers = 0 if os.name == 'nt' else 8

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    img_ds = ImagePathsDataset(images, transform=transform)
    loader = DataLoader(img_ds, num_workers=workers,
                        batch_size=batch_size)

    from app.insightface import model_loader

    model = model_loader()
    model = model.to(device)
    model.eval()

    embeddings = []
    img_paths = []

    with torch.no_grad():
        for xb, img_path in loader:
            xb = xb.to(device)
            b_embeddings = model(xb)
            b_embeddings = b_embeddings.to('cpu').numpy()

            embeddings.extend(b_embeddings)
            img_paths.extend(img_path)

    return embeddings


def store_face(face, save_path):
    os.makedirs(os.path.dirname(save_path) + "/", exist_ok=True)
    save_img(face, save_path)


def detect_faces_task(storage_root):
    # TODO Not sure about the try/except wrapping here.
    try:
        # get image data from db
        photos_result = Photo.query.all()  # replace with query based on something from request
        photo_id_list, photo_paths_list = list(zip(*[(photo.id, photo.location) for photo in photos_result]))

        # get paths figured out - doing this here instead of in the mtcnn wrapper. Should be fine since the dataloader is sequential
        load_paths_list = [os.path.join(app.config['UPLOAD_FOLDER'], photo_path) for photo_path in photo_paths_list]
        # save_paths_list = [os.path.join(storage_root, photo_path) for photo_path in photo_paths_list]

        paths_list, boxes_list, box_probs_list, faces_list = mtcnn_detect_faces(load_paths_list)
        face_meta_list = []

        for photo_id, path, boxes, probs, faces in zip(photo_id_list, photo_paths_list, boxes_list, box_probs_list,
                                                       faces_list):
            image_path, ext = os.path.splitext(path)
            if faces is not None:
                faces = list(transforms.functional.to_pil_image(x * 255) for x in faces.unbind())
                for i, (box, prob, face) in enumerate(zip(boxes, probs, faces)):
                    save_path = storage_root + '/' + image_path + '_' + str(i) + ext
                    db_face = PhotoFace(location=save_path,
                                        sequence=i,
                                        bb_x1=box[0],
                                        bb_y1=box[1],
                                        bb_x2=box[2],
                                        bb_y2=box[3],
                                        bb_prob=prob,
                                        photo_id=photo_id,
                                        bb_auto=True
                                        )
                    db.session.add(db_face)
                    store_face(face, save_path)
        db.session.commit()


    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        raise ChildProcessError
    finally:
        _set_task_progress(100)


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.progress = progress
        if progress >= 100:
            task.complete = True
        db.session.commit()


def create_embeddings_task():
    try:
        faces_result = PhotoFace.query.all()
        face_id_list, face_paths_list = list(zip(*[(face.id, face.location) for face in faces_result]))
        face_embeddings = get_arcface_embeddings(face_paths_list)
        for id, embedding in zip(face_id_list, face_embeddings):
            face_embedding = FaceEmbedding(embedding=embedding, photo_face_id=id)
            db.session.add(face_embedding)
        db.session.commit()
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
        raise ChildProcessError
    finally:
        _set_task_progress(100)
