import os
from typing import Iterable, List
import requests
from flask import current_app

from .mirror import FileMirror
from flickrapi import FlickrAPI
from .util import (
    MAX_TAKEN_DATE,
    PER_PAGE_DEFAULT,
    ImageSearch,
)

SEARCH_METADATA_FILENAME = "previous_search.json"
IMAGES_SUBDIR = "images"


class ImageDownloader:
    def __init__(self, api_key: str, api_secret: str, file_mirror: FileMirror, temp_file_mirror: FileMirror):
        self._api_key = api_key
        self._api_secret = api_secret
        self._flickrapi = FlickrAPI(api_key, api_secret, token_cache_location=os.getenv("FLICKR_CACHE"))
        self._file_mirror = file_mirror
        self._temp_file_mirror = temp_file_mirror
        self._current_search = None

    def end_session(self):
        current_app.logger.debug("ImageDownloader - session ended")
        self._current_search = None

    def new_session(self, download_path: str, search: ImageSearch):
        current_app.logger.debug("ImageDownloader - new session")
        mirror_path = os.path.join(download_path, IMAGES_SUBDIR)
        os.makedirs(mirror_path, exist_ok=True)
        self._file_mirror.set_upload_path(upload_prefix=mirror_path)
        self._temp_file_mirror.set_upload_path(upload_prefix=mirror_path)
        self._current_search = search

    def _get_download_link(self, photo_id: str, size_label: str = "Original") -> str:
        current_app.logger.debug(f"Getting download options for photo {photo_id}")
        sizes = self._flickrapi.photos.getSizes(photo_id=photo_id, format="parsed-json")
        current_app.logger.debug("Done")
        max_size_link = None
        max_size = 0
        size_label_used = None
        for size in sizes["sizes"]["size"]:
            if size["label"] == size_label:
                return size["source"], size_label
            image_size = size["width"] * size["height"]
            if image_size > max_size:
                max_size = image_size
                max_size_link = size["source"]
                size_label_used = size["label"]
        return max_size_link, size_label_used

    @staticmethod
    def _make_filename(photo_id: str, size_label: str, file_format: str = "jpg"):
        return f"{photo_id}_{size_label.replace(' ', '_')}.{file_format}"

    def download_photo(self, photo_id: str):
        link, size = self._get_download_link(photo_id=photo_id)
        current_app.logger.debug(f"Downloading from {link}...")
        data = requests.get(link, headers={"Content-Type": "image/jpg"}).content
        current_app.logger.debug("Done")
        return data, size

    def save_photo(self, photo: bytes, photo_id: str, photo_size: str, file_format: str = "jpg"):
        upload_path = self._make_filename(photo_id=photo_id, size_label=photo_size, file_format=file_format)
        return (
            self._temp_file_mirror.upload_data(
                data=photo,
                upload_path=upload_path,
            ),
            self._file_mirror.upload_data(
                data=photo,
                upload_path=upload_path,
                wait_complete=False,
            )
        )

    def download_and_save_photo(self, photo_id: str, file_format: str = "jpg") -> str:
        img, size = self.download_photo(photo_id=photo_id)
        return self.save_photo(photo=img, photo_id=photo_id, photo_size=size, file_format=file_format)
    
    def search_photos(self, search_text: str, per_page: int = PER_PAGE_DEFAULT, page: int = 0, max_taken_date: int = MAX_TAKEN_DATE) -> List[str]:
        current_app.logger.debug(f"Searching for photos: '{search_text}', page {page}")
        photos = self._flickrapi.photos.search(text=search_text, per_page=per_page, page=page + 1, format="parsed-json", max_taken_date=max_taken_date)
        current_app.logger.debug("Done")
        return [photo["id"] for photo in photos["photos"]["photo"]]

    def iter_photos(self) -> Iterable:
        assert self._current_search is not None, "search has not been initializied"
        page = self._current_search.last_page_idx
        start_image = self._current_search.last_image_idx
        while True:
            for i, photo_id in enumerate(
                self.search_photos(
                    search_text=self._current_search.query,
                    per_page=self._current_search.per_page,
                    page=page,
                    max_taken_date=self._current_search.max_taken_date,
                )
            ):
                if i < start_image:
                    continue
                yield photo_id, *self.download_and_save_photo(photo_id=photo_id)
            page += 1
            start_image = 0
