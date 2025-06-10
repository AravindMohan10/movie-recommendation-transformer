import React from "react";

export default function GlassOrb() {
  return (
    <div
      style={{
        position: "absolute",
        top: "45%",
        left: "50%",
        transform: "translate(-50%, -60%)",
        zIndex: 5,
        width: "440px",
        height: "440px",
        pointerEvents: "none",
        filter: "blur(1.8px)",
        background: "radial-gradient(circle at 55% 42%, rgba(255,255,255,0.28) 0%, rgba(120,255,220,0.20) 33%, rgba(62,80,255,0.08) 85%, rgba(36,46,56,0.01) 100%)",
        borderRadius: "50%",
        boxShadow:
          "0 2px 80px 26px rgba(42,247,237,0.13), 0 2px 44px 4px rgba(255,255,255,0.06)",
        border: "1.2px solid rgba(255,255,255,0.13)",
        backdropFilter: "blur(24px) saturate(180%)",
        transition: "box-shadow 0.6s cubic-bezier(0.3,0.8,0.3,1)"
      }}
      aria-hidden="true"
    />
  );
}