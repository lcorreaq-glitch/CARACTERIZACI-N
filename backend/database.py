"""MongoDB connection singleton."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

_mongo_url = os.environ["MONGO_URL"]
_client = AsyncIOMotorClient(_mongo_url)
db = _client[os.environ["DB_NAME"]]


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.students.create_index([("cedula", 1), ("periodo", 1)])
    await db.students.create_index("programa")
    await db.students.create_index("ciudad_codigo")
    await db.uploads.create_index("id", unique=True)
    await db.facultades.create_index("id", unique=True)
    await db.programas.create_index("id", unique=True)
    await db.materias.create_index("id", unique=True)
    await db.periodos.create_index("id", unique=True)
    await db.docente_materia.create_index([("docente_id", 1), ("materia_id", 1), ("periodo", 1)])
