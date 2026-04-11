import type {
  DeviceState,
  CommandRecord,
  DeviceControlRequest,
  TextCommandRequest,
  DeviceConfigRequest,
} from "./types";

const BASE = ""; // Vite proxy handles /api -> http://localhost:8000

export async function fetchDevices(): Promise<DeviceState[]> {
  const res = await fetch(`${BASE}/api/devices/`);
  if (!res.ok) throw new Error(`Failed to fetch devices: ${res.status}`);
  return res.json();
}

export async function fetchDeviceState(
  deviceId: string,
): Promise<DeviceState> {
  const res = await fetch(
    `${BASE}/api/devices/${encodeURIComponent(deviceId)}`,
  );
  if (!res.ok) throw new Error(`Failed to fetch device: ${res.status}`);
  return res.json();
}

export async function controlDevice(
  deviceId: string,
  req: DeviceControlRequest,
): Promise<Record<string, unknown>> {
  const res = await fetch(
    `${BASE}/api/devices/${encodeURIComponent(deviceId)}/control`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    },
  );
  if (!res.ok) throw new Error(`Failed to control device: ${res.status}`);
  return res.json();
}

export async function discoverDevices(): Promise<DeviceState[]> {
  const res = await fetch(`${BASE}/api/devices/discover`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to discover devices: ${res.status}`);
  return res.json();
}

export async function addDevice(
  req: DeviceConfigRequest,
): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/api/devices/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Failed to add device: ${res.status}`);
  return res.json();
}

export async function sendTextCommand(
  req: TextCommandRequest,
): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/api/commands/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...req, source: req.source ?? "dashboard" }),
  });
  if (!res.ok) throw new Error(`Failed to send command: ${res.status}`);
  return res.json();
}

export async function fetchCommandHistory(
  limit = 50,
  offset = 0,
): Promise<CommandRecord[]> {
  const res = await fetch(
    `${BASE}/api/commands/history?limit=${limit}&offset=${offset}`,
  );
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`);
  return res.json();
}
