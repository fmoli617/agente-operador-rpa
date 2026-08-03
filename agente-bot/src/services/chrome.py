"""Fábrica do WebDriver Chrome usado pelo rpa_pipeline."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def criar_driver(headless: bool = True, maximizado: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    if maximizado:
        options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)
