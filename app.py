import hashlib
import os
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.responses import RedirectResponse


DB_PATH = Path(os.getenv("DENUNCIAS_DB", "data/denuncias.db"))


class DenunciaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(min_length=2, max_length=80)
    descripcion: str = Field(min_length=20, max_length=10_000)
    fecha_incidente: datetime | None = None
    ubicacion: str | None = Field(default=None, max_length=300)

    @field_validator("categoria", "descripcion", "ubicacion", mode="before")
    @classmethod
    def quitar_espacios_exteriores(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class DenunciaCreada(BaseModel):
    id: str
    codigo_seguimiento: str
    estado: str


class EstadoDenuncia(BaseModel):
    id: str
    estado: str
    creada_en: datetime


def conectar_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def inicializar_db() -> None:
    with conectar_db() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS denuncias (
                id TEXT PRIMARY KEY,
                codigo_hash TEXT NOT NULL,
                categoria TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                fecha_incidente TEXT,
                ubicacion TEXT,
                estado TEXT NOT NULL,
                creada_en TEXT NOT NULL
            )"""
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    inicializar_db()
    yield


app = FastAPI(
    title="API de Denuncias",
    description="Registro anónimo de denuncias y consulta privada de su estado.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def inicio() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"estado": "ok"}


@app.post(
    "/denuncias",
    response_model=DenunciaCreada,
    status_code=status.HTTP_201_CREATED,
    tags=["Denuncias"],
)
def crear_denuncia(entrada: DenunciaEntrada) -> DenunciaCreada:
    denuncia_id = str(uuid.uuid4())
    codigo = secrets.token_urlsafe(32)
    creada_en = datetime.now(timezone.utc).isoformat()

    with conectar_db() as connection:
        connection.execute(
            """INSERT INTO denuncias (
                id, codigo_hash, categoria, descripcion, fecha_incidente,
                ubicacion, estado, creada_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                denuncia_id,
                hashlib.sha256(codigo.encode()).hexdigest(),
                entrada.categoria,
                entrada.descripcion,
                entrada.fecha_incidente.isoformat() if entrada.fecha_incidente else None,
                entrada.ubicacion,
                "recibida",
                creada_en,
            ),
        )

    return DenunciaCreada(
        id=denuncia_id,
        codigo_seguimiento=codigo,
        estado="recibida",
    )


@app.get(
    "/denuncias/{denuncia_id}/estado",
    response_model=EstadoDenuncia,
    tags=["Denuncias"],
)
def consultar_estado(
    denuncia_id: str,
    codigo_seguimiento: Annotated[str, Header(alias="X-Codigo-Seguimiento")],
) -> EstadoDenuncia:
    codigo_hash = hashlib.sha256(codigo_seguimiento.encode()).hexdigest()
    with conectar_db() as connection:
        denuncia = connection.execute(
            "SELECT id, estado, creada_en FROM denuncias WHERE id = ? AND codigo_hash = ?",
            (denuncia_id, codigo_hash),
        ).fetchone()

    if denuncia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Denuncia no encontrada")

    return EstadoDenuncia(
        id=denuncia["id"],
        estado=denuncia["estado"],
        creada_en=datetime.fromisoformat(denuncia["creada_en"]),
    )