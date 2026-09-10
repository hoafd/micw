"""
test_audio.py - Kiểm tra nhanh audio từ WO Mic device
Hiển thị mức âm thanh thực tế trong terminal để xác nhận mic hoạt động
"""
import pyaudio
import struct
import math
import time
import sys

DEVICE_INDEX = 9   # Thử thay đổi nếu cần
SAMPLE_RATE  = 48000
CHANNELS     = 1
CHUNK        = 1024
FORMAT       = pyaudio.paInt16

def rms_to_db(rms):
    if rms == 0:
        return -100
    return 20 * math.log10(rms / 32768.0)

def draw_bar(db, width=40):
    # db range: -60 to 0
    pct = max(0, min(1, (db + 60) / 60))
    filled = int(pct * width)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def main():
    p = pyaudio.PyAudio()
    
    print("=" * 60)
    print("  WO Mic Audio Level Meter")
    print("=" * 60)
    
    # List all devices first
    print("\nTất cả Input Devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']} ({info['defaultSampleRate']:.0f}Hz)")
    
    print(f"\n→ Đang mở device [{DEVICE_INDEX}]...")
    
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=DEVICE_INDEX,
            frames_per_buffer=CHUNK
        )
        print("✓ Mở thành công!\n")
        print("Nói vào mic - xem thanh mức âm thanh bên dưới:")
        print("(Ctrl+C để thoát)\n")
        
        zero_count = 0
        
        for _ in range(500):  # ~10 giây
            data = stream.read(CHUNK, exception_on_overflow=False)
            
            # Parse PCM int16
            samples = struct.unpack(f'<{len(data)//2}h', data)
            
            # RMS amplitude
            rms = math.sqrt(sum(s*s for s in samples) / len(samples))
            peak = max(abs(s) for s in samples)
            db = rms_to_db(rms)
            
            # Count zero frames
            non_zero = sum(1 for s in samples if s != 0)
            if non_zero == 0:
                zero_count += 1
            else:
                zero_count = 0
            
            bar = draw_bar(db)
            status = "🔴 SIGNAL" if db > -50 else ("⚪ silence" if db > -80 else "⚫ ZERO")
            
            print(f"\r  {bar} {db:6.1f}dB  Peak:{peak:6d}  {status}   ", end='', flush=True)
            
            if zero_count > 20:
                print(f"\n\n⚠️  CẢNH BÁO: Device trả về toàn số 0 ({zero_count} chunks liên tiếp)")
                print("    → WO Mic có thể chưa kết nối với điện thoại")
                print("    → Thử device index khác hoặc kiểm tra WO Mic Client")
                break
        
        stream.stop_stream()
        stream.close()
        
    except OSError as e:
        print(f"✗ Lỗi mở device: {e}")
        print("\nThử các device index khác: 1, 5, 15")
    finally:
        p.terminate()

if __name__ == "__main__":
    # Cho phép truyền device index từ argument
    if len(sys.argv) > 1:
        DEVICE_INDEX = int(sys.argv[1])
    main()
