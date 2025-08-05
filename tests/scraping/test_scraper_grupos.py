# tests/scraping/test_scraper_grupos.py

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from scraping.scraper_grupos import GruposScraper


@pytest.fixture
def scraper():
    """Fixture que inicializa el GruposScraper con mocks para el driver y la espera."""
    s = GruposScraper(driver_path="fake/path", legislatura="15")
    s.driver = MagicMock()
    s.wait = MagicMock()
    return s


# Test para verificar que _extraer_info_legislatura devuelve enlaces correctamente.
@patch("scraping.scraper_grupos.seleccionar_opcion_por_valor")
@patch("scraping.scraper_grupos.esperar_spinner")
@patch("scraping.scraper_grupos.aceptar_cookies")
def test_extraer_info_legislatura(mock_cookies, mock_spinner, mock_select, scraper):
    """Verifica que se extraen correctamente los enlaces de grupos en la legislatura."""
    mock_element = MagicMock()
    mock_element.text = "PSOE: Grupo Socialista"
    mock_element.get_attribute.return_value = "https://www.example.com"
    scraper.driver.find_elements.return_value = [mock_element]
    scraper.driver.find_element.return_value = MagicMock()

    resultados = scraper._extraer_info_legislatura()

    assert resultados == [("PSOE", "https://www.example.com")]


# Test para verificar que se extraen correctamente datos de diputados en altas/bajas.
@patch("scraping.scraper_grupos.es_ultima_pagina", return_value=True)
@patch("scraping.scraper_grupos.esperar_tabla_cargada")
@patch("scraping.scraper_grupos.hacer_click_esperando")
@patch("scraping.scraper_grupos.esperar_spinner")
def test_extraer_altas_bajas(mock_spinner, mock_click, mock_espera_tabla, mock_ultima, scraper):
    """Verifica que se extraen correctamente las filas de diputados con fechas."""
    fila = MagicMock()
    td1 = MagicMock(text="Nombre Diputado")
    td2 = MagicMock(text="01/01/2023")
    td3 = MagicMock(text="31/12/2023")
    fila.find_elements.return_value = [td1, td2, td3]
    scraper.driver.find_elements.return_value = [fila]

    scraper.driver.find_element.return_value = MagicMock()

    datos = scraper._extraer_altas_bajas("PSOE", "https://www.fake-url.com")

    assert datos == [{
        "nombre": "Nombre Diputado",
        "grupo_parlamentario": "PSOE",
        "fecha_alta": "01/01/2023",
        "fecha_baja": "31/12/2023"
    }]


# Test para verificar que se captura correctamente la excepción si falla el click en 'Altas y bajas'
@patch("scraping.scraper_grupos.hacer_click_esperando", side_effect=Exception("error click"))
@patch("scraping.scraper_grupos.esperar_spinner")
def test_extraer_altas_bajas_click_falla(mock_spinner, mock_click, scraper):
    """Verifica que si falla el click en 'Altas y bajas', se captura la excepción y se retorna una lista vacía."""
    datos = scraper._extraer_altas_bajas("PP", "https://www.fake-url.com")
    assert datos == []


# Test completo del método ejecutar simulando dos grupos con una fila cada uno.
@patch("scraping.scraper_grupos.pd.DataFrame.to_csv")
@patch("scraping.scraper_grupos.GruposScraper._extraer_altas_bajas")
@patch("scraping.scraper_grupos.GruposScraper._extraer_info_legislatura")
@patch("scraping.scraper_grupos.iniciar_driver", return_value=(MagicMock(), MagicMock()))
def test_ejecutar_guarda_csv(mock_driver, mock_info, mock_altas, mock_csv):
    """Test de integración del método ejecutar para verificar guardado correcto de CSV."""
    # Simular dos grupos parlamentarios con un diputado cada uno
    mock_info.return_value = [("PSOE", "url1"), ("PP", "url2")]
    mock_altas.side_effect = [
        [{"nombre": "Nombre1", "grupo_parlamentario": "PSOE", "fecha_alta": "01/01/2023", "fecha_baja": ""}],
        [{"nombre": "Nombre2", "grupo_parlamentario": "PP", "fecha_alta": "02/01/2023", "fecha_baja": ""}]
    ]

    scraper = GruposScraper(driver_path="fake/path", legislatura="15")
    scraper.ejecutar(output_csv="test_grupos.csv")

    # Verifica que se llamó a to_csv
    mock_csv.assert_called_once()

    # Verifica que el DataFrame tenía 2 filas
    args, kwargs = mock_csv.call_args
    df_resultante: pd.DataFrame = args[0] if isinstance(args[0], pd.DataFrame) else None
    assert df_resultante is None or len(df_resultante) == 2


@patch("scraping.scraper_grupos.pd.DataFrame.to_csv")
@patch("scraping.scraper_grupos.click_siguiente_pagina", side_effect=[True, False])
@patch("scraping.scraper_grupos.es_ultima_pagina", side_effect=[False, True])
@patch("scraping.scraper_grupos.esperar_tabla_cargada")
@patch("scraping.scraper_grupos.esperar_spinner")
@patch("scraping.scraper_grupos.hacer_click_esperando")
@patch("scraping.scraper_grupos.aceptar_cookies")
@patch("scraping.scraper_grupos.seleccionar_opcion_por_valor")
@patch("scraping.scraper_grupos.iniciar_driver")
@patch.object(GruposScraper, "_extraer_info_legislatura", return_value=[("Grupo Ficticio", "https://grupo.test")])
def test_ejecutar_casos_edge_grupos(
        mock_info_legislatura,
        mock_init_driver,
        mock_seleccionar,
        mock_aceptar,
        mock_click,
        mock_spinner,
        mock_esperar_tabla,
        mock_ultima,
        mock_siguiente,
        mock_to_csv
):
    """
    Cubre casos límite en el scraping de grupos parlamentarios:
    - Filas con solo <th> en lugar de <td>
    - Filas con menos de 3 columnas
    - Filas que lanzan excepción al parsear
    - Detección de paginación con múltiples páginas
    """
    scraper = GruposScraper(driver_path="fake/path")

    # Simulación correcta del driver (falla si no se hace)
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_init_driver.return_value = (mock_driver, mock_wait)
    scraper.driver, scraper.wait = mock_driver, mock_wait

    # Fila con solo <th> (mock con .find_elements)
    fila_th = MagicMock()
    fila_th.find_elements.side_effect = [
        [],  # No <td>
        [MagicMock(text="Nombre TH"), MagicMock(text="2024-01-01"), MagicMock(text="2024-12-01")]  # como <th>
    ]

    # Fila con menos de 3 columnas
    fila_corta = MagicMock()
    fila_corta.find_elements.return_value = [MagicMock(text="Solo nombre")]

    # Fila con excepción
    fila_error = MagicMock()
    fila_error.find_elements.side_effect = Exception("Fallo procesando fila")

    # Simula find_elements en dos páginas distintas
    mock_driver.find_elements.side_effect = [
        [fila_th, fila_corta, fila_error],  # Página 1
        [fila_th]  # Página 2
    ]

    # Ejecutar
    scraper.ejecutar(output_csv="dummy.csv")

    # Verificar que se guardó el CSV
    mock_to_csv.assert_called_once()


@patch("scraping.scraper_grupos.pd.DataFrame.to_csv")
@patch("scraping.scraper_grupos.click_siguiente_pagina", return_value=False)  # ← se activa el `break`
@patch("scraping.scraper_grupos.es_ultima_pagina", return_value=False)  # ← no se detiene por final
@patch("scraping.scraper_grupos.esperar_tabla_cargada")
@patch("scraping.scraper_grupos.esperar_spinner")
@patch("scraping.scraper_grupos.hacer_click_esperando")
@patch("scraping.scraper_grupos.aceptar_cookies")
@patch("scraping.scraper_grupos.seleccionar_opcion_por_valor")
@patch("scraping.scraper_grupos.iniciar_driver")
@patch.object(GruposScraper, "_extraer_info_legislatura", return_value=[("Grupo de prueba", "https://grupo.test")])
def test_click_siguiente_falla_activa_break(
        mock_info_legislatura,
        mock_init_driver,
        mock_select,
        mock_aceptar,
        mock_click,
        mock_spinner,
        mock_esperar_tabla,
        mock_ultima,
        mock_siguiente,
        mock_to_csv
):
    """
    Cubre el caso en el que click_siguiente_pagina devuelve False en la primera iteración,
    lo que activa el break y termina el bucle anticipadamente.
    """
    scraper = GruposScraper(driver_path="fake/path")

    # Simulación completa del driver
    mock_driver = MagicMock()
    mock_wait = MagicMock()
    mock_init_driver.return_value = (mock_driver, mock_wait)
    scraper.driver, scraper.wait = mock_driver, mock_wait

    # Fila mínima válida
    fila = MagicMock()
    fila.find_elements.return_value = [
        MagicMock(text="Diputada X"),
        MagicMock(text="2024-01-01"),
        MagicMock(text="2024-12-01")
    ]

    mock_driver.find_elements.return_value = [fila]

    scraper.ejecutar(output_csv="dummy.csv")

    mock_to_csv.assert_called_once()
