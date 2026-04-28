import uuid
from app.db.session import SessionLocal
from app.models.user import User
from app.models.community import Community
from app.models.ad import Ad
from app.routes.api.auth import hash_password

def run():
    db = SessionLocal()
    try:
        # 1. Corrigir Senhas (Reset para admin123)
        admin = db.query(User).filter(User.role == "admin").first()
        if admin:
            admin.password_hash = hash_password("admin123")
            print(f"Senha do admin ({admin.email}) resetada para: admin123")
        
        # 2. Criar Comunidades
        communities_data = [
            {"name": "JDM Legends", "slug": "jdm", "description": "O melhor da cultura japonesa: turbos, drift e performance."},
            {"name": "Clássicos & Antigos", "slug": "antigos", "description": "Relíquias restauradas e carros que marcar obsoletos."},
            {"name": "Off-Road 4x4", "slug": "offroad", "description": "Para quem gosta de lama, trilha e aventura extrema."},
        ]

        created_communities = []
        for data in communities_data:
            comm = db.query(Community).filter(Community.slug == data["slug"]).first()
            if not comm:
                comm = Community(
                    id=uuid.uuid4(),
                    name=data["name"],
                    slug=data["slug"],
                    description=data["description"]
                )
                db.add(comm)
                print(f"Comunidade criada: {data['name']}")
            created_communities.append(comm)
        
        db.commit()

        # 3. Vincular Anúncios Aleatórios
        ads = db.query(Ad).limit(10).all()
        if ads and created_communities:
            for i, ad in enumerate(ads):
                # Distribui entre as comunidades
                target_comm = created_communities[i % len(created_communities)]
                if ad not in target_comm.ads:
                    target_comm.ads.append(ad)
            db.commit()
            print(f"Vínculos criados: {len(ads)} anúncios distribuídos.")

        print("\nSucesso! Agora você pode logar com seu admin e a senha 'admin123'.")

    except Exception as e:
        db.rollback()
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
