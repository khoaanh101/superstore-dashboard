import os
import sys
import psycopg
from psycopg import rows

from dotenv import load_dotenv

load_dotenv()


DB_config = {
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": os.environ.get("PG_PORT", "5422"),
    "dbname": os.environ.get("PG_DATABASE", "supermarket_sales"),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "")
}

sql_file_path = os.path.join(os.path.dirname(__file__), "SQL queries")
script_file_path = os.path.join(os.path.dirname(__file__))

def get_connection():
    try:
        conn =  psycopg.connect(**DB_config, row_factory=rows.dict_row)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)
    


def test_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"Connected to PostgreSQL database. Version: {version['version']}")


def list_tables(schema="public"):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name;  
            """,
            (schema,),
            )
            tables = [row["table_name"] for row in cur.fetchall()]
            print(f"Tables in schema '{schema}': {tables}")
            for t in tables:
                print(f"Table: {t}")
            return tables


def run_query(query, params=None, fetch=True):
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                else:
                    conn.commit()
                    print(f"Query executed successfully: {query}, {cur.rowcount} rows affected.")
                    return None
        except Exception as e:
            conn.rollback()
            print(f"Error executing query: {e}")
            raise

def run_sql_file(filepath, params=None, fetch=False):
    with open(filepath, "r", encoding = "utf-8") as f:
        sql_content = f.read()
    statements = [s.strip() for s in sql_content.split(";") if s.strip()]
    if not statements:
        print(f"No SQL statements found in file: {filepath}")
        return None
    with get_connection() as conn:
        try:
            result = None
            with conn.cursor() as cur:
                for i, stmt in enumerate(statements):
                    is_last = i == len(statements) - 1
                    cur.execute(stmt, params if len(statements) ==  1 else None)
                    if is_last and fetch:
                        result = cur.fetchall()
                conn.commit()
            print(f"Finished running {len(statements)} from file '{filepath}'. ")
            return result
        except Exception as e:
            conn.rollback()
            print(f"Error executing SQL file '{filepath}': {e}")
            raise

def run_setup(filename):
    print(f"\n=== Running setup file: {filename} ===")
    run_sql_file(os.path.join(script_file_path, filename), fetch=False)

def run_report(filename):
    print(f"\n=== Running report: {filename} ===")
    rows = run_sql_file(os.path.join(sql_file_path, filename), fetch=True)
    if rows:
        for row in rows:
            print(row)
    else:
        print("No data returned from the report.")

if __name__ == "__main__":
    test_connection()
    tables = list_tables()

    run_setup("init.sql")
    for e in os.scandir(sql_file_path):
        with open(e.path, "r") as f:
            run_report(e.name)