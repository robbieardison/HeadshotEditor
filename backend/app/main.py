from __future__ import annotations

import io
from typing import Final

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image
from rembg import remove

MAX_UPLOAD_BYTES: Final[int] = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/jpg",
    }
)

app = FastAPI(title="HeadshotEditor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
    ],
    # Local dev: Vite may use 5174+ if 5173 is taken; [::1] vs localhost are different origins.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|\[::1\]):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Disposition"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/remove-background")
async def remove_background(file: UploadFile = File(...)) -> Response:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data.") from exc

    try:
        output_bytes = remove(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Background removal failed.",
        ) from exc

    return Response(
        content=output_bytes,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="cutout.png"'},
    )
