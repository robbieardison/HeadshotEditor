# HeadshotEditor

Local tool for **automatic background removal** (Python + [rembg](https://github.com/danielgatis/rembg)), then **compositing** in the browser: solid circular plate, adjustable colors, and separate shadows for the plate and the subject. Export as PNG.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the Vite frontend)

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The first run of `rembg` may **download model weights**; that can take a minute and use noticeable CPU.

- Health: `GET http://localhost:8000/health`
- Remove background: `POST http://localhost:8000/api/remove-background` (multipart field `file`, max 15 MB, JPEG/PNG/WebP)

## Frontend (Vite + React)

```bash
cd frontend
cp .env.example .env   # optional; defaults to http://localhost:8000
npm install
npm run dev
```

Open the URL shown (typically `http://localhost:5173`). Keep the API running on port 8000 so uploads work.

## Workspace folder

To open this project in Cursor alongside your other repos: **File → Add Folder to Workspace** and choose `Documents/projects/HeadshotEditor` (or the full path on your machine).

## Project layout

- `backend/` — FastAPI app and `rembg` integration
- `frontend/` — React UI, canvas compositor, PNG download
# HeadshotEditor
