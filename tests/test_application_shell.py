"""Tests for application-shell state."""

from expedite.pages.application_shell import ApplicationStatus


def test_application_status_updates_message_and_detail() -> None:
    status = ApplicationStatus()

    status.update("Saved", "receipt.png")

    assert status.message == "Saved"
    assert status.detail == "receipt.png"


def test_application_status_retains_detail_when_update_omits_it() -> None:
    status = ApplicationStatus(detail="Current event")

    status.update("Ready")

    assert status.message == "Ready"
    assert status.detail == "Current event"
