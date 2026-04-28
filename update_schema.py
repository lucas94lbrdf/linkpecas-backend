from sqlalchemy import text
from app.db.session import engine
from app.models.marketplace import Marketplace

def run():
    print("Atualizando esquema do banco de dados...")
    try:
        with engine.connect() as conn:
            # 1. Adicionar colunas ao model Ad
            # Usamos IF NOT EXISTS para evitar erros se rodar mais de uma vez
            conn.execute(text("ALTER TABLE ads ADD COLUMN IF NOT EXISTS condition VARCHAR(20) DEFAULT 'new'"))
            conn.execute(text("ALTER TABLE ads ADD COLUMN IF NOT EXISTS warranty VARCHAR(100)"))
            conn.commit()
            print("Colunas 'condition' e 'warranty' adicionadas à tabela ads.")

        # 2. Criar tabela marketplaces
        Marketplace.__table__.create(bind=engine, checkfirst=True)
        print("Tabela 'marketplaces' verificada/criada.")

        print("\nSucesso! Esquema atualizado.")
    except Exception as e:
        print(f"Erro ao atualizar esquema: {e}")

if __name__ == "__main__":
    run()
