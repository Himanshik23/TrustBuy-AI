"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Clipboard, ImagePlus, Loader2, X } from "lucide-react";
import axios from "axios";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useCreateImageInvestigation, useCreateInvestigation } from "@/hooks/use-investigation";
import { checkShoppingUrl, EXAMPLE_URLS, normalizeShoppingUrl } from "@/lib/url-normalize";
import type { ApiErrorBody } from "@/types/auth";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Three equally-supported ways in: URL only, image only, or both together
 * (cross-checked against each other server-side - Feature: "Image-Based
 * Product Analysis"). The URL field stays the primary, unchanged flow;
 * attaching an image is purely additive. */
export function UrlSubmitForm({ size = "default" }: { size?: "default" | "large" }) {
  const router = useRouter();
  const [url, setUrl] = React.useState("");
  const [image, setImage] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [touched, setTouched] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const { mutateAsync, isPending } = useCreateInvestigation();
  const { mutateAsync: mutateImageAsync, isPending: isImagePending } = useCreateImageInvestigation();
  const pending = isPending || isImagePending;

  function validateNow(value: string): boolean {
    if (!value.trim() && image) return true; // image-only submission never needs a URL
    const result = checkShoppingUrl(value);
    setError(result.ok ? null : result.message ?? null);
    return result.ok;
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setTouched(true);

    if (image) {
      // Image present: URL is optional, so only validate it if the user
      // actually typed something (an image-only submission skips this).
      if (url.trim() && !validateNow(url)) {
        inputRef.current?.focus();
        return;
      }
      try {
        const result = await mutateImageAsync({
          image,
          url: url.trim() ? normalizeShoppingUrl(url) : undefined,
        });
        router.push(`/investigate/${result.investigation_id}`);
      } catch (err) {
        const message =
          (axios.isAxiosError(err) && (err.response?.data as ApiErrorBody | undefined)?.error?.message) ||
          "We couldn't start that investigation. Please try again in a moment.";
        setError(message);
      }
      return;
    }

    if (!validateNow(url)) {
      inputRef.current?.focus();
      return;
    }
    const normalized = normalizeShoppingUrl(url);
    try {
      const result = await mutateAsync(normalized);
      router.push(`/investigate/${result.investigation_id}`);
    } catch (err) {
      const message =
        (axios.isAxiosError(err) && (err.response?.data as ApiErrorBody | undefined)?.error?.message) ||
        "We couldn't start that investigation. Please try again in a moment.";
      setError(message);
    }
  }

  async function onPasteClick() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text);
        setError(null);
        inputRef.current?.focus();
      }
    } catch {
      // Clipboard permission denied/unavailable - fall back to a normal
      // focus so the user can paste with their own keyboard shortcut.
      inputRef.current?.focus();
    }
  }

  function onClear() {
    setUrl("");
    setError(null);
    inputRef.current?.focus();
  }

  function onImageChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-choosing the same file later
    if (!file) return;
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      setError("Please choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError("That image is larger than 10 MB - please choose a smaller file.");
      return;
    }
    setError(null);
    setImage(file);
  }

  const large = size === "large";

  return (
    <div className="flex w-full flex-col gap-2">
      <form onSubmit={onSubmit} className={cn("flex w-full flex-col gap-2 sm:flex-row", large && "gap-3")}>
        <div className="relative flex-1">
          <input
            ref={inputRef}
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (error) setError(null);
            }}
            onBlur={() => {
              setTouched(true);
              if (url.trim()) validateNow(url);
            }}
            placeholder={
              image
                ? "Optional: also add the product URL to cross-check against the image"
                : "Paste a product link - nike.in, amazon.in/product, flipkart.com..."
            }
            aria-label="Product URL"
            aria-invalid={touched && Boolean(error)}
            disabled={pending}
            className={cn(
              "flex w-full rounded-xl border bg-surface pr-28 text-foreground placeholder:text-muted-foreground transition-all",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-50",
              large ? "h-14 pl-5 text-base sm:text-lg" : "h-12 pl-4 text-base",
              touched && error ? "border-destructive" : "border-input"
            )}
          />
          <div className="absolute inset-y-0 right-2 flex items-center gap-1">
            {url && !pending && (
              <button
                type="button"
                onClick={onClear}
                aria-label="Clear"
                className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
            {!pending && (
              <button
                type="button"
                onClick={onPasteClick}
                aria-label="Paste from clipboard"
                title="Paste from clipboard"
                className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Clipboard className="h-4 w-4" />
              </button>
            )}
            {!pending && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_IMAGE_TYPES.join(",")}
                  onChange={onImageChosen}
                  className="hidden"
                  aria-hidden
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  aria-label="Upload a product image or screenshot instead"
                  title="Upload a product image or screenshot instead"
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full transition-colors hover:bg-secondary hover:text-foreground",
                    image ? "text-primary" : "text-muted-foreground"
                  )}
                >
                  <ImagePlus className="h-4 w-4" />
                </button>
              </>
            )}
          </div>
        </div>
        <Button type="submit" size="lg" className={cn(large ? "h-14 px-8 text-base" : "h-12")} disabled={pending || (!url.trim() && !image)}>
          {pending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Investigating...
            </>
          ) : (
            <>
              Analyze <ArrowRight className="h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      {image && (
        <div className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs text-foreground">
          <ImagePlus className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
          <span className="truncate">{image.name}</span>
          <span className="text-muted-foreground">attached - will be analyzed{url.trim() ? " together with the URL above" : ""}</span>
          <button
            type="button"
            onClick={() => setImage(null)}
            aria-label="Remove image"
            className="ml-auto shrink-0 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {touched && error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span>Try:</span>
          {EXAMPLE_URLS.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setUrl(example);
                setError(null);
                inputRef.current?.focus();
              }}
              className="rounded-full border border-border px-2 py-0.5 transition-colors hover:border-primary/40 hover:bg-secondary hover:text-foreground"
            >
              {example}
            </button>
          ))}
          <span className="ml-1">or tap</span>
          <ImagePlus className="h-3 w-3" aria-hidden />
          <span>to upload a screenshot instead</span>
        </div>
      )}
    </div>
  );
}
