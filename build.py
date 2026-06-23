"""
Fetches a given WinPython distribution, installs the requirements and then creates a zip file
containing the nlp-winpython folder
"""
import argparse

import pathlib
import shlex
import shutil
import subprocess
import tarfile
from typing import Literal
import zipfile

import requests

WP_RELEASE = "17.4.20260511final"
WP_FILE = "WinPython64-3.13.13.0dot.zip"

WP_ASSET = f"https://github.com/winpython/winpython/releases/download/{WP_RELEASE}/{WP_FILE}"
WP_OUT_FOLDER = pathlib.Path(WP_FILE).stem
NLP_WP_OUT_FILE = "nlp-winpython"

VSCODE_ASSET = "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-archive"

REQUIREMENTS_FILE = "winpython-requirements.txt"

_REPORT_INTERVAL = 500
_CHUNK_SIZE = 8192


def _parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true", help="Only build WinPython, do not create compressed archive")
    parser.add_argument("--report-interval", type=int, default=_REPORT_INTERVAL)
    parser.add_argument("--chunk-size", type=int, default=_CHUNK_SIZE)
    parser.add_argument("--compression-type", choices=["zip", "tar.gz"], default="tar.gz")
    return parser.parse_args(args)

def _archive_io(file: str, compression_type: Literal["zip", "tar.gz"]) -> zipfile.ZipFile | tarfile.TarFile:
    if compression_type == "zip":
        return zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
    elif compression_type == "tar.gz":
        return tarfile.open(file, "w:gz")


def main():
    args = _parse_args()

    report_interval: int = args.report_interval
    chunk_size: int = args.chunk_size
    compression_type: Literal["zip", "tar.gz"] = args.compression_type
    build_only: bool = args.build_only

    if pathlib.Path(WP_OUT_FOLDER).exists():
        print(f"Removing {WP_OUT_FOLDER}")
        shutil.rmtree(WP_OUT_FOLDER)
    
    if pathlib.Path(WP_FILE).exists():
        print(f"Removing {WP_FILE}")
        pathlib.Path(WP_FILE).unlink()
    
    if pathlib.Path(NLP_WP_OUT_FILE).exists():
        print(f"Removing {NLP_WP_OUT_FILE}")
        pathlib.Path(NLP_WP_OUT_FILE).unlink()
    
    print(f"Downloading {WP_ASSET}")
    response = requests.head(WP_ASSET, allow_redirects=True, headers={"Accept-Encoding": "identity"})

    file_size_bytes = response.headers.get('Content-Length')
    file_size_bytes = (int(file_size_bytes) or None) if file_size_bytes is not None else None

    with requests.get(WP_ASSET, stream=True) as r:
        r.raise_for_status()
        chunks = 0
        with open(WP_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                chunks += 1
                if (chunks % report_interval == 0 or len(chunk) < chunk_size) and file_size_bytes is not None:
                    downloaded_mb = ((chunks - 1) * chunk_size + len(chunk)) / 1024 / 1024
                    total_mb = file_size_bytes / 1024 / 1024
                    print(f"Downloaded {downloaded_mb:.2f} MB of {total_mb:.2f} MB ({100 * downloaded_mb / total_mb:.2f}%)")
    
    with zipfile.ZipFile(WP_FILE, "r") as zip_ref:
        print(f"Extracting {WP_FILE}")
        zip_ref.extractall(WP_OUT_FOLDER)
    
    pathlib.Path(WP_FILE).unlink()

    folder_path = pathlib.Path(WP_OUT_FOLDER)
    top_dir = next(folder_path.iterdir())

    print(f"Downloading {VSCODE_ASSET}")
    response = requests.head(VSCODE_ASSET, allow_redirects=True, headers={"Accept-Encoding": "identity"})

    vscode_out_file = top_dir / "t" / "vscode.zip" # Leave zipped for size reasons
    vscode_out_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_size_bytes = response.headers.get('Content-Length')
    file_size_bytes = (int(file_size_bytes) or None) if file_size_bytes is not None else None

    with requests.get(VSCODE_ASSET, stream=True) as r:
        r.raise_for_status()
        chunks = 0
        with open(vscode_out_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                chunks += 1
                if (chunks % report_interval == 0 or len(chunk) < chunk_size) and file_size_bytes is not None:
                    downloaded_mb = ((chunks - 1) * chunk_size + len(chunk)) / 1024 / 1024
                    total_mb = file_size_bytes / 1024 / 1024
                    print(f"Downloaded {downloaded_mb:.2f} MB of {total_mb:.2f} MB ({100 * downloaded_mb / total_mb:.2f}%)")

    python_path = top_dir / "python" / "python.exe"
    pip_cmd = [str(python_path), "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--no-warn-script-location"]

    print(shlex.join(pip_cmd)) # show pip command
    subprocess.run(pip_cmd, check=True)

    out_file = NLP_WP_OUT_FILE + '.tar.gz' if compression_type == 'tar.gz' else NLP_WP_OUT_FILE + '.zip'
    if build_only:
        print(f"Only building {out_file}")
        return
    
    print(f"Archiving {top_dir}")
    with _archive_io(NLP_WP_OUT_FILE + '.tar.gz' if compression_type == 'tar.gz' else NLP_WP_OUT_FILE + '.zip', compression_type) as archive:

        def write(file: pathlib.Path, arcname: str):
            if isinstance(archive, zipfile.ZipFile):
                archive.write(file, arcname=arcname)
            else:
                archive.add(file, arcname=arcname)
        
        for file in top_dir.rglob("*"):
            if file.is_dir():
                continue
            
            # place in nlp-winpython folder
            file_name = (pathlib.Path("nlp-winpython") / file.relative_to(top_dir)).as_posix()
            write(file, file_name)

            file.unlink() # conserve disk space
    
    print(f"Removing {WP_OUT_FOLDER}")
    shutil.rmtree(WP_OUT_FOLDER)

    print(f"{NLP_WP_OUT_FILE + '.tar.gz' if compression_type == 'tar.gz' else NLP_WP_OUT_FILE + '.zip'} created successfully")

if __name__ == "__main__":
    main()
