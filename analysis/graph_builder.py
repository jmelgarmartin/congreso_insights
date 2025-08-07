# analysis/graph_builder.py

import pandas as pd
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, CypherSyntaxError

import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Clase principal para importar datos de diputados, grupos parlamentarios y suplencias
    al grafo de Neo4j a partir de archivos CSV.
    Ahora, la legislatura se recibe como argumento y no depende del CSV.
    """

    def __init__(self, uri: str, user: str, password: str, database: str):
        """
        Inicializa el driver de conexión con Neo4j.

        :param uri: URI de conexión, p. ej. 'bolt://localhost:7687'
        :param user: Usuario de acceso a Neo4j
        :param password: Contraseña del usuario
        :param database: Nombre de la base de datos
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.database = database
            logger.info("Conexión a Neo4j establecida correctamente.")
        except ServiceUnavailable as e:
            logger.error(f"No se pudo conectar a Neo4j: {e}")
            raise

    def close(self):
        """Cierra la conexión con el driver de Neo4j."""
        self.driver.close()

    def crear_indices(self):
        """
        Crea índices únicos en los nodos de tipo Diputado, Grupo, Provincia y Legislatura
        para evitar duplicados en las cargas.
        """
        constraints = [
            ("Diputado", "nombre", "diputado_nombre_unico"),
            ("Grupo", "nombre", "grupo_nombre_unico"),
            ("Provincia", "nombre", "provincia_nombre_unico"),
            ("Legislatura", "numero", "legislatura_numero_unico"),
        ]

        with self.driver.session(database=self.database) as session:
            for label, field, constraint in constraints:
                try:
                    session.run(f"""
                        CREATE CONSTRAINT {constraint}
                        IF NOT EXISTS
                        FOR (n:{label}) REQUIRE n.{field} IS UNIQUE
                    """)
                    logger.info(f"Constraint '{constraint}' verificado para {label}.{field}")
                except CypherSyntaxError as e:
                    logger.error(f"Error creando constraint para {label}: {e}")

    def importar_grupos(self, path_csv: str, legislatura: str):
        """
        Importa diputados y su relación con grupos parlamentarios desde un CSV.

        :param path_csv: Ruta al archivo CSV que contiene columnas:
                         nombre, grupo_parlamentario, fecha_alta, fecha_baja
        :param legislatura: Número de legislatura a asociar (ej. '15')
        """
        logger.info(f"Path csv: {path_csv}")
        df = pd.read_csv(path_csv)
        required_columns = {"nombre", "grupo_parlamentario", "fecha_alta", "fecha_baja", "legislatura"}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Faltan columnas requeridas en el CSV: {required_columns}")

        df = df.fillna("")

        with self.driver.session(database=self.database) as session:
            for _, row in df.iterrows():
                try:
                    session.run("""
                        MERGE (l:Legislatura {numero: $legislatura})
                        MERGE (g:Grupo {nombre: $grupo})
                        MERGE (g)-[:EXISTE_EN]->(l)
                        MERGE (d:Diputado {nombre: $nombre})
                        MERGE (d)-[r:PERTENECE_A]->(g)
                        SET r.fecha_alta = date($fecha_alta),
                            r.fecha_baja = CASE WHEN $fecha_baja <> "" THEN date($fecha_baja) ELSE NULL END
                        MERGE (d)-[:PARTICIPA_EN]->(l)
                    """, nombre=row["nombre"],
                                grupo=row["grupo_parlamentario"],
                                fecha_alta=self.formatear_fecha(row["fecha_alta"]),
                                fecha_baja=self.formatear_fecha(row["fecha_baja"]),
                                legislatura=legislatura)
                except Exception as e:
                    logger.warning(f"Error procesando fila {row.to_dict()}: {e}")

    def importar_diputados(self, path_csv: str, legislatura: str):
        """
        Importa relaciones de representación y suplencias entre diputados desde un CSV.

        :param path_csv: Ruta al archivo CSV que contiene columnas como:
                         nombre, provincia, sustituye_a, fecha_alta_suplencia, fecha_baja_suplencia
        :param legislatura: Número de legislatura a asociar (ej. '15')
        """
        df = pd.read_csv(path_csv)
        required_columns = {
            "nombre",
            "provincia",
            "sustituye_a",
            "fecha_alta_suplencia",
            "fecha_baja_suplencia",
            "legislatura"
        }
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Faltan columnas requeridas en el CSV: {required_columns}")

        df = df.fillna("")

        with self.driver.session(database=self.database) as session:
            for _, row in df.iterrows():
                nombre = row.get("nombre")
                provincia = self.normalizar_provincia(row.get("provincia", ""))

                # Crear relación REPRESENTA_A y con Legislatura
                if nombre and provincia and legislatura:
                    try:
                        session.run("""
                            MERGE (d:Diputado {nombre: $nombre})
                            MERGE (p:Provincia {nombre: $provincia})
                            MERGE (l:Legislatura {numero: $legislatura})
                            MERGE (d)-[:REPRESENTA_A]->(p)
                            MERGE (d)-[:PARTICIPA_EN]->(l)
                        """, nombre=nombre, provincia=provincia, legislatura=legislatura)
                    except Exception as e:
                        logger.warning(f"Error creando relación REPRESENTA_A: {e}")

                # Crear relación de suplencia (si hay datos)
                sustituido = row.get("sustituye_a", "")
                if nombre and sustituido:
                    try:
                        session.run("""
                            MERGE (d1:Diputado {nombre: $sustituto})
                            MERGE (d2:Diputado {nombre: $sustituido})
                            MERGE (d1)-[r:SUSTITUYE_A]->(d2)
                            SET r.fecha_alta = date($fecha_alta),
                                r.fecha_baja = CASE WHEN $fecha_baja <> "" THEN date($fecha_baja) ELSE NULL END
                        """, sustituto=nombre,
                                    sustituido=sustituido,
                                    fecha_alta=self.formatear_fecha(row.get("fecha_alta_suplencia", "")),
                                    fecha_baja=self.formatear_fecha(row.get("fecha_baja_suplencia", "")))
                    except Exception as e:
                        logger.warning(f"Error creando suplencia: {e}")

    @staticmethod
    def formatear_fecha(fecha: str) -> str:
        """
        Convierte una fecha en formato DD/MM/YYYY a YYYY-MM-DD para Neo4j.

        :param fecha: Fecha como string
        :return: Fecha en formato compatible con Cypher
        """
        if not fecha or pd.isna(fecha):
            return ""
        try:
            return datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Fecha inválida: {fecha}")
            return ""

    @staticmethod
    def normalizar_provincia(texto: str) -> str:
        """
        Elimina el prefijo 'Diputado por' o 'Diputada por' para extraer el nombre de la provincia.

        :param texto: Texto que contiene la provincia
        :return: Nombre limpio de la provincia
        """
        if isinstance(texto, str):
            return texto.replace("Diputado por ", "").replace("Diputada por ", "").strip()
        return texto
