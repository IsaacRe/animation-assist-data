import os
from flask import Flask, render_template, redirect, request, url_for, send_from_directory

from flickr import ImageDownloader
from label import LabelImagesController
from mirror import LocalFileStore

DOWNLOAD_PATH = "data"
FLICKR_SECRET_FILE = "secrets/flickr.yaml"

app = Flask(__name__)
file_store = LocalFileStore(DOWNLOAD_PATH)
flickr_downloader = ImageDownloader(secret_file=FLICKR_SECRET_FILE, file_mirror=file_store)
controller = LabelImagesController(
    download_path=DOWNLOAD_PATH,
    image_downloader=flickr_downloader,
)


@app.route('/')
def label_images_view():
    return render_template(
        'label_view.html',
        curr_img=controller.curr_image_path,
        search_text=controller.search_text,
        images_path=controller.session_images_path,
    )


@app.route('/new-search', methods=("GET", "POST"))
def new_search():
    search_text = request.form["search_text"]
    controller.new_session(search_text=search_text)
    controller.next_image()
    return redirect(url_for("label_images_view"))


@app.route('/label-image')
def label_image():
    label = None # TODO get from params
    controller.label(label=label)
    controller.next_image()
    return redirect(url_for("label_images_view"))


@app.route('/<path:filepath>')
def get_image(filepath: str):
    return send_from_directory("./", filepath, as_attachment=True)
