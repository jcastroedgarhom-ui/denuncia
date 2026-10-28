# API de Denuncias

API REST para enviar denuncias de forma anónima y consultar su estado con un código privado.

## Ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

La documentación interactiva queda disponible en `http://127.0.0.1:8000/docs`. Los datos se guardan en `data/denuncias.db`; se puede cambiar la ubicación con la variable `DENUNCIAS_DB`.

## Endpoints

- `GET /health`: comprobación básica del servicio.
- `POST /denuncias`: registra categoría, descripción y, opcionalmente, fecha y ubicación. No solicita identidad ni datos de contacto. Devuelve un identificador y un código de seguimiento; guarda solo el hash de ese código.
- `GET /denuncias/{id}/estado`: consulta únicamente el estado. Requiere el encabezado `X-Codigo-Seguimiento` con el código recibido al crear la denuncia.

No existe un endpoint público para listar denuncias o leer sus descripciones. El código de seguimiento se muestra una sola vez; si se pierde, no se puede recuperar.

## Pruebas

```bash
python -m unittest
```