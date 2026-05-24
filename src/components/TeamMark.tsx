"use client";

import Image from "next/image";
import { useState } from "react";

interface TeamMarkProps {
  team: string;
  shortCode: string;
  logoPath: string;
  primary: string;
  size?: number;
}

export function TeamMark({ team, shortCode, logoPath, primary, size = 18 }: TeamMarkProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <span
        aria-label={`${team} mark`}
        className="inline-flex items-center justify-center rounded-full text-[10px] font-bold text-white"
        style={{ width: size, height: size, backgroundColor: primary }}
      >
        {shortCode.slice(0, 1)}
      </span>
    );
  }

  return (
    <Image
      src={logoPath}
      alt={`${team} logo`}
      width={size}
      height={size}
      className="shrink-0 object-contain"
      onError={() => setHasError(true)}
    />
  );
}

