import React, { useRef, useEffect } from "react";

// Animated gradient: deep blue → indigo → teal → gold → fade
function AnimatedGradient() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const c = canvasRef.current;
    const ctx = c.getContext("2d");
    let w = window.innerWidth, h = window.innerHeight;
    c.width = w; c.height = h;
    let t = 0;
    function draw() {
      ctx.clearRect(0, 0, w, h);
      // Cinematic: slow, moody, subtle movement
      const grad = ctx.createLinearGradient(
        w * (0.12 + 0.07 * Math.sin(t / 900)), h * (0.12 + 0.08 * Math.cos(t / 750)),
        w * (0.93 - 0.07 * Math.cos(t / 850)), h * (0.86 - 0.07 * Math.sin(t / 1000))
      );
      grad.addColorStop(0,   "#171A22");   // midnight blue
      grad.addColorStop(0.22,"#222A38");   // deep navy/steel
      grad.addColorStop(0.44,"#44337a");   // indigo-violet (cinematic accent)
      grad.addColorStop(0.64,"#1e505c");   // teal blue
      grad.addColorStop(0.8, "#836045");   // muted gold
      grad.addColorStop(0.93,"#dfa855");   // amber highlight
      grad.addColorStop(1,   "#181B26");   // fade out to shadow
      ctx.fillStyle = grad;
      ctx.globalAlpha = 1;
      ctx.fillRect(0, 0, w, h);
      t++;
      requestAnimationFrame(draw);
    }
    draw();
    const resize = () => { c.width = window.innerWidth; c.height = window.innerHeight; w = c.width; h = c.height; };
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
    return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        zIndex: 0,
        inset: 0,
        width: "100vw",
        height: "100vh",
        pointerEvents: "none",
        transition: "filter 0.3s"
      }}
      aria-hidden="true"
    />
  );
}

function CinematicVignette() {
  return (
    <div
      className="pointer-events-none fixed inset-0"
      style={{
        zIndex: 1,
        background:
          "radial-gradient(ellipse at center, transparent 67%, rgba(18,16,24,0.96) 100%)",
        mixBlendMode: "multiply",
      }}
    />
  );
}

function FilmGrain() {
  const grain =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E";
  return (
    <div
      className="pointer-events-none fixed inset-0"
      style={{
        zIndex: 2,
        backgroundImage: `url(${grain})`,
        backgroundRepeat: "repeat",
        opacity: 0.05,
      }}
    />
  );
}

export default function CinematicBackdrop() {
  return (
    <>
      <AnimatedGradient />
      <CinematicVignette />
      <FilmGrain />
    </>
  );
}