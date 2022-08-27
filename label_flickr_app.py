import os
from flask import Flask, render_template, redirect, request, url_for, send_from_directory

from flickr import ImageDownloader
from label import LabelImagesController, ImageLabelWriter
from mirror import GCSFileUploader, LocalFileStore

DOWNLOAD_PATH = "data"
FLICKR_SECRET_FILE = "secrets/flickr.yaml"
GCS_SECRET_FILE = "secrets/gcloud.yaml"

app = Flask(__name__)
file_store = LocalFileStore(DOWNLOAD_PATH)
image_uploader = GCSFileUploader.from_secret_file(GCS_SECRET_FILE)
label_uploader = GCSFileUploader.from_secret_file(GCS_SECRET_FILE)
flickr_downloader = ImageDownloader(secret_file=FLICKR_SECRET_FILE, temp_file_mirror=file_store, file_mirror=image_uploader)
label_writer = ImageLabelWriter(DOWNLOAD_PATH, backup_file_mirror=label_uploader)
controller = LabelImagesController(
    download_path=DOWNLOAD_PATH,
    image_downloader=flickr_downloader,
    label_writer=label_writer,
)


# @app.after_request
# def add_header(r):
#     """
#     Add headers to both force latest IE rendering engine or Chrome Frame,
#     and also to cache the rendered page for 10 minutes.
#     """
#     r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     r.headers["Pragma"] = "no-cache"
#     r.headers["Expires"] = "0"
#     r.headers['Cache-Control'] = 'public, max-age=0'
#     return r


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
