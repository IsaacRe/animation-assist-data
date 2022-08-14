import yaml


def load_yaml(file_path: str):
    with open(file_path) as f:
        return yaml.load(f, Loader=yaml.Loader)
    