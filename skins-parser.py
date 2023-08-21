import os
from urllib.request import Request, urlopen
import pathlib
from fake_headers import Headers
from joblib import Parallel, delayed
from PIL import Image
from io import BytesIO
from constants import SKINS_DIRECTORY

PLAYER_SKIN_WIDTH = 64
LAST_SKIN_ID = 6545503281


def get_last_downloaded_skin_id() -> int:
    ids = map(lambda filename: int(filename.split('.')[0]), os.listdir(SKINS_DIRECTORY))
    return max(ids, key=lambda x: x, default=None)


def download_skin(id: int):
    url = f"http://novask.in/{id}.png"
    request = Request(url, headers=Headers().generate())

    try:
        response = urlopen(request)
        img_data = BytesIO(response.read())

        with Image.open(img_data) as img:
            if img.width != PLAYER_SKIN_WIDTH:
                print(f"{url} - skipped")
                return

            img.save(f"skins/{id}.png", "PNG")

        print(f"{url} - success")
    except Exception as e:
        print(f"{url} - fail ({e})")


if __name__ == '__main__':
    last_downloaded_skin_id = get_last_downloaded_skin_id() or 0

    pathlib.Path(SKINS_DIRECTORY).mkdir(parents=True, exist_ok=True)  # ensure "skins" folder exists
    Parallel(n_jobs=-1)(delayed(download_skin)(i) for i in range(last_downloaded_skin_id + 1, LAST_SKIN_ID + 1))
