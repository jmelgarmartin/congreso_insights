from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def iniciar_driver(driver_path: str, headless: bool = False) -> tuple[webdriver.Chrome, WebDriverWait]:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)
    return driver, wait


def aceptar_cookies(driver: webdriver.Chrome, wait: WebDriverWait):
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space(text())='Aceptar todas']"))).click()
        print("Cookies aceptadas.")
    except Exception as e:
        print("No se pudo aceptar cookies:", e)


def seleccionar_opcion_por_valor(select_element, valor: str):
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.get_attribute("value") == valor:
            option.click()
            return True
    return False


def esperar_spinner(wait: WebDriverWait):
    wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-border")))


def esperar_tabla_cargada(wait: WebDriverWait, selector: str):
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))


def hacer_click_esperando(driver: webdriver.Chrome, wait: WebDriverWait, by: By, selector: str):
    """
    Espera a que un elemento sea clickable y hace clic sobre él con JavaScript.
    """
    elemento = wait.until(EC.element_to_be_clickable((by, selector)))
    driver.execute_script("arguments[0].click();", elemento)
