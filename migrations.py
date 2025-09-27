import sqlite3
import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime

def migrate_sqlite_to_postgresql():
    """Migre les données de SQLite vers PostgreSQL"""
    
    # Configuration
    sqlite_path = 'instance/database.db'
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL non trouvée")
        return
    
    # Connexion SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connexion PostgreSQL
    parsed_url = urlparse(database_url)
    pg_conn = psycopg2.connect(
        database=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port
    )
    pg_cursor = pg_conn.cursor()
    
    try:
        # Migrer chaque table
        tables = ['users', 'phrases', 'photos', 'letters', 'memories', 'activities']
        
        for table in tables:
            print(f"🔄 Migration de la table {table}...")
            
            # Récupérer les données SQLite
            sqlite_cursor = sqlite_conn.execute(f'SELECT * FROM {table}')
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"ℹ️  Table {table} vide, ignorée")
                continue
            
            # Préparer l'insertion PostgreSQL
            columns = list(rows[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            # Vider la table PostgreSQL
            pg_cursor.execute(f'DELETE FROM {table}')
            
            # Insérer les données
            for row in rows:
                values = [row[col] for col in columns]
                pg_cursor.execute(f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})', values)
            
            print(f"✅ {len(rows)} lignes migrées pour {table}")
        
        pg_conn.commit()
        print("🎉 Migration terminée avec succès !")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        pg_conn.rollback()
    
    finally:
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

if __name__ == '__main__':
    migrate_sqlite_to_postgresql()