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
from routers.config_router import router as config_router  # noqa: E402
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
app.include_router(config_router)

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
    # ------ Role migration (docente→profesor, admin/viewer→direccion) ------
    from database import db as _db
    await _db.users.update_many({"role": "docente"}, {"$set": {"role": "profesor"}})
    await _db.users.update_many({"role": "admin"}, {"$set": {"role": "direccion"}})
    await _db.users.update_many({"role": "viewer"}, {"$set": {"role": "direccion"}})
    # Backfill download_enabled on existing users (idempotent)
    await _db.users.update_many(
        {"role": {"$in": ["superadmin", "direccion"]}, "download_enabled": {"$exists": False}},
        {"$set": {"download_enabled": True}},
    )
    await _db.users.update_many(
        {"role": {"$in": ["profesor", "decano", "coordinador"]}, "download_enabled": {"$exists": False}},
        {"$set": {"download_enabled": False}},
    )
    # ------ Recompute students.promedio excluding extension/inglés fuera de malla ------
    try:
        from academic_filter import academic_notes_match
        periodos = await _db.historico_notas.distinct("periodo")
        ultimo = sorted([p for p in periodos if p])[-1] if periodos else None
        if ultimo:
            match = academic_notes_match({"periodo": ultimo})
            pipe = [
                {"$match": match},
                {"$group": {
                    "_id": "$cedula",
                    "prom": {"$avg": "$nota"},
                    "total": {"$sum": 1},
                    "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
                }},
            ]
            n_updated = 0
            async for row in _db.historico_notas.aggregate(pipe):
                aprob = row.get("aprob", 0)
                total = row.get("total", 1) or 1
                await _db.students.update_one(
                    {"cedula": row["_id"]},
                    {"$set": {
                        "promedio": round(row.get("prom", 0) or 0, 2),
                        "total_materias": total,
                        "aprobadas": aprob,
                        "avance_pct": round((aprob / total * 100.0) if total else 0, 2),
                    }},
                )
                n_updated += 1
            logger.info(f"Recomputado promedio académico (sin extensión/inglés fuera de malla) para {n_updated} estudiantes del periodo {ultimo}.")
    except Exception as e:
        logger.warning(f"Falló recompute de promedios académicos: {e}")

    if os.environ.get("SEED_DEMO_DATA", "false").lower() == "true":
        # Run seed in background to avoid blocking startup
        asyncio.create_task(seed_students())
    logger.info("Startup completo.")



# ---------- Health check (Cloud Run / GCP LB) ----------
@app.get("/api/health")
async def health():
    """Liveness + readiness probe. Verifica que la app está viva y que Mongo responde."""
    from database import db as _hdb
    try:
        await _hdb.command("ping")
        db_ok = True
    except Exception as e:
        logger.warning(f"Mongo ping falló: {e}")
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}
