import pandas as pd
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    esperar_spinner,
    esperar_tabla_cargada,
    seleccionar_opcion_por_valor,
    hacer_click_esperando
)
from scraping.enriquecedor_suplencias import EnriquecedorSuplencias


class DiputadosScraper:
    def __init__(self, driver_path: str, output_csv: str, legislatura: str = "15"):
        self.url = "https://www.congreso.es/busqueda-de-diputados"
        self.driver_path = driver_path
        self.output_csv = output_csv
        self.legislatura = legislatura
        self.driver = None
        self.wait = None

    def _init_driver(self):
        self.driver, self.wait = iniciar_driver(self.driver_path)

    def _buscar_diputados(self):
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

    def _es_ultima_pagina(self):
        try:
            # Probar ambos IDs por si uno no está disponible
            posibles_ids = [
                "_diputadomodule_resultsShowedDiputados",
                "_diputadomodule_resultsShowedFooterDiputados"
            ]
            for id_ in posibles_ids:
                try:
                    texto = self.driver.find_element(By.ID, id_).text
                    match = re.search(r"Resultados\s+(\d+)\s+a\s+(\d+)\s+de\s+(\d+)", texto)
                    if match:
                        hasta = int(match.group(2))
                        total = int(match.group(3))
                        return hasta >= total
                except:
                    continue
        except Exception as e: # pragma: no cover
            print(f"No se pudo determinar si es la última página: {e}")
        return False

    def _siguiente_pagina(self):
        try:
            # Primero comprobamos si ya estamos en la última página
            if self._es_ultima_pagina():
                print("Última página detectada.")
                return False

            siguiente = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//ul[@id='_diputadomodule_paginationLinksDiputados']//a[text()='>']"))
            )
            self.driver.execute_script("arguments[0].click();", siguiente)
            esperar_spinner(self.wait)
            esperar_tabla_cargada(self.wait, "#_diputadomodule_contentPaginationDiputados table tbody tr")
            print("Pasando a la siguiente página de resultados...")
            return True
        except Exception as e:
            print(f"No hay más páginas disponibles o error: {e}")
            return False

    def guardar_csv(self, df: pd.DataFrame):
        print(f"Guardando resultados en CSV: {self.output_csv}")
        df.to_csv(self.output_csv, index=False, encoding="utf-8")

    def ejecutar(self):
        self._init_driver()
        self._buscar_diputados()
        resultados_totales = []

        while True:
            resultados_totales.extend(self._procesar_pagina())
            if not self._siguiente_pagina():
                break

        self.driver.quit()
        df_diputados = pd.DataFrame(resultados_totales)

        enriquecedor = EnriquecedorSuplencias(driver_path=self.driver_path, legislatura=self.legislatura)
        df_diputados = enriquecedor.enriquecer_df_diputados(df_diputados)


        # Guardamos los resultados
        df_diputados.to_csv("diputados.csv", index=False, encoding="utf-8")

        print(f"Total diputados guardados: {len(df_diputados)}")

        self.guardar_csv(df_diputados)
        print(f"Total diputados guardados: {len(df_diputados)}")
