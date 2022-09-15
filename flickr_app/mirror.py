import os
from google.cloud import storage
from google.oauth2 import service_account
from typing import Dict, Union
from concurrent.futures import ThreadPoolExecutor, Future
from flask import current_app


class FileMirror:
    def __init__(self, upload_prefix: str, executor: ThreadPoolExecutor = None):
        self._upload_prefix = upload_prefix
        self._upload_futures: Dict[str, Future] = {}
        self._upload_executor = executor

    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None, wait_complete: bool = True) -> str:
        raise NotImplementedError

    def upload_data_concurrent(self, data: Union[str, bytes], upload_path: str, prefix: str = None) -> str:
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

    def __init__(self, project_name: str, bucket_name: str, auth_json_path: str = "", upload_prefix: str = "", executor: ThreadPoolExecutor = None) -> None:
        super().__init__(upload_prefix=upload_prefix, executor=executor)
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

    def _make_remove_upload_future_callback(self, upload_url: str):
        def remove_upload_future(future: Future):
            future_ = self._upload_futures[upload_url]
            if future_ == future:
                self._upload_futures.pop(upload_url)
        return remove_upload_future

    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None, wait_complete: bool = True) -> str:
        # TODO: only upload if doesnt already exist
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=upload_path, prefix=prefix))
        current_app.logger.debug(f"Uploading to {blob.public_url}")
        # TODO: async not working
        # if wait_complete:
        #     blob.upload_from_string(data=data)
        # else:
        #     future = self._upload_executor.submit(blob.upload_from_string, data)
        #     future.add_done_callback(self._make_remove_upload_future_callback(upload_url=blob.public_url))
        #     if blob.public_url in self._upload_futures:
        #         self._upload_futures[blob.public_url].cancel() # TODO this doesnt work
        #     self._upload_futures[blob.public_url] = future
        blob.upload_from_string(data=data)
        current_app.logger.debug("Done")
        return blob.public_url
    
    def upload_file(self, filepath: str, upload_path: str, prefix: str = None) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=upload_path, prefix=prefix))
        current_app.logger.debug(f"Uploading to {blob.public_url}")
        blob.upload_from_filename(filename=filepath)
        current_app.logger.debug("Done")
        return blob.public_url

    def download_data(self, filepath: str, prefix: str) -> bytes:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=filepath, prefix=prefix))
        current_app.logger.debug(f"Downloading from {blob.public_url}")
        return blob.download_as_bytes()

    def download_file(self, download_path: str, filepath: str, prefix: str = None) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=filepath, prefix=prefix))
        blob.download_to_filename(filename=download_path)
        current_app.logger.debug(f"Downloading from {blob.public_url}")
        return download_path


class LocalFileStore(FileMirror):
    def upload_data(self, data: Union[str, bytes], upload_path: str, prefix: str = None, wait_complete: bool = True) -> str:
        if prefix is None:
            prefix = self._upload_prefix
        if prefix:
            upload_path = os.path.join(prefix, upload_path)
        open_conf = 'w+'
        if isinstance(data, bytes):
            open_conf = 'wb+'
        current_app.logger.debug(f"Uploading to {upload_path}")
        with open(upload_path, open_conf) as f:
            f.write(data)
            return upload_path

    def upload_file(self, filepath: str, upload_path: str, prefix: str = None) -> str:
        if prefix is None:
            prefix = self._upload_prefix
        if prefix:
            upload_path = os.path.join(prefix, upload_path)
        current_app.logger.debug(f"Downloading from {upload_path}")
        with open(upload_path, 'wb+') as f:
            with open(filepath, 'rb') as g:
                f.write(g.read())
                return upload_path
