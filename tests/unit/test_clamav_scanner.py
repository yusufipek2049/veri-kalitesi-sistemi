"""F-04: clamd INSTREAM adapter'ının protokol ve fail-closed davranışı.

Testler gerçek bir TCP soketi üzerinden sahte bir clamd ile konuşur; böylece
protokol çerçeveleme (4 baytlık uzunluk önekleri, sıfır uzunluklu sonlandırıcı)
ve yanıt yorumlama, harici bir servise ihtiyaç duymadan doğrulanır.
"""

from __future__ import annotations

import io
import socket
import threading
from collections.abc import Iterator

import pytest

from veri_kalitesi.issues.clamav import (
    ClamAVScanner,
    ClamAVSettings,
    build_production_scanner,
)

_END_OF_STREAM = b"\x00\x00\x00\x00"


class FakeClamd:
    """Tek bağlantı kabul eden, sabit yanıt döndüren minimal clamd taklidi."""

    def __init__(self, response: bytes, *, close_without_response: bool = False) -> None:
        self.response = response
        self.close_without_response = close_without_response
        self.received_command = b""
        self.received_payload = bytearray()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        try:
            connection, _ = self._server.accept()
        except OSError:
            return
        with connection:
            buffer = bytearray()
            while b"\x00" not in buffer:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer.extend(chunk)
            command, rest = bytes(buffer).split(b"\x00", 1)
            self.received_command = command
            if command == b"zPING":
                connection.sendall(self.response)
                return
            self._drain_stream(connection, bytearray(rest))
            if not self.close_without_response:
                connection.sendall(self.response)

    def _drain_stream(self, connection: socket.socket, buffer: bytearray) -> None:
        while True:
            while len(buffer) < 4:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer.extend(chunk)
            length = int.from_bytes(buffer[:4], "big")
            del buffer[:4]
            if length == 0:
                return
            while len(buffer) < length:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer.extend(chunk)
            self.received_payload.extend(buffer[:length])
            del buffer[:length]

    def close(self) -> None:
        self._server.close()
        self._thread.join(timeout=2)


@pytest.fixture
def clamd_factory() -> Iterator[list[FakeClamd]]:
    servers: list[FakeClamd] = []
    yield servers
    for server in servers:
        server.close()


def _scanner(servers: list[FakeClamd], response: bytes, **kwargs: object) -> ClamAVScanner:
    server = FakeClamd(response, **kwargs)  # type: ignore[arg-type]
    servers.append(server)
    return ClamAVScanner(ClamAVSettings(host="127.0.0.1", port=server.port, timeout_seconds=5.0))


def test_clean_file_is_accepted(clamd_factory: list[FakeClamd]) -> None:
    scanner = _scanner(clamd_factory, b"stream: OK\x00")

    clean, reason = scanner.scan(io.BytesIO(b"harmless evidence"))

    assert clean is True
    assert reason is None
    assert clamd_factory[-1].received_command == b"zINSTREAM"
    assert bytes(clamd_factory[-1].received_payload) == b"harmless evidence"


def test_large_file_is_streamed_in_full(clamd_factory: list[FakeClamd]) -> None:
    payload = b"x" * (64 * 1024 * 2 + 17)
    scanner = _scanner(clamd_factory, b"stream: OK\x00")

    clean, _reason = scanner.scan(io.BytesIO(payload))

    assert clean is True
    assert bytes(clamd_factory[-1].received_payload) == payload


def test_infected_file_is_rejected_with_signature_reason(
    clamd_factory: list[FakeClamd],
) -> None:
    scanner = _scanner(clamd_factory, b"stream: Eicar-Test-Signature FOUND\x00")

    clean, reason = scanner.scan(io.BytesIO(b"payload"))

    assert clean is False
    assert reason == "MALWARE_DETECTED_EICAR_TEST_SIGNATURE"


def test_daemon_error_response_raises_instead_of_passing(
    clamd_factory: list[FakeClamd],
) -> None:
    """Teknik arıza asla 'temiz' sayılmamalı; OSError SCAN_FAILED'a çevrilir."""

    scanner = _scanner(clamd_factory, b"INSTREAM size limit exceeded. ERROR\x00")

    with pytest.raises(OSError, match="scan error"):
        scanner.scan(io.BytesIO(b"payload"))


def test_unknown_response_raises(clamd_factory: list[FakeClamd]) -> None:
    scanner = _scanner(clamd_factory, b"stream: something unexpected\x00")

    with pytest.raises(OSError):
        scanner.scan(io.BytesIO(b"payload"))


def test_connection_closed_without_verdict_raises(clamd_factory: list[FakeClamd]) -> None:
    scanner = _scanner(clamd_factory, b"", close_without_response=True)

    with pytest.raises(OSError, match="without a verdict"):
        scanner.scan(io.BytesIO(b"payload"))


def test_unreachable_daemon_raises_oserror() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    scanner = ClamAVScanner(ClamAVSettings(host="127.0.0.1", port=port, timeout_seconds=2.0))

    with pytest.raises(OSError):
        scanner.scan(io.BytesIO(b"payload"))


def test_missing_unix_socket_raises_oserror(tmp_path) -> None:
    scanner = ClamAVScanner(
        ClamAVSettings(unix_socket=str(tmp_path / "absent.sock"), timeout_seconds=2.0)
    )

    with pytest.raises(OSError):
        scanner.scan(io.BytesIO(b"payload"))


def test_ping_confirms_daemon_availability(clamd_factory: list[FakeClamd]) -> None:
    scanner = _scanner(clamd_factory, b"PONG\x00")

    scanner.ping()

    assert clamd_factory[-1].received_command == b"zPING"


def test_ping_rejects_unexpected_response(clamd_factory: list[FakeClamd]) -> None:
    scanner = _scanner(clamd_factory, b"NOT-PONG\x00")

    with pytest.raises(OSError, match="ping response"):
        scanner.ping()


# ----------------------------------------------------------------------
# Yapilandirma
# ----------------------------------------------------------------------


def test_settings_require_exactly_one_transport() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ClamAVSettings()
    with pytest.raises(ValueError, match="Exactly one"):
        ClamAVSettings(host="clamav", unix_socket="/var/run/clamd.sock")


def test_settings_validate_port_and_timeout() -> None:
    with pytest.raises(ValueError, match="port"):
        ClamAVSettings(host="clamav", port=0)
    with pytest.raises(ValueError, match="timeout"):
        ClamAVSettings(host="clamav", timeout_seconds=0)


def test_unconfigured_environment_yields_no_scanner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yapılandırma yoksa fail-closed davranış korunur."""

    monkeypatch.delenv("DQ_CLAMAV_HOST", raising=False)
    monkeypatch.delenv("DQ_CLAMAV_SOCKET", raising=False)

    assert ClamAVSettings.from_environment() is None
    assert build_production_scanner() is None


def test_environment_configuration_builds_scanner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DQ_CLAMAV_HOST", "clamav.internal")
    monkeypatch.setenv("DQ_CLAMAV_PORT", "3311")
    monkeypatch.setenv("DQ_CLAMAV_TIMEOUT_SECONDS", "12.5")
    monkeypatch.delenv("DQ_CLAMAV_SOCKET", raising=False)

    scanner = build_production_scanner()

    assert scanner is not None
    assert scanner.settings.host == "clamav.internal"
    assert scanner.settings.port == 3311
    assert scanner.settings.timeout_seconds == 12.5
    assert scanner.settings.describe() == "tcp:clamav.internal:3311"


def test_unix_socket_configuration_is_described(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DQ_CLAMAV_HOST", raising=False)
    monkeypatch.setenv("DQ_CLAMAV_SOCKET", "/var/run/clamav/clamd.ctl")

    settings = ClamAVSettings.from_environment()

    assert settings is not None
    assert settings.describe() == "unix:/var/run/clamav/clamd.ctl"
