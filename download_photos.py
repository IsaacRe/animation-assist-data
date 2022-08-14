from argparse import ArgumentParser, Namespace

from flickr import ImageDownloader
from gcs import GCSFileUploader


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument("--flickr-secret-file", default="secrets/flickr.yaml")
    parser.add_argument("--gcs-secret-file", default="secrets/gcloud.yaml")

    parser.add_argument("--search-text", type=str)

    return parser.parse_args()


def main():
    args = parse_args()

    gcs_mirror = GCSFileUploader.from_secret_file(file_path=args.gcs_secret_file)
    image_dl = ImageDownloader(secret_file=args.flickr_secret_file, file_mirror=gcs_mirror)

    images = image_dl.search_photos(search_text=args.search_text)
    image_dl.download_photo(images[0])


if __name__ == "__main__":
    main()