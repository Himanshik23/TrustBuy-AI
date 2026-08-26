"use client";

import * as React from "react";

/**
 * Minimal, dependency-free Markdown renderer for Copilot replies
 * (Feature: "AI Purchase Assistant" - requirement 7, "Markdown support for
 * formatted answers"). Builds React elements directly (never
 * dangerouslySetInnerHTML), so it only ever needs to support the small
 * subset the Copilot's own template/LLM answers actually produce:
 * **bold**, `inline code`, "- " bullet lists, and paragraphs/line breaks.
 */
export function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="flex flex-col gap-1.5">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n");
        const isList = lines.length > 0 && lines.every((l) => l.trim() === "" || /^[-*]\s+/.test(l.trim()));
        if (isList) {
          const items = lines.filter((l) => l.trim() !== "");
          return (
            <ul key={blockIndex} className="list-inside list-disc space-y-0.5">
              {items.map((line, i) => (
                <li key={i}>{renderInline(line.trim().replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={blockIndex}>
            {lines.map((line, i) => (
              <React.Fragment key={i}>
                {renderInline(line)}
                {i < lines.length - 1 && <br />}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter((p) => p !== "");
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="rounded bg-black/10 px-1 py-0.5 font-mono text-xs dark:bg-white/10">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}
