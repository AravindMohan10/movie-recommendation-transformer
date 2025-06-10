// src/components/MovieBubbles.jsx
import React, { useRef, useEffect } from "react";

function randomColor() {
  const palette = ["#fb97e2", "#fcffae", "#beecfd", "#b6afff", "#ffe3e7"];
  return palette[Math.floor(Math.random() * palette.length)];
}

function randomBetween(a, b) {
  return a + Math.random() * (b - a);
}

export default function MovieBubbles() {
  const canvasRef = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let bubbles = Array.from({ length: 25 }, () => ({
      x: randomBetween(0, canvas.width),
      y: randomBetween(0, canvas.height),
      r: randomBetween(28, 64),
      color: randomColor(),
      vx: randomBetween(-0.5, 0.5),
      vy: randomBetween(0.04, 0.14),
      alpha: randomBetween(0.09, 0.28),
    }));

    let animationId;
    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      bubbles.forEach((b) => {
        ctx.globalAlpha = b.alpha;
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, 2 * Math.PI);
        ctx.fillStyle = b.color;
        ctx.shadowColor = b.color;
        ctx.shadowBlur = 28;
        ctx.fill();
        ctx.closePath();
        b.x += b.vx;
        b.y += b.vy;
        // Loop bubbles to top when out of screen
        if (b.y - b.r > canvas.height) {
          b.y = -b.r;
          b.x = randomBetween(0, canvas.width);
        }
        if (b.x - b.r > canvas.width || b.x + b.r < 0) {
          b.x = randomBetween(0, canvas.width);
        }
      });
      animationId = requestAnimationFrame(animate);
    }

    animate();
    return () => cancelAnimationFrame(animationId);
  }, []);

  // Make sure the canvas fills the background
  return (
    <canvas
      ref={canvasRef}
      width={window.innerWidth}
      height={window.innerHeight}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 1,
        width: "100vw",
        height: "100vh",
        pointerEvents: "none",
        opacity: 0.32,
      }}
    />
  );
}