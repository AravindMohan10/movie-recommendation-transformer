// src/components/InfoTooltip.jsx
import React, { useRef, useState } from "react";
import { Info } from "lucide-react"; // or use any icon you want

export default function InfoTooltip({ text }) {
  const [open, setOpen] = useState(false);
  const iconRef = useRef(null);
  const tooltipRef = useRef(null);

  const handleOpen = () => {
    setOpen(true);
    setTimeout(() => {
      if (tooltipRef.current && iconRef.current) {
        const iconRect = iconRef.current.getBoundingClientRect();
        const tooltipRect = tooltipRef.current.getBoundingClientRect();

        // If the tooltip is going off the right edge, flip to the left
        if (tooltipRect.right > window.innerWidth - 16) {
          tooltipRef.current.style.left = "auto";
          tooltipRef.current.style.right = "0";
          tooltipRef.current.style.transform = "translateX(0)";
        } else {
          tooltipRef.current.style.left = "100%";
          tooltipRef.current.style.right = "auto";
          tooltipRef.current.style.transform = "translateX(12px)";
        }
      }
    }, 10);
  };

  return (
    <div className="relative flex items-center">
      <button
        ref={iconRef}
        onMouseEnter={handleOpen}
        onMouseLeave={() => setOpen(false)}
        onFocus={handleOpen}
        onBlur={() => setOpen(false)}
        className="rounded-full border border-yellow-300 text-yellow-300 p-1 bg-transparent hover:bg-yellow-300/10 transition"
        aria-label="Info"
        tabIndex={0}
      >
        <Info size={26} />
      </button>
      {open && (
        <div
          ref={tooltipRef}
          className="absolute top-1/2 left-full z-50 min-w-[200px] max-w-xs bg-black/90 text-white text-sm px-4 py-3 rounded-xl shadow-xl border border-yellow-400 whitespace-pre-line"
          style={{
            transform: "translateY(-50%) translateX(12px)",
            pointerEvents: "none", // tooltip disappears on mouseout
          }}
        >
          {text}
        </div>
      )}
    </div>
  );
}