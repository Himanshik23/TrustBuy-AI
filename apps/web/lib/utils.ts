import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes without specificity clashes - the standard
 * shadcn/ui `cn()` helper, used by every component in components/ui. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
