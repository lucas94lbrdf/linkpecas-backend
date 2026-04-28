from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.vehicle import Manufacturer, VehicleModel, VehicleYear

router = APIRouter()


@router.get("/manufacturers")
def list_manufacturers(db: Session = Depends(get_db)):
    manufacturers = (
        db.query(Manufacturer)
        .filter(Manufacturer.is_active.is_(True))
        .order_by(Manufacturer.name.asc())
        .all()
    )
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "slug": item.slug,
            "logo_url": item.logo_url,
        }
        for item in manufacturers
    ]


@router.get("/models/{manufacturer_id}")
def list_models_by_manufacturer(manufacturer_id: str, db: Session = Depends(get_db)):
    models = (
        db.query(VehicleModel)
        .filter(
            VehicleModel.manufacturer_id == manufacturer_id,
            VehicleModel.is_active.is_(True),
        )
        .order_by(VehicleModel.name.asc())
        .all()
    )
    return [
        {
            "id": str(item.id),
            "manufacturer_id": str(item.manufacturer_id),
            "name": item.name,
            "slug": item.slug,
            "vehicle_type": item.vehicle_type,
            "generation": item.generation,
            "image_url": item.image_url,
        }
        for item in models
    ]


@router.get("/vehicles/search")
def search_vehicle_catalog(
    q: str = Query(..., min_length=1),
    manufacturer_slug: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    pattern = f"%{q.strip()}%"
    query = (
        db.query(VehicleModel, Manufacturer)
        .join(Manufacturer, Manufacturer.id == VehicleModel.manufacturer_id)
        .filter(
            Manufacturer.is_active.is_(True),
            VehicleModel.is_active.is_(True),
            or_(VehicleModel.name.ilike(pattern), VehicleModel.slug.ilike(pattern)),
        )
    )
    if manufacturer_slug:
        query = query.filter(Manufacturer.slug == manufacturer_slug)

    rows = query.order_by(Manufacturer.name.asc(), VehicleModel.name.asc()).limit(limit).all()

    model_ids = [row[0].id for row in rows]
    years_rows = (
        db.query(VehicleYear)
        .filter(VehicleYear.model_id.in_(model_ids), VehicleYear.is_active.is_(True))
        .all()
        if model_ids
        else []
    )
    years_by_model: dict[str, list[int]] = {}
    for item in years_rows:
        key = str(item.model_id)
        years_by_model.setdefault(key, []).append(item.year)

    return [
        {
            "manufacturer": {
                "id": str(manufacturer.id),
                "name": manufacturer.name,
                "slug": manufacturer.slug,
            },
            "model": {
                "id": str(model.id),
                "name": model.name,
                "slug": model.slug,
            },
            "years": sorted(years_by_model.get(str(model.id), [])),
            "seo_path": f"/{manufacturer.slug}/{model.slug}",
        }
        for model, manufacturer in rows
    ]
