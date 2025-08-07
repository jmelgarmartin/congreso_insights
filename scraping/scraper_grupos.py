# scraping/scraper_grupos.py

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    esperar_spinner,
    esperar_tabla_cargada,
    hacer_click_esperando,
    seleccionar_opcion_por_valor,
    es_ultima_pagina,
    click_siguiente_pagina
)
import logging
logger = logging.getLogger(__name__)


class GruposScraper:
    def __init__(self, driver_path: str, legislatura: str = "15"):
        self.url_base = "https://www.congreso.es/es/grupos/composicion-en-la-legislatura"
        self.driver_path = driver_path
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path, headless=True)

    def _extraer_info_legislatura(self):
        self.driver.get(self.url_base)
        aceptar_cookies(self.driver, self.wait)
        esperar_spinner(self.wait)  # Reemplaza time.sleep(1) por una espera más robusta

        logger.info("Seleccionando legislatura...")
        select_legislatura = self.driver.find_element(By.ID, "_grupos_legislatura")
        # Usa seleccionar_opcion_por_valor para elegir la legislatura
        seleccionar_opcion_por_valor(select_legislatura, self.legislatura)

        esperar_spinner(self.wait)  # Espera a que la página se actualice después de seleccionar la legislatura
        self.wait.until(EC.presence_of_element_located(
            (By.ID, "_grupos_ajaxContentGrupo")))  # Espera que el contenido del grupo cargue

        enlaces = self.driver.find_elements(By.CSS_SELECTOR, "#_grupos_ajaxContentGrupo a")  # Usar CSS Selector
        resultado = [(enlace.text.strip().split(':')[0], enlace.get_attribute("href")) for enlace in enlaces]
        return resultado

    def _extraer_altas_bajas(self, grupo_nombre: str, url: str):
        """
        Accede a la página del grupo parlamentario y extrae los datos de altas y bajas de sus diputados.

        :param grupo_nombre: Nombre del grupo parlamentario (ej. 'PSOE').
        :param url: URL específica del grupo parlamentario.
        :return: Lista de diccionarios con nombre, fecha_alta y fecha_baja.
        """
        self.driver.get(url)
        esperar_spinner(self.wait)

        try:
            # Hacer clic en el radio "Altas y bajas"
            hacer_click_esperando(self.driver, self.wait, By.ID, "_grupos_altaBajaA")
            esperar_spinner(self.wait)
            self.wait.until(EC.presence_of_element_located((By.ID, "_grupos_ajaxContentDiputados")))
            esperar_tabla_cargada(self.wait, "#_grupos_contentPaginationDiputados table tbody tr")
        except Exception as e:
            logger.error(f"No se pudo seleccionar 'Altas y bajas' para {grupo_nombre}: {e}")
            return []

        datos = []
        while True:
            filas = self.driver.find_elements(By.CSS_SELECTOR, "#_grupos_contentPaginationDiputados table tbody tr")
            for fila in filas:
                try:
                    # Nombre en <th>
                    nombre = fila.find_element(By.TAG_NAME, "th").text.strip()

                    # Fechas en <td>
                    columnas = fila.find_elements(By.TAG_NAME, "td")
                    fecha_alta = columnas[0].text.strip() if len(columnas) > 0 else ""
                    fecha_baja = columnas[1].text.strip() if len(columnas) > 1 else ""

                    if nombre:
                        datos.append({
                            "nombre": nombre,
                            "grupo_parlamentario": grupo_nombre,
                            "fecha_alta": fecha_alta,
                            "fecha_baja": fecha_baja,
                            "legislatura":self.legislatura
                        })
                except Exception as e:
                    logger.error(f"Error al procesar fila en {grupo_nombre}: {e}")
                    continue

            if es_ultima_pagina(self.driver, "_grupos_resultsShowedFooterDiputados"):
                break

            if not click_siguiente_pagina(
                    driver=self.driver,
                    wait=self.wait,
                    xpath_siguiente="//ul[@id='_grupos_paginationLinksDiputados']//a[text()='>']",
                    by_tabla=By.CSS_SELECTOR,
                    selector_tabla="#_grupos_contentPaginationDiputados table tbody tr",
                    id_paginador="_grupos_resultsShowedFooterDiputados"
            ):
                break

        return datos

    def ejecutar(self, output_csv="altas_bajas_grupos.csv"):
        self._init_driver()
        logger.info("Accediendo a grupos parlamentarios...")
        enlaces_grupos = self._extraer_info_legislatura()

        todos_los_datos = []
        for nombre_grupo, url in enlaces_grupos:
            logger.info(f"Procesando grupo: {nombre_grupo}")
            datos = self._extraer_altas_bajas(nombre_grupo, url)
            logger.info(f"  -> {len(datos)} diputados extraídos")
            todos_los_datos.extend(datos)

        self.driver.quit()
        df = pd.DataFrame(todos_los_datos)
        df.to_csv(output_csv, index=False, encoding="utf-8")
        logger.info(f"Guardado CSV con {len(df)} filas en {output_csv}")