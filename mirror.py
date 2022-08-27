import os
from google.cloud import storage
from google.oauth2 import service_account
from typing import Union

from util.yaml_parse import load_yaml


class FileMirror:
    def __init__(self, upload_prefix: str):
        self._upload_prefix = upload_prefix

    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None) -> str:
        raise NotImplementedError

    def upload_file(self, filepath: str, upload_path: str, prefix: str = None) -> str:
        raise NotImplementedError

    def download_data(self, filepath: str, prefix: str) -> bytes:
        raise NotImplementedError

    def download_file(self, download_path: str, filepath: str, prefix: str = None) -> str:
        raise NotImplementedError

    def set_upload_path(self, upload_prefix: str):
        self._upload_prefix = upload_prefix


class GCSFileUploader(FileMirror):

    def __init__(self, project_name: str, bucket_name: str, auth_json_path: str = "", upload_prefix: str = "") -> None:
        super().__init__(upload_prefix=upload_prefix)
        self._project_name = project_name
        self._bucket_name = bucket_name
        self._upload_prefix = upload_prefix
        credentials = service_account.Credentials.from_service_account_file(
            auth_json_path, scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        self._client = storage.Client(project=project_name, credentials=credentials)
        self._bucket = self._client.bucket(bucket_name=self._bucket_name)

    def _get_upload_path(self, upload_path: str, prefix: str = None) -> str:
        if prefix is None:
            prefix = self._upload_prefix
        if prefix:
            return self._upload_prefix + "/" + upload_path
        return upload_path

    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=upload_path, prefix=prefix))
        blob.upload_from_string(data=data)
        return blob.public_url
    
    def upload_file(self, filepath: str, upload_path: str, prefix: str = None) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=upload_path, prefix=prefix))
        blob.upload_from_filename(filename=filepath)
        return blob.public_url

    def download_data(self, filepath: str, prefix: str) -> bytes:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=filepath, prefix=prefix))
        return blob.download_as_bytes()

    def download_file(self, download_path: str, filepath: str, prefix: str = None) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=filepath, prefix=prefix))
        blob.download_to_filename(filename=download_path)
        return download_path

    @staticmethod
    def from_secret_file(file_path: str) -> "GCSFileUploader":
        secret_file = load_yaml(file_path=file_path)
        return GCSFileUploader(
            project_name=secret_file.get("gcp_project"),
            bucket_name=secret_file.get("gcs_upload_bucket"),
            auth_json_path=secret_file.get("gcp_auth_json"),
            upload_prefix=secret_file.get("gcs_upload_prefix"),
        )


class LocalFileStore(FileMirror):
    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None) -> str:
        if prefix is None:
            prefix = self._upload_prefix
        if prefix:
            upload_path = os.path.join(prefix, upload_path)
        open_conf = 'w+'
        if isinstance(data, bytes):
            open_conf = 'wb+'
        with open(upload_path, open_conf) as f:
            f.write(data)
            return upload_path

    def upload_file(self, filepath: str, upload_path: str, prefix: str = None) -> str:
        if prefix is None:
            prefix = self._upload_prefix
        if prefix:
            upload_path = os.path.join(prefix, upload_path)
        with open(upload_path, 'wb+') as f:
            with open(filepath, 'rb') as g:
                f.write(g.read())
                return upload_path
