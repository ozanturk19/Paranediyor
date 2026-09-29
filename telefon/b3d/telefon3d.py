"""Telefon filmi 3D sahneleri (Blender 5 Python modülü, Cycles CPU).

Kullanım:  python3 telefon3d.py <sahne> [yüzde] [örnek]
  hero    : modern telefon, 4 katman ayrı ayrı (ekran, gövde, kart, arka) şeffaf zeminde -> patlatma animasyonu
  eski    : 2016 dönemi telefon ahşap masada (ekran köşeleri JSON'a yazılır)
  devlet  : karanlık sahnede kaide üstünde telefon + arkada yükselecek sütunlar (ayrı şeffaf katman)
  kule    : gece tepede baz istasyonu, uzakta kasaba ışıkları; açık ve kapalı iki durum
  cep     : kot pantolon arka cebi; zemin, telefon ve cep kapağı ayrı katmanlar
Çıktı: TEKSTIL_3D_OUT klasörüne çok katmanlı EXR (+ gerekirse .json yardımcı bilgi).
"""
import json, math, os, random, sys
import bpy
import bmesh
from mathutils import Vector, Euler
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ortak3d as T

PW, PH, PT = 0.0716, 0.1476, 0.0083           # telefon ölçüleri (m)


# ------------------------------------------------------------------ yardımcılar
def rrect_pts(w, h, r, nseg=12):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for k in range(nseg + 1):
            a = math.radians(a0 + 90 * k / nseg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism(name, pts, t, loc=(0, 0, 0), m=None, bevel=0.0, index=0, smooth_sides=True):
    """2B çokgeni t kalınlığında kalıba dök (yan yüzler yumuşak, üst/alt düz)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    top = [bm.verts.new((x, y, t / 2)) for x, y in pts]
    bot = [bm.verts.new((x, y, -t / 2)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((bot[i], bot[j], top[j], top[i]))
        f.smooth = smooth_sides
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if m is not None:
        o.data.materials.append(m)
    if bevel > 0:
        md = o.modifiers.new("pah", "BEVEL")
        md.width = bevel
        md.segments = 3
        md.limit_method = "ANGLE"
        md.angle_limit = math.radians(40)
    o.pass_index = index
    return o


def rrect(name, w, h, t, r, loc=(0, 0, 0), m=None, bevel=0.0, index=0):
    return prism(name, rrect_pts(w, h, r), t, loc, m, bevel, index)


def img_material(name, path, strength=1.0, emit=True, rough=0.3):
    img = bpy.data.images.load(path)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emit:
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = strength
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        gl = nt.nodes.new("ShaderNodeBsdfGlossy")                  # ekran camının yansıması
        gl.inputs["Roughness"].default_value = 0.05
        gl.inputs["Color"].default_value = (0.04, 0.04, 0.045, 1)
        ad = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(em.outputs[0], ad.inputs[0])
        nt.links.new(gl.outputs[0], ad.inputs[1])
        nt.links.new(ad.outputs[0], out.inputs[0])
    else:
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        b.inputs["Roughness"].default_value = rough
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(b.outputs[0], out.inputs[0])
    return m


def uv_plane(name, w, h, loc, m, rot=(0, 0, 0), index=0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    o.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(m)
    o.pass_index = index
    return o


def parent_all(objs, name, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = e
    e.location = loc
    e.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()
    return e


def screen_px(pts, cam):
    """Dünya noktalarını 1080x1920 ekran pikseline çevir."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    out = []
    for p in pts:
        v = world_to_camera_view(sc, cam, Vector(p))
        out.append([v.x * 1080, (1 - v.y) * 1920, v.z])
    return out


def save_json(name, data):
    os.makedirs(T.OUT, exist_ok=True)
    with open(os.path.join(T.OUT, name + ".json"), "w") as f:
        json.dump(data, f, indent=1)


def transparent(on=True):
    bpy.context.scene.render.film_transparent = on


def only(objs_visible, all_objs):
    vis = set(o.name for o in objs_visible)
    for o in all_objs:
        o.hide_render = o.name not in vis


# ------------------------------------------------------------------ ekran görüntüleri (PIL, yazısız/genel)
def lock_screen(path, w=720, h=1480):
    """Modern kilit ekranı: koyu zemin, sarı-camgöbeği ışık akışı, saat 20:27 (2027'ye selam)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import numpy as np
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32) + np.array([6, 8, 14], np.float32)
    for cx, cy, rx, ry, col, k in ((0.2, 0.75, 0.7, 0.35, (255, 190, 40), 0.9), (0.85, 0.55, 0.6, 0.3, (40, 200, 255), 0.6),
                                   (0.5, 0.95, 0.9, 0.25, (255, 120, 30), 0.5)):
        r = ((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2
        img += np.exp(-r * 2.2)[..., None] * np.array(col, np.float32) * k
    for i in range(7):                                         # ince ışık kurdeleleri
        ph = i * 0.9
        yc = h * (0.62 + 0.05 * i) + 60 * np.sin(xx / w * 5 + ph)
        img += np.exp(-((yy - yc) / 6) ** 2)[..., None] * np.array([255, 210, 90], np.float32) * (0.25 - 0.025 * i)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    fd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "altyazi", "fonts")
    try:
        f1 = ImageFont.truetype(os.path.join(fd, "Montserrat.ttf"), 210)
        f1.set_variation_by_axes([300])
        f2 = ImageFont.truetype(os.path.join(fd, "Inter.ttf"), 44)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    d.text((w / 2, 330), "20:27", font=f1, fill=(245, 245, 250), anchor="mm")
    d.text((w / 2, 470), "Cuma, 1 Ocak", font=f2, fill=(220, 220, 230), anchor="mm")
    d.ellipse([w / 2 - 16, 34, w / 2 + 16, 66], fill=(0, 0, 0))            # ön kamera deliği
    m = Image.new("L", (w, h), 0)                                           # yuvarlak köşeler
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=int(w * 0.14), fill=255)
    black = Image.new("RGB", (w, h), (0, 0, 0))
    Image.composite(im, black, m).save(path)
    return path


def old_home(path, w=620, h=1100):
    """2016 dönemi ana ekran: düz renk simgeler, kalın durum çubuğu (yazısız, genel)."""
    from PIL import Image, ImageDraw
    import numpy as np
    yy = np.linspace(0, 1, h)[:, None, None]
    img = (np.array([20, 60, 110]) * (1 - yy) + np.array([60, 20, 70]) * yy) * np.ones((h, w, 3))
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 48], fill=(10, 10, 12))
    for i in range(4):                                           # sinyal çubukları
        d.rectangle([w - 150 + i * 14, 36 - i * 7, w - 142 + i * 14, 40], fill=(230, 230, 230))
    d.rectangle([w - 70, 16, w - 22, 38], outline=(230, 230, 230), width=3)
    d.rectangle([w - 67, 19, w - 50, 35], fill=(230, 230, 230))
    cols = [(230, 80, 60), (60, 170, 90), (70, 130, 230), (240, 180, 40), (150, 90, 210), (40, 190, 200),
            (230, 120, 170), (120, 120, 130)]
    rng = random.Random(4)
    for r in range(5):
        for c in range(4):
            x, y = 50 + c * 140, 110 + r * 170
            col = cols[rng.randrange(len(cols))]
            d.rounded_rectangle([x, y, x + 100, y + 100], radius=22, fill=col)
            d.rounded_rectangle([x + 28, y + 28, x + 72, y + 72], radius=10, outline=(255, 255, 255), width=5)
            d.rectangle([x + 10, y + 115, x + 90, y + 125], fill=(210, 210, 220))
    for c in range(4):                                           # alt dok
        x = 50 + c * 140
        d.rounded_rectangle([x, h - 150, x + 100, h - 50], radius=22, fill=cols[(c * 3) % len(cols)])
    im.save(path)
    return path


# ------------------------------------------------------------------ malzemeler
def materials():
    return dict(
        titan=T.mat("titan", (0.42, 0.40, 0.37), rough=0.32, metal=1.0, var=0.12, var_scale=60, bump=0.05, bump_scale=300),
        glass=T.mat("on_cam", (0.004, 0.004, 0.005), rough=0.03, spec=0.8, coat=1.0),
        back=T.mat("arka_cam", (0.018, 0.026, 0.045), rough=0.38, spec=0.6, coat=0.9, var=0.05, var_scale=40),
        bump=T.mat("kamera_ada", (0.022, 0.03, 0.05), rough=0.18, coat=1.0),
        lens=T.mat("lens", (0.002, 0.002, 0.004), rough=0.02, spec=1.0, coat=1.0),
        ring=T.mat("halka", (0.55, 0.53, 0.5), rough=0.18, metal=1.0),
        flash=T.mat("flas", (0.9, 0.82, 0.6), rough=0.3, spec=0.8, coat=1.0),
        pcb=T.mat("kart", (0.012, 0.045, 0.03), rough=0.42, coat=0.4, var=0.2, var_scale=200),
        chip=T.mat("cip", (0.03, 0.03, 0.032), rough=0.3, coat=0.2),
        lid=T.mat("cip_kapak", (0.6, 0.6, 0.62), rough=0.22, metal=1.0, var=0.1, var_scale=300),
        gold=T.mat("altin", (0.95, 0.68, 0.25), rough=0.2, metal=1.0),
        foil=T.mat("pil", (0.08, 0.08, 0.085), rough=0.35, metal=0.6, var=0.15, var_scale=30, bump=0.05, bump_scale=80),
        label=T.mat("etiket", (0.6, 0.6, 0.58), rough=0.5),
        flex=T.mat("flex", (0.7, 0.35, 0.04), rough=0.35, coat=0.5),
        button=T.mat("tus", (0.46, 0.44, 0.41), rough=0.25, metal=1.0),
        gasket=T.mat("conta", (0.01, 0.01, 0.01), rough=0.6),
    )


def modern_phone(M, ui_path, name="tel"):
    """Telefonu katmanlarıyla kur (yerel eksen: ekran +Z yönüne bakar). Katman sözlüğü döndürür."""
    L = {"ekran": [], "govde": [], "kart": [], "arka": []}
    # ---- gövde (çerçeve + tuşlar + iç conta)
    L["govde"].append(rrect(f"{name}_cerceve", PW, PH, PT * 0.72, 0.0105, (0, 0, 0), M["titan"], bevel=0.0007, index=2))
    for y, hh in ((0.028, 0.012), (0.012, 0.012)):
        L["govde"].append(T.box(f"{name}_ses", (0.0012, hh, 0.0022), (-PW / 2 - 0.0004, y, 0), M["button"], bevel=0.0004, index=2))
    L["govde"].append(T.box(f"{name}_guc", (0.0012, 0.018, 0.0022), (PW / 2 + 0.0004, 0.02, 0), M["button"], bevel=0.0004, index=2))
    for k in (-1, 1):                                          # anten çizgileri
        L["govde"].append(T.box(f"{name}_anten", (PW + 0.0002, 0.0012, PT * 0.73), (0, k * 0.058, 0), M["gasket"], index=2))
    # ---- ekran
    L["ekran"].append(rrect(f"{name}_on_cam", PW - 0.0006, PH - 0.0006, 0.0010, 0.0102, (0, 0, PT / 2 - 0.0005),
                            M["glass"], bevel=0.0004, index=1))
    ui = img_material(f"{name}_ui", ui_path, strength=1.6)
    L["ekran"].append(uv_plane(f"{name}_goruntu", PW - 0.0032, PH - 0.0032, (0, 0, PT / 2 + 0.00002), ui, index=1))
    # ---- iç kart + pil
    kart = L["kart"]
    kart.append(T.box(f"{name}_pcb", (PW - 0.010, 0.040, 0.0009), (0, PH / 2 - 0.028, 0), M["pcb"], index=3))
    kart.append(T.box(f"{name}_pcb2", (0.016, 0.070, 0.0009), (PW / 2 - 0.013, 0.005, 0), M["pcb"], index=3))
    kart.append(T.box(f"{name}_soc_alt", (0.0165, 0.0165, 0.0008), (-0.006, PH / 2 - 0.030, 0.0008), M["chip"], bevel=0.0003, index=3))
    kart.append(T.box(f"{name}_soc", (0.0135, 0.0135, 0.0009), (-0.006, PH / 2 - 0.030, 0.0016), M["lid"], bevel=0.0004, index=3))
    rng = random.Random(7)
    for i in range(14):                                        # küçük çipler
        w_, h_ = rng.uniform(0.003, 0.008), rng.uniform(0.003, 0.007)
        x_ = rng.uniform(-PW / 2 + 0.008, PW / 2 - 0.008)
        y_ = rng.uniform(PH / 2 - 0.045, PH / 2 - 0.012)
        if abs(x_ + 0.006) < 0.012 and abs(y_ - (PH / 2 - 0.030)) < 0.012:
            continue
        kart.append(T.box(f"{name}_cip{i}", (w_, h_, 0.0007), (x_, y_, 0.0008), M["chip"], bevel=0.0002, index=3))
    for i in range(26):                                        # altın yollar
        horiz = i % 2 == 0
        L_ = rng.uniform(0.006, 0.02)
        x_ = rng.uniform(-PW / 2 + 0.007, PW / 2 - 0.007)
        y_ = rng.uniform(PH / 2 - 0.046, PH / 2 - 0.01)
        size = (L_, 0.00035, 0.0001) if horiz else (0.00035, L_, 0.0001)
        kart.append(T.box(f"{name}_yol{i}", size, (x_, y_, 0.00047), M["gold"], index=3))
    for i in range(6):                                         # kondansatörler
        kart.append(T.box(f"{name}_kond{i}", (0.0016, 0.0009, 0.0009), (0.004 + i * 0.0024, PH / 2 - 0.016, 0.0009),
                          M["gold"], index=3))
    kart.append(T.box(f"{name}_pil", (PW - 0.014, 0.084, 0.0042), (-0.003, -0.022, 0.0), M["foil"], bevel=0.0012, index=3))
    kart.append(T.box(f"{name}_pil_etiket", (0.030, 0.030, 0.0001), (-0.003, -0.018, 0.00215), M["label"], index=3))
    kart.append(T.box(f"{name}_flex", (0.010, 0.030, 0.0003), (0.018, -0.056, 0.001), M["flex"], index=3))
    kart.append(T.box(f"{name}_flex2", (0.030, 0.006, 0.0003), (0.0, PH / 2 - 0.050, 0.0012), M["flex"], index=3))
    # ---- arka kapak + kamera adası
    arka = L["arka"]
    arka.append(rrect(f"{name}_arka", PW - 0.0006, PH - 0.0006, 0.0010, 0.0102, (0, 0, -PT / 2 + 0.0005), M["back"],
                      bevel=0.0004, index=4))
    bx, by = -PW / 2 + 0.0205, PH / 2 - 0.0205
    arka.append(rrect(f"{name}_ada", 0.031, 0.031, 0.0016, 0.0075, (bx, by, -PT / 2 - 0.0006), M["bump"], bevel=0.0005,
                      index=4))
    for dx, dy in ((-0.0072, 0.0072), (-0.0072, -0.0072), (0.0072, 0.0)):
        z = -PT / 2 - 0.0016
        arka.append(T.cyl(f"{name}_lens_h", 0.0056, 0.0012, (bx + dx, by + dy, z), M["ring"], verts=48, index=4))
        arka.append(T.cyl(f"{name}_lens", 0.0043, 0.0014, (bx + dx, by + dy, z - 0.0002), M["lens"], verts=48, index=4))
    arka.append(T.cyl(f"{name}_flas", 0.0017, 0.0006, (bx + 0.0074, by + 0.0092, -PT / 2 - 0.0014), M["flash"], verts=24,
                      index=4))
    return L


def studio_lights(scale=1.0, warm=1.0):
    T.area_light("tepe", (-0.35 * scale, -0.25 * scale, 0.55 * scale), (0.5 * scale, 0.35 * scale), 38 * scale ** 2 * warm,
                 T.kelvin(4200), rot=(40, 0, -35))
    T.area_light("sag_kontur", (0.45 * scale, 0.25 * scale, 0.12 * scale), (0.08 * scale, 0.6 * scale), 45 * scale ** 2,
                 (0.55, 0.8, 1.0), rot=(90, 0, 115))
    T.area_light("sol_kontur", (-0.45 * scale, 0.3 * scale, 0.05 * scale), (0.06 * scale, 0.5 * scale), 50 * scale ** 2,
                 T.kelvin(2700), rot=(90, 0, -120))
    T.area_light("alt_dolgu", (0.0, -0.5 * scale, -0.3 * scale), (0.6 * scale, 0.3 * scale), 3 * scale ** 2, (0.8, 0.85, 1.0),
                 rot=(-60, 0, 0))


# ================================================================== HERO: 4 katman
def hero(pct=100, samples=64):
    T.reset(1)
    M = materials()
    ui = lock_screen(os.path.join(T.OUT, "hero_ekran.png"))
    L = modern_phone(M, ui)
    allo = [o for v in L.values() for o in v]
    ph = parent_all(allo, "telefon", (0, 0, 0), (90, 0, 26))
    ph.rotation_euler = Euler((math.radians(90 + 6), math.radians(-4), math.radians(26)), "XYZ")
    T.world((0.0, 0.0, 0.0), 0.0)
    studio_lights(1.0)
    T.render_setup(samples=samples, pct=pct, clamp=10)
    transparent(True)
    cam = T.camera((0.0, -0.40, 0.027), (0.004, 0.0, -0.017), lens=85, fstop=5.6)
    bpy.context.view_layer.update()
    # patlatma için: telefonun normal ekseni ekranda hangi yöne düşüyor (metre başına piksel)
    mw = ph.matrix_world
    c = mw @ Vector((0, 0, 0))
    n = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    p0, p1 = screen_px([c, c + n * 0.05], cam)
    corners = screen_px([mw @ Vector((sx * (PW / 2 - 0.0016), sy * (PH / 2 - 0.0016), PT / 2)) for sx, sy in
                         ((-1, 1), (1, 1), (1, -1), (-1, -1))], cam)
    save_json("hero", dict(center=p0, normal_px_per_m=[(p1[0] - p0[0]) / 0.05, (p1[1] - p0[1]) / 0.05],
                           depth_scale_per_m=(p0[2] / p1[2] - 1) / 0.05, screen_corners=corners,
                           layers={"ekran": PT / 2, "govde": 0.0, "kart": 0.0, "arka": -PT / 2}))
    for k, objs in L.items():
        only(objs, allo)
        T.render(f"hero_{k}")


# ================================================================== ESKİ: 2016 telefonu masada
def eski(pct=100, samples=64):
    T.reset(2)
    wood = T.mat("ahsap", (0.14, 0.08, 0.045), rough=0.55, var=0.55, var_scale=2.5, bump=0.15, bump_scale=25, coat=0.15)
    body = T.mat("plastik", (0.012, 0.012, 0.014), rough=0.22, coat=0.6, var=0.06, var_scale=20)
    trim = T.mat("krom_serit", (0.5, 0.5, 0.52), rough=0.25, metal=1.0)
    glass = T.mat("cam", (0.005, 0.005, 0.006), rough=0.05, coat=1.0, spec=0.7)
    dust = T.mat("toz", (0.3, 0.28, 0.25), rough=0.9, alpha=0.25)
    T.plane("masa", (1.6, 1.2), (0, 0, 0), wood)
    w, h, t = 0.074, 0.150, 0.0095
    parts = [rrect("eski_govde", w, h, t, 0.009, (0, 0, t / 2), body, bevel=0.0012, index=1)]
    parts.append(rrect("eski_cerceve", w + 0.0006, h + 0.0006, 0.0018, 0.0093, (0, 0, t * 0.55), trim, bevel=0.0005, index=1))
    parts.append(rrect("eski_cam", w - 0.002, h - 0.002, 0.0006, 0.008, (0, 0, t + 0.0003), glass, index=1))
    home = img_material("eski_ui", old_home(os.path.join(T.OUT, "eski_ekran.png")), strength=0.9)
    sw, sh = 0.062, 0.110
    parts.append(uv_plane("eski_goruntu", sw, sh, (0, 0.002, t + 0.00062), home, index=2))
    parts.append(T.cyl("eski_ev_tusu", 0.0055, 0.0008, (0, -0.064, t + 0.0003), trim, verts=40, index=1))
    parts.append(T.box("eski_ahize", (0.012, 0.0014, 0.0004), (0, 0.066, t + 0.0005), T.mat("izgara", (0.1, 0.1, 0.1)), index=1))
    phone = parent_all(parts, "eski_tel", (0.0, 0.0, 0.0), (0, 0, -14))
    # masada hayat: kalem, fincan halkası izi, kâğıt
    T.cyl("kalem", 0.004, 0.14, (0.11, 0.06, 0.004), T.mat("kalem", (0.6, 0.45, 0.05), rough=0.4), rot=(0, 90, 30), verts=6)
    T.box("kagit", (0.21, 0.297, 0.0004), (-0.13, 0.1, 0.0002), T.mat("kagit", (0.75, 0.73, 0.68), rough=0.9, var=0.1),
          rot=(0, 0, 12))
    T.torus("fincan_izi", 0.035, 0.0012, (0.09, -0.11, 0.0001), T.mat("iz", (0.12, 0.06, 0.03), rough=0.8), maj=48, mino=6)
    T.world((0.02, 0.022, 0.03), 0.6)
    T.area_light("pencere", (-0.9, 0.3, 0.7), (0.9, 0.6), 30, (0.75, 0.85, 1.0), rot=(0, -50, 20))
    T.point_light("lamba", (0.5, -0.4, 0.45), 9, T.kelvin(2500), radius=0.08)
    T.render_setup(samples=samples, pct=pct, clamp=8)
    cam = T.camera((0.035, -0.19, 0.25), (0.0, 0.004, 0.0), lens=50, fstop=2.8, focus=0.31)
    mw = bpy.data.objects["eski_goruntu"].matrix_world
    corners = screen_px([mw @ Vector((sx * sw / 2, sy * sh / 2, 0)) for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1))], cam)
    save_json("eski", dict(screen_corners=corners))
    if not os.environ.get("SADECE_JSON"):
        T.render("eski")


# ================================================================== DEVLET: kaide, telefon, sütunlar
def devlet(pct=100, samples=64):
    T.reset(3)
    M = materials()
    floor = T.mat("mermer", (0.02, 0.02, 0.022), rough=0.22, coat=0.6, var=0.4, var_scale=1.5, bump=0.02, bump_scale=10)
    stone = T.mat("tas", (0.36, 0.36, 0.35), rough=0.8, var=0.35, var_scale=2, bump=0.35, bump_scale=14)
    plinth = T.mat("kaide", (0.015, 0.015, 0.016), rough=0.35, coat=0.3)
    T.plane("zemin", (30, 30), (0, 0, 0), floor)
    ped = [T.cyl("kaide", 0.13, 0.12, (0, 0, 0.06), plinth, verts=64, bevel=0.004)]
    ui = lock_screen(os.path.join(T.OUT, "devlet_ekran.png"))
    L = modern_phone(M, ui, "dv")
    ph_objs = [o for v in L.values() for o in v]
    parent_all(ph_objs, "dv_tel", (0, 0.0, 0.12 + PH / 2 + 0.002), (90 - 4, 0, 18))
    cols = []
    R = 2.9
    for i in range(9):                                         # yarım daire sütunlar (arkada)
        a = math.radians(-60 + i * 15)
        x, y = R * math.sin(a), 2.0 + R * math.cos(a) * 0.55
        cols.append(T.box("kaide_s", (0.62, 0.62, 0.22), (x, y, 0.11), stone, bevel=0.02))
        c_ = T.cyl("sutun", 0.25, 4.6, (x, y, 0.22 + 2.3), stone, verts=20)
        for f_ in c_.data.polygons:                          # köşeli yüzler: yivli taş sütun hissi
            f_.use_smooth = False
        cols.append(c_)
        cols.append(T.box("baslik", (0.6, 0.6, 0.2), (x, y, 0.22 + 4.6 + 0.1), stone, bevel=0.02))
    cols.append(T.box("kiris", (5.6, 0.8, 0.5), (0, 2.0 + R * 0.55 * 0.6, 5.2), stone, bevel=0.03))
    cols.append(T.box("basamak1", (6.5, 2.4, 0.08), (0, 2.6, 0.04), stone, bevel=0.01))
    T.world((0.0, 0.0, 0.0), 0.0)
    T.spot_light("tepe_spot", (0.1, -0.35, 1.3), 45, (0, 0, 0.18), T.kelvin(3600), size_deg=22, blend=0.5, radius=0.05)
    T.area_light("telefon_on", (0.25, -0.6, 0.35), (0.3, 0.3), 6, T.kelvin(4500), rot=(70, 0, 20))
    T.area_light("sutun_ust", (-2.5, -1.5, 6.5), (2.0, 2.0), 900, T.kelvin(5200), rot=(35, 0, -40))
    T.area_light("sutun_alt", (1.5, -0.5, 0.3), (2.0, 0.4), 60, T.kelvin(2400), rot=(-70, 0, 20))
    T.area_light("arka_isik", (0, 4.5, 3.0), (6.0, 3.0), 400, (0.35, 0.45, 0.7), rot=(-110, 0, 0))
    T.render_setup(samples=samples, pct=pct, clamp=8)
    cam = T.camera((0.0, -0.85, 0.2), (0.0, 0.0, 0.3), lens=30, fstop=4.0, focus=0.85)
    p = screen_px([(0, 0, 0.12 + PH / 2), (0, 0, 0.12 + PH)], cam)
    save_json("devlet", dict(phone_center=p[0], phone_top=p[1]))
    allo = [o for o in bpy.data.objects if o.type == "MESH"]
    only([o for o in allo if o not in cols], allo)
    transparent(False)
    T.render("devlet_sahne")
    only(cols, allo)
    transparent(True)
    T.render("devlet_sutun")


# ================================================================== KULE: gece baz istasyonu
def kule(pct=100, samples=64):
    T.reset(4)
    rng = random.Random(4)
    ground = T.mat("toprak", (0.035, 0.034, 0.03), rough=0.95, var=0.5, var_scale=0.08, bump=0.4, bump_scale=1.5)
    slope_m = T.mat("yamac", (0.008, 0.008, 0.007), rough=0.95, var=0.4, var_scale=0.02)
    steel = T.mat("kule_celik", (0.38, 0.39, 0.41), rough=0.4, metal=0.9)
    panel = T.mat("anten", (0.72, 0.72, 0.7), rough=0.45)
    T.plane("ova", (3000, 3000), (0, 0, 0), ground)
    slope = T.plane("yamac", (1400, 700), (0, 600, 0), slope_m, rot=(9, 0, 0))
    Hh, base, top = 34.0, 3.4, 1.0
    x0, y0 = 0.0, 22.0
    parts = []

    def P(z, sx, sy):
        s_ = base + (top - base) * z / Hh
        return Vector((x0 + sx * s_ / 2, y0 + sy * s_ / 2, z))

    def beam(a, b, r=0.06):
        d = b - a
        o = T.cyl("kiris", r, d.length, (a + b) / 2, steel, verts=8)
        o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        parts.append(o)
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    for sx, sy in corners:
        beam(P(0, sx, sy), P(Hh, sx, sy), 0.13)
    z = 0.0
    while z < Hh - 0.1:
        z2 = min(Hh, z + 3.4)
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            beam(P(z, *a), P(z2, *b), 0.05)
            beam(P(z, *b), P(z2, *a), 0.05)
            beam(P(z2, *a), P(z2, *b), 0.055)
        z = z2
    beam(Vector((x0, y0, Hh)), Vector((x0, y0, Hh + 4.0)), 0.09)          # tepe direği
    for k in range(3):                                          # sektör antenleri
        a = math.radians(k * 120 + 20)
        for lvl in (0.0, -2.6):
            c = Vector((x0 + 0.95 * math.cos(a), y0 + 0.95 * math.sin(a), Hh - 1.0 + lvl))
            o = T.box("anten_panel", (0.34, 0.13, 1.7), c, panel, bevel=0.02)
            o.rotation_euler = (0, 0, a + math.pi / 2)
            parts.append(o)
    for k in range(2):                                          # mikrodalga çanakları
        a = math.radians(200 + k * 70)
        o = T.cyl("canak", 0.5, 0.28, (x0 + 1.0 * math.cos(a), y0 + 1.0 * math.sin(a), Hh - 6.5 - k * 1.6), panel, verts=32)
        o.rotation_euler = (math.radians(90), 0, a + math.pi / 2)
        parts.append(o)
    # tabanda teknik kabin + çit
    T.box("kabin", (3.2, 2.4, 2.6), (x0 + 4.5, y0 - 2.0, 1.3), T.mat("kabin", (0.5, 0.5, 0.48), rough=0.6, var=0.3), bevel=0.03)
    for k in range(16):
        T.cyl("cit", 0.04, 2.0, (x0 - 6 + k * 1.0, y0 - 7.0, 1.0), steel, verts=6)
    T.box("cit_tel", (16, 0.02, 1.6), (x0 + 1.5, y0 - 7.0, 1.1), T.mat("tel", (0.3, 0.3, 0.3), rough=0.5, metal=0.8, alpha=0.25))
    red_on = T.emission("ikaz_acik", (1.0, 0.04, 0.02), 80)
    red_off = T.mat("ikaz_kapali", (0.08, 0.01, 0.01), rough=0.4)
    beacons = [T.sphere("ikaz", 0.2, (x0, y0, Hh + 4.2), red_on, seg=16),
               T.sphere("ikaz2", 0.14, (x0 + base * 0.33, y0 - base * 0.33, Hh * 0.5), red_on, seg=12)]
    win_on = T.emission("pencere_acik", T.kelvin(2500), 30)
    win_on2 = T.emission("pencere_acik2", T.kelvin(4000), 22)
    win_off = T.mat("pencere_kapali", (0.015, 0.015, 0.015), rough=0.8)
    src = [T.box("isik_a", (1.6, 1.6, 1.6), (0, -50, -50), win_on), T.box("isik_b", (1.6, 1.6, 1.6), (0, -50, -50), win_on2),
           T.box("isik_c", (1.6, 1.6, 1.6), (0, -50, -50), win_off)]
    cols = [T.collect([o], f"isik_{i}") for i, o in enumerate(src)]
    for c in cols:
        c.objects[0].location = (0, 0, 0)
    tan9 = math.tan(math.radians(9))
    towns = [(-260, 420, 150, 60), (120, 520, 110, 45), (-40, 330, 70, 30), (330, 380, 90, 40)]
    lights = []
    for i in range(2600):
        cx, cy, rx, ry = towns[i % len(towns)]
        r_ = rng.uniform(0, 1) ** 0.7
        a = rng.uniform(0, 2 * math.pi)
        x, y = cx + rx * r_ * math.cos(a), cy + ry * r_ * math.sin(a)
        zz = max(0.0, (y - 250) * tan9) + 1.0
        on = rng.random() < 0.82
        lights.append((x, y, zz, on))
    inst_on = [instance(cols[0] if (k % 5) else cols[1], (x, y, z)) for k, (x, y, z, on) in enumerate(lights)]
    for c in cols:
        hide_source(c)
    T.world((0.003, 0.005, 0.013), 1.0)
    T.sun("ay", 20, 150, 0.9, (0.55, 0.65, 1.0), angle=0.6)
    flood = T.spot_light("projektor", (x0 + 3.0, y0 - 3.5, 2.8), 9000, (x0, y0, 16.0), T.kelvin(3800), size_deg=40, blend=0.6)
    T.area_light("kasaba_hale", (0, 450, 90), (900, 300), 5000, T.kelvin(2300), rot=(180, 0, 0))
    T.render_setup(samples=samples, pct=pct, clamp=8, bounces=4)
    cam = T.camera((7.0, 4.0, 1.7), (-0.5, 22.0, 17.5), lens=26, fstop=None)
    tp = screen_px([Vector((x0, y0, Hh + 4.2))], cam)
    save_json("kule", dict(top=tp[0]))
    T.render("kule_acik")
    for b in beacons:
        b.data.materials[0] = red_off
    flood.data.energy = 0
    for k, e in enumerate(inst_on):
        if rng.random() < 0.9:
            e.instance_collection = cols[2]
    bpy.data.objects["kasaba_hale"].data.energy = 600
    T.render("kule_kapali")


def instance(col, loc):
    e = bpy.data.objects.new("kopya", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = col
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def hide_source(col):
    lc = bpy.context.view_layer.layer_collection.children[col.name]
    lc.exclude = True


# ================================================================== CEP: kot arka cebi
def denim_mat(name, base=(0.018, 0.04, 0.1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 0.12
    b.inputs["Sheen Tint"].default_value = (*[min(1, c * 4) for c in base], 1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(35))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 900
    wv.inputs["Distortion"].default_value = 2
    wv.inputs["Detail"].default_value = 2
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 18
    nz.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*[c * 0.55 for c in base], 1)
    mix.inputs["B"].default_value = (*[min(1, c * 2.4 + 0.03) for c in base], 1)
    mt = nt.nodes.new("ShaderNodeMath")
    mt.operation = "MULTIPLY"
    nt.links.new(wv.outputs["Fac"], mt.inputs[0])
    nt.links.new(nz.outputs["Fac"], mt.inputs[1])
    nt.links.new(mt.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.35
    bp.inputs["Distance"].default_value = 0.001
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def cep(pct=100, samples=64):
    T.reset(5)
    M = materials()
    denim = denim_mat("kot")
    denim2 = denim_mat("kot_cep", (0.02, 0.045, 0.11))
    thread = T.mat("iplik", (0.75, 0.45, 0.12), rough=0.6, sheen=0.4)
    copper = T.mat("percin", (0.6, 0.33, 0.18), rough=0.3, metal=1.0, var=0.3, var_scale=200)
    bpy.ops.mesh.primitive_plane_add(size=0.7, location=(0, 0, 0))
    base = bpy.context.object
    base.data.materials.append(denim)
    # cep kapağı: beşgen yama (üst kenarı açık)
    pw_, ph_ = 0.15, 0.165
    pts = [(-pw_ / 2, ph_ / 2), (-pw_ / 2, -ph_ / 2 + 0.035), (0, -ph_ / 2), (pw_ / 2, -ph_ / 2 + 0.035), (pw_ / 2, ph_ / 2)]
    patch = prism("cep_yama", pts, 0.0025, (0, 0, 0.0075), denim2, bevel=0.0012, index=5)
    stitch = []
    for inset, zz in ((0.004, 0.0091), (0.0075, 0.0091)):
        q = [(-pw_ / 2 + inset, ph_ / 2 - 0.003), (-pw_ / 2 + inset, -ph_ / 2 + 0.035 + inset * 0.3),
             (0, -ph_ / 2 + inset * 1.1), (pw_ / 2 - inset, -ph_ / 2 + 0.035 + inset * 0.3), (pw_ / 2 - inset, ph_ / 2 - 0.003)]
        for a, b in zip(q[:-1], q[1:]):
            n = max(2, int(math.dist(a, b) / 0.004))
            for k in range(n):
                u0, u1 = k / n, (k + 0.6) / n
                p0 = (a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0, zz)
                p1 = (a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1, zz)
                stitch.append(T.curve("dikis", [p0, p1], 0.0005, thread, res=2, index=5))
    for k in range(38):                                         # üst kenar bandı dikişi
        x = -pw_ / 2 + 0.004 + k * (pw_ - 0.008) / 38
        stitch.append(T.curve("dikis_ust", [(x, ph_ / 2 - 0.012, 0.0091), (x + 0.0024, ph_ / 2 - 0.012, 0.0091)], 0.0005,
                              thread, res=2, index=5))
    rivets = [T.cyl("percin", 0.0035, 0.002, (sx * (pw_ / 2 - 0.006), ph_ / 2 - 0.006, 0.0095), copper, verts=24, index=5)
              for sx in (-1, 1)]
    # yama bitişikte kumaşa hafif gölge veren kalın kenar
    ui = lock_screen(os.path.join(T.OUT, "cep_ekran.png"))
    L = modern_phone(M, ui, "cp")
    ph_objs = [o for v in L.values() for o in v]
    # telefon: arkası kameraya dönük, dik, alt kısmı cebin içinde (cep ağzının altında ~%55)
    parent_all(ph_objs, "cp_tel", (0.004, 0.044, 0.0045), (0, 180, 3))
    T.world((0.02, 0.022, 0.03), 0.5)
    T.area_light("pencere", (-0.35, 0.25, 0.45), (0.5, 0.4), 9, T.kelvin(4800), rot=(-30, -35, 0))
    T.area_light("sicak", (0.4, -0.2, 0.25), (0.3, 0.3), 2.5, T.kelvin(2600), rot=(40, 50, 0))
    T.area_light("kontur", (0.0, 0.5, 0.12), (0.5, 0.1), 4, (0.6, 0.75, 1.0), rot=(-80, 0, 0))
    T.render_setup(samples=samples, pct=pct, clamp=8)
    cam = T.camera((0.022, -0.17, 0.22), (0.0, 0.035, 0.0), lens=50, fstop=2.8, focus=0.28)
    mw = bpy.data.objects["cp_tel"].matrix_world
    pts_ = screen_px([mw @ Vector((0, 0, 0)), mw @ Vector((0, 0.05, 0))], cam)
    lip = screen_px([(-pw_ / 2, ph_ / 2, 0.009), (pw_ / 2, ph_ / 2, 0.009)], cam)
    save_json("cep", dict(phone_center=pts_[0], up_px_per_5cm=[pts_[1][0] - pts_[0][0], pts_[1][1] - pts_[0][1]],
                          lip=lip))
    allo = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE")]
    front = [patch] + stitch + rivets
    only([o for o in allo if o.name not in set(x.name for x in ph_objs)], allo)
    transparent(False)
    T.render("cep_zemin")
    only(ph_objs, allo)
    transparent(True)
    T.render("cep_tel")
    only(front, allo)
    T.render("cep_yama")


if __name__ == "__main__":
    mode = sys.argv[1]
    pct = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    smp = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    {"hero": hero, "eski": eski, "devlet": devlet, "kule": kule, "cep": cep}[mode](pct, smp)
