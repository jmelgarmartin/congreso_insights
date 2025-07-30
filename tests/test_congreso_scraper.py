import os
import pytest
from unittest.mock import MagicMock, patch
from scraping.congreso_scraper import CongresoScraper

# Crea un directorio temporal para la salida de pruebas
@pytest.fixture
def test_output_dir():
    path = os.path.join("tests", "test_output")
    os.makedirs(path, exist_ok=True)
    return path

# Instancia del scraper con configuración dummy para pruebas
@pytest.fixture
def scraper(test_output_dir):
    return CongresoScraper(driver_path="dummy_path", output_dir=test_output_dir, legislatura="15")

# Verifica que el directorio de salida se cree correctamente
def test_init_crea_directorio(test_output_dir):
    assert os.path.exists(test_output_dir)

# Verifica que se apliquen correctamente los filtros del formulario
@patch("scraping.congreso_scraper.Select")
@patch("scraping.congreso_scraper.hacer_click_esperando")
@patch("scraping.congreso_scraper.seleccionar_opcion_por_valor")
def test_apply_filters(mock_seleccionar, mock_click, mock_select, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    select_mock = MagicMock()
    scraper.driver.find_element.return_value = select_mock
    scraper.wait.until.return_value = True
    scraper._apply_filters()
    mock_select.assert_called_once_with(select_mock)
    assert mock_click.called

# Verifica que _apply_filters lanza una excepción si falla algún paso
@patch("scraping.congreso_scraper.hacer_click_esperando")
def test_apply_filters_error(mock_click, scraper):
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.wait.until.side_effect = Exception("fallo simulado")
    with pytest.raises(Exception):
        scraper._apply_filters()

# Verifica que se extraen correctamente los valores de rango desde el texto
@patch("scraping.congreso_scraper.re")
def test_get_rango_resultados(mock_re, scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.return_value.text = "Resultados 1 a 10 de 100"
    mock_match = MagicMock()
    mock_match.group.side_effect = [10, 100]
    mock_re.search.return_value = mock_match
    hasta, total = scraper._get_rango_resultados()
    assert hasta == 10
    assert total == 100

# Devuelve None si el texto no contiene el patrón esperado
def test_get_rango_resultados_none(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.return_value.text = "Texto no esperable"
    hasta, total = scraper._get_rango_resultados()
    assert hasta is None
    assert total is None

# Devuelve None si ocurre una excepción al buscar el rango
def test_get_rango_resultados_exception(scraper):
    scraper.driver = MagicMock()
    scraper.driver.find_element.side_effect = Exception("fallo simulando find_element")
    hasta, total = scraper._get_rango_resultados()
    assert hasta is None
    assert total is None

# Verifica que se descarga y guarda correctamente un pleno si no existe aún
@patch("scraping.congreso_scraper.BeautifulSoup")
def test_procesar_fila_descarga(mock_soup, scraper, test_output_dir):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-PL-123")]
    fila.find_element.return_value.get_attribute.return_value = "http://example.com/file"
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.output_dir = test_output_dir
    contenido = MagicMock()
    mock_section = MagicMock()
    mock_section.__str__.return_value = "<html>contenido</html>"
    contenido.find.return_value = mock_section
    mock_soup.return_value = contenido
    with patch("scraping.congreso_scraper.os.path.exists", return_value=False):
        with patch("scraping.congreso_scraper.open", create=True) as mock_open:
            result = scraper._procesar_fila(fila)
            assert result is True
            assert mock_open.called

# Verifica que no se descarga si el identificador no es de pleno
@patch("scraping.congreso_scraper.BeautifulSoup")
def test_procesar_fila_sin_pl(mock_soup, scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-SR-999")]
    result = scraper._procesar_fila(fila)
    assert result is False

# Verifica que el archivo se procesa aunque no se encuentre contenido HTML
@patch("scraping.congreso_scraper.BeautifulSoup")
def test_procesar_fila_sin_contenido(mock_soup, scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-PL-123")]
    fila.find_element.return_value.get_attribute.return_value = "http://example.com/file"
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.output_dir = "tests/test_output"
    mock_soup.return_value.find.return_value = None
    with patch("scraping.congreso_scraper.os.path.exists", return_value=False):
        result = scraper._procesar_fila(fila)
        assert result is True

# Verifica que no se vuelve a descargar un archivo ya existente
def test_procesar_fila_ya_existe(scraper):
    fila = MagicMock()
    fila.find_elements.return_value = [MagicMock(text="DSCD-15-PL-999")]
    fila.find_element.return_value.get_attribute.return_value = "http://example.com/file"
    scraper.driver = MagicMock()
    scraper.wait = MagicMock()
    scraper.output_dir = "tests/test_output"
    with patch("scraping.congreso_scraper.os.path.exists", return_value=True):
        result = scraper._procesar_fila(fila)
        assert result is False

# Simula el proceso completo de descarga de plenos con paginación
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", side_effect=[(10, 20), (20, 20)])
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos(mock_init_driver, mock_get_rango, mock_proc_fila, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock(), MagicMock()]
    mock_init_driver.return_value = (mock_driver, MagicMock())
    scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
    scraper.descargar_plenos()
    assert mock_aplicar.called
    assert mock_proc_fila.call_count == 4
    assert mock_get_rango.call_count == 2

# Verifica que el proceso se detiene si _get_rango_resultados devuelve None
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", return_value=(None, None))
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_sin_rango(mock_init_driver, mock_get_rango, mock_proc_fila, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_init_driver.return_value = (mock_driver, MagicMock())
    scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
    scraper.descargar_plenos()
    assert mock_proc_fila.call_count == 1

# Verifica que si no hay botón siguiente se procesa solo la primera página
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", side_effect=[(10, 20)])
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_sin_siguiente(mock_init_driver, mock_get_rango, mock_proc_fila, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_driver.find_element.side_effect = Exception("no hay botón siguiente")
    mock_init_driver.return_value = (mock_driver, MagicMock())
    scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
    scraper.descargar_plenos()
    assert mock_proc_fila.call_count == 1

# Verifica que si el botón siguiente falla al hacer click, no se rompe el flujo
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True)
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", side_effect=[(10, 20)])
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_falla_click_siguiente(mock_init_driver, mock_get_rango, mock_proc_fila, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    boton_mock = MagicMock()
    boton_mock.click.side_effect = Exception("fallo al hacer click")
    mock_driver.find_element.return_value = boton_mock
    mock_init_driver.return_value = (mock_driver, MagicMock())
    scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
    scraper.descargar_plenos()
    assert mock_proc_fila.call_count == 1

# Verifica que los errores internos en _procesar_fila se reintentan hasta 3 veces
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", side_effect=Exception("fallo interno"))
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", return_value=(10, 10))
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_error_en_procesar(mock_init_driver, mock_get_rango, mock_proc_fila, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = [MagicMock()]
    mock_init_driver.return_value = (mock_driver, MagicMock())
    scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
    scraper.descargar_plenos()
    assert mock_proc_fila.call_count == 3

# Verifica que si las filas disminuyen tras actualizar la página, se evitan errores de índice
@patch("scraping.congreso_scraper.CongresoScraper._apply_filters")
@patch("scraping.congreso_scraper.CongresoScraper._get_rango_resultados", return_value=(10, 10))
@patch("scraping.congreso_scraper.iniciar_driver")
def test_descargar_plenos_filas_disminuyen(mock_init_driver, mock_get_rango, mock_aplicar, test_output_dir):
    mock_driver = MagicMock()
    fila1 = MagicMock()
    fila2 = MagicMock()
    mock_driver.find_elements.return_value = [fila1, fila2]
    def side_effect_find_elements(*args, **kwargs):
        if test_descargar_plenos_filas_disminuyen.call_count == 0:
            test_descargar_plenos_filas_disminuyen.call_count += 1
            return [fila1, fila2]
        else:
            return [fila1]
    test_descargar_plenos_filas_disminuyen.call_count = 0
    mock_driver.find_elements.side_effect = side_effect_find_elements
    mock_driver.find_element.side_effect = Exception("no siguiente")
    mock_init_driver.return_value = (mock_driver, MagicMock())
    with patch("scraping.congreso_scraper.CongresoScraper._procesar_fila", return_value=True) as mock_proc_fila:
        scraper = CongresoScraper(driver_path="path", output_dir=test_output_dir, legislatura="15")
        scraper.descargar_plenos()
        assert mock_proc_fila.call_count == 1
