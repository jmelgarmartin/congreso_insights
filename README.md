# Congreso Insights

**Congreso Insights** es una herramienta modular que permite automatizar la descarga, análisis y visualización de datos parlamentarios del Congreso de los Diputados de España.

---

## Estructura del proyecto

```text
congreso_insights/
├── scraping/
│ └── congreso_scraper.py
├── analysis/
│ └── graph_builder.py
├── tests/
│ └── test_congreso_scraper.py
│ └── test_graph_builder.py
├── diarios_html/
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
```
---
## Componentes

- `scraping/`: Código para descargar los diarios de sesiones desde la web del Congreso.
- `analysis/`: Funciones para conectar con Neo4j y analizar relaciones entre intervenciones, partidos y temas.
- `tests/`: Tests unitarios para garantizar el correcto funcionamiento del sistema.
- `diarios_html/`: Carpeta donde se guardan los HTML descargados.

## Uso

```bash
python main.py
```
## Requisitos
- `Python 3.8+`
- `ChromeDriver`
- `Neo4j`

## Instalación

```bash
pip install -r requirements.txt
```
