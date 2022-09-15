from concurrent.futures import Future, ThreadPoolExecutor
from flask import current_app
import os

from db.client import DBClient
from flickr_app.util import MAX_TAKEN_DATE, ImageSearch, InvalidSearchException

from .flickr import (
    ImageDownloader,
    PER_PAGE_DEFAULT,
    IMAGES_SUBDIR,
)
from .mirror import FileMirror


TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"
DF_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
BUFFER_SIZE_DEFAULT = 1


class DatabaseInterface:

    def __init__(self, db_client: DBClient):
        self._db_client = db_client
        self._search_id = None

    def new_search(self, query: str) -> ImageSearch:  # TODO: allow specification of search parameters
        per_page = PER_PAGE_DEFAULT
        max_taken_date = MAX_TAKEN_DATE
        last_page_idx = 0
        last_image_idx = 0
        current_app.logger.debug(f"Syncing new search '{query}' with database")
        with self._db_client.transaction() as session:
            result = session.execute(
                """
                    SELECT id, per_page, max_taken_date, last_page_idx, last_image_idx
                    FROM searches WHERE query = :query
                    LIMIT 1
                """,
                {"query": query}
            ).fetchone()
            if result is not None:
                current_search = ImageSearch(
                    id=result["id"],
                    query=query,
                    last_image_idx=result["last_image_idx"],
                    last_page_idx=result["last_page_idx"],
                    per_page=result["per_page"],
                    max_taken_date=result["max_taken_date"],
                )
                session.execute(
                    "UPDATE searches SET last_search_time = NOW() WHERE id = :id",
                    {"id": current_search.id},
                )
                current_app.logger.debug(f"Found existing search {current_search.id}")
            else:
                result = session.execute(
                    """
                        INSERT INTO searches(query, per_page, max_taken_date, last_page_idx, last_image_idx)
                        VALUES (:query, :per_page, :max_taken_date, :last_page_idx, :last_image_idx)
                        ON CONFLICT(query) DO NOTHING
                        RETURNING id
                    """,
                    {
                        "query": query,
                        "per_page": per_page,
                        "last_page_idx": last_page_idx,
                        "last_image_idx": last_image_idx,
                        "max_taken_date": max_taken_date,
                    }
                ).fetchone()
                if result is None:
                    raise InvalidSearchException("Failed to insert query")
                current_search = ImageSearch(
                    id=result["id"],
                    query=query,
                    last_page_idx=last_image_idx,
                    last_image_idx=last_image_idx,
                    max_taken_date=max_taken_date,
                )
                current_app.logger.debug(f"Initialized new search {current_search.id}")
            self._search_id = current_search.id
            return current_search

    def check_image_labeled(self, flickr_id: str) -> bool:
        current_app.logger.debug(f"Checking label for image {flickr_id}")
        with self._db_client.transaction() as session:
            image_labeled = session.execute(
                "SELECT flickr_id FROM images WHERE flickr_id = :id", {"id": flickr_id}
            ).fetchone() is not None
            if image_labeled:
                current_app.logger.debug("Found label")
            return image_labeled


    def label_image(self, user_id: int, flickr_id: str, image_path: str, label: int, search: ImageSearch) -> bool:
        current_app.logger.debug(f"Labeling image {flickr_id}: {label}")
        with self._db_client.transaction() as session:
            result = session.execute(
                """
                    WITH update_search AS (
                        UPDATE searches
                        SET
                            last_page_idx = :page_idx,
                            last_image_idx = :image_idx,
                            last_search_time = NOW()
                        WHERE id = :search_id
                    )
                    INSERT INTO images(flickr_id, image_path, label, user_id, search_id, page_idx, image_idx)
                    VALUES (:flickr_id, :image_path, :label, :user_id, :search_id, :page_idx, :image_idx)
                    ON CONFLICT (flickr_id) DO NOTHING
                    RETURNING flickr_id
                """,
                {
                    "flickr_id": flickr_id,
                    "image_path": image_path,
                    "label": label,
                    "user_id": user_id,
                    "search_id": search.id,
                    "page_idx": search.last_page_idx,
                    "image_idx": search.last_image_idx,
                }
            ).fetchone()
        return result is not None


class LabelImagesController:

    def __init__(
        self,
        download_path: str,
        image_downloader: ImageDownloader,
        dataset_interface: DatabaseInterface,
        executor: ThreadPoolExecutor,
        per_page: int = PER_PAGE_DEFAULT,
        download_buffer_size: int = BUFFER_SIZE_DEFAULT,
    ):
        self.user_id = None
        self._executor = executor
        self._base_download_path = download_path
        self._session_download_path = None
        self.session_images_path = None
        self._image_downloader = image_downloader
        self._images_iter = None
        self._dataset_interface = dataset_interface
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
        self._current_search: ImageSearch = None

    def end_session(self):
        current_app.logger.debug("LabelImagesController - session ended")
        if self._session_up:
            self._image_buffer = []
            self._image_downloader.end_session()
            self._session_up = False

    def new_session(self, search_text: str, user_id: int = 1): # TODO: specify user_id
        self.end_session()
        current_app.logger.debug("LabelImagesController - new session")
        self.user_id = user_id
        self.search_text = search_text
        self._session_download_path = os.path.join(self._base_download_path, search_text.replace(" ", "_"))
        self.session_images_path = os.path.join(self._session_download_path, IMAGES_SUBDIR)
        os.makedirs(self._session_download_path, exist_ok=True)
        self._current_search = self._dataset_interface.new_search(search_text)
        self._image_downloader.new_session(download_path=self._session_download_path, search=self._current_search)
        self._images_iter = self._image_downloader.iter_photos()
        self.do_buffer()
        self._session_up = True
        self.next_image()

    def _buffer(self):  # should happen in background
        current_app.logger.debug(f"Buffering {self._download_buffer_size - len(self._image_buffer)} images...")
        while len(self._image_buffer) < self._download_buffer_size:
            flickr_id, temp_download_path, remote_download_path = next(self._images_iter)
            if self._dataset_interface.check_image_labeled(flickr_id=flickr_id):
                continue
            self._image_buffer += [(flickr_id, temp_download_path, remote_download_path)]
            current_app.logger.debug(f"Image {flickr_id} added to buffer")

    def _clear_buffering_process(self):
        self._buffering_process = None
    
    def do_buffer(self):
        self._buffer()
        # TODO: async not working
        # if self._buffering_process is None:
        #     self._buffering_process = self._executor.submit(self._buffer)
        #     self._buffering_process.add_done_callback(lambda _: self._clear_buffering_process())

    def next_image(self):
        current_app.logger.debug("Attempting to load next image...")
        if not self.loading:
            self.loading = True
            while len(self._image_buffer) == 0:
                self.do_buffer()
            self.curr_image_id, self.curr_image_path, self._curr_image_remote_path = self._image_buffer.pop(0)
            current_app.logger.debug(f"Pulled image {self.curr_image_id} from buffer")
            self.do_buffer()
            self.loading = False
        else:
            current_app.logger.debug("Image already loading. Skipping...")

    def label(self, label: int):
        self._dataset_interface.label_image(
            user_id=self.user_id,
            flickr_id=self.curr_image_id,
            image_path=self._curr_image_remote_path,
            label=label,
            search=self._current_search,
        )
        self._current_search.incr_image()
        self.next_image()
