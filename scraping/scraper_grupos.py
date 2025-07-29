# scraping/scraper_grupos.py

import re
import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    esperar_spinner,
    esperar_tabla_cargada,
    hacer_click_esperando
)


class GruposScraper:
    def __init__(self, driver_path: str, legislatura: str = "15"):
        self.url_base = "https://www.congreso.es/es/grupos/composicion-en-la-legislatura"
        self.driver_path = driver_path
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path)

    def _extraer_info_legislatura(self):
        self.driver.get(self.url_base)
        aceptar_cookies(self.driver, self.wait)
        time.sleep(1)

        print("Seleccionando legislatura...")
        select = self.driver.find_element(By.ID, "_grupos_legislatura")
        for option in select.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == self.legislatura:
                option.click()
                break

        time.sleep(2)
        contenedor = self.driver.find_element(By.ID, "_grupos_ajaxContentGrupo")
        enlaces = contenedor.find_elements(By.TAG_NAME, "a")
        resultado = [(enlace.text.strip().split(':')[0], enlace.get_attribute("href")) for enlace in enlaces]
        return resultado

    def _extraer_altas_bajas(self, grupo_nombre: str, url: str):
        self.driver.get(url)
        esperar_spinner(self.wait)
        time.sleep(2)

        # Seleccionar radio button "Altas y bajas"
        try:
            radio_alta_baja = self.driver.find_element(By.ID, "_grupos_altaBajaA")
            self.driver.execute_script("arguments[0].click();", radio_alta_baja)
            esperar_spinner(self.wait)
            self.wait.until(EC.presence_of_element_located((By.ID, "_grupos_ajaxContentDiputados")))
            esperar_tabla_cargada(self.wait, "#_grupos_contentPaginationDiputados table tbody tr")
            time.sleep(1)
        except:
            print(f"No se pudo seleccionar 'Altas y bajas' para {grupo_nombre}")
            return []

        datos = []
        while True:
            filas = self.driver.find_elements(By.CSS_SELECTOR, "#_grupos_contentPaginationDiputados table tbody tr")
            for fila in filas:
                try:
                    columnas = fila.find_elements(By.TAG_NAME, "th") + fila.find_elements(By.TAG_NAME, "td")
                    if len(columnas) >= 3:
                        nombre = columnas[0].text.strip()
                        fecha_alta = columnas[1].text.strip()
                        fecha_baja = columnas[2].text.strip()
                    else:
                        nombre = columnas[0].text.strip() if columnas else ""
                        fecha_alta = ""
                        fecha_baja = ""

                    datos.append({
                        "nombre": nombre,
                        "grupo_parlamentario": grupo_nombre,
                        "fecha_alta": fecha_alta,
                        "fecha_baja": fecha_baja
                    })
                except:
                    continue

            try:
                resultados_texto = self.driver.find_element(By.ID, "_grupos_resultsShowedFooterDiputados").text
                match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", resultados_texto)
                if not match or int(match.group(2)) >= int(match.group(3)):
                    break
            except:
                break

            try:
                siguiente = self.driver.find_element(By.XPATH, "//ul[@id='_grupos_paginationLinksDiputados']//a[text()='>']")
                self.driver.execute_script("arguments[0].click();", siguiente)
                esperar_spinner(self.wait)
                self.wait.until(EC.presence_of_element_located((By.ID, "_grupos_ajaxContentDiputados")))
                esperar_tabla_cargada(self.wait, "#_grupos_contentPaginationDiputados table tbody tr")
                time.sleep(1)
            except:
                break

        return datos

    def ejecutar(self, output_csv="altas_bajas_grupos.csv"):
        self._init_driver()
        print("Accediendo a grupos parlamentarios...")
        enlaces_grupos = self._extraer_info_legislatura()

        todos_los_datos = []
        for nombre_grupo, url in enlaces_grupos:
            print(f"Procesando grupo: {nombre_grupo}")
            datos = self._extraer_altas_bajas(nombre_grupo, url)
            print(f"  -> {len(datos)} diputados extraídos")
            todos_los_datos.extend(datos)

        self.driver.quit()
        df = pd.DataFrame(todos_los_datos)
        df.to_csv(output_csv, index=False, encoding="utf-8")
        print(f"Guardado CSV con {len(df)} filas en {output_csv}")
