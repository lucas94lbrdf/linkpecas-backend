from sqlalchemy import text
from app.db.session import engine
from app.models.favorite import Favorite

def update_enthusiast_schema():
    print("Atualizando esquema para Entusiastas...")
    try:
        # 1. Criar tabela favorites
        Favorite.__table__.create(bind=engine, checkfirst=True)
        print("Tabela 'favorites' verificada/criada.")
        
        # 2. Adicionar coluna comment em ad_ratings
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ad_ratings ADD COLUMN IF NOT EXISTS comment VARCHAR(500)"))
            print("Coluna 'comment' verificada/adicionada à tabela ad_ratings.")
            
        print("Sucesso!")
    except Exception as e:
        print(f"Erro ao atualizar esquema: {e}")

if __name__ == "__main__":
    update_enthusiast_schema()
