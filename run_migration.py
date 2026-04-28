import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://lrodrigues:Seleida50@localhost:5432/auto-marketplace"
engine = create_engine(DATABASE_URL)

def update_schema():
    with engine.connect() as conn:
        print("Adicionando colunas de tracking avançado em 'click_events'...")
        try:
            conn.execute(text("ALTER TABLE click_events ADD COLUMN source_type VARCHAR(50)"))
            print("Coluna 'source_type' adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar 'source_type': {e}")
            
        try:
            conn.execute(text("ALTER TABLE click_events ADD COLUMN source_ref VARCHAR(255)"))
            print("Coluna 'source_ref' adicionada.")
        except Exception as e:
            print(f"Erro ao adicionar 'source_ref': {e}")

        print("Criando tabela 'search_logs'...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id UUID PRIMARY KEY,
                    term VARCHAR(255),
                    vehicle_context VARCHAR(255),
                    origin VARCHAR(50) NOT NULL DEFAULT 'site',
                    results_found INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Tabela 'search_logs' garantida.")
        except Exception as e:
            print(f"Erro ao criar tabela 'search_logs': {e}")
        
        conn.commit()
        print("Migração concluída com sucesso!")

if __name__ == "__main__":
    update_schema()
