"""Tests for allowlist validation -- Task 2 TDD."""
import pytest

from lisa.services.allowlist import validate_action


class TestAllowlist:
    def test_valid_turn_on_known_device(self):
        known = {"fake-lamp-1", "fake-plug-1"}
        valid, reason = validate_action("turn_on", "fake-lamp-1", known)
        assert valid is True
        assert reason == ""

    def test_valid_turn_off_known_device(self):
        known = {"fake-lamp-1", "fake-plug-1"}
        valid, reason = validate_action("turn_off", "fake-plug-1", known)
        assert valid is True
        assert reason == ""

    def test_rejects_unknown_action(self):
        known = {"fake-lamp-1"}
        valid, reason = validate_action("reboot", "fake-lamp-1", known)
        assert valid is False
        assert "reboot" in reason
        assert "not allowed" in reason

    def test_rejects_unknown_device(self):
        known = {"fake-lamp-1"}
        valid, reason = validate_action("turn_on", "unknown-device", known)
        assert valid is False
        assert "unknown-device" in reason

    def test_rejects_empty_action(self):
        known = {"fake-lamp-1"}
        valid, reason = validate_action("", "fake-lamp-1", known)
        assert valid is False

    def test_rejects_empty_device_set(self):
        valid, reason = validate_action("turn_on", "fake-lamp-1", set())
        assert valid is False
