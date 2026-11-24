import binascii

import pytest

from adapters import get_adapter
from adapters import serial_cobs_adapter
from adapters.serial_cobs_adapter import SerialCOBSAdapter, cobs_decode


def cobs_encode(data: bytes) -> bytes:
    out = bytearray([0])
    code_at, code = 0, 1
    for b in data:
        if b == 0:
            out[code_at] = code
            code_at, code = len(out), 1
            out.append(0)
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_at] = code
                code_at, code = len(out), 1
                out.append(0)
    out[code_at] = code
    return bytes(out)


def with_crc(body: bytes) -> bytes:
    c = binascii.crc_hqx(body, 0xFFFF)
    return body + bytes([c & 0xFF, c >> 8])


class FakeSerial:
    """Answers each write with the next canned reply; bytes before it are stale."""

    def __init__(self, replies=(), stale=b"", **kwargs):
        self.replies = list(replies)
        self.rx = bytearray(stale)
        self.written = []
        self.timeout = kwargs.get("timeout")
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self.rx)

    def reset_input_buffer(self):
        self.rx.clear()

    def write(self, data):
        self.written.append(bytes(data))
        if self.replies:
            self.rx += self.replies.pop(0)

    def read(self, n):
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def close(self):
        self.is_open = False


@pytest.fixture
def fake(monkeypatch):
    holder = {}

    def make(replies=(), stale=b""):
        def factory(**kwargs):
            holder["serial"] = FakeSerial(replies, stale, **kwargs)
            return holder["serial"]
        monkeypatch.setattr(serial_cobs_adapter.serial, "Serial", factory)
        return holder
    return make


@pytest.mark.parametrize("n", [0, 1, 253, 254, 255, 600])
def test_cobs_round_trip(n):
    data = bytes((i * 7) % 256 for i in range(n))
    enc = cobs_encode(data)
    assert 0 not in enc
    assert cobs_decode(enc) == data


def test_registered_as_serial_cobs():
    a = get_adapter("serial_cobs", "u", port="/dev/null", request="x\\n", crc="crc16")
    assert isinstance(a, SerialCOBSAdapter)
    assert a.request == b"x\n"


def test_unknown_crc_rejected():
    with pytest.raises(ValueError):
        SerialCOBSAdapter("u", port="/dev/null", crc="crc32")


def test_request_and_good_frame(fake):
    frame = with_crc(b"\x10\x00\x01\x02\x00")
    holder = fake(replies=[b"\x00" + cobs_encode(frame) + b"\x00"])
    with SerialCOBSAdapter("u", port="p", request="x", crc="crc16", settle=0) as a:
        m = a.measure()
    assert holder["serial"].written == [b"x"]
    assert m["status"] == "success"
    assert m["frame"] == frame.hex()
    assert m["crc_ok"] is True
    assert m["bad_frames"] == 0


def test_bad_crc_is_kept_and_counted(fake):
    frame = bytearray(with_crc(b"\x10abc"))
    frame[1] ^= 0xFF
    fake(replies=[cobs_encode(bytes(frame)) + b"\x00"] * 2)
    with SerialCOBSAdapter("u", port="p", request="x", crc="crc16", settle=0) as a:
        m1, m2 = a.measure(), a.measure()
    assert m1["status"] == "failed" and m1["crc_ok"] is False
    assert m1["frame"] == bytes(frame).hex()
    assert m2["bad_frames"] == 2


def test_stale_input_discarded(fake):
    old = cobs_encode(with_crc(b"\x01old")) + b"\x00"
    new = with_crc(b"\x10new")
    fake(replies=[cobs_encode(new) + b"\x00"], stale=old)
    with SerialCOBSAdapter("u", port="p", request="x", crc="crc16", settle=0) as a:
        assert a.measure()["frame"] == new.hex()


def test_timeout(fake):
    fake(replies=[])
    with SerialCOBSAdapter("u", port="p", request="x", timeout=0.1, settle=0) as a:
        assert a.measure()["status"] == "timeout"


def test_no_crc_configured(fake):
    fake(replies=[cobs_encode(b"\x01\x02") + b"\x00"])
    with SerialCOBSAdapter("u", port="p", request="x", settle=0) as a:
        m = a.measure()
    assert m["status"] == "success" and "crc_ok" not in m
