from dataclasses import dataclass
import os
from typing import Iterable, List, Tuple
import requests
import json

from util.yaml_parse import load_yaml
from mirror import FileMirror
from flickrapi import FlickrAPI

MAX_TAKEN_DATE = 1660730319
SEARCH_METADATA_FILENAME = "previous_search.json"
PER_PAGE_DEFAULT = 50
IMAGES_SUBDIR = "images"


class ImageDownloader:
    def __init__(self, secret_file: str, file_mirror: FileMirror):
        api_key, api_secret = self._load_api_key(secret_file)
        self._api_key = api_key
        self._api_secret = api_secret
        self._flickrapi = FlickrAPI(api_key, api_secret)
        self._file_mirror = file_mirror
        self._search_metadata_file = None
        self._previous_search_metadata = None

    def end_session(self):
        self._search_metadata_file = None
        self._previous_search_metadata = None

    def new_session(self, download_path: str):
        self._search_metadata_file = os.path.join(download_path, SEARCH_METADATA_FILENAME)
        mirror_path = os.path.join(download_path, IMAGES_SUBDIR)
        os.makedirs(mirror_path, exist_ok=True)
        self._file_mirror.set_upload_path(upload_prefix=mirror_path)
        self._load_search_metadata()

    @staticmethod
    def _load_api_key(secret_file: str) -> Tuple[str, str]:
        yaml_file = load_yaml(file_path=secret_file)
        return yaml_file["api_key"], yaml_file["api_secret"]

    def _load_search_metadata(self):
        if os.path.exists(self._search_metadata_file):
            with open(self._search_metadata_file, "r") as f:
                self._previous_search_metadata = json.load(f)

    def _save_search_metadata(self, per_page: int, search_text: str, last_page: int):
        self._previous_search_metadata = {
            "per_page": per_page,
            "search_text": search_text,
            "last_page": last_page,
        }
        with open(self._search_metadata_file, "w+") as f:
            json.dump(self._previous_search_metadata, f)

    def _compare_search_metadata(self, per_page: int, search_text: str):
        return (
            self._previous_search_metadata is None
            or (
                self._previous_search_metadata["per_page"] == per_page
                and self._previous_search_metadata["search_text"] == search_text
            )
        )

    def _get_next_page(self, per_page: int, search_text: str) -> int:
        if self._previous_search_metadata is None:
            return 0
        else:
            if not self._compare_search_metadata(per_page=per_page, search_text=search_text):
                raise Exception("Mismatch between previous setting of per_page")
            return self._previous_search_metadata["last_page"] + 1

    def _get_download_link(self, photo_id: str, size_label: str = "Original") -> str:
        sizes = self._flickrapi.photos.getSizes(photo_id=photo_id, format="parsed-json")
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
        return requests.get(link, headers={"Content-Type": "image/jpg"}).content, size

    def save_photo(self, photo: bytes, photo_id: str, photo_size: str, file_format: str = "jpg"):
        return self._file_mirror.upload_data(
            data=photo,
            upload_path=self._make_filename(photo_id=photo_id, size_label=photo_size, file_format=file_format),
        )

    def download_and_save_photo(self, photo_id: str, file_format: str = "jpg") -> str:
        img, size = self.download_photo(photo_id=photo_id)
        return self.save_photo(photo=img, photo_id=photo_id, photo_size=size, file_format=file_format)
    
    def search_photos(self, search_text: str, per_page: int = PER_PAGE_DEFAULT, page: int = 0) -> List[str]:
        photos = self._flickrapi.photos.search(text=search_text, per_page=per_page, page=page + 1, format="parsed-json", max_taken_date=MAX_TAKEN_DATE)
        return [photo["id"] for photo in photos["photos"]["photo"]]

    def iter_photos(self, search_text: str, per_page: int = PER_PAGE_DEFAULT) -> Iterable:
        next_page = self._get_next_page(per_page=per_page, search_text=search_text)
        self._save_search_metadata(per_page=per_page, search_text=search_text, last_page=next_page)
        for photo_id in self.search_photos(search_text=search_text, per_page=per_page, page=next_page):
            yield photo_id, self.download_and_save_photo(photo_id=photo_id)
