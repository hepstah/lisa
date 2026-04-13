import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { CommandRecord, LlmDebug } from "../api/types";

interface CommandHistoryProps {
  commands: CommandRecord[];
  loading: boolean;
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  const time = `${hours}:${minutes}`;

  if (isToday) return time;

  const month = date.toLocaleString("en-US", { month: "short" });
  return `${month} ${date.getDate()}, ${time}`;
}

const statusBadge: Record<
  CommandRecord["status"],
  { label: string; className: string }
> = {
  success: { label: "Success", className: "text-emerald-500" },
  error: { label: "Error", className: "text-red-500" },
  rejected: { label: "Rejected", className: "text-amber-500" },
};

export function CommandHistory({ commands, loading }: CommandHistoryProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (loading) {
    return (
      <div>
        <h2 className="mb-4 text-xl font-semibold">Command History</h2>
        <div className="space-y-2">
          <Skeleton className="h-10 w-full rounded" />
          <Skeleton className="h-10 w-full rounded" />
          <Skeleton className="h-10 w-full rounded" />
        </div>
      </div>
    );
  }

  if (commands.length === 0) {
    return (
      <div>
        <h2 className="mb-4 text-xl font-semibold">Command History</h2>
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
          <h3 className="text-lg font-semibold">No commands yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Use the text input above to send your first command.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Command History</h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20">Time</TableHead>
            <TableHead>Command</TableHead>
            <TableHead className="w-28">Device</TableHead>
            <TableHead className="w-24">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {commands.map((cmd) => {
            const isExpanded = expandedId === cmd.id;
            const badge = statusBadge[cmd.status];
            return (
              <>
                <TableRow
                  key={cmd.id}
                  className="cursor-pointer"
                  aria-expanded={isExpanded}
                  onClick={() =>
                    setExpandedId(isExpanded ? null : cmd.id)
                  }
                >
                  <TableCell className="font-mono text-xs">
                    {formatTime(cmd.timestamp)}
                  </TableCell>
                  <TableCell>
                    <span className="block max-w-[240px] truncate">
                      {cmd.raw_input ?? "--"}
                    </span>
                  </TableCell>
                  <TableCell>{cmd.device_id ?? "--"}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={badge.className}>
                      {badge.label}
                    </Badge>
                  </TableCell>
                </TableRow>
                {isExpanded && (
                  <TableRow key={`${cmd.id}-detail`}>
                    <TableCell colSpan={4}>
                      <div className="space-y-1 py-2 text-xs text-muted-foreground">
                        {cmd.raw_input && (
                          <p>
                            <span className="font-medium text-foreground">
                              Full command:
                            </span>{" "}
                            {cmd.raw_input}
                          </p>
                        )}
                        {cmd.error_message && (
                          <p>
                            <span className="font-medium text-foreground">
                              Error:
                            </span>{" "}
                            <span className="text-red-500">
                              {cmd.error_message}
                            </span>
                          </p>
                        )}
                        {cmd.error_stage && (
                          <p>
                            <span className="font-medium text-foreground">
                              Stage:
                            </span>{" "}
                            {cmd.error_stage}
                          </p>
                        )}
                        {cmd.duration_ms != null && (
                          <p>
                            <span className="font-medium text-foreground">
                              Duration:
                            </span>{" "}
                            {cmd.duration_ms}ms
                          </p>
                        )}
                        {cmd.llm_debug && (
                          <LlmDebugSection debug={cmd.llm_debug} />
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function LlmDebugSection({ debug }: { debug: LlmDebug }) {
  const decision = debug.decision;
  let summary: JSX.Element;
  let statsRow: JSX.Element | null = null;

  if ("error" in decision) {
    summary = (
      <p>
        <span className="font-medium text-foreground">Decision:</span>{" "}
        <span className="text-red-500">Error: {decision.error}</span>
      </p>
    );
  } else if (decision.tool_used) {
    summary = (
      <p>
        <span className="font-medium text-foreground">Decision:</span>{" "}
        Tool: control_device(device={decision.device_id}, action={decision.action})
      </p>
    );
  } else {
    const snippet = decision.text.slice(0, 80);
    summary = (
      <p>
        <span className="font-medium text-foreground">Decision:</span>{" "}
        No tool -- text: "{snippet}"
      </p>
    );
  }

  if (!("error" in decision) && debug.usage && debug.stop_reason) {
    statsRow = (
      <p>
        <span className="font-medium text-foreground">Stats:</span> input{" "}
        {debug.usage.input_tokens} tok | output {debug.usage.output_tokens} tok |
        stop: {debug.stop_reason}
      </p>
    );
  }

  return (
    <div className="mt-2">
      <p>
        <span className="font-medium text-foreground">LLM Debug:</span>
      </p>
      {summary}
      {statsRow}
      <details className="mt-1">
        <summary className="cursor-pointer text-foreground">
          Devices seen ({debug.devices_seen.length})
        </summary>
        <table className="mt-1 w-full text-xs">
          <thead>
            <tr>
              <th className="text-left">device_id</th>
              <th className="text-left">alias</th>
              <th className="text-left">is_on</th>
            </tr>
          </thead>
          <tbody>
            {debug.devices_seen.map((d) => (
              <tr key={d.device_id}>
                <td className="font-mono">{d.device_id}</td>
                <td>{d.alias}</td>
                <td>{d.is_on ? "on" : "off"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
