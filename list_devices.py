"""
Kiểm tra WO Mic audio devices trên Windows
Liệt kê tất cả audio input devices để tìm WO Mic Device
"""
import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    print("=" * 60)
    print("  Danh sách Audio Input Devices")
    print("=" * 60)
    
    device_count = p.get_device_count()
    print(f"\nTổng số devices: {device_count}\n")
    
    input_devices = []
    for i in range(device_count):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            input_devices.append((i, info))
            print(f"  [{i}] {info['name']}")
            print(f"       Input channels: {info['maxInputChannels']}")
            print(f"       Sample rate: {info['defaultSampleRate']}")
            print()
    
    p.terminate()
    
    if not input_devices:
        print("  ✗ Không tìm thấy audio input device nào!")
    else:
        print(f"\n✓ Tìm thấy {len(input_devices)} input device(s)")
        
    # Tìm WO Mic device
    womic_devices = [(i, info) for i, info in input_devices 
                     if 'wo mic' in info['name'].lower() or 'womic' in info['name'].lower()]
    if womic_devices:
        print(f"\n✓ WO Mic Device tìm thấy!")
        for i, info in womic_devices:
            print(f"  Index: {i}, Name: {info['name']}")
    else:
        print("\n⚠ WO Mic Device chưa xuất hiện.")
        print("  → WO Mic Driver chưa được cài hoặc WO Mic chưa kết nối.")
    
    return input_devices

if __name__ == "__main__":
    list_audio_devices()
