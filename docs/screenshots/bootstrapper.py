
import pathlib

SCRIPT = (
    'from PIL import Image, ImageDraw, ImageFont\n'
    'import random\n'
    '\n'
    'random.seed(42)\n'
    '\n'
    'W, H = 1200, 800\n'
    '\n'
    'BG = "#0f172a"\n'
    'HEADER_BG = "#1e293b"\n'
    'CARD_BG = "#1e293b"\n'
    'CARD_BORDER = "#334155"\n'
    'MAP_BG = "#0c1222"\n'
    'SIDEBAR_BG = "#1e293b"\n'
    'CAM_BG = "#111827"\n'
    'TEXT_WHITE = "#f1f5f9"\n'
    'TEXT_MUTED = "#94a3b8"\n'
    'TEXT_DIM = "#64748b"\n'
    'GRID_LINE = "#1a2744"\n'
    'ACCENT_GREEN = "#22c55e"\n'
    'ACCENT_YELLOW = "#eab308"\n'
    'ACCENT_BLUE = "#3b82f6"\n'
    'ACCENT_ORANGE = "#f97316"\n'
    'ACCENT_RED = "#ef4444"\n'
    'ACCENT_CYAN = "#06b6d4"\n'
    'BORDER_SUBTLE = "#253352"\n'
)
pathlib.Path(r'r:\hacksagon2\docs\screenshots\test2.py').write_text(SCRIPT)
print('Done writing', len(SCRIPT), 'bytes')
