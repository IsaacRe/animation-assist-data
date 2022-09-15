import os
from flask import Flask, render_template, redirect, request, url_for, send_from_directory, current_app
from concurrent.futures import ThreadPoolExecutor

from db.client import DBClient

from .flickr import ImageDownloader
from .label import LabelImagesController, DatabaseInterface
from .mirror import GCSFileUploader, LocalFileStore

DOWNLOAD_PATH = os.getenv("LOCAL_DOWNLOAD_PATH", "data")

app = Flask(__name__)
app.logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
thread_executor = ThreadPoolExecutor(max_workers=4)
file_store = LocalFileStore(upload_prefix=DOWNLOAD_PATH, logger=app.logger)
image_uploader = GCSFileUploader(
    logger=app.logger,
    project_name=os.getenv("GCP_PROJECT"),
    bucket_name=os.getenv("GCP_BUCKET"),
    auth_json_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    executor=thread_executor,
)
db_client = DBClient(os.getenv("FLICKR_APP_DB_URL"))
flickr_downloader = ImageDownloader(
    logger=app.logger,
    api_key=os.getenv("FLICKR_API_KEY"),
    api_secret=os.getenv("FLICKR_API_SECRET"),
    temp_file_mirror=file_store,
    file_mirror=image_uploader,
)
labeler = DatabaseInterface(db_client=db_client, logger=app.logger)
controller = LabelImagesController(
    download_path=DOWNLOAD_PATH,
    image_downloader=flickr_downloader,
    dataset_interface=labeler,
    executor=thread_executor,
    download_buffer_size=5,
)


@app.route('/', methods=("GET", "POST"))
def label_images_view():
    return render_template(
        'label_view.html',
        curr_img=controller.curr_image_path,
        search_text=controller.search_text,
        images_path=controller.session_images_path,
        loading=controller.loading,
    )


@app.route('/new-search', methods=("GET", "POST"))
def new_search():
    search_text = request.form["search_text"]
    controller.new_session(search_text=search_text)
    return redirect(url_for("label_images_view"))


@app.route('/label-image', methods=("GET", "POST"))
def label_image():
    label = request.args.get("label")
    if controller.curr_image_path and not controller.loading:
        controller.label(label=label)
    else:
        current_app.logger.debug("Skipping label action because image loading is in progress.")
    return redirect(url_for("label_images_view"))


@app.route('/<path:filepath>')
def get_image(filepath: str):
    return send_from_directory("../", filepath, as_attachment=True)


@app.route('/ready')
def ready():
    return "ready"


@app.route('/live')
def live():
    return "live"
