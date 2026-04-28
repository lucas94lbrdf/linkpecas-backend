import uuid
from app.db.session import SessionLocal
from app.models.community import Community
from app.models.ad import Ad

def run():
    db = SessionLocal()
    try:
        comms_data = [
            {
                'name': 'JDM Legends', 
                'slug': 'jdm', 
                'desc': 'Cultura japonesa, performance extrema e o ronco dos motores turbo.', 
                'avatar': 'https://images.unsplash.com/photo-1580273916550-e323be2ae537?q=80&w=500', 
                'banner': 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=2000'
            },
            {
                'name': 'Clássicos & Antigos', 
                'slug': 'antigos', 
                'desc': 'A elegância do passado preservada em cada detalhe restaurado.', 
                'avatar': 'https://images.unsplash.com/photo-1558981403-c5f91cbba527?q=80&w=500', 
                'banner': 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=2000'
            },
            {
                'name': 'Off-Road 4x4', 
                'slug': 'offroad', 
                'desc': 'Trilhas, lama e a liberdade de explorar onde o asfalto não chega.', 
                'avatar': 'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?q=80&w=500', 
                'banner': 'https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?q=80&w=2000'
            }
        ]
        
        created = []
        for c in comms_data:
            # Verifica se já existe pelo slug
            obj = db.query(Community).filter(Community.slug == c['slug']).first()
            if not obj:
                obj = Community(
                    id=uuid.uuid4(), 
                    name=c['name'], 
                    slug=c['slug'], 
                    description=c['desc'], 
                    avatar_url=c['avatar'], 
                    banner_url=c['banner'],
                    image_url=c['avatar'] # Usa o avatar como capa do card também
                )
                db.add(obj)
                print(f"Comunidade {c['name']} criada.")
            else:
                # Atualiza as fotos se já existir
                obj.avatar_url = c['avatar']
                obj.banner_url = c['banner']
                print(f"Comunidade {c['name']} atualizada.")
            created.append(obj)
        
        db.commit()
        
        # Vincular Ads
        ads = db.query(Ad).limit(12).all()
        for i, ad in enumerate(ads):
            target = created[i % len(created)]
            if ad not in target.ads:
                target.ads.append(ad)
        
        db.commit()
        print("\nSeed de fotos e comunidades concluído com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
