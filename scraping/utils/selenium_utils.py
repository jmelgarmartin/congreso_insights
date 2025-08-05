# selenium_utils.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import re
from bs4 import BeautifulSoup


def iniciar_driver(driver_path: str, headless: bool = False) -> tuple[webdriver.Chrome, WebDriverWait]:
    """
    Inicializa un driver de Chrome con WebDriverWait.

    :param driver_path: Ruta al ejecutable de ChromeDriver.
    :param headless: Si es True, ejecuta Chrome en modo headless.
    :return: Una tupla con el driver de Chrome y una instancia WebDriverWait.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)
    return driver, wait


def aceptar_cookies(driver: webdriver.Chrome, wait: WebDriverWait):
    """
    Acepta el banner de cookies si está presente en la página.

    :param driver: Instancia del navegador Chrome.
    :param wait: Instancia WebDriverWait.
    """
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space(text())='Aceptar todas']"))).click()
        print("Cookies aceptadas.")
    except Exception as e:
        print("No se pudo aceptar cookies:", e)


def seleccionar_opcion_por_valor(select_element, valor: str):
    """
    Selecciona una opción específica en un elemento HTML <select> dado un valor.

    :param select_element: Elemento WebElement correspondiente al select.
    :param valor: Valor del atributo 'value' de la opción a seleccionar.
    :return: True si la opción se seleccionó correctamente, False en caso contrario.
    """
    try:
        Select(select_element).select_by_value(valor)
        return True
    except Exception as e:
        print(f"Error al seleccionar valor '{valor}': {e}")
        return False


def esperar_spinner(wait: WebDriverWait):
    """
    Espera hasta que el spinner de carga desaparezca de la pantalla.

    :param wait: Instancia WebDriverWait.
    """
    wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-border")))


def esperar_tabla_cargada(wait: WebDriverWait, selector: str):
    """
    Espera hasta que la tabla especificada por el selector esté cargada en la página.

    :param wait: Instancia WebDriverWait.
    :param selector: Selector CSS para la tabla.
    """
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))


def hacer_click_esperando(driver: webdriver.Chrome, wait: WebDriverWait, by: By, selector: str):
    """
    Espera a que un elemento sea clicable y luego hace clic usando JavaScript.

    :param driver: Instancia del navegador Chrome.
    :param wait: Instancia WebDriverWait.
    :param by: Método para localizar elementos (By.XPATH, By.CSS_SELECTOR, etc.).
    :param selector: Selector para localizar el elemento.
    """
    elemento = wait.until(EC.element_to_be_clickable((by, selector)))
    driver.execute_script("arguments[0].click();", elemento)


def es_ultima_pagina(driver: webdriver.Chrome, element_id: str) -> bool:
    """
    Determina si la página actual es la última según el texto del paginador.

    :param driver: Instancia del navegador Chrome.
    :param element_id: ID del elemento que contiene la información del paginador.
    :return: True si es la última página, False en caso contrario.
    """
    try:
        texto = driver.find_element(By.ID, element_id).text
        match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", texto)
        if match:
            hasta = int(match.group(2))
            total = int(match.group(3))
            return hasta >= total
    except:
        pass
    return False


def click_siguiente_pagina(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    xpath_siguiente: str,
    by_tabla: By, # <-- NUEVO PARÁMETRO
    selector_tabla: str,
    id_paginador: str = None
) -> bool:
    """
    Intenta hacer clic en el botón de siguiente página y espera que el contenido se actualice.

    :param driver: Navegador Selenium.
    :param wait: Objeto WebDriverWait.
    :param xpath_siguiente: XPath del botón de paginación.
    :param by_tabla: Método para localizar elementos de la tabla (By.XPATH, By.CSS_SELECTOR, etc.).
    :param selector_tabla: Selector para la tabla de resultados.
    :param id_paginador: ID del elemento que muestra el rango de resultados.
    :return: True si avanza de página, False si no hay más páginas o falla.
    """
    import time
    import re

    try:
        rango_anterior = None
        if id_paginador:
            try:
                texto = driver.find_element(By.ID, id_paginador).text
                match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", texto)
                if match:
                    rango_anterior = match.group(1)
            except Exception as e:
                print(f"No se pudo leer el rango anterior: {e}")

        # Rebuscar el botón de siguiente siempre justo antes del clic
        try:
            boton = driver.find_element(By.XPATH, xpath_siguiente)
            driver.execute_script("arguments[0].click();", boton)
        except Exception as e:
            print(f"No se pudo hacer clic en el botón siguiente: {e}")
            return False

        esperar_spinner(wait)

        # Esperar que cambie el rango
        if id_paginador and rango_anterior:
            for _ in range(20):
                try:
                    texto = driver.find_element(By.ID, id_paginador).text
                    match = re.search(r"Resultados (\\d+) a (\\d+) de (\\d+)", texto)
                    if match and match.group(1) != rango_anterior:
                        break # pragma: no cover
                except:
                    pass
                time.sleep(0.5)

        # Confirmar que la tabla aparece usando el by_tabla y selector_tabla
        wait.until(EC.presence_of_element_located((by_tabla, selector_tabla))) # <-- CAMBIO AQUI
        return True

    except Exception as e:
        print(f"Error inesperado en click_siguiente_pagina: {e}")
        return False



def get_rango_resultados(driver: webdriver.Chrome, element_id: str) -> tuple[int, int]:
    """
    Obtiene el rango actual de resultados y el total del texto del paginador.

    :param driver: Instancia del navegador Chrome.
    :param element_id: ID del elemento que contiene el texto del paginador.
    :return: Tupla con (hasta, total) resultados. (None, None) si falla.
    """
    try:
        texto = driver.find_element(By.ID, element_id).text
        match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", texto)
        if match:
            return int(match.group(2)), int(match.group(3))
    except:
        pass
    return None, None


def guardar_html_contenido(driver: webdriver.Chrome, wait: WebDriverWait, selector: str, ruta_archivo: str) -> bool:
    """
    Guarda el contenido HTML de un selector específico en un archivo.

    :param driver: Instancia del navegador Chrome.
    :param wait: Instancia WebDriverWait.
    :param selector: Selector CSS del elemento cuyo contenido HTML será guardado.
    :param ruta_archivo: Ruta completa del archivo donde se guardará el contenido.
    :return: True si el contenido se guardó correctamente, False si no se encontró.
    """
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        contenido = soup.select_one(selector)
        if contenido:
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(str(contenido))
            return True
    except Exception as e:
        print(f"Error al guardar el contenido HTML: {e}")
    return False
