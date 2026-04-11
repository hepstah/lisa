import { useState, type FormEvent } from "react";
import { Loader2, Send } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface TextCommandProps {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
}

export function TextCommand({ onSend, disabled }: TextCommandProps) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = text.trim().length > 0 && !submitting && !disabled;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    try {
      await onSend(text.trim());
      setText("");
    } catch {
      // Keep text in input on error so user can retry
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={disabled ? "Connecting..." : "Type a command..."}
        disabled={submitting || disabled}
        className="flex-1"
      />
      <Button type="submit" disabled={!canSubmit}>
        {submitting ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Send className="size-4" />
        )}
        Send Command
      </Button>
    </form>
  );
}
