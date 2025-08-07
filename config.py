# config.py

import os
from dotenv import load_dotenv

# Carga el archivo .env
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")  # por defecto 'neo4j'

# Validación mínima
if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE]):
    raise ValueError("Faltan variables de entorno necesarias para conectar con Neo4j.")