from app.main import app
from fastapi.routing import APIRoute

print("List of routes registered in FastAPI:")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"Path: {route.path}, Name: {route.name}, Tags: {route.tags}")
