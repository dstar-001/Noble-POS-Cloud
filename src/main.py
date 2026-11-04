import logging

import flet as ft

from app import NoblePOSApp

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)


async def main(page: ft.Page):
    page.title = "Noble POS Cloud"
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.BLUE_GREY_50
    preferences = ft.SharedPreferences()
    file_picker = ft.FilePicker()
    app = NoblePOSApp(page, preferences, file_picker)
    await app.start()


ft.run(main)
