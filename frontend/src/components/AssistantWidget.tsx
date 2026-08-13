import { useState } from "react";
import { MessageCircle, X } from "lucide-react";
import { useSendChatMessage } from "../api/queries";
import { cn } from "../lib/utils";

interface LocalMessage {
  role: "user" | "assistant";
  content: string;
  grounded?: boolean;
  source_type?: "internal_data" | "general_knowledge";
  evidence_refs?: string[];
}

function GroundingBadge({ grounded, sourceType, evidenceRefs }: {
  grounded: boolean; sourceType?: string; evidenceRefs?: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  const count = evidenceRefs?.length ?? 0;

  if (grounded) {
    return (
      <div className="mt-1">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="rounded-full bg-success/15 px-2 py-0.5 text-[11px] font-medium text-success hover:bg-success/25"
        >
          Grounded in {count} live signal{count === 1 ? "" : "s"}
        </button>
        {expanded && evidenceRefs && (
          <div className="mt-1 space-y-0.5 rounded-md border border-border bg-muted/40 p-2 text-[11px] text-muted-foreground">
            {evidenceRefs.map((id) => (
              <div key={id} className="font-mono">{id}</div>
            ))}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="mt-1">
      <span className="rounded-full bg-warning/15 px-2 py-0.5 text-[11px] font-medium text-warning">
        General knowledge, not from live monitoring
      </span>
    </div>
  );
}

export function ChatTranscript({ messages, compact }: { messages: LocalMessage[]; compact?: boolean }) {
  return (
    <div className={cn("space-y-3", compact ? "text-sm" : "text-base")}>
      {messages.map((m, i) => (
        <div key={i} className={cn("flex flex-col", m.role === "user" ? "items-end" : "items-start")}>
          <div
            className={cn(
              "max-w-[85%] rounded-lg px-3 py-2",
              m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
            )}
          >
            {m.content}
          </div>
          {m.role === "assistant" && (
            <GroundingBadge grounded={!!m.grounded} sourceType={m.source_type} evidenceRefs={m.evidence_refs} />
          )}
        </div>
      ))}
    </div>
  );
}

export function useChatController() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const send = useSendChatMessage();

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    try {
      const res = await send.mutateAsync({ session_id: sessionId ?? undefined, message: text });
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply, grounded: res.grounded, source_type: res.source_type, evidence_refs: res.evidence_refs },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong sending that message.", grounded: false, source_type: "general_knowledge" },
      ]);
    }
  }

  return { messages, sendMessage, isPending: send.isPending };
}

export default function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const { messages, sendMessage, isPending } = useChatController();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input;
    setInput("");
    sendMessage(text);
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {open && (
        <div className="mb-3 flex h-[480px] w-80 flex-col rounded-lg border border-border bg-card shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-semibold">Ask MMT Assistant</span>
            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {messages.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Ask about a destination, signal, or recent change. Answers grounded in live monitoring data are
                labeled; answers from general knowledge are labeled too.
              </p>
            ) : (
              <ChatTranscript messages={messages} compact />
            )}
          </div>
          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 rounded-md border border-input bg-background px-2 py-1.5 text-sm"
              disabled={isPending}
            />
            <button
              type="submit"
              disabled={isPending || !input.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-mmt-blueLight"
      >
        <MessageCircle className="h-5 w-5" />
      </button>
    </div>
  );
}
