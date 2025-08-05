# Congreso Insights

**Congreso Insights** es una herramienta modular y automatizada para el scraping, análisis y visualización de datos parlamentarios del Congreso de los Diputados de España. El objetivo es obtener insights políticos a través de procesamiento de datos y grafos.

---

## 📁 Estructura del Proyecto

```text
congreso_insights/
│
├── main.py                         # Script principal de ejecución por argumentos (plenos, diputados, grupos...)
├── README.md                       # Documentación del proyecto
├── requirements.txt                # Dependencias para ejecución
├── requirements-dev.txt            # Dependencias adicionales para desarrollo y test
├── .gitignore                      # Archivos y carpetas ignoradas por Git
│
├── diarios_html/                   # HTMLs descargados de diarios de sesiones
├── fake/                           # Archivos de ejemplo o mocks
├── htmlcov/                        # Reporte de cobertura generado por pytest-cov
│
├── scraping/                       # Módulo de scraping
│   ├── __init__.py
│   ├── congreso_scraper.py         # Scraper para diarios de sesiones del Congreso
│   ├── scraper_diputados.py        # Scraper de diputados (nombre, grupo, provincia)
│   ├── scraper_grupos.py           # Scraper de composición por grupo parlamentario
│   ├── enriquecedor_suplencias.py  # Añade fechas y relaciones de suplencias a diputados
│   └── utils/
│       ├── __init__.py
│       └── selenium_utils.py       # Utilidades comunes para Selenium (esperas, clicks, paginación...)
│
├── analysis/                       # Módulo de análisis (en desarrollo)
│   ├── __init__.py
│   └── graph_builder.py            # Carga los datos y construye el grafo en Neo4j
│
├── tests/                          # Tests automatizados con pytest
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures compartidas
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── test_congreso_scraper.py
│   │   ├── test_scraper_diputados.py
│   │   ├── test_scraper_grupos.py
│   │   ├── test_enriquecedor_suplencias.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── test_selenium_utils.py
│   └── test_output/                # Salidas temporales generadas en tests
│
├── diputados.csv                   # Resultado final del scraping de diputados enriquecido con suplencias
├── grupos.csv                      # Altas y bajas por grupo parlamentario
├── ministros_xv.csv                # Lista manual de ministros de la XV legislatura
```
---
## 🚀 Ejecución
El script principal es main.py. Puedes ejecutarlo en diferentes modos según los datos que quieras descargar:
```text
python main.py --modo plenos         # Descarga diarios de sesiones
python main.py --modo diputados      # Descarga y enriquece diputados
python main.py --modo grupos         # Descarga composición de grupos
```
---
## 🧪 Testing y cobertura
El Proyecto ha sido testeado con Python 3.x

Para entorno de ejecución:
```text
pip install -r requirements.txt
```

Para desarrollo y tests:
```text
pip install -r requirements-dev.txt
```

Para ejecución de los test:
```text
pytest --cov=scraping tests/
```
---
## 💡 Estado del proyecto
✅ Scrapers funcionales y con cobertura de test al 100%.

🔄 En desarrollo módulo de análisis en grafos con Neo4j.

📈 Posible futura visualización web.
