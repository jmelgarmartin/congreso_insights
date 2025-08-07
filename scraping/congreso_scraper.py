# scraping/congreso_scraper.py

import os
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    seleccionar_opcion_por_valor,
    hacer_click_esperando,
    click_siguiente_pagina,
    get_rango_resultados,
    guardar_html_contenido
)
import logging
logger = logging.getLogger(__name__)

class CongresoScraper:
    """Scraper para descargar los plenos del Congreso desde la web oficial."""


    def __init__(self, driver_path: str, output_dir: str, legislatura: str = "15"):
        """
        Inicializa el scraper con los parámetros necesarios.

        :param driver_path: Ruta al ejecutable de ChromeDriver.
        :param output_dir: Directorio donde se guardarán los archivos HTML descargados.
        :param legislatura: Número de la legislatura a consultar (por defecto "15").
        """
        self.url = "https://www.congreso.es/busqueda-de-publicaciones"
        self.driver_path = driver_path
        self.output_dir = output_dir
        self.legislatura = legislatura
        self.driver = None
        self.wait = None
        os.makedirs(output_dir, exist_ok=True)

    def _apply_filters(self):
        """
        Aplica los filtros necesarios en la página web para obtener los plenos de la legislatura seleccionada.
        """
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "_publicaciones_legislatura")))
            logger.info("Aplicando filtros...")
            Select(self.driver.find_element(By.ID, "_publicaciones_legislatura")).select_by_value(self.legislatura)
            seleccionar_opcion_por_valor(self.driver.find_element(By.ID, "publicacion"), "D")
            seleccionar_opcion_por_valor(self.driver.find_element(By.ID, "seccion"), "CONGRESO")
            time.sleep(1)
            hacer_click_esperando(self.driver, self.wait, By.XPATH,
                                  "//button[.//span[normalize-space(text())='Buscar']]")

            logger.info("Buscando resultados...")
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//tr[td//a[contains(text(),'Texto íntegro')]]")))
            logger.info("Resultados cargados.")
        except Exception as e:
            logger.error("Error al aplicar filtros:  {e}")
            self.driver.quit()
            raise

    def _procesar_fila(self, fila):
        """
        Procesa una fila individual de resultados y guarda el contenido si corresponde a un pleno.

        :param fila: WebElement correspondiente a una fila de resultados.
        :return: True si se guardó un archivo nuevo, False en caso contrario.
        """
        cve_td = fila.find_elements(By.TAG_NAME, "td")
        cve_text = ""
        for td in cve_td:
            if "DSCD" in td.text:
                cve_text = td.text.strip()
                break
        if "-PL-" not in cve_text:
            return False

        match = re.search(r"(DSCD-\d+-PL-\d+)", cve_text)
        base = match.group(1) if match else re.sub(r"[^A-Za-z0-9\-]", "_", cve_text)
        nombre_archivo = f"{base}.html"
        ruta = os.path.join(self.output_dir, nombre_archivo)

        if os.path.exists(ruta):
            logger.info(f"Ya existe: {nombre_archivo}")
            return False

        texto_link = fila.find_element(By.XPATH, ".//a[contains(text(),'Texto íntegro')]")
        href = texto_link.get_attribute("href")
        logger.info(f"Procesando: {href}")

        self.driver.execute_script("window.open(arguments[0]);", href)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        if guardar_html_contenido(
                self.driver,
                self.wait,
                selector="section#portlet_publicaciones",
                ruta_archivo=ruta
        ):
            logger.info(f"Guardado: {nombre_archivo}")
        else:
            logger.error(f"No se encontró contenido en: {nombre_archivo}")

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return True

    def descargar_plenos(self):
        """Descarga todos los plenos disponibles aplicando los filtros y guardando el contenido en archivos HTML."""
        self.driver, self.wait = iniciar_driver(self.driver_path, headless=True)
        self.driver.get(self.url)
        aceptar_cookies(self.driver, self.wait)
        self._apply_filters()

        descargados = 0
        pagina = 1
        xpath_siguiente = "//ul[@id='_publicaciones_paginationLinksPublicaciones']//a[text()='>']"
        selector_tabla = "//tr[td//a[contains(text(),'Texto íntegro')]]"

        while True:
            logger.info(f"Página {pagina}")
            filas = self.driver.find_elements(By.XPATH, selector_tabla)

            for i in range(len(filas)):
                for intento in range(3):
                    try:
                        filas_actualizadas = self.driver.find_elements(By.XPATH, selector_tabla)
                        if i >= len(filas_actualizadas):
                            break
                        if self._procesar_fila(filas_actualizadas[i]):
                            descargados += 1
                        break
                    except Exception as e:
                        print(f"Error procesando fila {i + 1}: {e}")

            hasta, total = get_rango_resultados(self.driver, "_publicaciones_resultsShowedPublicaciones")
            if hasta is None or hasta >= total:
                print("Última página detectada.")
                break

            if not click_siguiente_pagina(self.driver, self.wait, xpath_siguiente, By.XPATH, selector_tabla):
                print("No hay más páginas.")
                break

            pagina += 1

        self.driver.quit()
        print("\nProceso completado")
        print(f"Total nuevos plenos descargados: {descargados}")