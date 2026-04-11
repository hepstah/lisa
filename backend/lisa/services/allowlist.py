"""Action allowlist validation. Per DEVICE-02: validate all commands against
known devices and supported actions before execution."""

ALLOWED_ACTIONS = {"turn_on", "turn_off"}


def validate_action(
    action: str, device_id: str, known_device_ids: set[str]
) -> tuple[bool, str]:
    """Validate a command against the allowlist.

    Returns (is_valid, rejection_reason).
    """
    if action not in ALLOWED_ACTIONS:
        return False, f"Action '{action}' is not allowed. Supported: {', '.join(sorted(ALLOWED_ACTIONS))}"
    if device_id not in known_device_ids:
        return False, f"Device '{device_id}' is not a known device"
    return True, ""
