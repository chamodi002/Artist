from fastapi import APIRouter
from app.controller.public_controller import public_router
from app.controller.admin_controller import admin_router

all_routers = APIRouter()
all_routers.include_router(public_router)
all_routers.include_router(admin_router)