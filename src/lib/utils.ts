import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a UTC timestamp as a human-readable AU locale string. */
export function formatRoundUpdatedLabel(timestamp: string): string {
  return new Date(timestamp).toLocaleString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

/** Determine whether baked data is fresh (≤6 h old) or stale. */
export function computeFreshness(lastSuccessfulUpdateAt: string): {
  label: string;
  variant: "fresh" | "stale";
} {
  const updatedMs = new Date(lastSuccessfulUpdateAt).getTime();
  const ageMs = Date.now() - updatedMs;
  const sixHours = 6 * 60 * 60 * 1000;
  return ageMs <= sixHours
    ? { label: "Fresh", variant: "fresh" }
    : { label: "Stale", variant: "stale" };
}
