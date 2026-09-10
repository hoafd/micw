"""
WO Mic TCP Probe Tool
Kết nối TCP đến WO Mic và xem dữ liệu gì được gửi.
Giúp reverse-engineer giao thức để biết handshake và format stream.
"""

import socket
import time
import struct
import sys
import threading

HOST = "192.168.10.80"
PORT = 8125
TIMEOUT = 10  # seconds


def bytes_to_hex(data, max_bytes=64):
    """Chuyển bytes thành hex string dễ đọc"""
    hex_str = " ".join(f"{b:02X}" for b in data[:max_bytes])
    if len(data) > max_bytes:
        hex_str += f" ... (+{len(data)-max_bytes} more bytes)"
    return hex_str


def bytes_to_ascii(data, max_bytes=64):
    """Chuyển bytes thành ASCII (dấu chấm cho non-printable)"""
    result = ""
    for b in data[:max_bytes]:
        if 32 <= b <= 126:
            result += chr(b)
        else:
            result += "."
    return result


def probe_tcp_listen(sock, duration=5):
    """Lắng nghe dữ liệu từ WO Mic trong duration giây"""
    print(f"\n[LISTEN] Đang lắng nghe {duration} giây...")
    sock.settimeout(1.0)
    total_bytes = 0
    packet_count = 0
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            data = sock.recv(4096)
            if not data:
                print("[!] Connection closed by remote")
                break
            packet_count += 1
            total_bytes += len(data)
            elapsed = time.time() - start_time
            print(f"\n  Packet #{packet_count} at {elapsed:.2f}s ({len(data)} bytes):")
            print(f"    HEX: {bytes_to_hex(data)}")
            print(f"    ASC: {bytes_to_ascii(data)}")

            # Thử detect audio: PCM 16-bit có amplitude values, không phải all-zero
            non_zero = sum(1 for b in data if b != 0)
            print(f"    Non-zero bytes: {non_zero}/{len(data)}")
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[ERROR] {e}")
            break

    print(f"\n[LISTEN RESULT] Total: {total_bytes} bytes, {packet_count} packets in {duration:.1f}s")
    return total_bytes > 0


def send_probe_bytes(sock, data, label=""):
    """Gửi bytes và log kết quả"""
    print(f"\n[SEND] {label}: {bytes_to_hex(data)}")
    try:
        sock.sendall(data)
        print(f"  ✓ Sent {len(data)} bytes")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("  WO Mic TCP Probe Tool")
    print(f"  Target: {HOST}:{PORT}")
    print("=" * 60)

    # === Bước 1: Kết nối TCP ===
    print(f"\n[STEP 1] Kết nối TCP đến {HOST}:{PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)

    try:
        sock.connect((HOST, PORT))
        print(f"  ✓ Kết nối thành công!")
    except Exception as e:
        print(f"  ✗ Không thể kết nối: {e}")
        return

    # === Bước 2: Lắng nghe ngay sau khi kết nối (có thể server gửi banner/hello) ===
    print("\n[STEP 2] Xem WO Mic gửi gì ngay sau khi connect...")
    got_data = probe_tcp_listen(sock, duration=3)

    if not got_data:
        print("\n  → Server không gửi gì tự động. Cần gửi handshake request.")

        # === Bước 3: Thử gửi các handshake patterns khác nhau ===

        # Pattern 1: Byte đơn - ID/magic number phổ biến
        probes = [
            (b"\x00", "Null byte"),
            (b"\x01", "Byte 0x01"),
            (b"\x02", "Byte 0x02"),
            (b"WO\x00", "WO prefix"),
            (b"\x57\x4F\x01\x00", "WO magic + version"),
            (b"\x01\x00\x00\x00", "Little-endian int 1"),
            (b"\x00\x00\x00\x01", "Big-endian int 1"),
            # WO Mic control protocol guess based on common audio streaming
            (struct.pack("<I", 1) + struct.pack("<I", 48000) + struct.pack("<H", 1) + struct.pack("<H", 16),
             "Config: rate=48000, ch=1, bits=16"),
        ]

        for probe_bytes, label in probes:
            if send_probe_bytes(sock, probe_bytes, label):
                got_data = probe_tcp_listen(sock, duration=2)
                if got_data:
                    print(f"\n  ✓✓ GOT DATA after sending: {label}")
                    # Lắng nghe thêm để xem stream
                    probe_tcp_listen(sock, duration=5)
                    break
            time.sleep(0.5)

    else:
        print("\n  → Server gửi data tự động! Lắng nghe thêm 10 giây...")
        probe_tcp_listen(sock, duration=10)

    sock.close()
    print("\n[DONE] Probe hoàn tất.")
    print("\nXem kết quả ở trên để hiểu giao thức WO Mic.")
    print("Nếu thấy dữ liệu audio (PCM), hãy ghi chép bytes đầu tiên để xác định handshake.")


if __name__ == "__main__":
    main()
