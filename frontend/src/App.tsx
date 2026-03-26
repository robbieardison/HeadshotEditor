import { useCallback, useEffect, useState } from "react";
import { removeBackground } from "./api/removeBackground";
import { HeadshotCompositor } from "./HeadshotCompositor";
import "./App.css";

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [originalPreviewUrl, setOriginalPreviewUrl] = useState<string | null>(null);
  const [cutoutUrl, setCutoutUrl] = useState<string | null>(null);
  const [originalFileName, setOriginalFileName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (originalPreviewUrl) URL.revokeObjectURL(originalPreviewUrl);
      if (cutoutUrl) URL.revokeObjectURL(cutoutUrl);
    };
  }, [originalPreviewUrl, cutoutUrl]);

  const onFileSelected = useCallback((file: File | null) => {
    if (!file) return;
    setSelectedFile(file);
    setError(null);
    setOriginalFileName(file.name);
    setCutoutUrl(null);
    setOriginalPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
  }, []);

  const onRemoveBackground = useCallback(async () => {
    if (!selectedFile) return;
    setError(null);
    setBusy(true);
    setCutoutUrl(null);
    try {
      const blob = await removeBackground(selectedFile);
      setCutoutUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Background removal failed.");
    } finally {
      setBusy(false);
    }
  }, [selectedFile]);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Headshot Editor</h1>
        <p className="app__lede">
          Remove the background with the local API, tune the circular plate and
          shadows, then export a PNG.
        </p>
      </header>

      <section className="app__upload">
        <label className="upload-zone">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              onFileSelected(f ?? null);
              e.target.value = "";
            }}
          />
          <span className="upload-zone__text">
            {busy ? "Removing background…" : "Choose a headshot (JPEG, PNG, WebP)"}
          </span>
        </label>
        {error ? <p className="app__error">{error}</p> : null}
      </section>

      {originalPreviewUrl ? (
        <section className="app__preview">
          <div className="app__preview-header">
            <h2 className="app__subtitle">
              {cutoutUrl ? "After (background removed)" : "Before (original)"}
            </h2>
            <button
              type="button"
              className="btn-primary"
              disabled={busy || !!cutoutUrl}
              onClick={() => {
                void onRemoveBackground();
              }}
            >
              {busy
                ? "Removing background..."
                : cutoutUrl
                  ? "Background removed"
                  : "Remove background"}
            </button>
          </div>

          <div className="app__preview-body">
            {cutoutUrl ? (
              <HeadshotCompositor
                imageSource={cutoutUrl}
                originalFileName={originalFileName}
              />
            ) : (
              <img
                className="app__original-image"
                src={originalPreviewUrl}
                alt="Original upload preview"
              />
            )}
          </div>
        </section>
      ) : (
        !busy && (
          <p className="app__hint">
            Start the FastAPI server (<code>uvicorn app.main:app --reload</code>{" "}
            from <code>backend/</code>), then upload an image.
          </p>
        )
      )}
    </div>
  );
}
