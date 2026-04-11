import { useState, useCallback, useEffect, useRef } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DeviceCard } from "./DeviceCard";
import type { DeviceState, WsEvent } from "../api/types";

interface DeviceListProps {
  devices: DeviceState[];
  loading: boolean;
  onToggle: (deviceId: string, action: "turn_on" | "turn_off") => void;
  onAddDevice: () => void;
  onWsEvent?: (cb: (e: WsEvent) => void) => void;
}

export function DeviceList({
  devices,
  loading,
  onToggle,
  onAddDevice,
  onWsEvent,
}: DeviceListProps) {
  const [togglingIds, setTogglingIds] = useState<Set<string>>(new Set());
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  // Clear toggling state on WS device_state event or after timeout
  const clearToggling = useCallback((deviceId: string) => {
    setTogglingIds((prev) => {
      const next = new Set(prev);
      next.delete(deviceId);
      return next;
    });
    const timer = timeoutsRef.current.get(deviceId);
    if (timer) {
      clearTimeout(timer);
      timeoutsRef.current.delete(deviceId);
    }
  }, []);

  // Listen for WS events to clear toggling state
  useEffect(() => {
    if (!onWsEvent) return;
    onWsEvent((event: WsEvent) => {
      if (event.type === "device_state") {
        clearToggling(event.device_id);
      }
    });
  }, [onWsEvent, clearToggling]);

  const handleToggle = useCallback(
    (deviceId: string, action: "turn_on" | "turn_off") => {
      setTogglingIds((prev) => new Set(prev).add(deviceId));
      // Timeout fallback to clear toggling state after 5s
      const timer = setTimeout(() => clearToggling(deviceId), 5000);
      timeoutsRef.current.set(deviceId, timer);
      onToggle(deviceId, action);
    },
    [onToggle, clearToggling],
  );

  // Cleanup timeouts on unmount
  useEffect(() => {
    const timers = timeoutsRef.current;
    return () => {
      for (const timer of timers.values()) clearTimeout(timer);
    };
  }, []);

  if (loading) {
    return (
      <div>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold">Devices</h2>
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-32 rounded-lg" />
          <Skeleton className="h-32 rounded-lg" />
        </div>
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold">Devices</h2>
        </div>
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
          <h3 className="text-lg font-semibold">No devices yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Add your first smart device to get started.
          </p>
          <Button variant="outline" className="mt-4" onClick={onAddDevice}>
            <Plus className="size-4" />
            Add Device
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Devices</h2>
        <Button variant="outline" onClick={onAddDevice}>
          <Plus className="size-4" />
          Add Device
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {devices.map((device) => (
          <DeviceCard
            key={device.device_id}
            device={device}
            onToggle={handleToggle}
            isToggling={togglingIds.has(device.device_id)}
          />
        ))}
      </div>
    </div>
  );
}
