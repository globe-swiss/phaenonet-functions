from pathlib import Path


def get_resource_path(name: str) -> str:
    return str(Path(__file__).parent / "resources" / name)
