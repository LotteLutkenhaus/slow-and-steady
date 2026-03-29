import logging
from datetime import datetime, timezone

from models import DeviceInfo, DeviceRecord, SessionData, DeviceNameRow, TrainingSessionRow

log = logging.getLogger(__name__)


def _assign_circuits(devices: list[DeviceRecord]) -> dict[str, int]:
    """
    Map each circuit id to a circuit number (1 or 2).

    Within a training session, devices belong to either circuit 1 or circuit 2 (as for Milon,
    you're supposed to complete the entire training circuit twice).

    Devices are sorted by their timestamp and actids are mapped to a circuit number based on the
    order in which they are first encountered.
    """
    sorted_devices = sorted(devices, key=lambda d: d.timestamp)
    actid_to_circuit: dict[str, int] = {}

    for device in sorted_devices:
        if device.actid and device.actid not in actid_to_circuit:
            actid_to_circuit[device.actid] = len(actid_to_circuit) + 1

    return actid_to_circuit


def parse_device_names(catalogue: dict[int, DeviceInfo]) -> list[DeviceNameRow]:
    return [
        DeviceNameRow(
            device_id=device_id,
            name=info.name,
            device_type=info.device_type,
            muscle_group=info.muscle_group,
        )
        for device_id, info in catalogue.items()
    ]


def parse_sessions(
    sessions: list[SessionData],
    catalogue: dict[int, DeviceInfo],
) -> list[TrainingSessionRow]:
    """
    Flatten all sessions into a list of TrainingSessionRow dataclasses.
    Device name and muscle group are enriched from the catalogue.
    """
    rows: list[TrainingSessionRow] = []

    for session in sessions:
        session_ts = datetime.fromtimestamp(session.training.timestamp, tz=timezone.utc)
        actid_to_circuit = _assign_circuits(session.devices)

        for device in session.devices:
            info = catalogue.get(device.device_id)
            circuit = actid_to_circuit.get(device.actid or "", 1)

            rows.append(TrainingSessionRow(
                session_ts=session_ts,
                iteration=session.training.iteration,
                device_id=device.device_id,
                device_name=info.name if info else None,
                muscle_group=info.muscle_group if info else None,
                circuit=circuit,
                concentric_weight=device.concentric_weight,
                eccentric_weight=device.eccentric_weight,
                quality_score=device.quality_score,
                reps=device.reps,
                actid=device.actid,
                ngid=device.ngid,
            ))

    log.info("Parsed %d row(s) from %d session(s)", len(rows), len(sessions))
    return rows