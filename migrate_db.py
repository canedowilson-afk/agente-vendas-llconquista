import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "dados.sqlite"

def migrate():
    if not Path(DB_PATH).exists():
        print(f"Erro: Arquivo {DB_PATH} não encontrado.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Colunas que a tabela 'leads' deve ter segundo sessions.py
    required_columns = {
        "id": "TEXT PRIMARY KEY",
        "name": "TEXT",
        "phone": "TEXT UNIQUE",
        "source": "TEXT",
        "first_msg": "TEXT",
        "sent_checkout": "INTEGER DEFAULT 0",
        "created_at": "TEXT NOT NULL",
        "updated_at": "TEXT NOT NULL"
    }

    # Verificar colunas atuais
    cursor.execute("PRAGMA table_info(leads)")
    current_columns = {row[1] for row in cursor.fetchall()}
    
    print(f"Colunas atuais na tabela 'leads': {current_columns}")

    added = []
    for col, col_def in required_columns.items():
        if col not in current_columns:
            print(f"Adicionando coluna faltante: {col}...")
            try:
                # SQLite ALTER TABLE ADD COLUMN tem limitações (ex: NOT NULL sem default)
                # Se for NOT NULL, precisamos de um valor default temporário ou permitir NULL se possível.
                # Para simplificar a migração e garantir que rode:
                if "NOT NULL" in col_def:
                    # Adiciona com default vazio para satisfazer NOT NULL
                    alter_query = f"ALTER TABLE leads ADD COLUMN {col} {col_def.replace('NOT NULL', '')} DEFAULT ''"
                else:
                    alter_query = f"ALTER TABLE leads ADD COLUMN {col} {col_def}"
                
                cursor.execute(alter_query)
                added.append(col)
            except Exception as e:
                print(f"Erro ao adicionar coluna {col}: {e}")

    conn.commit()
    conn.close()

    if added:
        print(f"\nSucesso! Colunas adicionadas: {', '.join(added)}")
    else:
        print("\nNenhuma coluna nova precisou ser adicionada.")

if __name__ == "__main__":
    migrate()
