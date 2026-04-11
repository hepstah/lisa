import type { WsStatus } from "../api/types";

const statusConfig = {
  connected: {
    dotClass: "bg-emerald-500",
    label: "Connected",
  },
  disconnected: {
    dotClass: "bg-red-500",
    label: "Disconnected",
  },
  connecting: {
    dotClass: "bg-amber-500 motion-safe:animate-pulse",
    label: "Reconnecting...",
  },
} as const satisfies Record<WsStatus, { dotClass: string; label: string }>;

export function StatusBar({ status }: { status: WsStatus }) {
  const config = statusConfig[status];

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center justify-between px-4 lg:px-8">
        <span className="text-xl font-semibold">Lisa</span>

        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2 w-2 rounded-full ${config.dotClass}`}
            aria-hidden="true"
          />
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {config.label}
          </span>
          <span className="sr-only">{config.label}</span>
        </div>
      </div>
    </header>
  );
}
