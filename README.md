# Congreso Insights

**Congreso Insights** es una herramienta modular que permite automatizar la descarga, análisis y visualización de datos parlamentarios del Congreso de los Diputados de España.

---

## Estructura del proyecto

```text
congreso_insights/
│
├── main.py                         # Script principal de ejecución
├── README.md                       # Documentación del proyecto
├── requirements.txt                # Dependencias necesarias
├── .gitignore                      # Archivos excluidos del control de versiones
├── diputados.csv                   # Salida generada con datos de diputados
├── diarios_html/                   # HTMLs descargados de los diarios del Congreso
│
├── analysis/                       # Módulo de análisis de discursos
│   ├── __init__.py
│   └── graph_builder.py           # Carga del grafo en Neo4j 
│
├── scraping/                       # Módulo de scraping web
│   ├── __init__.py
│   ├── congreso_scraper.py        # Scraper de diarios de sesiones
│   ├── scraper_diputados.py       # Scraper del listado de diputados
│   ├── enriquecedor_suplencias.py # Enriquecimiento de suplencias parlamentarias
│   └── utils/                     # Utilidades compartidas
│       ├── __init__.py
│       └── selenium_utils.py      # Inicialización y helpers para Selenium
│
├── test/                           # Tests unitarios del proyecto
│   ├── __init__.py
│   ├── test_congreso_scraper.py   # Tests del scraper de plenos
│   ├── test_graph_builder.py      # Tests de construcción de grafos
│   └── test_output/               # Carpeta de salida para pruebas (ignorada en Git)

```
---
## Componentes

- `scraping/`: Código para descargar los datos necesarios desde la web del Congreso.
- `analysis/`: Funciones para conectar con Neo4j y analizar relaciones entre intervenciones, partidos y temas.
- `tests/`: Tests unitarios para garantizar el correcto funcionamiento del sistema.
- `diarios_html/`: Carpeta donde se guardan los HTML descargados.

## Uso

```bash
python main.py (opción)
```
## Requisitos
- `Python 3.8+`
- `ChromeDriver`
- `Neo4j`

## Instalación

```bash
pip install -r requirements.txt
```
