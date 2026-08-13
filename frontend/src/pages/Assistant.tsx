import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { ChatTranscript, useChatController } from "../components/AssistantWidget";

export default function Assistant() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, isPending } = useChatController();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input;
    setInput("");
    sendMessage(text);
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-bold">Ask MMT Assistant</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Questions are answered from real monitored data when available. Every reply says which mode it used.
      </p>

      <Card className="mt-4">
        <CardHeader><CardTitle>Transcript</CardTitle></CardHeader>
        <CardContent>
          <div className="min-h-[300px]">
            {messages.length === 0 ? (
              <p className="text-sm text-muted-foreground">No messages yet. Ask about a destination or signal.</p>
            ) : (
              <ChatTranscript messages={messages} />
            )}
          </div>
          <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
              disabled={isPending}
            />
            <button
              type="submit"
              disabled={isPending || !input.trim()}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
