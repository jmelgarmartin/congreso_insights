# tests/scraping/test_scraper_diputados.py

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from scraping.scraper_diputados import DiputadosScraper


@pytest.fixture
def scraper():
    """Crea una instancia del scraper con paths ficticios para pruebas."""
    return DiputadosScraper(driver_path="fake/path", output_csv="salida.csv", legislatura="15")


# Test para verificar que el método _init_driver asigna correctamente el driver y wait
@patch("scraping.scraper_diputados.iniciar_driver")
def test_init_driver(mock_init, scraper):
    driver_mock, wait_mock = MagicMock(), MagicMock()
    mock_init.return_value = (driver_mock, wait_mock)

    scraper._init_driver()

    assert scraper.driver == driver_mock
    assert scraper.wait == wait_mock


# Test para verificar que se aplican correctamente los filtros en la búsqueda
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
@patch("scraping.scraper_diputados.esperar_spinner")
@patch("scraping.scraper_diputados.hacer_click_esperando")
@patch("scraping.scraper_diputados.seleccionar_opcion_por_valor")
@patch("scraping.scraper_diputados.aceptar_cookies")
def test_buscar_diputados(mock_aceptar, mock_sel, mock_click, mock_spinner, mock_tabla, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()

    # Simular que el selector no tiene el valor de la legislatura
    select_mock = MagicMock()
    select_mock.get_attribute.return_value = "13"
    scraper.driver.find_element.return_value = select_mock

    scraper._buscar_diputados()

    # Se espera que se seleccione la legislatura si no coincide
    mock_sel.assert_any_call(select_mock, "15")
    mock_click.assert_called_once()
    mock_spinner.assert_called()
    mock_tabla.assert_called_once()


# Test para verificar que se extrae correctamente la información de un diputado
def test_extraer_info_diputado(scraper):
    fila = MagicMock()
    celda1, celda2 = MagicMock(), MagicMock()
    fila.find_elements.return_value = [celda1, celda2]
    celda1.text = "Grupo A"
    celda2.text = "Provincia X"
    fila.find_element.return_value.text = "Juan Pérez"

    resultado = scraper._extraer_info_diputado(fila)

    assert resultado["nombre"] == "Juan Pérez"
    assert resultado["grupo_actual"] == "Grupo A"
    assert resultado["provincia"] == "Provincia X"


# Test para verificar que se procesan correctamente los diputados de una página
@patch("scraping.scraper_diputados.esperar_tabla_cargada")
def test_procesar_pagina(mock_esperar, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()

    fila = MagicMock()
    scraper.driver.find_elements.return_value = [fila]
    scraper._extraer_info_diputado = MagicMock(return_value={"nombre": "Dip", "grupo_actual": "G", "provincia": "P"})

    resultados = scraper._procesar_pagina()

    assert len(resultados) == 1
    assert resultados[0]["nombre"] == "Dip"


# Test para verificar que guardar_csv utiliza pandas to_csv correctamente
@patch("pandas.DataFrame.to_csv")
def test_guardar_csv(mock_to_csv, scraper):
    df = pd.DataFrame([{"nombre": "X"}])
    scraper.guardar_csv(df)
    mock_to_csv.assert_called_once_with("salida.csv", index=False, encoding="utf-8")


# Test completo del método ejecutar para flujo con una sola página sin paginación
@patch("scraping.scraper_diputados.EnriquecedorSuplencias")
@patch("scraping.scraper_diputados.pd.DataFrame")
@patch("scraping.scraper_diputados.click_siguiente_pagina", return_value=False)
@patch("scraping.scraper_diputados.es_ultima_pagina", return_value=True)
@patch("scraping.scraper_diputados.DiputadosScraper._procesar_pagina")
@patch("scraping.scraper_diputados.DiputadosScraper._buscar_diputados")
@patch("scraping.scraper_diputados.DiputadosScraper._init_driver")
def test_ejecutar_flujo_simple(
    mock_init, mock_buscar, mock_procesar, mock_es_ultima, mock_siguiente, mock_df, mock_enriquecedor, scraper
):
    scraper.driver = MagicMock()

    mock_procesar.return_value = [{"nombre": "Dip", "grupo_actual": "Grupo", "provincia": "Provincia"}]

    df_mock = MagicMock()
    mock_df.return_value = df_mock
    enriq_mock = MagicMock()
    enriq_mock.enriquecer_df_diputados.return_value = df_mock
    mock_enriquecedor.return_value = enriq_mock

    scraper.guardar_csv = MagicMock()

    scraper.ejecutar()

    mock_init.assert_called_once()
    mock_buscar.assert_called_once()
    mock_procesar.assert_called_once()
    scraper.guardar_csv.assert_called_once_with(df_mock)


# Test de ejecución con múltiples páginas (click_siguiente_pagina devuelve True una vez, luego False)
@patch("scraping.scraper_diputados.EnriquecedorSuplencias")
@patch("scraping.scraper_diputados.click_siguiente_pagina")
@patch("scraping.scraper_diputados.es_ultima_pagina", return_value=False)
@patch("scraping.scraper_diputados.DiputadosScraper._procesar_pagina")
@patch("scraping.scraper_diputados.DiputadosScraper._buscar_diputados")
@patch("scraping.scraper_diputados.DiputadosScraper._init_driver")
@patch("scraping.scraper_diputados.pd.DataFrame.to_csv")
def test_ejecutar_multiple_paginas(
    mock_to_csv,
    mock_init,
    mock_buscar,
    mock_procesar,
    mock_es_ultima,
    mock_click_siguiente,
    mock_enriquecedor
):
    """
    Test para ejecutar el flujo completo simulando múltiples páginas de resultados
    y asegurando que se llama más de una vez a _procesar_pagina.
    """
    # Simular llamada a _procesar_pagina dos veces con un diputado cada una
    mock_procesar.side_effect = [
        [{"nombre": "Dip1", "grupo_actual": "G1", "provincia": "P1"}],
        [{"nombre": "Dip2", "grupo_actual": "G2", "provincia": "P2"}]
    ]

    # Simular click_siguiente_pagina True la primera vez, False después
    mock_click_siguiente.side_effect = [True, False]

    # Simular retorno del enriquecedor
    mock_enriquecedor().enriquecer_df_diputados.return_value = pd.DataFrame([
        {"nombre": "Dip1", "grupo_actual": "G1", "provincia": "P1"},
        {"nombre": "Dip2", "grupo_actual": "G2", "provincia": "P2"}
    ])

    # Crear instancia y mockear el driver (necesario para que .quit() no falle)
    scraper = DiputadosScraper(driver_path="fake_path", output_csv="output.csv")
    scraper.driver = MagicMock()  # Añadir este mock para evitar el error de 'NoneType'

    # Ejecutar
    scraper.ejecutar()

    # Verificar que _procesar_pagina se llamó dos veces
    assert mock_procesar.call_count == 2
    mock_click_siguiente.assert_called()
    mock_enriquecer_df = mock_enriquecedor().enriquecer_df_diputados
    mock_enriquecer_df.assert_called_once()
    mock_to_csv.assert_called_once()

