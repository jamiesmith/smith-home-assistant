"""Support for Broadlink devices."""
import socket
import threading
import random
import time
from typing import Generator, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .exceptions import check_error, exception
from .protocol import Datetime

HelloResponse = Tuple[int, Tuple[str, int], str, str, bool]


def scan(
    timeout: int = 10,
    local_ip_address: str = None,
    discover_ip_address: str = "255.255.255.255",
    discover_ip_port: int = 80,
) -> Generator[HelloResponse, None, None]:
    """Broadcast a hello message and yield responses."""
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    if local_ip_address:
        conn.bind((local_ip_address, 0))
        port = conn.getsockname()[1]
    else:
        local_ip_address = "0.0.0.0"
        port = 0

    packet = bytearray(0x30)
    packet[0x08:0x14] = Datetime.pack(Datetime.now())
    packet[0x18:0x1C] = socket.inet_aton(local_ip_address)[::-1]
    packet[0x1C:0x1E] = port.to_bytes(2, "little")
    packet[0x26] = 6

    checksum = sum(packet, 0xBEAF) & 0xFFFF
    packet[0x20:0x22] = checksum.to_bytes(2, "little")

    start_time = time.time()
    discovered = []

    try:
        while (time.time() - start_time) < timeout:
            time_left = timeout - (time.time() - start_time)
            conn.settimeout(min(1, time_left))
            conn.sendto(packet, (discover_ip_address, discover_ip_port))

            while True:
                try:
                    resp, host = conn.recvfrom(1024)
                except socket.timeout:
                    break

                devtype = resp[0x34] | resp[0x35] << 8
                mac = resp[0x3A:0x40][::-1]

                if (host, mac, devtype) in discovered:
                    continue
                discovered.append((host, mac, devtype))

                name = resp[0x40:].split(b"\x00")[0].decode()
                is_locked = bool(resp[-1])
                yield devtype, host, mac, name, is_locked
    finally:
        conn.close()


def ping(address: str, port: int = 80) -> None:
    """Send a ping packet to an address.

    This packet feeds the watchdog timer of firmwares >= v53.
    Useful to prevent reboots when the cloud cannot be reached.
    It must be sent every 2 minutes in such cases.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        packet = bytearray(0x30)
        packet[0x26] = 1
        conn.sendto(packet, (address, port))


class device:
    """Controls a Broadlink device."""

    TYPE = "Unknown"

    __INIT_KEY = "097628343fe99e23765c1513accf8b02"
    __INIT_VECT = "562e17996d093d28ddb3ba695a2e6f58"

    def __init__(
        self,
        host: Tuple[str, int],
        mac: Union[bytes, str],
        devtype: int,
        timeout: int = 10,
        name: str = "",
        model: str = "",
        manufacturer: str = "",
        is_locked: bool = False,
    ) -> None:
        """Initialize the controller."""
        self.host = host
        self.mac = bytes.fromhex(mac) if isinstance(mac, str) else mac
        self.devtype = devtype
        self.timeout = timeout
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.is_locked = is_locked
        self.count = random.randint(0x8000, 0xFFFF)
        self.iv = bytes.fromhex(self.__INIT_VECT)
        self.id = 0
        self.type = self.TYPE  # For backwards compatibility.
        self.lock = threading.Lock()

        self.aes = None
        self.update_aes(bytes.fromhex(self.__INIT_KEY))

    def __repr__(self) -> str:
        """Return a formal representation of the device."""
        return (
            "%s.%s(%s, mac=%r, devtype=%r, timeout=%r, name=%r, "
            "model=%r, manufacturer=%r, is_locked=%r)"
        ) % (
            self.__class__.__module__,
            self.__class__.__qualname__,
            self.host,
            self.mac,
            self.devtype,
            self.timeout,
            self.name,
            self.model,
            self.manufacturer,
            self.is_locked,
        )

    def __str__(self) -> str:
        """Return a readable representation of the device."""
        model = []
        if self.manufacturer:
            model.append(self.manufacturer)
        if self.model:
            model.append(self.model)
        model.append(hex(self.devtype))
        model = " ".join(model)

        info = []
        info.append(model)
        info.append(f"{self.host[0]}:{self.host[1]}")
        info.append(":".join(format(x, "02x") for x in self.mac).upper())
        info = " / ".join(info)
        return "%s (%s)" % (self.name or "Unknown", info)

    def update_aes(self, key: bytes) -> None:
        """Update AES."""
        self.aes = Cipher(
            algorithms.AES(bytes(key)), modes.CBC(self.iv), backend=default_backend()
        )

    def encrypt(self, payload: bytes) -> bytes:
        """Encrypt the payload."""
        encryptor = self.aes.encryptor()
        return encryptor.update(bytes(payload)) + encryptor.finalize()

    def decrypt(self, payload: bytes) -> bytes:
        """Decrypt the payload."""
        decryptor = self.aes.decryptor()
        return decryptor.update(bytes(payload)) + decryptor.finalize()

    def auth(self) -> bool:
        """Authenticate to the device."""
        self.id = 0
        self.update_aes(bytes.fromhex(self.__INIT_KEY))

        payload = bytearray(0x50)
        payload[0x04:0x14] = [0x31]*16
        payload[0x1E] = 0x01
        payload[0x2D] = 0x01
        payload[0x30:0x36] = "Test 1".encode()

        response = self.send_packet(0x65, payload)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])

        key = payload[0x04:0x14]
        if len(key) % 16 != 0:
            return False

        self.id = int.from_bytes(payload[:0x4], "little")
        self.update_aes(key)
        return True

    def hello(self, local_ip_address=None) -> bool:
        """Send a hello message to the device.

        Device information is checked before updating name and lock status.
        """
        responses = scan(
            timeout=self.timeout,
            local_ip_address=local_ip_address,
            discover_ip_address=self.host[0],
            discover_ip_port=self.host[1],
        )
        try:
            devtype, host, mac, name, is_locked = next(responses)
        except StopIteration:
            raise exception(-4000)  # Network timeout.

        if (devtype, host, mac) != (self.devtype, self.host, self.mac):
            raise exception(-2040)  # Device information is not intact.

        self.name = name
        self.is_locked = is_locked
        return True

    def ping(self) -> None:
        """Ping the device.

        This packet feeds the watchdog timer of firmwares >= v53.
        Useful to prevent reboots when the cloud cannot be reached.
        It must be sent every 2 minutes in such cases.
        """
        ping(self.host[0], port=self.host[1])

    def get_fwversion(self) -> int:
        """Get firmware version."""
        packet = bytearray([0x68])
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        payload = self.decrypt(response[0x38:])
        return payload[0x4] | payload[0x5] << 8

    def set_name(self, name: str) -> None:
        """Set device name."""
        packet = bytearray(4)
        packet += name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = self.is_locked
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        self.name = name

    def set_lock(self, state: bool) -> None:
        """Lock/unlock the device."""
        packet = bytearray(4)
        packet += self.name.encode("utf-8")
        packet += bytearray(0x50 - len(packet))
        packet[0x43] = bool(state)
        response = self.send_packet(0x6A, packet)
        check_error(response[0x22:0x24])
        self.is_locked = bool(state)

    def get_type(self) -> str:
        """Return device type."""
        return self.type

    def send_packet(self, packet_type: int, payload: bytes) -> bytes:
        """Send a packet to the device."""
        self.count = ((self.count + 1) | 0x8000) & 0xFFFF
        packet = bytearray(0x38)
        packet[0x00:0x08] = bytes.fromhex("5aa5aa555aa5aa55")
        packet[0x24:0x26] = self.devtype.to_bytes(2, "little")
        packet[0x26:0x28] = packet_type.to_bytes(2, "little")
        packet[0x28:0x2a] = self.count.to_bytes(2, "little")
        packet[0x2a:0x30] = self.mac[::-1]
        packet[0x30:0x34] = self.id.to_bytes(4, "little")

        p_checksum = sum(payload, 0xBEAF) & 0xFFFF
        packet[0x34:0x36] = p_checksum.to_bytes(2, "little")

        padding = (16 - len(payload)) % 16
        payload = self.encrypt(payload + bytes(padding))
        packet.extend(payload)

        checksum = sum(packet, 0xBEAF) & 0xFFFF
        packet[0x20:0x22] = checksum.to_bytes(2, "little")

        with self.lock and socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
            timeout = self.timeout
            start_time = time.time()

            while True:
                time_left = timeout - (time.time() - start_time)
                conn.settimeout(min(1, time_left))
                conn.sendto(packet, self.host)

                try:
                    resp = conn.recvfrom(2048)[0]
                    break
                except socket.timeout:
                    if (time.time() - start_time) > timeout:
                        raise exception(-4000)  # Network timeout.

        if len(resp) < 0x30:
            raise exception(-4007)  # Length error.

        checksum = int.from_bytes(resp[0x20:0x22], "little")
        if sum(resp, 0xBEAF) - sum(resp[0x20:0x22]) & 0xFFFF != checksum:
            raise exception(-4008)  # Checksum error.

        return resp
