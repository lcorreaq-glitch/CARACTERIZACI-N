from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from database import db, ensure_indexes  # noqa: E402
from routers.auth_router import router as auth_router  # noqa: E402
from routers.admin_router import router as admin_router  # noqa: E402
from routers.upload_router import router as upload_router  # noqa: E402
from routers.dashboards_router import router as dashboards_router  # noqa: E402
from routers.docente_router import router as docente_router  # noqa: E402
from routers.caracterizacion_router import router as caracterizacion_router  # noqa: E402
from routers.divipola_admin_router import router as divipola_admin_router  # noqa: E402
from routers.exports_router import router as exports_router  # noqa: E402
from routers.ai_router import router as ai_router  # noqa: E402
from seed import seed_superadmin, seed_students  # noqa: E402
from divipola import list_all  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="IU Digital Analytics", version="1.0.0")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "IU Digital Analytics", "status": "ok"}


@api_router.get("/divipola")
async def get_divipola():
    return {"municipios": list_all()}


app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(upload_router)
app.include_router(dashboards_router)
app.include_router(docente_router)
app.include_router(caracterizacion_router)
app.include_router(divipola_admin_router)
app.include_router(exports_router)
app.include_router(ai_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    await seed_superadmin()
    # Backfill download_enabled on existing users (idempotent)
    from database import db as _db
    await _db.users.update_many(
        {"role": {"$in": ["superadmin", "admin"]}, "download_enabled": {"$exists": False}},
        {"$set": {"download_enabled": True}},
    )
    await _db.users.update_many(
        {"role": {"$in": ["docente", "viewer"]}, "download_enabled": {"$exists": False}},
        {"$set": {"download_enabled": False}},
    )
    if os.environ.get("SEED_DEMO_DATA", "false").lower() == "true":
        # Run seed in background to avoid blocking startup
        asyncio.create_task(seed_students())
    logger.info("Startup completo.")
