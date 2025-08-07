# scraping/enriquecedor suplencias.py

import pandas as pd
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    esperar_spinner,
    esperar_tabla_cargada,
    seleccionar_opcion_por_valor,
    aceptar_cookies,
    es_ultima_pagina,
    hacer_click_esperando,
    click_siguiente_pagina
)
import logging
logger = logging.getLogger(__name__)


class EnriquecedorSuplencias:
    def __init__(self, driver_path: str, legislatura: str = "15"):
        self.url = "https://www.congreso.es/es/diputados-sustituidos-y-sustitutos"
        self.driver_path = driver_path
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path, headless=True) # pragma: no cover

    def _seleccionar_filtros(self):
        self.driver.get(self.url)
        aceptar_cookies(self.driver, self.wait) # pragma: no cover
        esperar_spinner(self.wait) # pragma: no cover

        # Esperar a que los selectores estén cargados
        self.wait.until(EC.presence_of_element_located((By.ID, "_diputadomodule_legislatura")))

        seleccionar_opcion_por_valor(
            self.driver.find_element(By.ID, "_diputadomodule_legislatura"), self.legislatura
        )
        seleccionar_opcion_por_valor(
            self.driver.find_element(By.ID, "_diputadomodule_tipoSustitucion"), "0"
        )

        # Usar hacer_click_esperando para el botón de búsqueda
        hacer_click_esperando(self.driver, self.wait, By.XPATH, "//button[.//span[contains(text(), 'Buscar')]]")

        esperar_spinner(self.wait)
        esperar_tabla_cargada(
            self.wait, "#_diputadomodule_contentPaginationSustituciones table tbody tr"
        )

    def _parsear_fila(self, fila):
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if len(columnas) < 3:
            return None

        # La columna 0 contiene el nombre del diputado y la información de sustitución
        raw_html = columnas[0].get_attribute("innerHTML")

        # Extraer nombre del diputado principal
        nombre_match = re.search(r'>([^<]+)</a>', raw_html)
        nombre = nombre_match.group(1).strip() if nombre_match else ""

        sustituye_a = ""
        sustituido_por = ""

        # Usar re.search para encontrar "Sustituye a:"
        sustituye_match = re.search(r'Sustituy.*?a:\s*.*?<a[^>]*?>([^<]+)</a>', raw_html)
        if sustituye_match:
            sustituye_a = sustituye_match.group(1).strip()

        # Usar re.search para encontrar "Sustituido por:"
        sustituido_por_match = re.search(r'Sustituido.*?por:\s*.*?<a[^>]*?>([^<]+)</a>', raw_html)
        if sustituido_por_match:
            sustituido_por = sustituido_por_match.group(1).strip()

        fecha_alta = columnas[1].text.strip()
        fecha_baja = columnas[2].text.strip()

        return {
            "nombre": nombre,
            "fecha_alta": fecha_alta,
            "fecha_baja": fecha_baja,
            "sustituye_a": sustituye_a,
            "sustituido_por": sustituido_por,
        }

    # Se ha eliminado _es_ultima_pagina y _siguiente_pagina de aquí
    # porque ahora se usarán las funciones de selenium_utils.py

    def obtener_df_suplencias(self) -> pd.DataFrame:
        self._init_driver()
        logger.info("Abriendo página de sustituciones...")
        self._seleccionar_filtros()

        datos = []
        while True:
            filas = self.driver.find_elements(
                By.CSS_SELECTOR,
                "#_diputadomodule_contentPaginationSustituciones table tbody tr"
            )
            for fila in filas:
                datos_dict = self._parsear_fila(fila)
                if datos_dict:
                    datos.append(datos_dict)

            # Usar es_ultima_pagina de utils
            if es_ultima_pagina(self.driver, "_diputadomodule_resultsShowedFooterSustituciones"):
                logger.info("Última página de suplencias detectada.")
                break

            # Usar click_siguiente_pagina de utils
            if not click_siguiente_pagina(
                    driver=self.driver,
                    wait=self.wait,
                    xpath_siguiente="//ul[@id='_diputadomodule_paginationLinksSustituciones']//a[text()='>']",
                    by_tabla=By.CSS_SELECTOR,  # Especificar que la tabla se localiza por CSS
                    selector_tabla="#_diputadomodule_contentPaginationSustituciones table tbody tr",
                    id_paginador="_diputadomodule_resultsShowedFooterSustituciones"  # ID del paginador
            ):
                logger.error("No hay más páginas de suplencias o ocurrió un error al avanzar.")
                break

        self.driver.quit()
        return pd.DataFrame(datos)

    def enriquecer_df_diputados(self, df_diputados: pd.DataFrame) -> pd.DataFrame:
        logger.info("Obteniendo datos de suplencias...")
        df_suplencias = self.obtener_df_suplencias()
        logger.info(f"Total de registros de suplencias obtenidos: {len(df_suplencias)}")

        df_final = df_diputados.copy()

        # Renombrar columnas para evitar conflictos y asegurar merge correcto
        df_suplencias_renamed = df_suplencias.rename(columns={
            "fecha_alta": "fecha_alta_suplencia",
            "fecha_baja": "fecha_baja_suplencia",
            "sustituye_a": "sustituye_a",
            "sustituido_por": "sustituido_por"
        })

        # Combinar los DataFrames
        # Usar un merge 'left' para mantener todos los diputados originales y añadir info de suplencias si existe
        df_final = pd.merge(
            df_final,
            df_suplencias_renamed,
            on="nombre",
            how="left",
            suffixes=('_diputado', '_suplencia')  # Para manejar columnas con nombres duplicados si los hubiera
        )
        logger.info("DataFrame de diputados enriquecido con datos de suplencias.")
        return df_final
