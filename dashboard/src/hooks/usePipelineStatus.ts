import { useState, useCallback } from "react";
import type { WsEvent, PipelineState } from "../api/types";

export function usePipelineStatus() {
  const [status, setStatus] = useState<PipelineState>("offline");

  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === "pipeline_status") {
      setStatus(event.status);
    }
  }, []);

  const reset = useCallback(() => setStatus("offline"), []);

  return { status, handleWsEvent, reset };
}
