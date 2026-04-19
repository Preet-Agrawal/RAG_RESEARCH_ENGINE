'use client';

interface LogoProps {
  size?: number;
  className?: string;
}

/**
 * RAG Research Engine logo — "Focus Band"
 *
 * A minimalist mark representing the core concept: LLMs attend to document
 * edges (faint lines top/bottom) but miss the middle (bright central band
 * — what PARA recovers).
 *
 * Inline SVG so it respects CSS effects and stays crisp at any size.
 */
export default function Logo({ size = 28, className = '' }: LogoProps) {
  const id = `logo-${Math.random().toString(36).slice(2, 9)}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="RAG Research Engine"
    >
      <defs>
        <linearGradient id={`${id}-bg`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#d4a87b" />
          <stop offset="100%" stopColor="#8b5a2b" />
        </linearGradient>
        <linearGradient id={`${id}-band`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
          <stop offset="50%" stopColor="#fff4e0" stopOpacity="1" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.85" />
        </linearGradient>
        <filter id={`${id}-glow`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle cx="32" cy="32" r="32" fill={`url(#${id}-bg)`} />

      {/* Top edge lines — what LLMs attend to by default */}
      <rect x="16" y="16" width="32" height="2" rx="1" fill="white" opacity="0.35" />
      <rect x="20" y="21" width="24" height="2" rx="1" fill="white" opacity="0.25" />

      {/* Middle focus band — what PARA recovers */}
      <rect
        x="10"
        y="28"
        width="44"
        height="8"
        rx="4"
        fill={`url(#${id}-band)`}
        filter={`url(#${id}-glow)`}
      />

      {/* Bottom edge lines */}
      <rect x="20" y="41" width="24" height="2" rx="1" fill="white" opacity="0.25" />
      <rect x="16" y="46" width="32" height="2" rx="1" fill="white" opacity="0.35" />
    </svg>
  );
}

/**
 * Full logo lockup — mark + wordmark, for the hero area.
 */
export function LogoLockup({ className = '' }: { className?: string }) {
  return (
    <div className={`inline-flex items-center gap-3 ${className}`}>
      <Logo size={40} />
      <div className="leading-tight">
        <div className="text-lg font-semibold tracking-tight text-claude-text">
          RAG Research Engine
        </div>
        <div className="text-[10px] uppercase tracking-[0.15em] text-claude-text-muted">
          Position-Aware Retrieval
        </div>
      </div>
    </div>
  );
}
