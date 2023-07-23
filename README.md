# Animation Assist

This project is directed towards developing a model for automatic cleaning of rough sketches (see this [paper](https://cragl.cs.gmu.edu/sketchbench/) for a background on the problem). This repo contains an app developed to download and label images from Flickr for curation of a dataset to this end. Several jupyter notebooks containing my initial experimentation are also included.

## Flickr Labeling App

### Local Setup

Install dependencies

`pipenv install`

Activate environnent

`pipenv shell`

Set the following environment variables:
- `FLASK_APP=flickr_app.label_flickr_app:app`
- `FLICKR_APP_DB_URL=<URL to postgresql DB for Flickr image labels>`

Then run `python -m flask`


### Deploying

Add your GCP credentials file to the local path `secrets/gcp-credentials.json` then run `docker build . -t gcr.io/<full project name>/flickr-app:latest` and `docker push gcr.io/<full project name>/flickr-app:latest`, replacing `<full project name>` with the full name of your GCP project to deploy to.

Configure the Deployment for your GCP environment. The repo isn't set up to use Helm, so this currently involves updating the following deployment variables (anything with `[REPLACE ME]`):

1. The GCP_PROJECT and FLICKR_APP_DB_URL in flick-app.yaml (set to name of your project and postgresql:// URL to your Cloud SQL DB, respectively)
2. The image tag to use in the service deployment (set to the tag you pushed with earlier)
3. Flickr API key and secret in flickr-api-secret.yaml. **IMPORTANT: first run `git rm --cached deployment/flickr-api-secret.yaml` to prevent version control from tracking this file in the future.**

Run `kubectl apply -f deployment` to deploy.

## Notebooks

Notebooks can be found in the `notebooks/` directory:

- `Exploring Sketch Intensity.ipynb` - Strokes in clean sketches often correspond to heavier (darker) strokes in the corresponding rough sketch. This notebook goes through isolating such strokes in rough sketches. Demonstrates that stroke intensity signal is insufficient for synthesis of clean sketches.
- `Predicting Sketch Roughness.ipynb` - Several attempts at hand-designed filters to predict the "roughness" of localities in a given sketch.
- `Learning Roughness Prediction and Clean Sketch Generation.ipynb` - Use Contrastive Learning with a novel data augmentation to train a Resnet18 that predicts which of a pair of sketches is rougher. Qualitative analysis suggests that the end model is able to detect clusters of lines in the input image that are indicative of rough sketches.
