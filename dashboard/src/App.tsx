import { useState, useCallback } from "react";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { StatusBar } from "./components/StatusBar";
import { DeviceList } from "./components/DeviceList";
import { CommandHistory } from "./components/CommandHistory";
import { TextCommand } from "./components/TextCommand";
import { DeviceConfig } from "./components/DeviceConfig";
import { useWebSocket } from "./hooks/useWebSocket";
import { useDevices } from "./hooks/useDevices";
import { useCommands } from "./hooks/useCommands";
import { usePipelineStatus } from "./hooks/usePipelineStatus";
import { controlDevice, sendTextCommand } from "./api/client";
import type { WsEvent } from "./api/types";

function App() {
  const [configOpen, setConfigOpen] = useState(false);

  const {
    devices,
    loading: devicesLoading,
    refresh: refreshDevices,
    handleWsEvent: handleDeviceWsEvent,
  } = useDevices();

  const {
    commands,
    loading: commandsLoading,
    handleWsEvent: handleCommandWsEvent,
  } = useCommands();

  const {
    status: pipelineStatus,
    handleWsEvent: handlePipelineWsEvent,
  } = usePipelineStatus();

  const handleWsMessage = useCallback(
    (event: WsEvent) => {
      handleDeviceWsEvent(event);
      handleCommandWsEvent(event);
      handlePipelineWsEvent(event);
    },
    [handleDeviceWsEvent, handleCommandWsEvent, handlePipelineWsEvent],
  );

  const { status: wsStatus } = useWebSocket(handleWsMessage);

  const handleToggle = async (
    deviceId: string,
    action: "turn_on" | "turn_off",
  ) => {
    try {
      await controlDevice(deviceId, { action });
      const device = devices.find((d) => d.device_id === deviceId);
      toast.success(
        `${device?.alias ?? deviceId} turned ${action === "turn_on" ? "on" : "off"}`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Command failed");
    }
  };

  const handleTextCommand = async (text: string) => {
    try {
      const result = await sendTextCommand({ text });
      if (result.status === "success") {
        toast.success("Command executed");
      } else {
        toast.error(
          (result.error_message as string) ?? "Command failed",
        );
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Command failed");
      throw err; // Re-throw so TextCommand keeps the input text
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground dark">
      <StatusBar status={wsStatus} pipelineStatus={pipelineStatus} />

      <main className="container mx-auto px-4 py-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Devices section -- 2/3 width on desktop */}
          <div className="lg:col-span-2">
            <DeviceList
              devices={devices}
              loading={devicesLoading}
              onToggle={handleToggle}
              onAddDevice={() => setConfigOpen(true)}
            />
          </div>

          {/* Command panel -- 1/3 width on desktop */}
          <div className="space-y-6">
            <TextCommand
              onSend={handleTextCommand}
              disabled={wsStatus !== "connected"}
            />
            <CommandHistory commands={commands} loading={commandsLoading} />
          </div>
        </div>
      </main>

      <DeviceConfig
        open={configOpen}
        onOpenChange={setConfigOpen}
        onDeviceAdded={refreshDevices}
      />

      <Toaster />
    </div>
  );
}

export default App;
