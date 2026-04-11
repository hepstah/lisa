import { useState, useEffect, useCallback } from "react";
import type { DeviceState, WsEvent } from "../api/types";
import { fetchDevices } from "../api/client";

export function useDevices() {
  const [devices, setDevices] = useState<DeviceState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial fetch
  useEffect(() => {
    fetchDevices()
      .then((data) => {
        setDevices(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch devices");
        setLoading(false);
      });
  }, []);

  // Handle WebSocket device_state events -- called by parent component
  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === "device_state") {
      setDevices((prev) => {
        const exists = prev.some((d) => d.device_id === event.device_id);
        if (exists) {
          return prev.map((d) =>
            d.device_id === event.device_id
              ? { ...d, is_on: event.is_on, is_reachable: event.is_reachable, alias: event.alias }
              : d,
          );
        }
        // New device appeared via WebSocket
        return [
          ...prev,
          {
            device_id: event.device_id,
            alias: event.alias,
            is_on: event.is_on,
            is_reachable: event.is_reachable,
          },
        ];
      });
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDevices();
      setDevices(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to refresh");
    } finally {
      setLoading(false);
    }
  }, []);

  return { devices, loading, error, refresh, handleWsEvent };
}
