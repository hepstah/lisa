import { useState, type FormEvent } from "react";
import { Loader2, Search, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { discoverDevices, addDevice } from "../api/client";
import type { DeviceState } from "../api/types";

interface DeviceConfigProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeviceAdded: () => void;
}

export function DeviceConfig({
  open,
  onOpenChange,
  onDeviceAdded,
}: DeviceConfigProps) {
  // Discovery state
  const [discovering, setDiscovering] = useState(false);
  const [discovered, setDiscovered] = useState<DeviceState[] | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  // Manual form state
  const [host, setHost] = useState("");
  const [alias, setAlias] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  function resetState() {
    setDiscovering(false);
    setDiscovered(null);
    setDiscoveryError(null);
    setHost("");
    setAlias("");
    setUsername("");
    setPassword("");
    setSaving(false);
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) resetState();
    onOpenChange(nextOpen);
  }

  async function handleDiscover() {
    setDiscovering(true);
    setDiscoveryError(null);
    setDiscovered(null);
    try {
      const devices = await discoverDevices();
      setDiscovered(devices);
    } catch (err) {
      setDiscoveryError(
        err instanceof Error
          ? `Discovery failed: ${err.message}. You can add a device manually below.`
          : "Discovery failed. You can add a device manually below.",
      );
    } finally {
      setDiscovering(false);
    }
  }

  async function handleAddDiscovered(device: DeviceState) {
    try {
      await addDevice({ host: device.device_id, alias: device.alias });
      onDeviceAdded();
      handleOpenChange(false);
    } catch {
      // Errors handled by toast in parent
    }
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!host.trim()) return;

    setSaving(true);
    try {
      await addDevice({
        host: host.trim(),
        alias: alias.trim() || host.trim(),
        ...(username.trim() && { kasa_username: username.trim() }),
        ...(password && { kasa_password: password }),
      });
      onDeviceAdded();
      handleOpenChange(false);
    } catch {
      // Errors handled by toast in parent
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Device</DialogTitle>
          <DialogDescription>
            How would you like to add a device?
          </DialogDescription>
        </DialogHeader>

        {/* Discovery section */}
        <div className="space-y-3">
          <Button
            type="button"
            onClick={handleDiscover}
            disabled={discovering}
            className="w-full"
          >
            {discovering ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Search className="size-4" />
                Discover Devices
              </>
            )}
          </Button>

          {discoveryError && (
            <p className="text-sm text-muted-foreground">{discoveryError}</p>
          )}

          {discovered && discovered.length === 0 && !discoveryError && (
            <p className="text-sm text-muted-foreground">
              No devices found on your network. Check that devices are powered
              on, or add one manually below.
            </p>
          )}

          {discovered && discovered.length > 0 && (
            <div className="space-y-2">
              {discovered.map((device) => (
                <div
                  key={device.device_id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <span className="text-sm font-medium">{device.alias}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAddDiscovered(device)}
                  >
                    <Plus className="size-3" />
                    Add
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="relative">
          <Separator />
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-popover px-2 text-xs text-muted-foreground">
            or add manually
          </span>
        </div>

        {/* Manual form */}
        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="device-host">Device IP Address</Label>
            <Input
              id="device-host"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="192.168.1.___"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="device-alias">Device Name</Label>
            <Input
              id="device-alias"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Bedroom Lamp"
            />
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium">
              TP-Link Credentials (if required)
            </p>
            <div className="space-y-2">
              <Label htmlFor="device-username">Username</Label>
              <Input
                id="device-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="device-password">Password</Label>
              <Input
                id="device-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!host.trim() || saving}>
              {saving && <Loader2 className="size-4 animate-spin" />}
              Save Device
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
