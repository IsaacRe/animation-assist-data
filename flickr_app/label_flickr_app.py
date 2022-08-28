import os
from flask import Flask, render_template, redirect, request, url_for, send_from_directory
from concurrent.futures import ThreadPoolExecutor

from .flickr import ImageDownloader
from .label import LabelImagesController, ImageLabelWriter
from .mirror import GCSFileUploader, LocalFileStore

DOWNLOAD_PATH = os.getenv("LOCAL_DOWNLOAD_PATH", "data")

app = Flask(__name__)
thread_executor = ThreadPoolExecutor(max_workers=4)
file_store = LocalFileStore(DOWNLOAD_PATH)
image_uploader = GCSFileUploader(
    project_name=os.getenv("GCP_PROJECT"),
    bucket_name=os.getenv("GCP_BUCKET"),
    auth_json_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    executor=thread_executor,
)
label_uploader = GCSFileUploader(
    project_name=os.getenv("GCP_PROJECT"),
    bucket_name=os.getenv("GCP_BUCKET"),
    auth_json_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    executor=thread_executor,
)
flickr_downloader = ImageDownloader(
    api_key=os.getenv("FLICKR_API_KEY"),
    api_secret=os.getenv("FLICKR_API_SECRET"),
    temp_file_mirror=file_store,
    file_mirror=image_uploader,
)
label_writer = ImageLabelWriter(DOWNLOAD_PATH, backup_file_mirror=label_uploader)
controller = LabelImagesController(
    download_path=DOWNLOAD_PATH,
    image_downloader=flickr_downloader,
    label_writer=label_writer,
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
    if controller.curr_image_path:
        controller.label(label=label)
    return redirect(url_for("label_images_view"))


@app.route('/<path:filepath>')
def get_image(filepath: str):
    return send_from_directory("./", filepath, as_attachment=True)


@app.route('/ready')
def ready():
    return "ready"


@app.route('/live')
def live():
    return "live"
