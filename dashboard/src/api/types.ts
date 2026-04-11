// Device types -- mirrors backend DeviceStateResponse
export interface DeviceState {
  device_id: string;
  alias: string;
  is_on: boolean;
  is_reachable: boolean;
}

// Command types -- mirrors backend CommandRecord
export interface CommandRecord {
  id: number;
  timestamp: string;
  source: string;
  raw_input: string | null;
  device_id: string | null;
  action: string | null;
  status: "success" | "error" | "rejected";
  error_message: string | null;
  error_stage: string | null;
  duration_ms: number | null;
}

// Request types
export interface DeviceControlRequest {
  action: "turn_on" | "turn_off";
}

export interface TextCommandRequest {
  text: string;
  source?: string;
}

export interface DeviceConfigRequest {
  host: string;
  alias: string;
  device_type?: string;
  kasa_username?: string;
  kasa_password?: string;
}

// Pipeline status -- voice assistant lifecycle states
export type PipelineState = "listening" | "processing" | "responding" | "error" | "offline";

// WebSocket event types -- from Research WebSocket Event Format
export type WsEvent =
  | { type: "device_state"; device_id: string; alias: string; is_on: boolean; is_reachable: boolean }
  | { type: "command_logged"; command: CommandRecord }
  | { type: "connection_status"; status: "connected" | "device_unreachable" }
  | { type: "pipeline_status"; status: PipelineState };

export type WsStatus = "connecting" | "connected" | "disconnected";
