from google.cloud import storage
from google.oauth2 import service_account

from util.yaml_parse import load_yaml


class GCSFileUploader:

    def __init__(self, project_name: str, bucket_name: str, auth_json_path: str = "", upload_prefix: str = "") -> None:
        self._project_name = project_name
        self._bucket_name = bucket_name
        self._upload_prefix = upload_prefix
        credentials = service_account.Credentials.from_service_account_file(
            auth_json_path, scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        self._client = storage.Client(project=project_name, credentials=credentials)
        self._bucket = self._client.bucket(bucket_name=self._bucket_name)

    def _get_upload_path(self, upload_path: str) -> str:
        if self._upload_prefix:
            return self._upload_prefix + "/" + upload_path
        return upload_path

    def upload_data(self, data: bytes, upload_path: str) -> str:
        blob = self._bucket.blob(blob_name=self._get_upload_path(upload_path=upload_path))
        blob.upload_from_string(data=data)
        return blob.public_url

    @staticmethod
    def from_secret_file(file_path: str) -> "GCSFileUploader":
        secret_file = load_yaml(file_path=file_path)
        return GCSFileUploader(
            project_name=secret_file.get("gcp_project"),
            bucket_name=secret_file.get("gcs_upload_bucket"),
            auth_json_path=secret_file.get("gcp_auth_json"),
            upload_prefix=secret_file.get("gcs_upload_prefix"),
        )
