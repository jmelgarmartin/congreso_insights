# tests/test_congreso_scraper.py

import pytest
from unittest.mock import MagicMock, patch
from scraping.congreso_scraper import CongresoScraper

@pytest.fixture
def scraper():
    return CongresoScraper("/fake/path/chromedriver", "test_output")

@patch("scraping.congreso_scraper.os.makedirs")
def test_constructor_crea_directorio(mock_makedirs):
    CongresoScraper("/fake/path/chromedriver", "test_output")
    mock_makedirs.assert_called_once_with("test_output", exist_ok=True)

def test_get_rango_resultados_correcto(scraper):
    scraper.driver = MagicMock()
    mock_element = MagicMock()
    mock_element.text = "Resultados 1 a 25 de 100"
    scraper.driver.find_element.return_value = mock_element
    hasta, total = scraper._get_rango_resultados()
    assert hasta == 25
    assert total == 100

def test_get_rango_resultados_sin_texto(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.side_effect = Exception("Elemento no encontrado")
    hasta, total = scraper._get_rango_resultados()
    assert hasta is None
    assert total is None

@patch("scraping.congreso_scraper.CongresoScraper._init_driver")
@patch("scraping.congreso_scraper.CongresoScraper._accept_cookies")
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", return_value=(1, 1))
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.webdriver.Chrome")
def test_descargar_plenos_flow(mock_driver, mock_proc_fila, mock_rango, mock_apf, mock_cookies, mock_init, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    fila_mock = MagicMock()
    scraper.driver.find_elements.return_value = [fila_mock]
    scraper.descargar_plenos()
    mock_proc_fila.assert_called()

@patch("scraping.congreso_scraper.os.path.exists", return_value=False)
@patch("scraping.congreso_scraper.open", create=True)
def test_procesar_fila_valida_y_guarda(mock_open, mock_exists, scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-PL-123")]
    link = MagicMock()
    link.get_attribute.return_value = "http://fake.url"
    fila.find_element.return_value = link

    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.driver.page_source = '<html><section id="portlet_publicaciones">contenido</section></html>'
    scraper.driver.window_handles = ["main", "new"]
    scraper.driver.execute_script = MagicMock()
    scraper.driver.switch_to = MagicMock()
    scraper.driver.switch_to.window = MagicMock()
    scraper.driver.close = MagicMock()

    resultado = scraper._procesar_fila(fila)
    assert resultado is True
    mock_open.assert_called()
