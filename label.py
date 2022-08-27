from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import os

from flickr import (
    ImageDownloader,
    PER_PAGE_DEFAULT,
    IMAGES_SUBDIR,
)
from mirror import FileMirror


TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"
DF_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
LABELS_FILENAME = "images.csv"
IMAGE_IDS_FILENAME = "image_ids.txt"
BUFFER_SIZE_DEFAULT = 1


class ImageLabelWriter:

    def __init__(self, save_path: str, backup_file_mirror: FileMirror):
        self._save_path = save_path
        self._labels_file_path = os.path.join(save_path, LABELS_FILENAME)
        self._ids_file_path = os.path.join(save_path, IMAGE_IDS_FILENAME)
        self._backup_file_mirror = backup_file_mirror
        backup_file_mirror.set_upload_path(upload_prefix="")
        self._labels_file_handle = None
        self._ids_file_handle = None
        self._labeled_image_ids = set()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self):
        self.close()

    def _write_header(self):
        self._labels_file_handle.write("flickr_id,image_path,label,timestamp\n")

    def _load_labeled_image_ids(self):
        with open(self._ids_file_path, "r") as f:
            self._labeled_image_ids = {
                int(id_) for id_ in f.readlines()
            }

    def _timestamped_filepath(self, filepath: str, timestamp: datetime):
        filepath, filename = os.path.split(filepath)
        return os.path.join(
            filepath,
            str(timestamp.year),
            str(timestamp.month),
            str(timestamp.day),
            f"{timestamp.strftime(TIMESTAMP_FORMAT)}_{filename}",
        )
    
    def open(self):
        if os.path.exists(self._labels_file_path):
            self._load_labeled_image_ids()
            self._labels_file_handle = open(self._labels_file_path, "a")
            self._ids_file_handle = open(self._ids_file_path, "a")
            return
        self._labels_file_handle = open(self._labels_file_path, "w+")
        self._ids_file_handle = open(self._ids_file_path, "w+")
        self._write_header()
        self.flush()

    def close(self):
        self._labels_file_handle.close()
        self._labels_file_handle = None
        self._ids_file_handle.close()
        self._ids_file_handle = None

    def flush(self):
        self._labels_file_handle.flush()
        self._ids_file_handle.flush()

    def backup(self):
        now = datetime.utcnow()
        self.flush()
        with open(self._labels_file_path, "r") as f:
            data = f.read()
            self._backup_file_mirror.upload_data(
                data=data,
                upload_path=self._timestamped_filepath(self._labels_file_path, now),
                wait_complete=False,
            )
            self._backup_file_mirror.upload_data(
                data=data,
                upload_path=self._labels_file_path,
                wait_complete=False,
            )
        with open(self._ids_file_path, "r") as f:
            data = f.read()
            self._backup_file_mirror.upload_data(
                data=data,
                upload_path=self._timestamped_filepath(self._labels_file_path, now),
                wait_complete=False,
            )
            self._backup_file_mirror.upload_data(
                data=data,
                upload_path=self._ids_file_path,
                wait_complete=False,
            )

    def check_image_labeled(self, flickr_id: str) -> bool:
        return int(flickr_id) in self._labeled_image_ids

    def label_image(self, flickr_id: str, image_path: str, label: int) -> bool:
        label_time = datetime.utcnow()
        if self.check_image_labeled(flickr_id=flickr_id):
            return False
        self._labeled_image_ids.add(int(flickr_id))
        self._labels_file_handle.write(f"{flickr_id},{image_path},{label},{label_time.strftime(DF_TIMESTAMP_FORMAT)}\n")
        self._ids_file_handle.write(f"{flickr_id}\n")
        self.flush()
        return True


class LabelImagesController:

    def __init__(
        self,
        download_path: str,
        image_downloader: ImageDownloader,
        label_writer: ImageLabelWriter,
        executor: ThreadPoolExecutor,
        per_page: int = PER_PAGE_DEFAULT,
        download_buffer_size: int = BUFFER_SIZE_DEFAULT,
    ):
        self._executor = executor
        self._base_download_path = download_path
        self._session_download_path = None
        self.session_images_path = None
        self._image_downloader = image_downloader
        self._images_iter = None
        self._label_writer = label_writer
        self._per_page = per_page
        self._download_buffer_size = download_buffer_size
        self.search_text = None
        self._image_buffer = []
        self.curr_image_path = None
        self._curr_image_remote_path = None
        self.curr_image_id = None
        self._session_up = False
        self.loading = False
        self._buffering_process: Future = None

    def end_session(self):
        if self._session_up:
            self._image_buffer = []
            self._label_writer.close()
            self._image_downloader.end_session()
            self._session_up = False

    def new_session(self, search_text: str):
        self.end_session()
        self.search_text = search_text
        self._session_download_path = os.path.join(self._base_download_path, search_text.replace(" ", "_"))
        self.session_images_path = os.path.join(self._session_download_path, IMAGES_SUBDIR)
        os.makedirs(self._session_download_path, exist_ok=True)
        self._label_writer.open()
        self._image_downloader.new_session(download_path=self._session_download_path)
        self._images_iter = self._image_downloader.iter_photos(
            search_text=search_text,
            per_page=self._per_page,
        )
        self.do_buffer()
        self._session_up = True
        self.next_image()

    def _buffer(self):  # should happen in background
        while len(self._image_buffer) < self._download_buffer_size:
            flickr_id, temp_download_path, remote_download_path = next(self._images_iter)
            if self._label_writer.check_image_labeled(flickr_id=flickr_id):
                continue
            self._image_buffer += [(flickr_id, temp_download_path, remote_download_path)]

    def _clear_buffering_process(self):
        self._buffering_process = None
    
    def do_buffer(self):
        if self._buffering_process is None:
            self._buffering_process = self._executor.submit(self._buffer)
            self._buffering_process.add_done_callback(lambda _: self._clear_buffering_process())

    def next_image(self):
        if not self.loading:
            self.loading = True
            while len(self._image_buffer) == 0:
                self.do_buffer()
            self.curr_image_id, self.curr_image_path, self._curr_image_remote_path = self._image_buffer.pop(0)
            self.do_buffer()
            self.loading = False

    def label(self, label: int):
        self._label_writer.label_image(
            flickr_id=self.curr_image_id,
            image_path=self._curr_image_remote_path,
            label=label,
        )
        self.next_image()
