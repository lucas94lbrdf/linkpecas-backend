from app.db.session import engine
from app.models.community import Community, ad_communities

def run():
    print("Recriando tabelas de comunidades com CASCADE...")
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Drop das tabelas com CASCADE via SQL puro para garantir remoção de dependências
            conn.execute(text("DROP TABLE IF EXISTS ad_communities CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS communities CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS dispatch_logs CASCADE"))
            conn.commit()
        
        # Criação
        Community.__table__.create(bind=engine)
        ad_communities.create(bind=engine)
        print("Sucesso! Tabelas recriadas do zero.")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    run()
