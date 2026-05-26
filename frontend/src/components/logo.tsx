import Link from "next/link";
import { cn } from "@/lib/utils";

/**
 * Logo "BI AZUL" — hexágono azul com seta de crescimento.
 * Inspirada na identidade visual da marca.
 */
export function Logo({
  className,
  href = "/",
  showText = true,
}: {
  className?: string;
  href?: string;
  showText?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2 font-bold tracking-tight",
        className,
      )}
    >
      <BiAzulMark className="h-8 w-8" />
      {showText && (
        <span className="text-lg text-[#1e5cff]">BI AZUL</span>
      )}
    </Link>
  );
}

export function BiAzulMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="BI AZUL"
    >
      {/* Hexágono externo */}
      <path
        d="M32 4 L56 18 L56 46 L32 60 L8 46 L8 18 Z"
        fill="#1e5cff"
      />
      {/* "Face" interna (sombra/profundidade) */}
      <path
        d="M32 60 L56 46 L56 18 L48 22 L48 50 Z"
        fill="#1748cc"
        opacity="0.6"
      />
      {/* Seta + ondulação no centro */}
      <g stroke="#ffffff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none">
        <path d="M16 38 Q24 30, 30 36 T46 26" />
        <polyline points="38,22 46,22 46,30" />
      </g>
    </svg>
  );
}
