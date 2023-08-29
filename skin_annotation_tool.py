import csv
import os
import PySimpleGUI as gui
import asyncio
import numpy as np
import pyperclip
from typing import Optional
from minepi import Skin
from PIL import Image, ImageOps
from io import BytesIO
from scipy.ndimage import binary_dilation
from constants import SKINS_DIRECTORY, CSV_FILENAME, CSV_DELIMITER
from pathlib import Path

SKIN_RENDER_HORIZONTAL_ROTATION = 35


def outline_image(img: Image, outline_color=(255, 255, 255)) -> Image:
    data = np.array(img)
    alpha_channel = data[..., 3] > 128
    outline = binary_dilation(alpha_channel) & ~alpha_channel
    data[outline, :3] = outline_color
    data[outline, 3] = 255

    return Image.fromarray(data)


async def render_skin(filename: str, hr: int, display_second_layer: bool, draw_outline: bool) -> bytes:
    skin = Skin(raw_skin=Image.open(f"{SKINS_DIRECTORY}/{filename}"))

    render = await skin.render_skin(hr=hr, vr=-20, vrra=-5, vrla=5, vrrl=-5, vrll=5, display_hair=display_second_layer, display_second_layer=display_second_layer, aa=True)

    if draw_outline:
        render = ImageOps.expand(render, border=1, fill=(255, 255, 255, 0))
        render = outline_image(render)

    with BytesIO() as bio:
        render.save(bio, format="PNG")
        return bio.getvalue()


def init_csv_file():
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=CSV_DELIMITER)
            csv_writer.writerow(['filename', 'description'])


def read_description(filename: str) -> Optional[str]:
    with open(CSV_FILENAME, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=CSV_DELIMITER)
        for row in csv_reader:
            if row[0] == filename:
                return row[1]

    return None


def update_description(filename: str, description: str):
    skins = []
    updated = False
    with open(CSV_FILENAME, 'r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=CSV_DELIMITER)
        for row in csv_reader:
            if row[0] == filename:
                row[1] = description
                updated = True
            skins.append(row)

    if not updated:
        skins.append([filename, description])

    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=CSV_DELIMITER)
        csv_writer.writerows(skins)


class MainWindow:
    def __init__(self) -> None:
        self.__init_window()

        self.__skins = sorted(os.listdir(SKINS_DIRECTORY), key=lambda filename: int(Path(filename).stem))
        self.__draw_skin_outline = True
        self.__display_skin_second_layer = True

        self.current_skin_index = 0

        self.__on_display_second_layer_changed()

    @property
    def current_skin_index(self) -> int:
        return self.__current_skin_index

    @current_skin_index.setter
    def current_skin_index(self, value) -> None:
        self.__current_skin_index = value
        self.__current_description = read_description(self.current_skin)
        self.__load_skin()

    @property
    def current_skin(self) -> str:
        return self.__skins[self.current_skin_index]

    def run(self) -> None:
        while True:
            event, values = self.__window.read()

            if event == gui.WINDOW_CLOSED:
                break
            elif event == "-NEXT-SKIN-BUTTON-":
                self.current_skin_index = (self.current_skin_index + 1) % len(self.__skins)
            elif event == "-PREVIOUS-SKIN-BUTTON-":
                self.current_skin_index = (self.current_skin_index - 1) % len(self.__skins)
            elif event == "-FIRST-SKIN-BUTTON-":
                self.current_skin_index = 0
            elif event == "-LAST-SKIN-BUTTON-":
                self.current_skin_index = len(self.__skins) - 1
            elif event == "-SAVE-DESCRIPTION-BUTTON-":
                update_description(self.current_skin, values["-SKIN-DESCRIPTION-INPUT-"])
            elif event == "-SKIN-DESCRIPTION-INPUT-":
                self.__on_skin_description_input_changed(values)
            elif event == "-TOGGLE-SKIN-OUTLINE-BUTTON-":
                self.__draw_skin_outline = not self.__draw_skin_outline
                self.__load_skin()
            elif event == "-TOGGLE-SKIN-SECOND-LEVEL-BUTTON-":
                self.__display_skin_second_layer = not self.__display_skin_second_layer
                self.__on_display_second_layer_changed()
            elif event == "-SKIN-FILENAME-BUTTON-":
                pyperclip.copy(self.__window[event].get_text())

        self.__window.close()

    def __init_window(self) -> None:
        layout = [
            [gui.Button("Toggle outline", key="-TOGGLE-SKIN-OUTLINE-BUTTON-"), gui.Button("Toggle 2nd level", key="-TOGGLE-SKIN-SECOND-LEVEL-BUTTON-")],
            [gui.Text("Front view"), gui.Text(key="-SKIN-SECOND-LEVEL-TEXT-", size=(15, 1), justification="center"), gui.Text("Back view")],
            [gui.Image(key="-SKIN-FRONT-IMAGE-", size=(220, 420)), gui.Image(key="-SKIN-BACK-IMAGE-", size=(220, 420))],
            [gui.Button("<<<", key="-FIRST-SKIN-BUTTON-"), gui.Button("<", key="-PREVIOUS-SKIN-BUTTON-", size=(4, None)), gui.Button(key="-SKIN-FILENAME-BUTTON-", size=(15, 1), tooltip="Copy filename"), gui.Button(">", key="-NEXT-SKIN-BUTTON-", size=(4, None)), gui.Button(">>>", key="-LAST-SKIN-BUTTON-")],
            [gui.Multiline(key='-SKIN-DESCRIPTION-INPUT-', size=(60, 4), expand_x=True, no_scrollbar=True, enable_events=True)],
            [gui.Button("Save", key="-SAVE-DESCRIPTION-BUTTON-", expand_x=True, disabled=True)]
        ]
        self.__window = gui.Window("Skin Annotator Tool", layout, element_justification="center", finalize=True)

    def __on_skin_description_input_changed(self, values: dict):
        save_button_disabled = not values["-SKIN-DESCRIPTION-INPUT-"] or values["-SKIN-DESCRIPTION-INPUT-"].isspace() or (values["-SKIN-DESCRIPTION-INPUT-"] == self.__current_description)
        self.__window["-SAVE-DESCRIPTION-BUTTON-"].update(disabled=save_button_disabled)
        self.__window.refresh()

    def __on_display_second_layer_changed(self):
        self.__window["-SKIN-SECOND-LEVEL-TEXT-"].update("2 layers" if self.__display_skin_second_layer else "1 layer")
        self.__load_skin()

    def __load_skin(self) -> None:
        self.__window["-SKIN-FRONT-IMAGE-"].update(data=asyncio.run(render_skin(self.current_skin, SKIN_RENDER_HORIZONTAL_ROTATION, self.__display_skin_second_layer, self.__draw_skin_outline)), size=(220, 420))
        self.__window["-SKIN-BACK-IMAGE-"].update(data=asyncio.run(render_skin(self.current_skin, SKIN_RENDER_HORIZONTAL_ROTATION - 180, self.__display_skin_second_layer, self.__draw_skin_outline)), size=(220, 420))
        self.__window["-SKIN-FILENAME-BUTTON-"].update(self.current_skin)
        self.__window["-SKIN-DESCRIPTION-INPUT-"].update(self.__current_description or "")
        self.__window.refresh()


if __name__ == "__main__":
    init_csv_file()

    gui.theme("Black")
    MainWindow().run()
