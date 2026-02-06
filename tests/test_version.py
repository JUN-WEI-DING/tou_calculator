
try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pathlib import Path

import taipower_tou


def test_version_consistency():
    """Verify that pyproject.toml version matches package __version__."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    pyproject_version = pyproject_data["project"]["version"]
    package_version = taipower_tou.__version__

    assert pyproject_version == package_version, (
        "Version mismatch: "
        f"pyproject.toml ({pyproject_version}) != package ({package_version})"
    )
