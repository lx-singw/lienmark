#!/usr/bin/env python3
import struct
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = REPO_ROOT / 'docs' / 'assets' / 'screenshots'
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def create_styled_png(filename, border_rgb, width=1280, height=720):
    raw = bytearray()
    for y in range(height):
        raw.append(0) # filter None
        for x in range(width):
            if x < 4 or x >= width - 4 or y < 4 or y >= height - 4:
                raw.extend(border_rgb)
            elif y < 70:
                raw.extend((15, 23, 42)) # slate-900 header
            elif y == 70 or y == 71:
                raw.extend(border_rgb)
            elif y >= height - 50:
                raw.extend((15, 23, 42)) # footer
            elif y == height - 51:
                raw.extend(border_rgb)
            else:
                card_col = (x - 40) // 380
                card_row = (y - 100) // 180
                in_card = (0 <= card_col < 3) and (0 <= card_row < 3) and ((x - 40) % 380 < 360) and ((y - 100) % 180 < 160)
                if in_card:
                    raw.extend((30, 41, 59)) # slate-800
                else:
                    raw.extend((2, 6, 23)) # slate-950
    compressed = zlib.compress(bytes(raw), 6)
    def chunk(tag, data):
        ch = tag + data
        crc = struct.pack('>I', zlib.crc32(ch) & 0xffffffff)
        return struct.pack('>I', len(data)) + ch + crc
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    target = SCREENSHOTS_DIR / filename
    target.write_bytes(png)
    print(f'Wrote PNG: {target} ({len(png)} bytes)')

def main():
    create_styled_png('dashboard_v7_baseline.png', (56, 189, 248))
    create_styled_png('dashboard_v8_drift.png', (239, 68, 68))
    create_styled_png('counsel_checkpoint_modal.png', (168, 85, 247))
    create_styled_png('form_eo_2026_schedule.png', (34, 197, 94))

if __name__ == '__main__':
    main()
