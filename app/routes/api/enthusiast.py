from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.ad import Ad
from app.models.favorite import Favorite
from app.models.rating import AdRating
from app.routes.api.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/enthusiast", tags=["Enthusiast"])

class RatingSchema(BaseModel):
    score: int
    comment: str = None

@router.post("/favorite/{ad_id}")
def toggle_favorite(ad_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")
    
    fav = db.query(Favorite).filter(Favorite.user_id == current_user.id, Favorite.ad_id == ad_id).first()
    if fav:
        db.delete(fav)
        db.commit()
        return {"message": "unfavorited"}
    else:
        new_fav = Favorite(user_id=current_user.id, ad_id=ad_id)
        db.add(new_fav)
        db.commit()
        return {"message": "favorited"}

@router.get("/favorites")
def get_favorites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    favs = db.query(Ad).join(Favorite).filter(Favorite.user_id == current_user.id).all()
    return favs

@router.post("/rate/{ad_id}")
def rate_ad(ad_id: str, data: RatingSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.score < 1 or data.score > 5:
        raise HTTPException(400, "A nota deve ser entre 1 e 5")
        
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(404, "Anúncio não encontrado")
        
    rating = db.query(AdRating).filter(AdRating.user_id == current_user.id, AdRating.ad_id == ad_id).first()
    if rating:
        rating.score = data.score
        rating.comment = data.comment
    else:
        rating = AdRating(user_id=current_user.id, ad_id=ad_id, score=data.score, comment=data.comment)
        db.add(rating)
        
    db.commit()
    return {"message": "Avaliação salva com sucesso"}

@router.get("/ratings")
def get_my_ratings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ratings = db.query(AdRating).filter(AdRating.user_id == current_user.id).all()
    # Adicionando título do anúncio para o dashboard
    results = []
    for r in ratings:
        ad = db.query(Ad).filter(Ad.id == r.ad_id).first()
        results.append({
            "id": str(r.id),
            "ad_id": str(r.ad_id),
            "ad_title": ad.title if ad else "Anúncio Excluído",
            "score": r.score,
            "comment": r.comment,
            "created_at": r.created_at
        })
    return results
