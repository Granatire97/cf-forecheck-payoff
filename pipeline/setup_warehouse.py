import duckdb
from pathlib import Path
from pipeline.config import DB_PATH

def create_warehouse(db_path: Path = DB_PATH) -> None:
    """
    Open or Create the warehouse and ensure the schema exist
    """
    con = duckdb.connect(db_path)
    try:
        # schemas are namespaces - folders in the database 
        con.execute('CREATE SCHEMA IF NOT EXISTS staging;')
        con.execute('CREATE SCHEMA IF NOT EXISTS clean;')
        con.execute('CREATE SCHEMA IF NOT EXISTS warehouse;')

        # show what schemas now exist, to confirm it work
        schemas = con.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name IN ('staging', 'clean', 'warehouse')
            ORDER BY schema_name
        
        """).fetchall()
        print(f"Warehouse ready at: {db_path}")
        print('Schemas present: ', [s[0] for s in schemas])

    finally:
        con.close()

if __name__ == '__main__':
    create_warehouse()