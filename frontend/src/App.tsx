import { useCallback, useEffect, useState } from "react";
import { removeBackground } from "./api/removeBackground";
import { HeadshotCompositor } from "./HeadshotCompositor";
import "./App.css";

export default function App() {
  const [cutoutUrl, setCutoutUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (cutoutUrl) URL.revokeObjectURL(cutoutUrl);
    };
  }, [cutoutUrl]);

  const onFile = useCallback(async (file: File | null) => {
    if (!file) return;
    setError(null);
    setBusy(true);
    setCutoutUrl(null);
    try {
      const blob = await removeBackground(file);
      setCutoutUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Background removal failed.");
    } finally {
      setBusy(false);
    }
  }, []);

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
              void onFile(f ?? null);
              e.target.value = "";
            }}
          />
          <span className="upload-zone__text">
            {busy ? "Removing background…" : "Choose a headshot (JPEG, PNG, WebP)"}
          </span>
        </label>
        {error ? <p className="app__error">{error}</p> : null}
      </section>

      {cutoutUrl ? (
        <HeadshotCompositor imageSource={cutoutUrl} />
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
