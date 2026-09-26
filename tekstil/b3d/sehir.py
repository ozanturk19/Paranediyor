"""Temsili Suriye şehri: düz damlı taş binalar, su depoları, çanak antenler, kubbeler, minareler,
tepede kale; sokakta dolaşık elektrik kabloları, jeneratör, bankamatik.

Kullanım: python3 sehir.py aksam|gece_acik|gece_kapali|sokak|atm [yüzde]
"""
import math, random, sys
import bpy
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ortak3d as T

FLOOR = 3.2


def window_mat(name, stone, lit=0.0, seed=0):
    """Taş duvar + pencere ızgarası. lit: pencerelerin yanık olma oranı (gece)."""
    m = T.mat(name, stone, rough=0.85, var=0.3, var_scale=0.6, bump=0.15, bump_scale=4)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])

    def fract_band(axis_out, period, lo, hi, offset=0.0):
        div = nt.nodes.new("ShaderNodeMath")
        div.operation = "DIVIDE"
        div.inputs[1].default_value = period
        nt.links.new(axis_out, div.inputs[0])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.inputs[1].default_value = offset
        nt.links.new(div.outputs[0], add.inputs[0])
        fr = nt.nodes.new("ShaderNodeMath")
        fr.operation = "FRACT"
        nt.links.new(add.outputs[0], fr.inputs[0])
        g1 = nt.nodes.new("ShaderNodeMath")
        g1.operation = "GREATER_THAN"
        g1.inputs[1].default_value = lo
        nt.links.new(fr.outputs[0], g1.inputs[0])
        l1 = nt.nodes.new("ShaderNodeMath")
        l1.operation = "LESS_THAN"
        l1.inputs[1].default_value = hi
        nt.links.new(fr.outputs[0], l1.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(g1.outputs[0], mul.inputs[0])
        nt.links.new(l1.outputs[0], mul.inputs[1])
        return mul.outputs[0]
    # pencereler hem X hem Y yönündeki cephelerde: iki yön bandının en büyüğü
    wx = fract_band(sep.outputs["X"], 2.6, 0.3, 0.7)
    wy = fract_band(sep.outputs["Y"], 2.6, 0.3, 0.7)
    wz = fract_band(sep.outputs["Z"], FLOOR, 0.35, 0.8)
    # cephe yönüne göre yatay eksen: X'e bakan cephede Y, Y'ye bakan cephede X kullanılır
    sn = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Normal"], sn.inputs["Vector"])
    ax = nt.nodes.new("ShaderNodeMath")
    ax.operation = "ABSOLUTE"
    nt.links.new(sn.outputs["X"], ax.inputs[0])
    ay = nt.nodes.new("ShaderNodeMath")
    ay.operation = "ABSOLUTE"
    nt.links.new(sn.outputs["Y"], ay.inputs[0])
    facx = nt.nodes.new("ShaderNodeMath")
    facx.operation = "GREATER_THAN"
    nt.links.new(ax.outputs[0], facx.inputs[0])
    nt.links.new(ay.outputs[0], facx.inputs[1])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "FLOAT"
    nt.links.new(facx.outputs[0], mx.inputs["Factor"])
    nt.links.new(wx, mx.inputs["A"])
    nt.links.new(wy, mx.inputs["B"])
    az = nt.nodes.new("ShaderNodeMath")                   # çatılarda pencere olmasın
    az.operation = "LESS_THAN"
    az.inputs[1].default_value = 0.5
    sz = nt.nodes.new("ShaderNodeMath")
    sz.operation = "ABSOLUTE"
    nt.links.new(sn.outputs["Z"], sz.inputs[0])
    nt.links.new(sz.outputs[0], az.inputs[0])
    mx2 = nt.nodes.new("ShaderNodeMath")
    mx2.operation = "MULTIPLY"
    nt.links.new(mx.outputs["Result"], mx2.inputs[0])
    nt.links.new(az.outputs[0], mx2.inputs[1])
    win = nt.nodes.new("ShaderNodeMath")
    win.operation = "MULTIPLY"
    nt.links.new(mx2.outputs[0], win.inputs[0])
    nt.links.new(wz, win.inputs[1])
    ground = nt.nodes.new("ShaderNodeMath")             # zemin katında pencere yok (dükkân kepengi dokusu yerine)
    ground.operation = "GREATER_THAN"
    ground.inputs[1].default_value = 2.9
    nt.links.new(sep.outputs["Z"], ground.inputs[0])
    win2 = nt.nodes.new("ShaderNodeMath")
    win2.operation = "MULTIPLY"
    nt.links.new(win.outputs[0], win2.inputs[0])
    nt.links.new(ground.outputs[0], win2.inputs[1])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    nt.links.new(win2.outputs[0], mixc.inputs["Factor"])
    base_link = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
    if base_link is not None:
        nt.links.new(base_link, mixc.inputs["A"])
    else:
        mixc.inputs["A"].default_value = (*stone, 1)
    mixc.inputs["B"].default_value = (0.02, 0.022, 0.025, 1)
    nt.links.new(mixc.outputs["Result"], b.inputs["Base Color"])
    if lit > 0:
        # her pencereye rastgele açık/kapalı: pencere hücresi başına beyaz gürültü + bina başına rastgele
        cell = nt.nodes.new("ShaderNodeVectorMath")
        cell.operation = "SNAP"
        cell.inputs[1].default_value = (2.6, 2.6, FLOOR)
        nt.links.new(tc.outputs["Object"], cell.inputs[0])
        oi = nt.nodes.new("ShaderNodeObjectInfo")
        addv = nt.nodes.new("ShaderNodeVectorMath")
        addv.operation = "ADD"
        nt.links.new(cell.outputs[0], addv.inputs[0])
        nt.links.new(oi.outputs["Location"], addv.inputs[1])
        wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
        wn.noise_dimensions = "3D"
        nt.links.new(addv.outputs[0], wn.inputs["Vector"])
        on = nt.nodes.new("ShaderNodeMath")
        on.operation = "LESS_THAN"
        on.inputs[1].default_value = lit
        nt.links.new(wn.outputs["Value"], on.inputs[0])
        em = nt.nodes.new("ShaderNodeMath")
        em.operation = "MULTIPLY"
        nt.links.new(on.outputs[0], em.inputs[0])
        nt.links.new(win2.outputs[0], em.inputs[1])
        tint = nt.nodes.new("ShaderNodeMix")                   # sıcak/soğuk pencere ışığı karışımı
        tint.data_type = "RGBA"
        nt.links.new(wn.outputs["Color"], tint.inputs["Factor"])
        tint.inputs["A"].default_value = (*T.kelvin(2700), 1)
        tint.inputs["B"].default_value = (*T.kelvin(4200), 1)
        nt.links.new(tint.outputs["Result"], b.inputs["Emission Color"])
        st = nt.nodes.new("ShaderNodeMath")
        st.operation = "MULTIPLY"
        st.inputs[1].default_value = 6.0
        nt.links.new(em.outputs[0], st.inputs[0])
        nt.links.new(st.outputs[0], b.inputs["Emission Strength"])
    return m


def building_parts(M, rng, w, d, floors, stone_mat):
    h = floors * FLOOR
    objs = [T.box("bina", (w, d, h), (0, 0, h / 2), stone_mat, bevel=0.03, seg=1)]
    objs.append(T.box("korkuluk", (w + 0.1, d + 0.1, 0.5), (0, 0, h + 0.25), M["parapet"]))
    objs.append(T.box("korkuluk_ic", (w - 0.3, d - 0.3, 0.52), (0, 0, h + 0.26), M["roof"]))
    for k in range(rng.randrange(1, 4)):                          # su depoları
        x, y = rng.uniform(-w / 2 + 1, w / 2 - 1), rng.uniform(-d / 2 + 1, d / 2 - 1)
        tank = M["tank_w"] if rng.random() < 0.6 else M["tank_b"]
        objs.append(T.cyl("depo", 0.55, 1.1, (x, y, h + 0.8), tank, verts=20))
    if rng.random() < 0.8:                                        # çanak antenler
        for k in range(rng.randrange(1, 5)):
            x, y = rng.uniform(-w / 2 + 0.8, w / 2 - 0.8), rng.uniform(-d / 2 + 0.8, d / 2 - 0.8)
            dish = T.sphere("canak", 0.45, (x, y, h + 1.0), M["dish"], scale=(1, 1, 0.35), seg=16)
            dish.rotation_euler = (math.radians(rng.uniform(40, 70)), 0, math.radians(rng.uniform(0, 360)))
            objs.append(dish)
            objs.append(T.cyl("anten_ayak", 0.03, 0.8, (x, y, h + 0.6), M["metal"], verts=6))
    if rng.random() < 0.5:
        objs.append(T.box("merdiven_kule", (2.4, 2.4, 2.6), (rng.uniform(-w / 4, w / 4), rng.uniform(-d / 4, d / 4), h + 1.3),
                          stone_mat, bevel=0.03, seg=1))
    for k in range(rng.randrange(0, 3)):                          # balkonlar (tek cephe)
        fz = rng.randrange(1, floors) * FLOOR + 0.1
        objs.append(T.box("balkon", (w * 0.4, 1.0, 0.18), (rng.uniform(-w / 4, w / 4), -d / 2 - 0.5, fz), M["parapet"]))
    return objs


def city(M, rng, lit=0.0, n=46, spacing=17.0, center=(110, 160)):
    stones = [window_mat(f"tas{i}", c, lit, i) for i, c in enumerate(
        [(0.62, 0.55, 0.45), (0.7, 0.64, 0.54), (0.55, 0.5, 0.43), (0.66, 0.6, 0.52), (0.5, 0.46, 0.4)])]
    variants = []
    for i in range(14):
        w, d = rng.uniform(9, 15), rng.uniform(9, 15)
        floors = rng.choice([2, 3, 3, 4, 4, 5, 6])
        col = T.collect(building_parts(M, rng, w, d, floors, stones[i % len(stones)]), f"bina{i}")
        T.hide_source(col)
        variants.append(col)
    cx, cy = center
    for i in range(-n // 2, n // 2):
        for j in range(-n // 2, n // 2):
            x = cx + i * spacing + rng.uniform(-1.5, 1.5)
            y = cy + j * spacing + rng.uniform(-1.5, 1.5)
            if math.hypot(x - 260, y - 420) < 140:              # kale tepesinin üstüne bina koyma
                continue
            v = variants[rng.randrange(len(variants))]
            T.instance(v, (x, y, 0), rng.choice([0, 90, 180, 270]) + rng.uniform(-3, 3), index=1 + rng.randrange(250))
    # kubbeli camiler ve minareler
    for k in range(9):
        x, y = cx + rng.uniform(-n / 2, n / 2) * spacing, cy + rng.uniform(-n / 2, n / 2) * spacing
        T.cyl("cami_govde", 7, 7, (x, y, 3.5), M["stone_light"], verts=40)
        T.sphere("kubbe", 7.2, (x, y, 7), M["dome"], scale=(1, 1, 0.8), seg=32)
        mx, my = x + 9, y + 3
        T.cyl("minare", 1.1, 30, (mx, my, 15), M["stone_light"], verts=16)
        T.cyl("minare_serefe", 1.7, 0.6, (mx, my, 24), M["stone_light"], verts=16)
        T.cone("minare_kulah", 1.2, 0.05, 4, (mx, my, 32), M["dome"], verts=16)


def citadel(M, loc):
    x, y = loc
    T.cone("kale_tepe", 120, 70, 40, (x, y, 20), M["hill"], verts=64)
    T.cyl("kale_sur", 72, 12, (x, y, 46), M["stone_light"], verts=48)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        T.box("burc", (9, 9, 18), (x + 70 * math.cos(a), y + 70 * math.sin(a), 49), M["stone_light"], bevel=0.3)
    T.box("kale_ic", (60, 40, 14), (x, y, 57), M["stone_light"])


def materials():
    return dict(
        parapet=T.mat("korkuluk", (0.6, 0.55, 0.47), rough=0.9, var=0.3),
        roof=T.mat("dam", (0.35, 0.33, 0.3), rough=0.95, var=0.4, var_scale=0.3),
        tank_w=T.mat("depo_beyaz", (0.75, 0.75, 0.72), rough=0.4),
        tank_b=T.mat("depo_siyah", (0.04, 0.04, 0.045), rough=0.5),
        dish=T.mat("canak", (0.8, 0.8, 0.78), rough=0.35, metal=0.2),
        metal=T.mat("metal", (0.3, 0.3, 0.32), rough=0.5, metal=0.8),
        stone_light=T.mat("acik_tas", (0.72, 0.65, 0.53), rough=0.85, var=0.3, var_scale=0.4, bump=0.2, bump_scale=2),
        dome=T.mat("kubbe", (0.35, 0.4, 0.38), rough=0.5, metal=0.3),
        hill=T.mat("tepe", (0.45, 0.4, 0.32), rough=0.95, var=0.4, var_scale=0.05, bump=0.3, bump_scale=0.5),
        ground=T.mat("zemin", (0.32, 0.29, 0.25), rough=0.95, var=0.4, var_scale=0.02),
        asphalt=T.mat("asfalt", (0.06, 0.06, 0.06), rough=0.75, var=0.5, var_scale=0.2, bump=0.2, bump_scale=20),
        cable=T.mat("kablo", (0.015, 0.015, 0.015), rough=0.4),
        pole=T.mat("direk", (0.4, 0.38, 0.35), rough=0.8, var=0.3),
        gen=T.mat("jenerator", (0.12, 0.25, 0.18), rough=0.5, metal=0.4, var=0.4, var_scale=3),
        shutter=T.mat("kepenk", (0.35, 0.36, 0.37), rough=0.4, metal=0.8, var=0.4, var_scale=2),
    )


def aerial(lit, sun_elev, pct, name, night=False):
    rng = random.Random(21)
    T.reset(21)
    M = materials()
    T.plane("zemin", (3000, 3000), (0, 0, 0), M["ground"])
    city(M, rng, lit=lit)
    citadel(M, (260, 420))
    if night:
        T.sky_world(sun_elev=-7.0, sun_rot=60, strength=0.03, dust=2.0)      # gün batımından sonra: lacivert geçiş
        T.sun("ay", 30, 200, 0.02, (0.6, 0.7, 1.0), angle=1.0)
        for k in range(160):                                     # sokak lambaları (turuncu)
            x, y = rng.uniform(-280, 280), rng.uniform(-280, 280)
            if lit > 0.3 or rng.random() < 0.3:
                T.point_light("lamba", (x, y, 6), 120, T.kelvin(2200), radius=0.2)
    else:
        T.sky_world(sun_elev=sun_elev, sun_rot=60, strength=0.1, dust=4.0, air=1.5)
        T.sun("gunes", sun_elev, 180 - 60, 1.6, T.kelvin(3300), angle=0.8)
    T.render_setup(samples=48, pct=pct, clamp=10)
    T.camera((-120, -150, 70), (180, 300, 20), lens=45)
    T.render(name)


def aksam(pct=50):
    aerial(0.0, 6.0, pct, "sehir_aksam")


def gece_acik(pct=50):
    aerial(0.65, 0, pct, "sehir_gece_acik", night=True)


def gece_kapali(pct=50):
    aerial(0.18, 0, pct, "sehir_gece_kapali", night=True)


def street(pct, name, cam):
    """Dar sokak, alacakaranlık: dolaşık kablolar, direk, jeneratör, kepenkler, bankamatik."""
    rng = random.Random(33)
    T.reset(33)
    M = materials()
    T.plane("yol", (200, 200), (0, 0, 0), M["asphalt"])
    stones = [window_mat(f"tas{i}", c, 0.35, i) for i, c in enumerate(
        [(0.62, 0.55, 0.45), (0.7, 0.64, 0.54), (0.55, 0.5, 0.43)])]
    for side in (-1, 1):                                          # sokağın iki yanında bitişik binalar
        y = -10.0
        while y < 90:
            w = rng.uniform(7, 12)
            floors = rng.choice([3, 4, 4, 5])
            h = floors * FLOOR
            x = side * (5.5 + 6)
            T.box("bina", (12, w, h), (x, y + w / 2, h / 2), stones[rng.randrange(3)], bevel=0.03, seg=1)
            T.box("kepenk", (0.1, w * 0.7, 2.6), (side * 5.45, y + w / 2, 1.3), M["shutter"])
            for k in range(floors - 1):                           # balkon ve klima
                if rng.random() < 0.6:
                    T.box("balkon", (1.0, w * 0.5, 0.15), (side * 5.0, y + w / 2, (k + 1) * FLOOR + 0.1), M["parapet"])
                if rng.random() < 0.5:
                    T.box("klima", (0.35, 0.8, 0.55), (side * 5.3, y + rng.uniform(1, w - 1), (k + 1) * FLOOR + 1.2),
                          T.mat("klima", (0.8, 0.8, 0.78), rough=0.5))
            y += w + 0.05
    T.box("kaldirim_sol", (1.5, 100, 0.15), (-4.75, 40, 0.075), M["pole"])
    T.box("kaldirim_sag", (1.5, 100, 0.15), (4.75, 40, 0.075), M["pole"])
    poles = [(-4.3, 6), (4.2, 18), (-4.3, 30), (4.2, 44), (-4.3, 58)]
    for (px, py) in poles:                                        # beton direkler + dolaşık kablolar
        T.cyl("direk", 0.16, 9, (px, py, 4.5), M["pole"], verts=12)
        T.box("travers", (1.6, 0.12, 0.12), (px, py, 8.6), M["metal"])
    for (ax, ay), (bx, by) in zip(poles[:-1], poles[1:]):
        for k in range(16):                                       # direkten direğe sarkan kablolar
            z0 = rng.uniform(6.8, 8.6)
            z1 = rng.uniform(6.8, 8.6)
            sag = rng.uniform(0.6, 2.2)
            pts = []
            for u in [i / 8 for i in range(9)]:
                x = ax + (bx - ax) * u + rng.uniform(-0.15, 0.15)
                yy = ay + (by - ay) * u
                z = z0 + (z1 - z0) * u - sag * 4 * u * (1 - u)
                pts.append((x, yy, z))
            T.curve("kablo", pts, rng.uniform(0.015, 0.035), M["cable"])
        for k in range(6):                                        # direkten binalara uzanan kaçak hatlar
            wx = rng.choice([-5.4, 5.4])
            wy = ay + rng.uniform(-4, 8)
            wz = rng.uniform(4, 11)
            pts = [(ax, ay, rng.uniform(7, 8.5)), ((ax + wx) / 2, (ay + wy) / 2, min(wz, 7) - rng.uniform(0.3, 1.2)),
                   (wx, wy, wz)]
            T.curve("kacak", pts, 0.02, M["cable"])
    T.box("jenerator", (1.1, 2.2, 1.4), (3.4, 12, 0.85), M["gen"], bevel=0.05)
    T.box("jenerator_kapak", (1.12, 0.8, 0.9), (3.4, 11.6, 0.9), M["metal"])
    for k in range(4):
        pts = [(3.0, 12.5 + k * 0.1, 1.3), (3.8, 13 + k * 0.3, 3), (5.4, 13.5 + k * 0.5, 4 + k)]
        T.curve("jen_kablo", pts, 0.012, M["cable"])
    T.cyl("sokak_lambasi_direk", 0.07, 6, (-4.4, 22, 3), M["metal"], verts=10)
    T.point_light("sokak_lambasi", (-3.9, 22, 5.9), 260, T.kelvin(2100), radius=0.1)
    T.point_light("sokak_lambasi2", (3.9, 48, 5.9), 200, T.kelvin(2100), radius=0.1)
    T.point_light("dukkan", (4.6, 8, 2.4), 40, T.kelvin(3000), radius=0.3)
    atm_wall = T.box("banka_cephe", (0.2, 5, 3), (5.4, 34, 1.5), T.mat("banka", (0.3, 0.28, 0.27), rough=0.6))
    T.box("atm_govde", (0.35, 0.9, 1.6), (5.2, 34, 1.1), T.mat("atm", (0.22, 0.23, 0.25), rough=0.35, metal=0.6), bevel=0.02)
    T.box("atm_ekran", (0.02, 0.42, 0.32), (5.02, 34, 1.45), T.emission("atm_ekran", (0.9, 0.15, 0.08), 3.0))
    T.box("atm_tus", (0.1, 0.4, 0.05), (5.05, 34, 1.12), T.mat("tus", (0.5, 0.5, 0.5), rough=0.3, metal=0.8), rot=(0, 20, 0))
    T.sky_world(sun_elev=-3.5, sun_rot=0, strength=0.06, dust=3.0)
    T.render_setup(samples=64, pct=pct, clamp=8)
    loc, tgt, lens, fstop, focus = cam
    T.camera(loc, tgt, lens=lens, fstop=fstop, focus=focus)
    T.render(name)


def sokak(pct=50):
    street(pct, "sehir_sokak", ((0.6, -4, 1.6), (0.0, 30, 6.5), 22, 4.0, 14))


def atm(pct=50):
    street(pct, "sehir_atm", ((2.4, 31.2, 1.55), (5.1, 34.2, 1.3), 40, 2.2, None))


if __name__ == "__main__":
    mode = sys.argv[1]
    pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    {"aksam": aksam, "gece_acik": gece_acik, "gece_kapali": gece_kapali, "sokak": sokak, "atm": atm}[mode](pct)
