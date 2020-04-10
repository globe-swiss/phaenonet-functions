import os


def get_resource_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'resources', name)
