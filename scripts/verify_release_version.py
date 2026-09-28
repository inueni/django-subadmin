"""Check that a release wheel's version matches its Git tag."""

import sys
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


def main():
    tag = sys.argv[1]
    dist = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dist")
    wheels = list(dist.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected one wheel in {dist}, found {len(wheels)}")

    with ZipFile(wheels[0]) as archive:
        metadata_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise SystemExit("Expected one wheel METADATA file")
        version = BytesParser().parsebytes(archive.read(metadata_files[0]))["Version"]

    if version != tag:
        raise SystemExit(f"Tag {tag!r} does not match package version {version!r}")


if __name__ == "__main__":
    main()
