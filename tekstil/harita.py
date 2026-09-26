"""Gerçek sınır verisiyle (Natural Earth 1:10m) harita: Türkiye, Suriye ve komşular.

Harita bir "kamera" ile çizilir: merkez (boylam, enlem) ve ölçek (derece başına piksel).
Sahneler kamerayı zamanla kaydırıp yakınlaştırarak hikâyeyi anlatır.
"""
import json, math, os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(HERE, "veri")
W, H = 1080, 1920
LAT0 = 37.0
COSL = math.cos(math.radians(LAT0))
ISO = ["TUR", "SYR", "GRC", "BGR", "GEO", "ARM", "AZE", "IRN", "IRQ", "LBN", "ISR", "PSX", "PSE", "JOR", "CYP",
       "EGY", "SAU", "CYN", "ROU", "MKD", "ALB", "KOS", "SRB", "MDA", "UKR", "RUS"]

CITIES = {  # enlem, boylam
    "İstanbul": (41.01, 28.98), "Bursa": (40.19, 29.06), "Denizli": (37.78, 29.09), "Uşak": (38.68, 29.41),
    "Adana": (37.00, 35.32), "Gaziantep": (37.07, 37.38), "Kahramanmaraş": (37.58, 36.94), "Şanlıurfa": (37.16, 38.79),
    "Malatya": (38.36, 38.31), "Tekirdağ": (40.98, 27.51), "Kilis": (36.72, 37.12), "Halep": (36.20, 37.16),
    "El-Rai": (36.61, 37.45), "Şam": (33.51, 36.29), "Ankara": (39.93, 32.86),
}
HUBS = ["İstanbul", "Bursa", "Denizli", "Uşak", "Adana", "Kahramanmaraş", "Gaziantep", "Şanlıurfa", "Malatya", "Tekirdağ"]


def _load():
    with open(os.path.join(VERI, "ne_10m_admin_0_countries.geojson")) as f:
        g = json.load(f)
    polys = {}
    for ft in g["features"]:
        pr = ft["properties"]
        iso = pr.get("ADM0_A3") or pr.get("ISO_A3")
        if iso not in ISO:
            continue
        geom = ft["geometry"]
        rings = geom["coordinates"] if geom["type"] == "Polygon" else [r for p in geom["coordinates"] for r in p]
        polys.setdefault(iso, [])
        for ring in rings:
            arr = np.asarray(ring, np.float64)
            if arr.ndim != 2 or len(arr) < 3:
                continue
            if arr[:, 0].max() < 18 or arr[:, 0].min() > 52 or arr[:, 1].max() < 26 or arr[:, 1].min() > 48:
                continue                                        # bölge dışındaki adalar/parçalar
            if len(arr) > 4000:                                 # çok ayrıntılı halkaları seyrelt
                arr = arr[::2]
            polys[iso].append(arr)
    lakes = []
    with open(os.path.join(VERI, "ne_10m_lakes.geojson")) as f:
        for ft in json.load(f)["features"]:
            geom = ft["geometry"]
            rings = geom["coordinates"] if geom["type"] == "Polygon" else [r for p in geom["coordinates"] for r in p]
            for ring in rings:
                arr = np.asarray(ring, np.float64)
                if arr.ndim == 2 and len(arr) > 2 and 25 < arr[:, 0].mean() < 50 and 30 < arr[:, 1].mean() < 44:
                    lakes.append(arr)
    rivers = []
    with open(os.path.join(VERI, "ne_10m_rivers_lake_centerlines.geojson")) as f:
        for ft in json.load(f)["features"]:
            geom = ft["geometry"]
            lines = [geom["coordinates"]] if geom["type"] == "LineString" else geom["coordinates"]
            for ln in lines:
                arr = np.asarray(ln, np.float64)
                if arr.ndim == 2 and len(arr) > 1 and 26 < arr[:, 0].mean() < 46 and 31 < arr[:, 1].mean() < 42:
                    rivers.append(arr)
    return polys, lakes, rivers


POLYS, LAKES, RIVERS = _load()


def project(lonlat, cam):
    """(boylam, enlem) dizisi -> ekran pikseli. cam = (merkez_boylam, merkez_enlem, derece_başına_piksel)."""
    lon0, lat0, s = cam
    ll = np.asarray(lonlat, np.float64)
    x = W / 2 + (ll[..., 0] - lon0) * COSL * s
    y = H / 2 - (ll[..., 1] - lat0) * s
    return np.stack([x, y], -1)


def city_xy(name, cam):
    lat, lon = CITIES[name]
    return project((lon, lat), cam)


_noise = None


def _land_texture():
    global _noise
    if _noise is None:
        rng = np.random.default_rng(5)
        n = np.zeros((H, W), np.float32)
        for s, a in ((3, 0.5), (9, 0.3), (27, 0.2)):
            small = rng.normal(0, 1, (H // s + 2, W // s + 2)).astype(np.float32)
            n += cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)[:H, :W] * a
        _noise = n
    return _noise


def base(cam, hi=None, t=0.0):
    """Harita zemini (doğrusal renk). hi: {ülke: (renk, güç)} vurgusu."""
    lon0, lat0, s = cam
    sea = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    sea += np.array([0.006, 0.012, 0.022], np.float32) * (1.1 - 0.3 * yy)
    land = np.zeros((H, W), np.uint8)
    masks = {}
    for iso, rings in POLYS.items():
        m = np.zeros((H, W), np.uint8)
        pts = [np.round(project(r, cam) * 8).astype(np.int32) for r in rings]
        pts = [p for p in pts if (p[:, 0].max() > -8 * W) and (p[:, 0].min() < 16 * W) and
               (p[:, 1].max() > -8 * H) and (p[:, 1].min() < 16 * H)]
        if pts:
            cv2.fillPoly(m, pts, 255, cv2.LINE_AA, shift=3)
        masks[iso] = m
        land = np.maximum(land, m)
    lf = land.astype(np.float32) / 255
    tex = _land_texture()
    land_col = np.array([0.028, 0.03, 0.032], np.float32)[None, None, :] * (1 + 0.12 * tex[..., None])
    img = sea * (1 - lf[..., None]) + land_col * lf[..., None]
    if hi:
        for iso, (col, k) in hi.items():
            if iso in masks and k > 0:
                mm = masks[iso].astype(np.float32)[..., None] / 255
                img = img * (1 - mm * k * 0.55) + np.asarray(col, np.float32) * mm * k * 0.55 * (1 + 0.1 * tex[..., None])
    for r in LAKES:                                             # göller
        p = np.round(project(r, cam) * 8).astype(np.int32)
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [p], 255, cv2.LINE_AA, shift=3)
        mm = m.astype(np.float32)[..., None] / 255
        img = img * (1 - mm) + sea * mm
    riv = np.zeros((H, W), np.uint8)                            # nehirler (Fırat, Dicle ...)
    for r in RIVERS:
        p = np.round(project(r, cam) * 8).astype(np.int32)
        cv2.polylines(riv, [p], False, 255, max(1, int(s / 60)), cv2.LINE_AA, shift=3)
    img += (riv.astype(np.float32)[..., None] / 255) * np.array([0.02, 0.05, 0.09], np.float32)
    bord = np.zeros((H, W), np.uint8)                           # sınırlar
    for iso, m in masks.items():
        e = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        bord = np.maximum(bord, e)
    img += (bord.astype(np.float32)[..., None] / 255) * np.array([0.09, 0.1, 0.11], np.float32)
    return img, masks


def border_line(masks, a, b):
    """İki ülkenin ortak sınır çizgisi (maske)."""
    k = np.ones((5, 5), np.uint8)
    return (cv2.dilate(masks[a], k) > 0) & (cv2.dilate(masks[b], k) > 0)


def lerp_cam(c0, c1, u):
    """Kamerayı yumuşak geçir: ölçek logaritmik, merkez doğrusal."""
    lon = c0[0] + (c1[0] - c0[0]) * u
    lat = c0[1] + (c1[1] - c0[1]) * u
    s = math.exp(math.log(c0[2]) + (math.log(c1[2]) - math.log(c0[2])) * u)
    return (lon, lat, s)


def km_per_px(cam):
    return 111.32 / cam[2]
