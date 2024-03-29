from fastapi import Depends, FastAPI, HTTPException, Request

from url_shortener.database import SessionLocal, engine


def raise_bad_request(message):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
