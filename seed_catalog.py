
from pathlib import Path
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.db.session import DATABASE_URL

load_dotenv(Path(__file__).resolve().parent / ".env")

MANUFACTURERS = [
    {"name": "Toyota", "slug": "toyota", "logo_url": "https://www.carlogos.org/car-logos/toyota-logo.png"},
    {"name": "Volkswagen", "slug": "volkswagen", "logo_url": "https://www.carlogos.org/car-logos/volkswagen-logo.png"},
    {"name": "Ford", "slug": "ford", "logo_url": "https://www.carlogos.org/car-logos/ford-logo.png"},
    {"name": "Fiat", "slug": "fiat", "logo_url": "https://www.carlogos.org/car-logos/fiat-logo.png"},
    {"name": "Chevrolet", "slug": "chevrolet", "logo_url": "https://www.carlogos.org/car-logos/chevrolet-logo.png"},
    {"name": "Honda", "slug": "honda", "logo_url": "https://www.carlogos.org/car-logos/honda-logo.png"},
    {"name": "Hyundai", "slug": "hyundai", "logo_url": "https://www.carlogos.org/car-logos/hyundai-logo.png"},
]

MODELS = {
    "toyota": ["Corolla", "Hilux", "Yaris", "Etios", "SW4"],
    "volkswagen": ["Gol", "Polo", "Golf", "T-Cross", "Nivus", "Amarok"],
    "ford": ["Ka", "Fiesta", "Focus", "Ranger", "EcoSport"],
    "fiat": ["Uno", "Palio", "Argo", "Cronos", "Toro", "Strada"],
    "chevrolet": ["Onix", "Prisma", "Cruze", "S10", "Tracker"],
    "honda": ["Civic", "Fit", "City", "HR-V"],
    "hyundai": ["HB20", "Creta", "i30", "Tucson"],
}

def seed():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        print("Limpando dados antigos do catálogo...")
        conn.execute(text("DELETE FROM vehicle_years"))
        conn.execute(text("DELETE FROM vehicle_models"))
        conn.execute(text("DELETE FROM manufacturers"))
        
        print("Inserindo montadoras e modelos...")
        for m_data in MANUFACTURERS:
            m_id = uuid.uuid4()
            conn.execute(
                text("INSERT INTO manufacturers (id, name, slug, logo_url, is_active) VALUES (:id, :name, :slug, :logo_url, true)"),
                {"id": m_id, "name": m_data["name"], "slug": m_data["slug"], "logo_url": m_data["logo_url"]}
            )
            
            models = MODELS.get(m_data["slug"], [])
            for model_name in models:
                model_id = uuid.uuid4()
                model_slug = model_name.lower().replace(" ", "-")
                conn.execute(
                    text("INSERT INTO vehicle_models (id, manufacturer_id, name, slug, is_active) VALUES (:id, :m_id, :name, :slug, true)"),
                    {"id": model_id, "m_id": m_id, "name": model_name, "slug": model_slug}
                )
                
                # Adicionar alguns anos para teste
                for year in range(2015, 2025):
                    conn.execute(
                        text("INSERT INTO vehicle_years (id, model_id, year, is_active) VALUES (:id, :model_id, :year, true)"),
                        {"id": uuid.uuid4(), "model_id": model_id, "year": year}
                    )
        
    print("Seed finalizado com sucesso!")

if __name__ == "__main__":
    seed()
