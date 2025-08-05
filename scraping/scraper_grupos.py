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


class GruposScraper:
    def __init__(self, driver_path: str, legislatura: str = "15"):
        self.url_base = "https://www.congreso.es/es/grupos/composicion-en-la-legislatura"
        self.driver_path = driver_path
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path, headless=False)  # Añadido headless para consistencia

    def _extraer_info_legislatura(self):
        self.driver.get(self.url_base)
        aceptar_cookies(self.driver, self.wait)
        esperar_spinner(self.wait)  # Reemplaza time.sleep(1) por una espera más robusta

        print("Seleccionando legislatura...")
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
        self.driver.get(url)
        esperar_spinner(self.wait)
        # Quitado time.sleep(2) aquí, espera implícita si es necesaria.

        # Seleccionar radio button "Altas y bajas" usando hacer_click_esperando
        try:
            hacer_click_esperando(self.driver, self.wait, By.ID, "_grupos_altaBajaA")
            esperar_spinner(self.wait)
            self.wait.until(EC.presence_of_element_located((By.ID, "_grupos_ajaxContentDiputados")))
            esperar_tabla_cargada(self.wait, "#_grupos_contentPaginationDiputados table tbody tr")
            # Quitado time.sleep(1) aquí
        except Exception as e:
            print(f"No se pudo seleccionar 'Altas y bajas' para {grupo_nombre}: {e}")
            return []

        datos = []
        while True:
            filas = self.driver.find_elements(By.CSS_SELECTOR, "#_grupos_contentPaginationDiputados table tbody tr")
            for fila in filas:
                try:
                    # Se asume que las columnas son td después de la cabecera (th)
                    columnas = fila.find_elements(By.TAG_NAME, "td")
                    # Ajuste si la primera columna es th en alguna fila de datos
                    if not columnas and fila.find_elements(By.TAG_NAME, "th"):
                        columnas = fila.find_elements(By.TAG_NAME, "th")

                    if len(columnas) >= 3:
                        nombre = columnas[0].text.strip()
                        fecha_alta = columnas[1].text.strip()
                        fecha_baja = columnas[2].text.strip()
                    else:
                        # Manejo para filas que no tienen suficientes columnas
                        nombre = columnas[0].text.strip() if columnas else ""
                        fecha_alta = ""
                        fecha_baja = ""

                    datos.append({
                        "nombre": nombre,
                        "grupo_parlamentario": grupo_nombre,
                        "fecha_alta": fecha_alta,
                        "fecha_baja": fecha_baja
                    })
                except Exception as e:
                    print(f"Error al procesar fila en {grupo_nombre}: {e}")
                    continue

            # Usar es_ultima_pagina de selenium_utils
            if es_ultima_pagina(self.driver, "_grupos_resultsShowedFooterDiputados"):
                break

            # Usar click_siguiente_pagina de selenium_utils
            if not click_siguiente_pagina(
                    driver=self.driver,
                    wait=self.wait,
                    xpath_siguiente="//ul[@id='_grupos_paginationLinksDiputados']//a[text()='>']",
                    by_tabla=By.CSS_SELECTOR,  # La tabla se localiza por CSS Selector
                    selector_tabla="#_grupos_contentPaginationDiputados table tbody tr",
                    id_paginador="_grupos_resultsShowedFooterDiputados"
            ):
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