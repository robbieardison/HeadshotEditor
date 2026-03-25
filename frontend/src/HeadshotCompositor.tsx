import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

const LOGICAL_SIZE = 800;

export type CompositorProps = {
  imageSource: string;
  /** Used for the download filename; not a filesystem path. */
  originalFileName?: string | null;
};

function downloadFilename(original: string | null | undefined): string {
  if (!original?.trim()) return "headshot.png";
  const base = original.replace(/\.[^./\\]+$/, "").trim();
  const safe = base.replace(/[\\/:*?"<>|]/g, "_");
  return `${safe || "headshot"}_headshot.png`;
}

export function HeadshotCompositor({
  imageSource,
  originalFileName,
}: CompositorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const [bgColor, setBgColor] = useState("#2d6cdf");
  const [circleRadiusPct, setCircleRadiusPct] = useState(28);
  const [circleCenterYNorm, setCircleCenterYNorm] = useState(0.62);
  const [subjectScale, setSubjectScale] = useState(1.05);
  const [subjectYOffset, setSubjectYOffset] = useState(0);

  const [plateBlur, setPlateBlur] = useState(28);
  const [plateOffX, setPlateOffX] = useState(0);
  const [plateOffY, setPlateOffY] = useState(14);
  const [plateOpacity, setPlateOpacity] = useState(0.35);

  const [subBlur, setSubBlur] = useState(18);
  const [subOffX, setSubOffX] = useState(0);
  const [subOffY, setSubOffY] = useState(10);
  const [subOpacity, setSubOpacity] = useState(0.28);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img?.complete || !img.naturalWidth) return;

    const dpr = Math.min(window.devicePixelRatio ?? 1, 2);
    const w = LOGICAL_SIZE;
    const h = LOGICAL_SIZE;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h * circleCenterYNorm;
    const r = (Math.min(w, h) * circleRadiusPct) / 100;

    ctx.save();
    ctx.shadowColor = `rgba(0,0,0,${plateOpacity})`;
    ctx.shadowBlur = plateBlur;
    ctx.shadowOffsetX = plateOffX;
    ctx.shadowOffsetY = plateOffY;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = bgColor;
    ctx.fill();
    ctx.restore();

    const iw = img.naturalWidth;
    const ih = img.naturalHeight;
    const baseW = w * 0.58 * subjectScale;
    const drawW = baseW;
    const drawH = (drawW * ih) / iw;
    const drawX = cx - drawW / 2;
    const drawY = cy + r * 0.42 - drawH + subjectYOffset;

    ctx.save();
    ctx.shadowColor = `rgba(0,0,0,${subOpacity})`;
    ctx.shadowBlur = subBlur;
    ctx.shadowOffsetX = subOffX;
    ctx.shadowOffsetY = subOffY;
    ctx.drawImage(img, drawX, drawY, drawW, drawH);
    ctx.restore();
  }, [
    bgColor,
    circleRadiusPct,
    circleCenterYNorm,
    subjectScale,
    subjectYOffset,
    plateBlur,
    plateOffX,
    plateOffY,
    plateOpacity,
    subBlur,
    subOffX,
    subOffY,
    subOpacity,
  ]);

  const drawRef = useRef(draw);
  drawRef.current = draw;

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = imageSource;
    img.onload = () => {
      imgRef.current = img;
      drawRef.current();
    };
    return () => {
      imgRef.current = null;
    };
  }, [imageSource]);

  useLayoutEffect(() => {
    drawRef.current();
  }, [draw]);

  const exportPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob: Blob | null) => {
      if (!blob) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = downloadFilename(originalFileName);
      a.click();
      URL.revokeObjectURL(a.href);
    }, "image/png");
  };

  return (
    <div className="compositor">
      <div className="compositor__canvas-wrap">
        <canvas ref={canvasRef} className="compositor__canvas" />
      </div>

      <div className="compositor__controls">
        <h2 className="compositor__h2">Plate &amp; color</h2>
        <label className="field">
          <span>Background color</span>
          <input
            type="color"
            value={bgColor}
            onChange={(e) => setBgColor(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Circle radius ({circleRadiusPct}% of min side)</span>
          <input
            type="range"
            min={12}
            max={42}
            value={circleRadiusPct}
            onChange={(e) => setCircleRadiusPct(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Circle vertical position</span>
          <input
            type="range"
            min={45}
            max={78}
            value={Math.round(circleCenterYNorm * 100)}
            onChange={(e) =>
              setCircleCenterYNorm(Number(e.target.value) / 100)
            }
          />
        </label>

        <h2 className="compositor__h2">Subject</h2>
        <label className="field">
          <span>Scale ({subjectScale.toFixed(2)})</span>
          <input
            type="range"
            min={60}
            max={150}
            value={Math.round(subjectScale * 100)}
            onChange={(e) => setSubjectScale(Number(e.target.value) / 100)}
          />
        </label>
        <label className="field">
          <span>Vertical nudge</span>
          <input
            type="range"
            min={-120}
            max={120}
            value={subjectYOffset}
            onChange={(e) => setSubjectYOffset(Number(e.target.value))}
          />
        </label>

        <h2 className="compositor__h2">Circular plate shadow</h2>
        <label className="field">
          <span>Blur ({plateBlur}px)</span>
          <input
            type="range"
            min={0}
            max={80}
            value={plateBlur}
            onChange={(e) => setPlateBlur(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Offset X ({plateOffX}px)</span>
          <input
            type="range"
            min={-40}
            max={40}
            value={plateOffX}
            onChange={(e) => setPlateOffX(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Offset Y ({plateOffY}px)</span>
          <input
            type="range"
            min={-40}
            max={60}
            value={plateOffY}
            onChange={(e) => setPlateOffY(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Opacity ({plateOpacity.toFixed(2)})</span>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(plateOpacity * 100)}
            onChange={(e) => setPlateOpacity(Number(e.target.value) / 100)}
          />
        </label>

        <h2 className="compositor__h2">Subject shadow</h2>
        <label className="field">
          <span>Blur ({subBlur}px)</span>
          <input
            type="range"
            min={0}
            max={80}
            value={subBlur}
            onChange={(e) => setSubBlur(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Offset X ({subOffX}px)</span>
          <input
            type="range"
            min={-40}
            max={40}
            value={subOffX}
            onChange={(e) => setSubOffX(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Offset Y ({subOffY}px)</span>
          <input
            type="range"
            min={-40}
            max={60}
            value={subOffY}
            onChange={(e) => setSubOffY(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span>Opacity ({subOpacity.toFixed(2)})</span>
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(subOpacity * 100)}
            onChange={(e) => setSubOpacity(Number(e.target.value) / 100)}
          />
        </label>

        <button type="button" className="btn-primary" onClick={exportPng}>
          Download PNG
        </button>
      </div>
    </div>
  );
}
