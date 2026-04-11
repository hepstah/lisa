import { Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import type { DeviceState } from "../api/types";

interface DeviceCardProps {
  device: DeviceState;
  onToggle: (deviceId: string, action: "turn_on" | "turn_off") => void;
  isToggling?: boolean;
}

export function DeviceCard({ device, onToggle, isToggling }: DeviceCardProps) {
  const disabled = !device.is_reachable || !!isToggling;

  return (
    <Card
      className={device.is_reachable ? undefined : "opacity-60"}
      aria-label={`${device.alias}: ${device.is_on ? "on" : "off"}, ${device.is_reachable ? "reachable" : "unreachable"}`}
    >
      <CardHeader className="flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb className="size-4 text-muted-foreground" />
          <span className="text-sm font-semibold">{device.alias}</span>
        </div>
        <div className={isToggling ? "opacity-50" : undefined}>
          <Switch
            checked={device.is_on}
            onCheckedChange={() =>
              onToggle(device.device_id, device.is_on ? "turn_off" : "turn_on")
            }
            disabled={disabled}
            aria-label={`Toggle ${device.alias}`}
          />
        </div>
      </CardHeader>
      <CardContent className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={device.is_on ? "text-emerald-500" : "text-zinc-500"}
        >
          {device.is_on ? "ON" : "OFF"}
        </Badge>
        {!device.is_reachable && (
          <Badge variant="secondary" className="text-amber-500">
            Unreachable
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
