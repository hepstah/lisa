import type { PipelineState } from "../api/types";

const stateConfig: Record<PipelineState, { label: string; dotClass: string }> = {
  listening:  { label: "Listening",  dotClass: "bg-emerald-500" },
  processing: { label: "Processing", dotClass: "bg-amber-500 motion-safe:animate-pulse" },
  responding: { label: "Responding", dotClass: "bg-blue-500" },
  error:      { label: "Error",      dotClass: "bg-red-500" },
  offline:    { label: "Offline",    dotClass: "bg-zinc-500" },
};

export function PipelineStatus({ status }: { status: PipelineState }) {
  const config = stateConfig[status];

  return (
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
  );
}
