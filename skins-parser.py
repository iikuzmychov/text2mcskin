import os
import pathlib
from typing import Optional
from urllib.request import Request, urlopen
from fake_headers import Headers
from joblib import Parallel, delayed
from PIL import Image
from io import BytesIO
from constants import SKINS_DIRECTORY

PLAYER_SKIN_SIZE = 64
START_SKIN_ID = 5313423606
LAST_SKIN_ID = 10_000_000_000


def get_last_downloaded_skin_id() -> Optional[int]:
    ids = map(lambda filename: int(filename.split('.')[0]), os.listdir(SKINS_DIRECTORY))
    return max(ids, key=lambda x: x, default=None)


def download_skin(id: int):
    url = f"http://novask.in/{id}.png"
    request = Request(url, headers=Headers().generate())

    try:
        response = urlopen(request)
        img_data = BytesIO(response.read())

        with Image.open(img_data) as img:
            if img.width != PLAYER_SKIN_SIZE or img.height != PLAYER_SKIN_SIZE:
                print(f"{url} - ignored (wrong sizes: {img.width}x{img.height})")
                return

            img.save(f"skins/{id}.png", "PNG")

        print(f"{url} - success")
    except Exception as e:
        print(f"{url} - fail ({e})")


if __name__ == '__main__':
    start_skin_id = START_SKIN_ID or get_last_downloaded_skin_id() + 1 or 1

    pathlib.Path(SKINS_DIRECTORY).mkdir(parents=True, exist_ok=True)  # ensure "skins" folder exists
    Parallel(n_jobs=-1)(delayed(download_skin)(i) for i in range(start_skin_id, LAST_SKIN_ID + 1))
