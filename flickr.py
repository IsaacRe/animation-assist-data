from typing import List, Tuple
import requests

from util.yaml_parse import load_yaml
from gcs import GCSFileUploader
from flickrapi import FlickrAPI


class ImageDownloader:
    def __init__(self, secret_file: str, file_mirror: GCSFileUploader):
        api_key, api_secret = self._load_api_key(secret_file)
        self._api_key = api_key
        self._api_secret = api_secret
        self._flickrapi = FlickrAPI(api_key, api_secret)
        self._file_mirror = file_mirror

    @staticmethod
    def _load_api_key(secret_file: str) -> Tuple[str, str]:
        yaml_file = load_yaml(file_path=secret_file)
        return yaml_file["api_key"], yaml_file["api_secret"]

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
        return f"{photo_id}_{size_label}.{file_format}"

    def download_photo(self, photo_id: str) -> str:
        link, size = self._get_download_link(photo_id=photo_id)
        return self._file_mirror.upload_data(
            data=requests.get(link, headers={"Content-Type": "image/jpg"}).content,
            upload_path=self._make_filename(photo_id=photo_id, size_label=size),
        )
    
    def search_photos(self, search_text: str, per_page: int = 10, page: int = 0) -> List[str]:
        photos = self._flickrapi.photos.search(text=search_text, per_page=per_page, page=page + 1, format="parsed-json")
        return [photo["id"] for photo in photos["photos"]["photo"]]

