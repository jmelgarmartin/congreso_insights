# scraping/congreso_scraper.py

import os
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from scraping.utils.selenium_utils import (
    iniciar_driver,
    aceptar_cookies,
    seleccionar_opcion_por_valor,
    esperar_spinner,
    esperar_tabla_cargada,
    hacer_click_esperando
)


class CongresoScraper:
    def __init__(self, driver_path: str, output_dir: str, legislatura: str = "15"):
        self.url = "https://www.congreso.es/busqueda-de-publicaciones"
        self.driver_path = driver_path
        self.output_dir = output_dir
        self.legislatura = legislatura
        self.driver = None
        self.wait = None
        os.makedirs(output_dir, exist_ok=True)

    def _apply_filters(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "_publicaciones_legislatura")))
            print("Aplicando filtros...")
            Select(self.driver.find_element(By.ID, "_publicaciones_legislatura")).select_by_value(self.legislatura)
            seleccionar_opcion_por_valor(self.driver.find_element(By.ID, "publicacion"), "D")
            seleccionar_opcion_por_valor(self.driver.find_element(By.ID, "seccion"), "CONGRESO")
            time.sleep(1)
            hacer_click_esperando(self.driver, self.wait, By.XPATH,
                                  "//button[.//span[normalize-space(text())='Buscar']]")

            print("Buscando resultados...")
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//tr[td//a[contains(text(),'Texto íntegro')]]")))
            print("Resultados cargados.")
        except Exception as e:
            print("Error al aplicar filtros:", e)
            self.driver.quit()
            raise

    def _get_rango_resultados(self):
        try:
            texto = self.driver.find_element(By.ID, "_publicaciones_resultsShowedPublicaciones").text
            match = re.search(r"Resultados (\d+) a (\d+) de (\d+)", texto)
            if match:
                return int(match.group(2)), int(match.group(3))
        except:
            pass
        return None, None

    def _procesar_fila(self, fila):
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
            print(f"Ya existe: {nombre_archivo}")
            return False

        texto_link = fila.find_element(By.XPATH, ".//a[contains(text(),'Texto íntegro')]")
        href = texto_link.get_attribute("href")
        print(f"Procesando: {href}")

        self.driver.execute_script("window.open(arguments[0]);", href)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        contenido = soup.find("section", id="portlet_publicaciones")
        if contenido:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(str(contenido))
            print(f"Guardado: {nombre_archivo}")
        else:
            print(f"No se encontró contenido en: {nombre_archivo}")

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return True

    def descargar_plenos(self):
        self.driver, self.wait = iniciar_driver(self.driver_path)
        self.driver.get(self.url)
        aceptar_cookies(self.driver, self.wait)
        self._apply_filters()

        descargados = 0
        pagina = 1

        while True:
            print(f"Página {pagina}")
            filas = self.driver.find_elements(By.XPATH, "//tr[td//a[contains(text(),'Texto íntegro')]]")

            i = 0
            while i < len(filas):
                for _ in range(3):
                    try:
                        filas_actualizadas = self.driver.find_elements(By.XPATH,
                                                                       "//tr[td//a[contains(text(),'Texto íntegro')]]")
                        if i >= len(filas_actualizadas):
                            break
                        if self._procesar_fila(filas_actualizadas[i]):
                            descargados += 1
                        break
                    except Exception as e:
                        print(f"Error procesando fila {i + 1}: {e}")
                i += 1

            hasta, total = self._get_rango_resultados()
            if hasta is None or hasta >= total:
                print("Ultima página detectada.")
                break

            try:
                siguiente = self.driver.find_element(By.XPATH,
                                                     "//ul[@id='_publicaciones_paginationLinksPublicaciones']//a[text()='>']")
                siguiente.click()
                pagina += 1
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//tr[td//a[contains(text(),'Texto íntegro')]]")))
            except Exception as e:
                print("No hay más páginas:", e)
                break

        self.driver.quit()
        print("\nProceso completado")
        print(f"Total nuevos plenos descargados: {descargados}")
