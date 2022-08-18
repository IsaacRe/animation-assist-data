import os
import pandas as pd

from flickr import (
    ImageDownloader,
    PER_PAGE_DEFAULT,
    IMAGES_SUBDIR,
)


LABELS_FILENAME = "images.csv"
IMAGE_IDS_FILENAME = "image_ids.txt"
BUFFER_SIZE_DEFAULT = 1


class ImageLabelWriter:

    def __init__(self, save_path: str):
        self._labels_file_path = os.path.join(save_path, LABELS_FILENAME)
        self._ids_file_path = os.path.join(save_path, IMAGE_IDS_FILENAME)
        self._labels_file_handle = None
        self._ids_file_handle = None
        self._labeled_image_ids = set()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self):
        self.close()

    def _write_header(self):
        self._labels_file_handle.write("flickr_id,image_path,label\n")

    def _load_labeled_image_ids(self):
        with open(self._ids_file_path, "r") as f:
            self._labeled_image_ids = {
                int(id_) for id_ in f.readlines()
            }

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

    def flush(self):
        self._labels_file_handle.flush()
        self._ids_file_handle.flush()

    def check_image_labeled(self, flickr_id: str) -> bool:
        return int(flickr_id) in self._labeled_image_ids

    def label_image(self, flickr_id: str, image_path: str, label: int) -> bool:
        if self.check_image_labeled():
            return False
        self._labeled_image_ids.add(int(flickr_id))
        self._labels_file_handle.write(f"{flickr_id},{image_path},{label}\n")
        self._ids_file_handle.write(f"{flickr_id}\n")
        return True


class LabelImagesController:

    def __init__(
        self,
        download_path: str,
        image_downloader: ImageDownloader,
        per_page: int = PER_PAGE_DEFAULT,
        download_buffer_size: int = BUFFER_SIZE_DEFAULT,
    ):
        self._base_download_path = download_path
        self._session_download_path = None
        self.session_images_path = None
        self._image_downloader = image_downloader
        self._images_iter = None
        self._label_writer = None
        self._per_page = per_page
        self._download_buffer_size = download_buffer_size
        self.search_text = None
        self._image_buffer = []
        self.curr_image_path = None
        self.curr_image_id = None

    def end_session(self):
        self._image_buffer = []
        # TODO cleanup

    def new_session(self, search_text: str):
        self.search_text = search_text
        self._session_download_path = os.path.join(self._base_download_path, search_text.replace(" ", "_"))
        self.session_images_path = os.path.join(self._session_download_path, IMAGES_SUBDIR)
        os.makedirs(self._session_download_path, exist_ok=True)
        self._label_writer = ImageLabelWriter(save_path=self._session_download_path)
        self._image_downloader.new_session(download_path=self._session_download_path)
        self._images_iter = self._image_downloader.iter_photos(
            search_text=search_text,
            per_page=self._per_page,
        )
        self.buffer()

    def buffer(self):
        while len(self._image_buffer) < self._download_buffer_size:
            flickr_id, download_path = next(self._images_iter)
            if self._label_writer.check_image_labeled(flickr_id=flickr_id):
                continue
            self._image_buffer += [(flickr_id, download_path)]

    def next_image(self):
        self.curr_image_id, self.curr_image_path = self._image_buffer.pop(0)
        self.buffer()

    def label(self, label: int):
        self._label_writer.label_image(
            flickr_id=self.curr_image_id,
            image_path=self.curr_image_path,
            label=label,
        )
