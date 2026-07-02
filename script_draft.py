import os
import sys
import psycopg
from psycopg import rows

from dotenv import load_dotenv

load_dotenv()

sql_file_path = os.path.join(os.path.dirname(__file__), "SQL queries")
script_file_path = os.path.join(os.path.dirname(__file__))


class DatabaseConfig:
    def __init__(self):
        self.host = os.environ.get("PG_HOST", "localhost")
        self.port = os.environ.get("PG_PORT", "5422")
        self.dbname = os.environ.get("PG_DATABASE", "supermarket_sales")
        self.user = os.environ.get("PG_USER", "postgres")
        self.password = os.environ.get("PG_PASSWORD", "")

    def to_dict(self):
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


class DatabaseConnection:
    def __init__(self):
        self.config = DatabaseConfig()
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg.connect(
                **self.config.to_dict(), row_factory=rows.dict_row
            )
            return self.conn
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            sys.exit(1)

    def test_connection(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(
                    f"Connected to PostgreSQL database. Version: {version['version']}"
                )


class TablesManager:
    def __init__(self):
        self.connection = DatabaseConnection()

    def list_tables(self, schema="public"):
        with self.connection.connect() as conn:
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


class RunQueries:
    def __init__(self):
        self.connection = DatabaseConnection()

    def run_query(self, query, params=None, fetch=True):
        with self.connection.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    if fetch:
                        return cur.fetchall()
                    else:
                        conn.commit()
                        print(
                            f"Query executed successfully: {query}, {cur.rowcount} rows affected."
                        )
                        return None
            except Exception as e:
                conn.rollback()
                print(f"Error executing query: {e}")
                raise

    def run_sql_file(self, filepath, params=None, fetch=True):
        with open(filepath, "r", encoding="utf-8") as f:
            sql_content = f.read()
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        if not statements:
            print(f"No SQL statements found in file: {filepath}")
            return None
        with self.connection.connect() as conn:
            try:
                result = None
                with conn.cursor() as cur:
                    for i, stmt in enumerate(statements):
                        is_last = i == len(statements) - 1
                        cur.execute(stmt, params if len(statements) == 1 else None)
                        if is_last and fetch:
                            result = cur.fetchall()
                    conn.commit()
                print(f"Finished running {len(statements)} from file '{filepath}'. ")
                return result
            except Exception as e:
                conn.rollback()
                print(f"Error executing SQL file '{filepath}': {e}")
                raise


class Report:
    def __init__(self, script_path, sql_path):
        self.queries_runner = RunQueries()
        self.script_path = script_path
        self.sql_path = sql_path

    def run_setup(self, filename):
        print(f"\n=== Running setup file: {filename} ===")
        filepath = os.path.join(self.script_path, filename)
        self.queries_runner.run_sql_file(filepath, fetch=False)

    def run_report(self, filename):
        print(f"\n=== Running report: {filename} ===")
        filepath = os.path.join(self.sql_path, filename)
        rows = self.queries_runner.run_sql_file(filepath, fetch=True)
        if rows:
            for row in rows:
                print(row)
        else:
            print("No data returned from the report.")


class Script:
    def __init__(self):
        self.config = DatabaseConfig()
        self.connection = DatabaseConnection()
        self.tables = TablesManager()
        self.base_path = script_file_path
        self.sql_path = sql_file_path
        self.report = Report(self.base_path, self.sql_path)

    def setup_db(self):
        try:
            self.connection.test_connection()
            self.tables.list_tables()
        except Exception as e:
            print(f"Setup error: {e}")
            raise

    def run(self):
        try:
            self.setup_db()
            setup_file = "init.sql"
            self.report.run_setup(setup_file)
            for e in os.scandir(self.sql_path):
                self.report.run_report(e.name)
        except Exception as e:
            print(f"Script error: {e}")
            raise


if __name__ == "__main__":
    script = Script()
    script.run()
