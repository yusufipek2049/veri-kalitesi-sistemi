"""clamd üzerinden konuşan production malware scanner adapter'ı.

F-04: Production composition ``scanner=None`` bağlıyordu; bu yüzden yüklenen
her kanıt dosyası ``SCAN_FAILED`` oluyor ve hiçbir zaman indirilebilir hale
gelmiyordu. Davranış fail-closed olduğu için güvenlik açığı değildi, eksik
production kabiliyetiydi.

Adapter ``MalwareScanner`` protokolünü clamd'in INSTREAM komutuyla gerçekler:
dosya clamd'e akıtılır, karar tek bir yanıt satırından okunur. Ağ/protokol
hataları ``OSError`` olarak yükselir; ``IssueEvidenceFileService.scan`` bunu
``SCAN_FAILED`` durumuna çevirir, yani teknik arıza asla "temiz" sayılmaz.

Yapılandırma tamamen ortam değişkeniyle yapılır ve hiçbiri set edilmemişse
fabrika ``None`` döner: yapılandırılmamış kurulum eski fail-closed davranışını
korur.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import BinaryIO

#: clamd INSTREAM sözleşmesi: her yığın 4 baytlık big-endian uzunlukla
#: öncelenir, sıfır uzunluk akışın sonunu bildirir.
_CHUNK_SIZE = 64 * 1024
_END_OF_STREAM = b"\x00\x00\x00\x00"
_MAX_RESPONSE_BYTES = 4096


@dataclass(frozen=True)
class ClamAVSettings:
    """clamd bağlantı ayarları; TCP veya unix socket'ten tam biri seçilir."""

    host: str | None = None
    port: int = 3310
    unix_socket: str | None = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if bool(self.host) == bool(self.unix_socket):
            raise ValueError("Exactly one of ClamAV host or unix socket must be configured.")
        if self.timeout_seconds <= 0:
            raise ValueError("ClamAV timeout must be positive.")
        if self.host and not 0 < self.port < 65536:
            raise ValueError("ClamAV port is invalid.")

    @classmethod
    def from_environment(cls) -> "ClamAVSettings | None":
        """Ortamdan ayarları okur; yapılandırma yoksa ``None`` döner."""

        host = os.environ.get("DQ_CLAMAV_HOST", "").strip() or None
        unix_socket = os.environ.get("DQ_CLAMAV_SOCKET", "").strip() or None
        if host is None and unix_socket is None:
            return None
        return cls(
            host=host,
            port=int(os.environ.get("DQ_CLAMAV_PORT", "3310")),
            unix_socket=unix_socket,
            timeout_seconds=float(os.environ.get("DQ_CLAMAV_TIMEOUT_SECONDS", "30")),
        )

    def describe(self) -> str:
        if self.unix_socket:
            return f"unix:{self.unix_socket}"
        return f"tcp:{self.host}:{self.port}"


class ClamAVScanner:
    """``MalwareScanner`` protokolünün clamd INSTREAM gerçeklemesi."""

    def __init__(self, settings: ClamAVSettings) -> None:
        self.settings = settings

    def ping(self) -> None:
        """clamd erişilebilirliğini doğrular; readiness kontrolünde kullanılır."""

        with self._connect() as connection:
            connection.sendall(b"zPING\x00")
            response = self._read_response(connection)
        if response != "PONG":
            raise OSError(f"ClamAV daemon returned an unexpected ping response: {response!r}")

    def scan(self, source: BinaryIO) -> tuple[bool, str | None]:
        with self._connect() as connection:
            connection.sendall(b"zINSTREAM\x00")
            while chunk := source.read(_CHUNK_SIZE):
                connection.sendall(len(chunk).to_bytes(4, "big") + chunk)
            connection.sendall(_END_OF_STREAM)
            response = self._read_response(connection)
        return _interpret_response(response)

    def _connect(self) -> socket.socket:
        settings = self.settings
        if settings.unix_socket:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.settimeout(settings.timeout_seconds)
            connection.connect(settings.unix_socket)
            return connection
        assert settings.host is not None  # __post_init__ garantiler
        return socket.create_connection(
            (settings.host, settings.port), timeout=settings.timeout_seconds
        )

    def _read_response(self, connection: socket.socket) -> str:
        buffer = bytearray()
        while b"\x00" not in buffer:
            chunk = connection.recv(_MAX_RESPONSE_BYTES)
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > _MAX_RESPONSE_BYTES:
                raise OSError("ClamAV daemon response exceeded the expected size.")
        return bytes(buffer).split(b"\x00", 1)[0].decode("utf-8", "replace").strip()


def _interpret_response(response: str) -> tuple[bool, str | None]:
    """clamd yanıtını (temiz mi, gerekçe kodu) çiftine çevirir.

    Bilinmeyen ya da ERROR yanıtı asla "temiz" sayılmaz: ``OSError`` yükselir
    ve çağıran katman dosyayı ``SCAN_FAILED`` olarak işaretler.
    """

    if not response:
        raise OSError("ClamAV daemon closed the connection without a verdict.")
    if response.endswith("OK") and "FOUND" not in response:
        return True, None
    if response.endswith("FOUND"):
        signature = response.rsplit(":", 1)[-1].removesuffix("FOUND").strip()
        return False, _reason_code(signature)
    raise OSError(f"ClamAV daemon reported a scan error: {response!r}")


def _reason_code(signature: str) -> str:
    """İmza adını audit ve API için güvenli, sınırlı bir gerekçe koduna indirger."""

    normalized = "".join(
        character if character.isalnum() else "_" for character in signature.upper()
    ).strip("_")
    if not normalized:
        return "MALWARE_DETECTED"
    return f"MALWARE_DETECTED_{normalized}"[:100]


def build_production_scanner() -> ClamAVScanner | None:
    """Ortam yapılandırılmışsa scanner üretir, aksi halde ``None`` döner."""

    settings = ClamAVSettings.from_environment()
    if settings is None:
        return None
    return ClamAVScanner(settings)
