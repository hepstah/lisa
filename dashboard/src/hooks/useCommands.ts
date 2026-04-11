import { useState, useEffect, useCallback } from "react";
import type { CommandRecord, WsEvent } from "../api/types";
import { fetchCommandHistory } from "../api/client";

export function useCommands() {
  const [commands, setCommands] = useState<CommandRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial fetch
  useEffect(() => {
    fetchCommandHistory()
      .then((data) => {
        setCommands(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch command history");
        setLoading(false);
      });
  }, []);

  // Handle WebSocket command_logged events -- called by parent component
  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === "command_logged") {
      setCommands((prev) => [event.command, ...prev]);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchCommandHistory();
      setCommands(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to refresh");
    } finally {
      setLoading(false);
    }
  }, []);

  return { commands, loading, error, refresh, handleWsEvent };
}
