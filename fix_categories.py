from app.db.session import SessionLocal
from sqlalchemy import text

def fix_categories_table():
    db = SessionLocal()
    try:
        print("Corrigindo tabela 'categories'...")
        
        # Adiciona colunas que podem estar faltando
        columns = [
            ("description", "VARCHAR(500)"),
            ("icon", "VARCHAR(50)"),
            ("is_active", "BOOLEAN DEFAULT TRUE")
        ]
        
        for col_name, col_type in columns:
            print(f"Verificando coluna '{col_name}'...")
            db.execute(text(f"ALTER TABLE categories ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
        
        db.commit()
        print("Tabela 'categories' atualizada com sucesso! ✅")
    except Exception as e:
        print(f"Erro ao atualizar categorias: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_categories_table()
