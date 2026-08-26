"use client";

import * as React from "react";
import { Loader2, MessageCircle, Send, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { createConversation, getConversation, sendMessage } from "@/lib/api/copilot";
import { SUGGESTED_QUESTIONS, type CopilotMessageOut } from "@/types/copilot";
import { Markdown } from "@/components/features/copilot/markdown-lite";

const CONVERSATION_KEY_PREFIX = "trustbuy:copilot:conversation:";

export function CopilotPanel({ investigationId }: { investigationId: string }) {
  const { user } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<CopilotMessageOut[]>([]);
  const [suggestions, setSuggestions] = React.useState<string[]>(SUGGESTED_QUESTIONS);
  const [input, setInput] = React.useState("");
  const [isSending, setIsSending] = React.useState(false);
  const [isStarting, setIsStarting] = React.useState(false);
  const [isHydrating, setIsHydrating] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Requirement 5: a different investigation means a different product -
  // never carry the previous investigation's conversation/context over.
  // Chat history *for this* investigation is restored from localStorage +
  // the server below (requirement 7, "Chat history for the current
  // investigation"), not kept in memory across products.
  React.useEffect(() => {
    setConversationId(null);
    setMessages([]);
    setSuggestions(SUGGESTED_QUESTIONS);
    setInput("");

    const storedId = typeof window !== "undefined" ? localStorage.getItem(CONVERSATION_KEY_PREFIX + investigationId) : null;
    if (!storedId) return;

    let cancelled = false;
    setIsHydrating(true);
    getConversation(storedId)
      .then((conversation) => {
        if (cancelled) return;
        setConversationId(conversation.id);
        setMessages(conversation.messages);
      })
      .catch(() => {
        // Conversation no longer reachable (expired session, different
        // user, etc.) - fall back to starting fresh, never throw a visible
        // error over a missing chat history.
        if (!cancelled) localStorage.removeItem(CONVERSATION_KEY_PREFIX + investigationId);
      })
      .finally(() => {
        if (!cancelled) setIsHydrating(false);
      });

    return () => {
      cancelled = true;
    };
  }, [investigationId]);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  async function ensureConversation(): Promise<string> {
    if (conversationId) return conversationId;
    setIsStarting(true);
    try {
      const conversation = await createConversation(investigationId);
      setConversationId(conversation.id);
      if (typeof window !== "undefined") {
        localStorage.setItem(CONVERSATION_KEY_PREFIX + investigationId, conversation.id);
      }
      return conversation.id;
    } finally {
      setIsStarting(false);
    }
  }

  async function handleOpen() {
    setOpen(true);
    if (user && !conversationId) {
      await ensureConversation();
    }
  }

  async function handleSend(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed, cited_evidence_ids: [], created_at: new Date().toISOString() },
    ]);
    setIsSending(true);
    try {
      const id = await ensureConversation();
      const response = await sendMessage(id, trimmed);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.reply,
          cited_evidence_ids: response.cited_evidence_ids,
          created_at: new Date().toISOString(),
        },
      ]);
      setSuggestions(response.suggested_followups?.length ? response.suggested_followups : SUGGESTED_QUESTIONS);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong reaching the Copilot. Please try again.",
          cited_evidence_ids: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  // The button itself is always visible once an investigation is done -
  // hiding it entirely for signed-out visitors made the feature impossible
  // to discover. The backend still requires a real account to actually
  // start a conversation (routes_copilot.py), so an anonymous click opens
  // a sign-in prompt instead of the chat, rather than silently failing.
  if (!open) {
    return (
      <Button
        onClick={handleOpen}
        className="fixed bottom-4 right-4 z-40 h-12 rounded-full px-4 shadow-lg sm:bottom-6 sm:right-6 sm:px-5"
        aria-label="Open AI Purchase Assistant"
      >
        <MessageCircle className="h-4 w-4" /> Ask the Copilot
      </Button>
    );
  }

  const showChips = !isSending && !isStarting && !isHydrating;

  return (
    <div className="fixed inset-x-3 bottom-4 z-40 flex h-[30rem] flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl animate-slide-up sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[32rem] sm:w-96 sm:rounded-lg">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <p className="text-sm font-semibold">AI Purchase Assistant</p>
          <p className="text-xs text-muted-foreground">Scoped to this investigation</p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {!user ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
          <MessageCircle className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Sign in to ask the AI Purchase Copilot about this investigation&apos;s evidence.
          </p>
          <Button asChild size="sm">
            <a href="/login">Sign in</a>
          </Button>
        </div>
      ) : (
      <>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3">
        {isHydrating && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading this investigation&apos;s chat history&hellip;
          </p>
        )}
        {messages.length === 0 && !isStarting && !isHydrating && (
          <p className="text-sm text-muted-foreground">Ask about this investigation&apos;s evidence:</p>
        )}
        {isStarting && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Starting conversation&hellip;
          </p>
        )}
        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "self-end" : "self-start"}>
              <div
                className={
                  m.role === "user"
                    ? "rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground"
                    : "max-w-[15rem] rounded-lg bg-secondary px-3 py-2 text-sm text-secondary-foreground"
                }
              >
                {m.role === "assistant" ? <Markdown text={m.content} /> : m.content}
              </div>
            </div>
          ))}
          {isSending && (
            <div className="self-start rounded-lg bg-secondary px-3 py-2.5">
              <TypingIndicator />
            </div>
          )}
        </div>
        {showChips && suggestions.length > 0 && (
          <div className="mt-3 flex flex-col gap-2">
            {messages.length === 0 && <p className="text-xs text-muted-foreground">Suggested questions:</p>}
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="rounded-full border border-border px-2.5 py-1 text-left text-xs hover:bg-secondary"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="flex items-center gap-2 border-t border-border p-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this purchase..."
          disabled={isSending}
          aria-label="Message"
        />
        <Button type="submit" size="icon" disabled={isSending || !input.trim()} aria-label="Send">
          <Send className="h-4 w-4" />
        </Button>
      </form>
      </>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1" aria-label="Assistant is typing" role="status">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </div>
  );
}
