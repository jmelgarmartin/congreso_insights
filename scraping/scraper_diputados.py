# scraping/scraper_diputados.py

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    esperar_spinner,
    esperar_tabla_cargada,
    seleccionar_opcion_por_valor,
    hacer_click_esperando,
    es_ultima_pagina,
    click_siguiente_pagina
)
from scraping.enriquecedor_suplencias import EnriquecedorSuplencias


class DiputadosScraper:
    """
    Scraper para obtener el listado de diputados y sus datos básicos desde la web del Congreso.
    """

    def __init__(self, driver_path: str, output_csv: str, legislatura: str = "15"):
        self.url = "https://www.congreso.es/busqueda-de-diputados"
        self.driver_path = driver_path
        self.output_csv = output_csv
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        """Inicializa el driver de Selenium."""
        self.driver, self.wait = iniciar_driver(self.driver_path, headless=True)

    def _buscar_diputados(self):
        """Aplica los filtros en la web para iniciar la búsqueda de diputados."""
        print("Abriendo página de búsqueda de diputados...")
        self.driver.get(self.url)
        aceptar_cookies(self.driver, self.wait)

        print("Esperando a que cargue el selector de legislatura...")
        self.wait.until(EC.presence_of_element_located((By.ID, "_diputadomodule_legislatura")))

        print(f"Seleccionando legislatura {self.legislatura} si es necesario...")
        select_legislatura = self.driver.find_element(By.ID, "_diputadomodule_legislatura")
        if select_legislatura.get_attribute("value") != self.legislatura:
            seleccionar_opcion_por_valor(select_legislatura, self.legislatura)
            print(f"Legislatura {self.legislatura} seleccionada")

        print("Seleccionando 'Todos' en el filtro de tipo...")
        seleccionar_opcion_por_valor(self.driver.find_element(By.ID, "_diputadomodule_tipo"), "2")
        print("Filtro 'Todos' seleccionado en tipo")

        print("Haciendo clic en el botón de búsqueda...")
        hacer_click_esperando(self.driver, self.wait, By.ID, "_diputadomodule_searchButtonDiputadosForm")

        print("Esperando a que desaparezca el spinner de carga...")
        esperar_spinner(self.wait)

        print("Esperando a que se muestren los resultados por tabla...")
        esperar_tabla_cargada(self.wait, "#_diputadomodule_contentPaginationDiputados table tbody tr")
        print("Resultados cargados")

    def _extraer_info_diputado(self, fila):
        """Extrae los datos de un diputado a partir de una fila de la tabla."""
        celdas = fila.find_elements(By.TAG_NAME, "td")
        nombre = fila.find_element(By.TAG_NAME, "a").text.strip()
        grupo = celdas[0].text.strip() if len(celdas) > 0 else ""
        provincia = celdas[1].text.strip() if len(celdas) > 1 else ""
        return {
            "nombre": nombre,
            "grupo_actual": grupo,
            "provincia": provincia
        }

    def _procesar_pagina(self):
        """Procesa la tabla de resultados de la página actual y devuelve una lista de diputados."""
        print("Procesando página de resultados...")
        esperar_tabla_cargada(self.wait, "#_diputadomodule_contentPaginationDiputados table tbody tr")
        filas = self.driver.find_elements(By.CSS_SELECTOR, "#_diputadomodule_contentPaginationDiputados table tbody tr")
        print(f"Número de diputados en esta página: {len(filas)}")
        resultados = []
        for fila in filas:
            datos = self._extraer_info_diputado(fila)
            print(f"Diputado: {datos['nombre']} - Grupo: {datos['grupo_actual']} - Provincia: {datos['provincia']}")
            resultados.append(datos)
        return resultados

    def guardar_csv(self, df: pd.DataFrame):
        """Guarda el DataFrame final de diputados en un archivo CSV."""
        print(f"Guardando resultados en CSV: {self.output_csv}")
        df.to_csv(self.output_csv, index=False, encoding="utf-8")

    def ejecutar(self):
        """Ejecuta el proceso completo de scraping y enriquecimiento."""
        self._init_driver()
        self._buscar_diputados()
        resultados_totales = []

        while True:
            resultados_totales.extend(self._procesar_pagina())

            # Comprobamos si es la última página usando función de utils
            posibles_ids = [
                "_diputadomodule_resultsShowedDiputados",
                "_diputadomodule_resultsShowedFooterDiputados"
            ]
            if any(es_ultima_pagina(self.driver, id_) for id_ in posibles_ids):
                print("Última página detectada.")
                break

            if not click_siguiente_pagina(
                    driver=self.driver,
                    wait=self.wait,
                    xpath_siguiente="//ul[@id='_diputadomodule_paginationLinksDiputados']//a[text()='>']",
                    by_tabla=By.CSS_SELECTOR,  # <-- AÑADE ESTA LÍNEA
                    selector_tabla="#_diputadomodule_contentPaginationDiputados table tbody tr"
            ):
                break

        self.driver.quit()
        df_diputados = pd.DataFrame(resultados_totales)

        enriquecedor = EnriquecedorSuplencias(driver_path=self.driver_path, legislatura=self.legislatura)
        df_diputados = enriquecedor.enriquecer_df_diputados(df_diputados)

        self.guardar_csv(df_diputados)
        print(f"Total diputados guardados: {len(df_diputados)}")
