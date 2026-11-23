"""Harita karoları: OpenStreetMap / uydu karolarını indirir ve diske önbelleğe alır; internet yokken önbellekten çalışır."""
from __future__ import annotations
import os, math, io, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor

SOURCES = {
    'osm': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    'sat': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    'topo': 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
}
UA = 'PixhawkLogAnaliz/1.0 (desktop log analysis tool)'
_lock = threading.Lock()


def cache_dir():
    from .paths import data_dir
    d = os.path.join(data_dir(), 'tiles'); os.makedirs(d, exist_ok=True); return d


def deg2num(lat, lon, z):
    lat = max(-85.0, min(85.0, lat))
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def num2deg(x, y, z):
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def tile_path(src, z, x, y):
    return os.path.join(cache_dir(), src, str(z), str(x), f'{y}.png')


def get_tile(src, z, x, y, online=True, timeout=8):
    p = tile_path(src, z, x, y)
    if os.path.exists(p):
        return p
    if not online:
        return None
    try:
        req = urllib.request.Request(SOURCES[src].format(z=z, x=x, y=y), headers={'User-Agent': UA})
        data = urllib.request.urlopen(req, timeout=timeout).read()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as f: f.write(data)
        return p
    except Exception:
        return None


def pick_zoom(lat0, lat1, lon0, lon1, max_tiles=16):
    for z in range(18, 1, -1):
        x0, y0 = deg2num(lat1, lon0, z); x1, y1 = deg2num(lat0, lon1, z)
        if (int(x1) - int(x0) + 1) * (int(y1) - int(y0) + 1) <= max_tiles:
            return z
    return 2


def mosaic(lat0, lat1, lon0, lon1, src='osm', online=True, max_tiles=16):
    """Bölgeyi kaplayan karo mozaiği: (PIL.Image, (lon_min, lon_max, lat_min, lat_max)) veya None."""
    from PIL import Image
    z = pick_zoom(lat0, lat1, lon0, lon1, max_tiles)
    x0, y0 = deg2num(lat1, lon0, z); x1, y1 = deg2num(lat0, lon1, z)
    xs = range(int(x0), int(x1) + 1); ys = range(int(y0), int(y1) + 1)
    jobs = [(x, y) for x in xs for y in ys]
    with ThreadPoolExecutor(6) as ex:
        paths = list(ex.map(lambda xy: get_tile(src, z, xy[0], xy[1], online), jobs))
    if not any(paths):
        return None
    img = Image.new('RGB', (256 * len(xs), 256 * len(ys)), (235, 235, 235))
    for (x, y), p in zip(jobs, paths):
        if p:
            try: img.paste(Image.open(p).convert('RGB'), ((x - xs[0]) * 256, (y - ys[0]) * 256))
            except Exception: pass
    la_top, lo_left = num2deg(xs[0], ys[0], z)
    la_bot, lo_right = num2deg(xs[-1] + 1, ys[-1] + 1, z)
    return img, (lo_left, lo_right, la_bot, la_top), z


def prefetch(lat0, lat1, lon0, lon1, zmin=10, zmax=17, src='osm', progress=None, cancel=None):
    """Offline kullanım için bir bölgenin karolarını önceden indirir."""
    jobs = []
    for z in range(zmin, zmax + 1):
        x0, y0 = deg2num(lat1, lon0, z); x1, y1 = deg2num(lat0, lon1, z)
        for x in range(int(x0), int(x1) + 1):
            for y in range(int(y0), int(y1) + 1):
                jobs.append((z, x, y))
    jobs = jobs[:6000]
    done = 0
    with ThreadPoolExecutor(4) as ex:
        for _ in ex.map(lambda j: get_tile(src, *j, online=True), jobs):
            done += 1
            if progress: progress(done, len(jobs))
            if cancel and cancel(): break
    return done
