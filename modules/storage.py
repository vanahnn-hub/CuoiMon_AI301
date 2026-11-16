import os
import sqlite3
import pandas as pd

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/data_storage.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_storage.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            rows_count INTEGER,
            cols_count INTEGER,
            table_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            insight_title TEXT,
            insight_category TEXT,
            severity TEXT,
            description TEXT,
            recommended_action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES dataset_metadata(id)
        )
    """)
    conn.commit()
    conn.close()

def save_dataframe_to_db(df: pd.DataFrame, dataset_name: str, source_type: str) -> tuple[int, str]:
    init_db()
    conn = get_connection()
    import re
    # Create safe table name
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', dataset_name).lower()
    table_name = f"data_{safe_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Save df
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # Save metadata
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dataset_metadata (dataset_name, source_type, rows_count, cols_count, table_name)
        VALUES (?, ?, ?, ?, ?)
    """, (dataset_name, source_type, len(df), len(df.columns), table_name))
    dataset_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return dataset_id, table_name

def list_stored_datasets() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM dataset_metadata ORDER BY created_at DESC", conn)
    conn.close()
    return df

def query_database(sql_query: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return df
    except Exception as e:
        conn.close()
        raise e

