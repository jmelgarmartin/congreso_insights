# test/scraping/test_enriquecedor_suplencias.py

import pytest
import pandas as pd
from scraping.enriquecedor_suplencias import EnriquecedorSuplencias
from unittest.mock import patch, MagicMock


@pytest.fixture
def scraper():
    """Fixture que devuelve una instancia del enriquecedor para reutilizar en varios tests"""
    return EnriquecedorSuplencias(driver_path="fake/path")


# Test: fila completa con nombre, sustituye_a y sustituido_por
def test_parsear_fila_completa(scraper):
    fila = MagicMock()
    columnas = [MagicMock(), MagicMock(), MagicMock()]
    fila.find_elements.return_value = columnas

    columnas[0].get_attribute.return_value = """
        <a href="#">Diputado Ejemplo</a><br>
        Sustituye a: <a href="#">Diputado A</a><br>
        Sustituido por: <a href="#">Diputado B</a>
    """
    columnas[1].text = "01/01/2023"
    columnas[2].text = "01/02/2023"

    resultado = scraper._parsear_fila(fila)
    assert resultado == {
        "nombre": "Diputado Ejemplo",
        "fecha_alta": "01/01/2023",
        "fecha_baja": "01/02/2023",
        "sustituye_a": "Diputado A",
        "sustituido_por": "Diputado B",
    }


# Test: solo sustituye_a
def test_parsear_fila_solo_sustituye(scraper):
    fila = MagicMock()
    columnas = [MagicMock(), MagicMock(), MagicMock()]
    fila.find_elements.return_value = columnas

    columnas[0].get_attribute.return_value = """
        <a href="#">Diputado Ejemplo</a><br>
        Sustituye a: <a href="#">Diputado A</a>
    """
    columnas[1].text = "10/01/2023"
    columnas[2].text = "10/03/2023"

    resultado = scraper._parsear_fila(fila)
    assert resultado["sustituye_a"] == "Diputado A"
    assert resultado["sustituido_por"] == ""


# Test: solo sustituido_por
def test_parsear_fila_solo_sustituido(scraper):
    fila = MagicMock()
    columnas = [MagicMock(), MagicMock(), MagicMock()]
    fila.find_elements.return_value = columnas

    columnas[0].get_attribute.return_value = """
        <a href="#">Diputado Ejemplo</a><br>
        Sustituido por: <a href="#">Diputado B</a>
    """
    columnas[1].text = "15/01/2023"
    columnas[2].text = "15/03/2023"

    resultado = scraper._parsear_fila(fila)
    assert resultado["sustituye_a"] == ""
    assert resultado["sustituido_por"] == "Diputado B"


# Test: fila incompleta (menos de 3 columnas)
def test_parsear_fila_incompleta(scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(), MagicMock()]  # solo 2 columnas
    resultado = scraper._parsear_fila(fila)
    assert resultado is None


def test_enriquecer_df_diputados_merge():
    """Verifica que enriquecer_df_diputados fusiona correctamente los datos de suplencias"""
    scraper = EnriquecedorSuplencias(driver_path="fake/path")

    df_diputados = pd.DataFrame([{"nombre": "Diputado Ejemplo", "grupo": "Grupo X"}])
    df_suplencias = pd.DataFrame([{
        "nombre": "Diputado Ejemplo",
        "fecha_alta": "2023-01-01",
        "fecha_baja": "2023-01-31",
        "sustituye_a": "Diputado A",
        "sustituido_por": ""
    }])

    with patch.object(scraper, "obtener_df_suplencias", return_value=df_suplencias):
        resultado = scraper.enriquecer_df_diputados(df_diputados)

    assert resultado.shape[0] == 1
    assert resultado.loc[0, "fecha_alta_suplencia"] == "2023-01-01"
    assert resultado.loc[0, "sustituye_a"] == "Diputado A"


@patch("scraping.enriquecedor_suplencias.click_siguiente_pagina", return_value=False)
@patch("scraping.enriquecedor_suplencias.es_ultima_pagina", return_value=True)
def test_obtener_df_suplencias_simple(mock_ultima, mock_click):
    scraper = EnriquecedorSuplencias(driver_path="fake/path")

    fila_mock = MagicMock()
    fila_dict = {
        "nombre": "Diputado X",
        "fecha_alta": "2023-01-01",
        "fecha_baja": "2023-01-02",
        "sustituye_a": "Diputado A",
        "sustituido_por": "Diputado B",
    }

    with patch.object(scraper, "_init_driver"), \
            patch.object(scraper, "_seleccionar_filtros"), \
            patch.object(scraper, "_parsear_fila", return_value=fila_dict), \
            patch.object(scraper, "driver") as mock_driver:
        mock_driver.find_elements.return_value = [fila_mock]
        df_resultado = scraper.obtener_df_suplencias()

    assert isinstance(df_resultado, pd.DataFrame)
    assert df_resultado.shape[0] == 1
    assert df_resultado.iloc[0]["nombre"] == "Diputado X"


@patch("scraping.enriquecedor_suplencias.esperar_tabla_cargada")
@patch("scraping.enriquecedor_suplencias.hacer_click_esperando")
@patch("scraping.enriquecedor_suplencias.seleccionar_opcion_por_valor")
@patch("scraping.enriquecedor_suplencias.esperar_spinner")
@patch("scraping.enriquecedor_suplencias.aceptar_cookies")
def test_seleccionar_filtros(mock_aceptar, mock_spinner, mock_sel_valor, mock_click, mock_tabla):
    """Verifica que _seleccionar_filtros ejecuta correctamente toda la cadena de selección"""
    scraper = EnriquecedorSuplencias(driver_path="fake/path")
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()

    elemento_mock = MagicMock()
    scraper.driver.find_element.return_value = elemento_mock
    scraper.wait.until.return_value = True

    scraper._seleccionar_filtros()

    mock_aceptar.assert_called_once()
    mock_spinner.assert_called()
    mock_sel_valor.assert_any_call(elemento_mock, "15")
    mock_click.assert_called()
    mock_tabla.assert_called_once()


def test_seleccionar_filtros_cubre_lineas_iniciales():
    """
    Cubre explícitamente:
    - self.driver.get(self.url)
    - aceptar_cookies(...)
    - esperar_spinner(...)
    """
    scraper = EnriquecedorSuplencias(driver_path="fake/path")

    # Solo mockeamos lo mínimo necesario
    mock_driver = MagicMock()
    mock_driver.get = MagicMock()
    mock_driver.find_element.return_value = MagicMock()
    scraper.driver = mock_driver

    scraper.wait = MagicMock()
    scraper.wait.until.return_value = True

    # Ejecutamos la función real
    scraper._seleccionar_filtros()

    # Confirmamos que las líneas fueron alcanzadas
    scraper.driver.get.assert_called_once_with("https://www.congreso.es/es/diputados-sustituidos-y-sustitutos")
    assert scraper.driver.find_element.called
    assert scraper.wait.until.called


@patch("scraping.enriquecedor_suplencias.click_siguiente_pagina", return_value=False)
@patch("scraping.enriquecedor_suplencias.es_ultima_pagina", return_value=False)
def test_obtener_df_suplencias_caso_no_hay_mas_paginas(mock_ultima, mock_click_siguiente):
    """
    Test que fuerza la ruta en la que click_siguiente_pagina devuelve False
    y por tanto se imprime el mensaje de fin de paginación alternativo.
    """
    scraper = EnriquecedorSuplencias(driver_path="fake/path")
    scraper._init_driver = MagicMock()
    scraper._seleccionar_filtros = MagicMock()

    mock_driver = MagicMock()
    mock_wait = MagicMock()

    # Simula una única fila sin datos relevantes
    fila_mock = MagicMock()
    fila_mock.find_elements.return_value = []
    mock_driver.find_elements.return_value = [fila_mock]

    scraper.driver = mock_driver
    scraper.wait = mock_wait

    df = scraper.obtener_df_suplencias()
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert mock_click_siguiente.called
