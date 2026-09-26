"""Konteyner limanı, gün batımı: yığınlar, vinç, asfalt saha.

Kullanım: python3 liman.py koridor|havadan [yüzde]
"""
import math, random, sys
import bpy
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ortak3d as T

L20, L40, CW, CH = 6.06, 12.19, 2.44, 2.59
COLORS = [(0.42, 0.07, 0.05), (0.7, 0.26, 0.04), (0.05, 0.09, 0.22), (0.08, 0.26, 0.13), (0.38, 0.4, 0.42),
          (0.7, 0.7, 0.66), (0.05, 0.28, 0.32), (0.55, 0.45, 0.1), (0.25, 0.08, 0.2)]


def corrugated(name, color):
    """Oluklu çelik: dalga dokusuyla kabartma + pas ve kir lekeleri."""
    m = T.mat(name, color, rough=0.55, metal=0.35, var=0.35, var_scale=1.2)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 3.6
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def container(name, length, color_mat, M):
    objs = [T.box("govde", (length, CW, CH), (0, 0, CH / 2), color_mat, bevel=0.02)]
    for sy in (-1, 1):                                    # üst ve alt raylar
        for z in (0.06, CH - 0.06):
            objs.append(T.box("ray", (length, 0.1, 0.12), (0, sy * (CW / 2 - 0.02), z), M["frame"]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z in (0.09, CH - 0.09):
                objs.append(T.box("kose", (0.18, 0.16, 0.18), (sx * (length / 2 - 0.08), sy * (CW / 2 - 0.06), z),
                                  M["frame"], bevel=0.01))
    for k in range(4):                                    # kapı kilit milleri (arka yüz)
        y = -CW / 2 + 0.35 + k * (CW - 0.7) / 3
        objs.append(T.cyl("kilit_mili", 0.022, CH - 0.3, (length / 2 + 0.03, y, CH / 2), M["steel"], verts=12))
    return T.collect(objs, name)


def build(seed=5, sun_elev=4.0, sun_azim=90.0):
    rng = random.Random(seed)
    T.reset(seed)
    M = dict(
        frame=T.mat("cerceve", (0.12, 0.12, 0.12), rough=0.6, metal=0.6),
        steel=T.mat("celik", (0.5, 0.5, 0.5), rough=0.35, metal=1.0),
        asphalt=T.mat("asfalt", (0.05, 0.05, 0.055), rough=0.6, var=0.5, var_scale=0.15, bump=0.06, bump_scale=40),
        paint=T.mat("boya", (0.8, 0.7, 0.2), rough=0.6, var=0.5, var_scale=2),
        crane=T.mat("vinc", (0.55, 0.14, 0.05), rough=0.5, metal=0.4, var=0.2),
        water=T.mat("deniz", (0.02, 0.04, 0.05), rough=0.08, metal=0.0, spec=0.6, bump=0.08, bump_scale=0.6),
    )
    T.plane("saha", (600, 600), (0, 0, 0), M["asphalt"])
    T.plane("deniz", (2000, 1000), (0, 700, -0.5), M["water"])
    variants = []
    for i, c in enumerate(COLORS):
        cm = corrugated(f"konteyner{i}", c)
        variants.append(container(f"k40_{i}", L40, cm, M))
        variants.append(container(f"k20_{i}", L20, cm, M))
    for v in variants:
        T.hide_source(v)
    # yığınlar: X boyunca konteyner, Y boyunca sıralar; aralarda koridor
    for row in range(-7, 8):
        y = row * 3.0 + (8.0 if row > 0 else -8.0 if row < 0 else 0)
        if row == 0:
            continue
        x = -40.0
        while x < 260:
            is40 = rng.random() < 0.7
            length = L40 if is40 else L20
            h = rng.choice([1, 2, 2, 3, 3, 3, 4, 4, 5])
            if rng.random() < 0.06:
                x += length + 0.4
                continue
            for lvl in range(h):
                v = variants[rng.randrange(len(COLORS)) * 2 + (0 if is40 else 1)]
                T.instance(v, (x + length / 2, y, lvl * (CH + 0.02)), 0 if rng.random() < 0.5 else 180, index=3)
            x += length + 0.35
            if rng.random() < 0.08:
                x += 12
    for sx in (-1, 1):                                    # koridor çizgileri
        T.plane("cizgi", (300, 0.15), (110, sx * 3.2, 0.01), M["paint"])
    for cx in (40, 120, 200):                             # rıhtım vinçleri (siluet)
        for lx in (-9, 9):
            for ly in (-6, 6):
                T.box("vinc_ayak", (1.2, 1.2, 42), (cx + lx, 60 + ly, 21), M["crane"])
        T.box("vinc_kiris", (20, 14, 3), (cx, 60, 43), M["crane"])
        T.box("vinc_bum", (4, 90, 2.5), (cx, 85, 46), M["crane"])
        T.box("vinc_kabin", (4, 4, 3), (cx, 70, 40.5), M["frame"])
    for k in range(14):                                   # saha aydınlatma direkleri (uzakta)
        x, y = rng.uniform(90, 250), rng.choice([-30, 30, -55, 55])
        T.cyl("direk", 0.25, 30, (x, y, 15), M["steel"], verts=12)
        T.box("projektor", (2.2, 0.6, 0.8), (x, y, 30.3), M["frame"])
    T.sky_world(sun_elev=sun_elev, sun_rot=sun_azim, strength=0.08)
    T.sun("gunes", sun_elev, 180 - sun_azim, 1.1, T.kelvin(3000), angle=0.8)     # gökyüzüyle aynı yönde
    return M


def koridor(pct=50):
    build()
    T.render_setup(samples=48, pct=pct, clamp=10)
    T.camera((-30, 0.0, 1.7), (80, 0.9, 6.0), lens=26, fstop=4.0, focus=30)
    T.render("liman_koridor")


def havadan(pct=50):
    build(sun_elev=6.0, sun_azim=53.0)
    T.render_setup(samples=48, pct=pct, clamp=10)
    T.camera((-60, -70, 55), (60, 15, 0), lens=40, fstop=None)
    T.render("liman_havadan")


def bariyer(pct=50):
    """Gümrük kapısı: kırmızı-beyaz bariyer kolu ve kulübe, arkada konteyner koridoru."""
    M = build()
    red = T.mat("bariyer_kirmizi", (0.6, 0.03, 0.02), rough=0.35, coat=0.3)
    white = T.mat("bariyer_beyaz", (0.8, 0.8, 0.78), rough=0.35, coat=0.3)
    for k in range(12):
        T.box("bariyer_kol", (0.12, 0.5, 0.12), (-33.0, -3.0 + k * 0.5 + 0.25, 1.05), red if k % 2 else white, bevel=0.01)
    T.box("bariyer_govde", (0.45, 0.45, 1.1), (-33.0, -3.6, 0.55), T.mat("gri", (0.35, 0.36, 0.38), rough=0.4, metal=0.5),
          bevel=0.02)
    T.box("kulube", (2.4, 2.2, 2.7), (-35.5, -6.2, 1.35), T.mat("kulube", (0.7, 0.7, 0.68), rough=0.6), bevel=0.03)
    T.box("kulube_cam", (0.02, 1.4, 0.9), (-34.29, -6.2, 1.6), T.emission("kulube_isik", T.kelvin(3000), 3.0))
    T.cyl("isik_direk", 0.05, 3.2, (-33.0, -4.2, 1.6), M["steel"], verts=10)
    T.box("isik_kutu", (0.25, 0.25, 0.6), (-33.0, -4.2, 3.3), T.mat("siyah", (0.02, 0.02, 0.02), rough=0.4))
    T.sphere("kirmizi_isik", 0.08, (-33.14, -4.2, 3.45), T.emission("kirmizi", (1.0, 0.05, 0.02), 30), seg=12)
    T.render_setup(samples=48, pct=pct, clamp=10)
    T.camera((-35.2, -1.6, 1.12), (-28.0, 1.2, 1.3), lens=28, fstop=2.8, focus=2.4)
    T.render("liman_bariyer")


if __name__ == "__main__":
    mode = sys.argv[1]
    pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    {"koridor": koridor, "havadan": havadan, "bariyer": bariyer}[mode](pct)
