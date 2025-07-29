import pandas as pd
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from scraping.utils.selenium_utils import (
    iniciar_driver,
    esperar_spinner,
    esperar_tabla_cargada,
    hacer_click_esperando,
    seleccionar_opcion_por_valor,
    aceptar_cookies
)


class EnriquecedorSuplencias:
    def __init__(self, driver_path: str, legislatura: str = "15"):
        self.url = "https://www.congreso.es/es/diputados-sustituidos-y-sustitutos"
        self.driver_path = driver_path
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path)

    def _seleccionar_filtros(self):
        self.driver.get(self.url)
        aceptar_cookies(self.driver, self.wait)
        esperar_spinner(self.wait)

        # Esperar a que los selectores estén cargados
        self.wait.until(EC.presence_of_element_located((By.ID, "_diputadomodule_legislatura")))

        seleccionar_opcion_por_valor(
            self.driver.find_element(By.ID, "_diputadomodule_legislatura"), self.legislatura
        )
        seleccionar_opcion_por_valor(
            self.driver.find_element(By.ID, "_diputadomodule_tipoSustitucion"), "0"
        )

        # Buscar el botón por su texto visible "Buscar"
        boton = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), 'Buscar')]]")
            )
        )
        boton.click()

        esperar_spinner(self.wait)
        esperar_tabla_cargada(
            self.wait, "#_diputadomodule_contentPaginationSustituciones table tbody tr"
        )

    def _parsear_fila(self, fila):
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if len(columnas) < 3:
            return None

        raw_html = columnas[0].get_attribute("innerHTML")
        nombre_match = re.search(r">([^<]+)</a>", raw_html)
        nombre = nombre_match.group(1).strip() if nombre_match else ""

        sustituye_a = ""
        sustituido_por = ""

        sustituye_match = re.search(r"Sustituy.*?a:.*?>([^<]+)<", raw_html)
        if sustituye_match:
            sustituye_a = sustituye_match.group(1).strip()

        sustituido_por_match = re.search(r"Sustituido.*?por:.*?>([^<]+)<", raw_html)
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

    def _es_ultima_pagina(self):
        try:
            texto = self.driver.find_element(By.ID, "_diputadomodule_resultsShowedFooterSustituciones").text
            match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", texto)
            if match:
                hasta = int(match.group(2))
                total = int(match.group(3))
                return hasta >= total
        except:
            pass
        return False

    def _siguiente_pagina(self):
        try:
            if self._es_ultima_pagina():
                return False
            siguiente = self.driver.find_element(
                By.XPATH,
                "//ul[@id='_diputadomodule_paginationLinksSustituciones']//a[text()='>']"
            )
            self.driver.execute_script("arguments[0].click();", siguiente)
            esperar_spinner(self.wait)
            esperar_tabla_cargada(
                self.wait, "#_diputadomodule_contentPaginationSustituciones table tbody tr"
            )
            return True
        except:
            return False

    def obtener_df_suplencias(self) -> pd.DataFrame:
        self._init_driver()
        print("Abriendo página de sustituciones...")
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
            if not self._siguiente_pagina():
                break

        self.driver.quit()
        return pd.DataFrame(datos)

    def enriquecer_df_diputados(self, df_diputados: pd.DataFrame) -> pd.DataFrame:
        df_suplencias = self.obtener_df_suplencias()

        df_final = df_diputados.copy()
        df_final = df_final.merge(
            df_suplencias[
                ["nombre", "fecha_alta", "fecha_baja", "sustituye_a", "sustituido_por"]
            ],
            on="nombre",
            how="left"
        )

        return df_final
