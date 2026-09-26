"""Tekstil atölyesi: sıra sıra dikiş makineleri, boş sandalyeler, yarısı sönük floresanlar.

Kullanım (Blender'ın Python modülüyle):
  python3 fabrika.py genis  [yüzde] [kare...]   # geniş plan, kamera yavaşça ilerler
  python3 fabrika.py yakin  [yüzde] [kare...]   # dikiş makinesi yakın çekim (iğne hareketli)
"""
import math, random, sys
import bpy
from mathutils import Vector
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ortak3d as T

TABLE_H = 0.74


# ------------------------------------------------------------------ malzemeler
def materials():
    M = dict(
        floor=T.mat("zemin", (0.16, 0.19, 0.17), rough=0.32, var=0.35, var_scale=0.8, bump=0.05, bump_scale=6),
        line=T.mat("serit", (0.75, 0.55, 0.05), rough=0.5, var=0.4, var_scale=3),
        wall=T.mat("duvar", (0.55, 0.55, 0.52), rough=0.9, var=0.25, var_scale=1.5, bump=0.1, bump_scale=3),
        ceil=T.mat("tavan", (0.08, 0.08, 0.085), rough=0.8),
        steel=T.mat("celik", (0.35, 0.36, 0.38), rough=0.45, metal=0.9, var=0.2, var_scale=4),
        duct=T.mat("kanal", (0.32, 0.32, 0.33), rough=0.45, metal=1.0),
        top=T.mat("masa", (0.62, 0.52, 0.38), rough=0.55, var=0.2, var_scale=5, coat=0.1),
        edge=T.mat("kenar", (0.12, 0.12, 0.12), rough=0.6),
        leg=T.mat("ayak", (0.25, 0.26, 0.28), rough=0.4, metal=0.8),
        mach=T.mat("makine", (0.78, 0.78, 0.74), rough=0.28, coat=0.4, var=0.08, var_scale=10),
        mach2=T.mat("makine2", (0.42, 0.5, 0.47), rough=0.3, coat=0.3, var=0.08, var_scale=10),
        chrome=T.mat("krom", (0.8, 0.8, 0.82), rough=0.15, metal=1.0),
        badge=T.mat("marka", (0.55, 0.06, 0.05), rough=0.3, coat=0.5),
        black=T.mat("siyah", (0.03, 0.03, 0.03), rough=0.4),
        motor=T.mat("motor", (0.08, 0.08, 0.09), rough=0.5, metal=0.3),
        seat=T.mat("oturak", (0.18, 0.1, 0.06), rough=0.6, var=0.2),
        cover=T.mat("ortu", (0.72, 0.72, 0.7), rough=0.95, sheen=0.6, var=0.15, var_scale=3, bump=0.3, bump_scale=8),
        crate=T.mat("kasa", (0.05, 0.18, 0.45), rough=0.45),
        tube_on=T.emission("tup_acik", T.kelvin(5200), 14.0),
        tube_off=T.mat("tup_kapali", (0.12, 0.12, 0.13), rough=0.3),
        housing=T.mat("armatur", (0.35, 0.35, 0.36), rough=0.4, metal=0.5),
        window=T.emission("pencere", (0.75, 0.82, 0.9), 3.0),
        frame=T.mat("cerceve", (0.2, 0.2, 0.22), rough=0.5, metal=0.6),
    )
    M["fabrics"] = [T.mat(f"kumas{i}", c, rough=0.9, sheen=0.7, var=0.25, var_scale=12, bump=0.2, bump_scale=60)
                    for i, c in enumerate([(0.05, 0.09, 0.2), (0.02, 0.02, 0.025), (0.5, 0.48, 0.45),
                                           (0.35, 0.05, 0.06), (0.62, 0.6, 0.55), (0.1, 0.18, 0.12)])]
    M["cones"] = [T.mat(f"bobin{i}", c, rough=0.6, sheen=0.5)
                  for i, c in enumerate([(0.85, 0.85, 0.82), (0.02, 0.02, 0.03), (0.05, 0.08, 0.25),
                                         (0.5, 0.05, 0.04), (0.55, 0.45, 0.3), (0.3, 0.3, 0.32)])]
    return M


# ------------------------------------------------------------------ dikiş makinesi (sanayi tipi düz makine)
def machine(M, body, loc=(0, 0, 0)):
    """Kol Y ekseni boyunca; iğne başı -Y ucunda, operatör +X tarafında (-X'e bakar)."""
    x, y, z = loc
    parts = [
        T.box("taban", (0.19, 0.5, 0.045), (x, y, z + 0.0225), body, bevel=0.012, seg=3),
        T.box("sutun", (0.14, 0.11, 0.3), (x - 0.005, y + 0.19, z + 0.19), body, bevel=0.025, seg=4),
        T.box("kol", (0.1, 0.42, 0.095), (x - 0.01, y - 0.0, z + 0.3), body, bevel=0.03, seg=4),
        T.box("bas", (0.12, 0.095, 0.21), (x - 0.005, y - 0.2, z + 0.225), body, bevel=0.022, seg=4),
        T.cyl("volan", 0.068, 0.034, (x - 0.005, y + 0.262, z + 0.23), M["black"], rot=(90, 0, 0), bevel=0.006),
        T.cyl("volan_gobek", 0.02, 0.05, (x - 0.005, y + 0.27, z + 0.23), M["chrome"], rot=(90, 0, 0)),
        T.cyl("gerginlik", 0.018, 0.02, (x + 0.068, y - 0.2, z + 0.25), M["black"], rot=(0, 90, 0)),
        T.box("baski_ayagi", (0.028, 0.03, 0.008), (x, y - 0.2, z + 0.05), M["chrome"], bevel=0.003),
        T.cyl("ayak_mili", 0.005, 0.07, (x - 0.02, y - 0.2, z + 0.09), M["chrome"]),
        T.box("plaka", (0.1, 0.12, 0.004), (x, y - 0.19, z + 0.047), M["chrome"], bevel=0.002),
        # ön yüz ayrıntıları: yüz kapağı, vidalar, gerginlik diskleri, iplik kolu, marka şeridi
        T.box("yuz_kapak", (0.004, 0.078, 0.15), (x + 0.057, y - 0.2, z + 0.225), M["chrome"], bevel=0.002),
        T.cyl("vida1", 0.0042, 0.006, (x + 0.06, y - 0.2, z + 0.165), M["chrome"], rot=(0, 90, 0), verts=12),
        T.cyl("vida2", 0.0042, 0.006, (x + 0.06, y - 0.2, z + 0.285), M["chrome"], rot=(0, 90, 0), verts=12),
        T.cyl("disk1", 0.012, 0.004, (x + 0.064, y - 0.168, z + 0.245), M["chrome"], rot=(0, 90, 0), verts=24),
        T.cyl("disk2", 0.012, 0.004, (x + 0.069, y - 0.168, z + 0.245), M["chrome"], rot=(0, 90, 0), verts=24),
        T.box("iplik_kolu", (0.045, 0.007, 0.012), (x + 0.075, y - 0.182, z + 0.3), M["chrome"], bevel=0.002),
        T.box("marka_seridi", (0.004, 0.14, 0.022), (x + 0.042, y - 0.02, z + 0.3), M["badge"], bevel=0.002),
        T.cyl("kaldirma_kolu", 0.004, 0.05, (x - 0.06, y - 0.2, z + 0.27), M["black"], rot=(0, 90, 0), verts=10),
    ]
    return parts


def needle(M, loc, phase):
    """İğne mili: phase 0-1 arası bir dikiş döngüsü (yukarı-aşağı)."""
    x, y, z = loc
    drop = 0.022 * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
    return [T.cyl("igne_mili", 0.0045, 0.075, (x + 0.005, y - 0.2, z + 0.1 - drop), M["chrome"]),
            T.cyl("igne", 0.0012, 0.03, (x + 0.005, y - 0.2, z + 0.052 - drop), M["chrome"], verts=8)]


def station(M, name, variant, rng):
    """Tek iş istasyonu (masa + makine + iplik standı + bobinler); X=0 masanın ortası."""
    objs = []
    objs.append(T.box("masa", (0.6, 1.15, 0.035), (0, 0, TABLE_H - 0.0175), M["top"], bevel=0.004))
    objs.append(T.box("masa_kenar", (0.604, 1.154, 0.012), (0, 0, TABLE_H - 0.03), M["edge"]))
    for sx in (-0.26, 0.26):
        for sy in (-0.52, 0.52):
            objs.append(T.box("ayak", (0.035, 0.035, TABLE_H - 0.04), (sx, sy, (TABLE_H - 0.04) / 2), M["leg"], bevel=0.004))
    objs.append(T.box("travers", (0.03, 1.04, 0.03), (-0.26, 0, 0.18), M["leg"]))
    objs.append(T.box("motor", (0.16, 0.2, 0.15), (0.05, 0.32, TABLE_H - 0.13), M["motor"], bevel=0.015))
    objs.append(T.box("pedal", (0.2, 0.28, 0.03), (0.18, 0.05, 0.06), M["leg"], rot=(0, 12, 0), bevel=0.005))
    body = M["mach"] if variant != "eski" else M["mach2"]
    mz = TABLE_H
    if variant == "bos":
        pass
    elif variant == "ortulu":
        cover = T.box("ortu", (0.3, 0.62, 0.42), (0.0, 0.0, mz + 0.2), M["cover"], bevel=0.08, seg=6)
        md = cover.modifiers.new("kivrim", "SUBSURF")
        md.levels = 2
        md.render_levels = 2
        tex = bpy.data.textures.new("kirisik", "CLOUDS")
        tex.noise_scale = 0.08
        dp = cover.modifiers.new("kirisiklik", "DISPLACE")
        dp.texture = tex
        dp.strength = 0.025
        objs.append(cover)
    else:
        objs += machine(M, body, (0.0, 0.0, mz))
        objs += needle(M, (0.0, 0.0, mz), 0.0)
    if variant == "bos":
        for o in objs:
            o.pass_index = 1
        return T.collect(objs, name)
    objs.append(T.cyl("stand", 0.008, 0.62, (-0.24, 0.35, mz + 0.31), M["chrome"]))
    objs.append(T.box("stand_ust", (0.012, 0.3, 0.012), (-0.24, 0.35, mz + 0.62), M["chrome"]))
    objs.append(T.box("stand_taban", (0.16, 0.3, 0.012), (-0.2, 0.35, mz + 0.006), M["leg"]))
    for k, dy in enumerate((0.26, 0.44)):
        cm = M["cones"][rng.randrange(len(M["cones"]))]
        objs.append(T.cone("bobin", 0.032, 0.014, 0.12, (-0.2, dy, mz + 0.072), cm, verts=24))
    if variant == "kumasli":
        for k in range(rng.randrange(2, 6)):
            fm = M["fabrics"][rng.randrange(len(M["fabrics"]))]
            objs.append(T.box("kumas", (0.26 + rng.random() * 0.06, 0.34, 0.012),
                              (0.08, -0.36 + rng.uniform(-0.02, 0.02), mz + 0.008 + k * 0.012), fm,
                              rot=(0, 0, rng.uniform(-8, 8)), bevel=0.004))
    for o in objs:
        o.pass_index = 1
    return T.collect(objs, name)


def chair(M, name):
    objs = [T.box("oturak", (0.4, 0.4, 0.035), (0, 0, 0.46), M["seat"], bevel=0.01)]
    for sx in (-0.17, 0.17):
        for sy in (-0.17, 0.17):
            objs.append(T.cyl("sandalye_ayak", 0.012, 0.45, (sx, sy, 0.225), M["leg"], verts=12))
    objs.append(T.box("arkalik", (0.03, 0.36, 0.24), (0.19, 0, 0.72), M["seat"], bevel=0.01))
    objs.append(T.box("arkalik_dikme", (0.02, 0.02, 0.3), (0.19, -0.15, 0.6), M["leg"]))
    objs.append(T.box("arkalik_dikme2", (0.02, 0.02, 0.3), (0.19, 0.15, 0.6), M["leg"]))
    for o in objs:
        o.pass_index = 2
    return T.collect(objs, name)


def crate(M, name):
    objs = [T.box("kasa", (0.4, 0.55, 0.28), (0, 0, 0.14), M["crate"], bevel=0.015)]
    objs.append(T.box("kasa_ici", (0.36, 0.5, 0.05), (0, 0, 0.27), M["fabrics"][2], bevel=0.02))
    return T.collect(objs, name)


# ------------------------------------------------------------------ salon
def hall(M, rng, light_on):
    T.plane("zemin", (30, 70), (0, 25, 0), M["floor"])
    for sx in (-0.95, 0.95):
        T.plane("serit", (0.08, 62), (sx, 26, 0.002), M["line"])
    T.plane("tavan", (30, 70), (0, 25, 5.2), M["ceil"], rot=(180, 0, 0))
    T.box("sol_duvar", (0.3, 70, 5.2), (-13, 25, 2.6), M["wall"])
    T.box("sag_duvar", (0.3, 70, 5.2), (13, 25, 2.6), M["wall"])
    T.box("arka_duvar", (26, 0.3, 5.2), (0, 52, 2.6), M["wall"])
    for i in range(12):                                        # yüksek pencereler (gün ışığı)
        y = -2 + i * 4.5
        for sx in (-12.84, 12.84):
            T.box("pencere", (0.02, 2.6, 1.3), (sx, y, 3.7), M["window"])
            T.box("pencere_kasa", (0.06, 2.7, 0.06), (sx, y, 3.02), M["frame"])
        T.area_light(f"gunisigi{i}", (-12.6, y, 3.7), (2.6, 1.3), 170, (0.78, 0.86, 1.0), rot=(0, 90, 0))
        T.area_light(f"gunisigi_s{i}", (12.6, y, 3.7), (2.6, 1.3), 120, (0.78, 0.86, 1.0), rot=(0, -90, 0))
    for i in range(3):
        T.box("arka_pencere", (5.5, 0.02, 1.6), (-7 + i * 7, 51.84, 3.5), M["window"])
    for y in range(-4, 52, 5):                                 # tavan kirişleri
        T.box("kiris", (26, 0.18, 0.45), (0, y, 4.95), M["steel"])
    for sx in (-3.3, 3.3):                                     # havalandırma kanalı
        T.cyl("kanal", 0.28, 62, (sx, 25, 4.45), M["duct"], rot=(90, 0, 0), verts=40)
    for y in range(4, 50, 8):                                  # kolonlar
        for sx in (-7.0, 7.0):
            T.box("kolon", (0.42, 0.42, 5.2), (sx, y, 2.6), M["wall"], bevel=0.01)
    # floresan armatürler: makine sıralarının üstünde; uzak yarısı sönük (duran fabrika)
    for lx in (-1.8, -4.3, 1.8, 4.3):
        for k in range(18):
            y = 0.2 + k * 2.6
            on = light_on(lx, y, rng)
            T.box("armatur", (0.16, 1.25, 0.06), (lx, y, 3.0), M["housing"], bevel=0.005)
            T.box("tup", (0.06, 1.18, 0.02), (lx, y, 2.965), M["tube_on"] if on else M["tube_off"])
            if on:
                T.area_light(f"floresan{lx}_{k}", (lx, y, 2.95), (0.1, 1.18), 55, T.kelvin(5200))
            T.cyl("askı", 0.004, 2.0, (lx, y - 0.5, 4.0), M["steel"], verts=6)
            T.cyl("askı", 0.004, 2.0, (lx, y + 0.5, 4.0), M["steel"], verts=6)


def populate(M, rng, n=17):
    variants = {"normal": station(M, "ist_normal", "normal", rng),
                "kumasli": station(M, "ist_kumasli", "kumasli", rng),
                "eski": station(M, "ist_eski", "eski", rng),
                "ortulu": station(M, "ist_ortulu", "ortulu", rng),
                "bos": station(M, "ist_bos", "bos", rng)}
    ch = chair(M, "sandalye")
    cr = crate(M, "kasa")
    for col in list(variants.values()) + [ch, cr]:
        T.hide_source(col)
    for side in (-1, 1):
        for lx in (1.8, 4.3):
            x = side * lx
            for k in range(n):
                y = 1.0 + k * 1.3
                far = y > 12
                r = rng.random()
                if far and r < 0.45:
                    v = "ortulu"
                elif r < 0.12:
                    v = "bos"                                  # makinesi sökülmüş masa
                if side < 0 and lx == 1.8 and k < 3:
                    v = "kumasli"                              # ön plandaki makineler dolu, iş yarım kalmış
                elif r < 0.35:
                    v = "kumasli"
                elif r < 0.5:
                    v = "eski"
                else:
                    v = "normal"
                T.instance(variants[v], (x, y, 0), 0 if side < 0 else 180, index=1)
                if rng.random() < 0.82:                        # boş sandalye (bazıları yamuk bırakılmış)
                    cx = x + side * -0.68 + rng.uniform(-0.05, 0.12) * -side
                    T.instance(ch, (cx, y + rng.uniform(-0.12, 0.12), 0),
                               (0 if side < 0 else 180) + rng.uniform(-25, 25), index=2)
                if rng.random() < 0.18:
                    T.instance(cr, (x + side * -0.75, y + 0.62, 0), rng.uniform(-10, 10))


def build(light_near=0.8, light_far=0.2, seed=4):
    rng = random.Random(seed)
    T.reset(seed)
    M = materials()

    def light_on(lx, y, r):
        p = light_near if y < 14 else light_far
        return r.random() < p
    hall(M, rng, light_on)
    populate(M, rng)
    T.world((0.012, 0.014, 0.018), 1.0)
    return M


def genis(pct=50, frames=(0,), n_frames=144):
    build()
    T.render_setup(samples=48, pct=pct)
    cam = T.camera((-0.8, -0.6, 1.05), (-2.6, 9.0, 0.88), lens=24, fstop=1.8, focus=1.9)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, n_frames - 1
    cam.location = (-0.8, -0.6, 1.05)
    cam.keyframe_insert("location", frame=0)
    cam.location = (-0.8, -0.35, 1.04)
    cam.keyframe_insert("location", frame=n_frames - 1)
    for fc in cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    for f in frames:
        T.render(f"fabrika_genis_{f:04d}", frame=f)


def yakin(pct=50, frames=(0,), loop=8):
    """Yakın çekim: tek makine, iğne döngüsü `loop` karede tamamlanır (sonsuz döngü).

    0. kare tam çizilir; diğer karelerde yalnız iğnenin hareket ettiği küçük bölge çizilir (hızlı).
    """
    from bpy_extras.object_utils import world_to_camera_view
    rng = random.Random(9)
    T.reset(9)
    M = materials()
    hall(M, rng, lambda lx, y, r: r.random() < 0.8)
    populate(M, rng)
    T.world((0.012, 0.014, 0.018), 1.0)
    mz = TABLE_H
    T.box("masa", (0.6, 1.15, 0.035), (0, 0, mz - 0.0175), M["top"], bevel=0.004)
    machine(M, M["mach"], (0, 0, mz))
    thread = T.mat("iplik", (0.85, 0.8, 0.65), rough=0.45, sheen=0.5)
    fab = M["fabrics"][0]
    T.box("kumas_alt", (0.36, 0.9, 0.003), (0.03, -0.2, mz + 0.0485), fab, bevel=0.001)
    T.box("kumas_ust", (0.3, 0.9, 0.003), (0.05, -0.2, mz + 0.0515), fab, rot=(0, 0, 0.6), bevel=0.001)
    for k in range(60):                                     # dikilmiş iz: iğnenin arkasında düzgün teyel
        x = -0.004 - k * 0.0042
        T.box("dikis", (0.0032, 0.0016, 0.0012), (x, -0.2, mz + 0.0538), thread, bevel=0.0005)
    # ipliğin yolu: yukarıdaki bobinden kol üstüne, gerginlik disklerine, iplik koluna, oradan iğneye
    T.curve("iplik_yolu", [(0.0, 0.25, mz + 0.9), (0.01, 0.05, mz + 0.4), (0.03, -0.1, mz + 0.352),
                           (0.066, -0.168, mz + 0.258), (0.07, -0.168, mz + 0.235), (0.095, -0.182, mz + 0.3),
                           (0.07, -0.195, mz + 0.2), (0.03, -0.2, mz + 0.14), (0.014, -0.2, mz + 0.118)],
            0.00055, thread, res=24)
    T.box("led", (0.03, 0.008, 0.002), (0.03, -0.2, mz + 0.1195), T.emission("led_isik", T.kelvin(5600), 2.5))
    T.spot_light("led_spot", (0.03, -0.2, mz + 0.117), 0.35, (0.0, -0.2, mz), T.kelvin(5600), size_deg=80, blend=0.8,
                 radius=0.012)
    grp = bpy.data.objects.new("igne_grubu", None)
    bpy.context.scene.collection.objects.link(grp)
    parts = needle(M, (0, 0, mz), 0.0)
    parts.append(T.cyl("iplik_ust", 0.0006, 0.09, (0.012, -0.2, mz + 0.12), thread, verts=6))
    for o in parts:
        o.parent = grp
    sc = bpy.context.scene
    for f in range(loop + 1):
        grp.location = (0, 0, -0.022 * (0.5 - 0.5 * math.cos(2 * math.pi * f / loop)))
        grp.keyframe_insert("location", frame=f)
    T.render_setup(samples=64, pct=pct)
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    cam = T.camera((0.5, -0.72, mz + 0.19), (-0.02, -0.18, mz + 0.085), lens=85, fstop=3.2)
    cam.data.dof.focus_distance = (Vector((0.0, -0.2, mz + 0.07)) - cam.location).length
    bpy.context.view_layer.update()
    pts = [Vector((dx, -0.2 + dy, mz + dz)) for dx in (-0.02, 0.03) for dy in (-0.02, 0.02) for dz in (0.02, 0.2)]
    uv = [world_to_camera_view(sc, cam, p) for p in pts]
    bx0, bx1 = max(0, min(v.x for v in uv) - 0.04), min(1, max(v.x for v in uv) + 0.04)
    by0, by1 = max(0, min(v.y for v in uv) - 0.04), min(1, max(v.y for v in uv) + 0.04)
    for f in frames:
        sc.render.use_border = f != 0
        sc.render.use_crop_to_border = False
        sc.render.border_min_x, sc.render.border_max_x = bx0, bx1
        sc.render.border_min_y, sc.render.border_max_y = by0, by1
        T.render(f"fabrika_yakin_{f:04d}", frame=f)
    print("bolge", round(bx0, 3), round(bx1, 3), round(by0, 3), round(by1, 3))


if __name__ == "__main__":
    mode = sys.argv[1]
    pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    frames = [int(a) for a in sys.argv[3:]] or [0]
    {"genis": genis, "yakin": yakin}[mode](pct, frames)


def dene(pct=25, cams=()):
    """Hızlı kadraj denemesi: aynı sahneden birkaç kamera açısı (düşük örnek)."""
    build()
    T.render_setup(samples=12, pct=pct)
    for i, (loc, tgt, lens, focus) in enumerate(cams):
        for o in [o for o in bpy.data.objects if o.type == "CAMERA"]:
            bpy.data.objects.remove(o, do_unlink=True)
        T.camera(loc, tgt, lens=lens, fstop=2.0, focus=focus)
        T.render(f"fabrika_dene_{i}")
