"""
Fetches a given WinPython distribution, installs the requirements and then creates a zip file
containing the nlp-winpython folder
"""

import pathlib
import shlex
import shutil
import subprocess
import zipfile

import requests

WP_RELEASE = "17.4.20260511final"
WP_FILE = "WinPython64-3.13.13.0dot.zip"

WP_ASSET = f"https://github.com/winpython/winpython/releases/download/{WP_RELEASE}/{WP_FILE}"
WP_OUT_FOLDER = pathlib.Path(WP_FILE).stem
NLP_WP_OUT_FILE = "nlp-winpython.zip"

REQUIREMENTS_FILE = "winpython-requirements.txt"

_REPORT_INTERVAL = 500
_CHUNK_SIZE = 8192


def main():
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
            for chunk in r.iter_content(chunk_size=_CHUNK_SIZE):
                f.write(chunk)
                chunks += 1
                if (chunks % _REPORT_INTERVAL == 0 or len(chunk) < _CHUNK_SIZE) and file_size_bytes is not None:
                    downloaded_mb = ((chunks - 1) * _CHUNK_SIZE + len(chunk)) / 1024 / 1024
                    total_mb = file_size_bytes / 1024 / 1024
                    print(f"Downloaded {downloaded_mb:.2f} MB of {total_mb:.2f} MB ({100 * downloaded_mb / total_mb:.2f}%)")
    
    with zipfile.ZipFile(WP_FILE, "r") as zip_ref:
        print(f"Extracting {WP_FILE}")
        zip_ref.extractall(WP_OUT_FOLDER)

    pathlib.Path(WP_FILE).unlink()

    folder_path = pathlib.Path(WP_OUT_FOLDER)
    top_dir = next(folder_path.iterdir())

    python_path = top_dir / "python" / "python.exe"

    pip_cmd = [str(python_path), "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--no-warn-script-location"]

    print(shlex.join(pip_cmd)) # show pip command
    subprocess.run(pip_cmd, check=True)
    
    print(f"Archiving {top_dir}")
    with zipfile.ZipFile(NLP_WP_OUT_FILE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zip_ref:
        for file in top_dir.rglob("*"):
            if file.is_dir():
                continue
            # place in nlp-winpython folder
            file_name = (pathlib.Path("nlp-winpython") / file.relative_to(top_dir)).as_posix()
            zip_ref.write(file, arcname=file_name)

            file.unlink() # conserve disk space
    
    print(f"Removing {WP_OUT_FOLDER}")
    shutil.rmtree(WP_OUT_FOLDER)

    print(f"{NLP_WP_OUT_FILE} created successfully")

if __name__ == "__main__":
    main()
