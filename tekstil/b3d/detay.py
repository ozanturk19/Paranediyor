"""Yakın detay sahneleri: kilit ve zincir (yaptırımlar kalkıyor), bankamatik (bankacılık zayıf).

Kullanım: python3 detay.py kilit|atm [yüzde] [kare...]
"""
import math, os, random, sys
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ortak3d as T


def bokeh_background(rng, n=40, dist=(6, 14), colors=((1.0, 0.6, 0.25), (1.0, 0.8, 0.5), (0.6, 0.75, 1.0))):
    for k in range(n):
        c = colors[rng.randrange(len(colors))]
        x, y, z = rng.uniform(-6, 6), rng.uniform(*dist), rng.uniform(-1, 4)
        T.sphere("isik", rng.uniform(0.04, 0.12), (x, y, z), T.emission(f"bokeh{k}", c, rng.uniform(4, 15)), seg=12)


def chain_link(name, m):
    o = T.torus(name, 0.022, 0.0065, (0, 0, 0), m, maj=32, mino=12)
    o.scale = (1.65, 1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def kilit(pct=50, frames=(0,), n_open=7):
    rng = random.Random(3)
    T.reset(3)
    rust = T.mat("pas", (0.2, 0.09, 0.05), rough=0.85, metal=0.4, var=0.5, var_scale=30, bump=0.5, bump_scale=80)
    steel = T.mat("zincir_celik", (0.55, 0.55, 0.56), rough=0.32, metal=1.0, var=0.35, var_scale=40, bump=0.15, bump_scale=120)
    brass = T.mat("pirinc", (0.72, 0.52, 0.2), rough=0.3, metal=1.0, var=0.25, var_scale=25, bump=0.1, bump_scale=90)
    dark = T.mat("anahtar_deligi", (0.01, 0.01, 0.01), rough=0.6)
    for k in range(-4, 5):                                      # paslı demir kapı parmaklıkları
        T.cyl("parmaklik", 0.018, 3.0, (k * 0.13, 0.05, 0.4), rust, verts=16)
    for z in (-0.45, 0.35):
        T.box("yatay", (1.3, 0.03, 0.05), (0, 0.05, z), rust, bevel=0.005)
    # zincir: iki parmaklığın arasından sarkan halkalar (katener)
    pts = []
    N = 15
    for i in range(N):
        u = i / (N - 1)
        x = -0.36 + 0.72 * u
        z = 0.12 - 0.22 * 4 * u * (1 - u)
        pts.append(Vector((x, -0.01 + 0.02 * math.sin(u * 9), z)))
    for i in range(N - 1):
        p, q = pts[i], pts[i + 1]
        o = chain_link(f"halka{i}", steel)
        o.location = (p + q) / 2
        d = q - p
        yaw = math.atan2(d.z, d.x)
        o.rotation_euler = (math.radians(90) if i % 2 else 0, -yaw, 0)
    # asma kilit: gövde + U kilit dili (açılma animasyonu için ayrı nesne)
    body = T.box("kilit_govde", (0.075, 0.032, 0.066), (0.0, -0.03, -0.14), brass, bevel=0.008, seg=4)
    T.cyl("anahtar_yuvasi", 0.007, 0.004, (0.0, -0.047, -0.155), dark, rot=(90, 0, 0), verts=20)
    T.box("anahtar_yarik", (0.003, 0.004, 0.012), (0.0, -0.048, -0.163), dark)
    shackle_parts = [T.torus("dil_ust", 0.026, 0.0055, (0.0, -0.03, -0.082), steel, rot=(90, 0, 0), maj=40, mino=12)]
    shackle_parts += [T.cyl("dil_sol", 0.0055, 0.03, (-0.026, -0.03, -0.097), steel, verts=16),
                      T.cyl("dil_sag", 0.0055, 0.03, (0.026, -0.03, -0.097), steel, verts=16)]
    for o in shackle_parts:
        o.pass_index = 5
    # alt yarısını kes: torusun alt yarısı gövdenin içinde kalır, görünmez
    piv = bpy.data.objects.new("dil_pivot", None)
    piv.location = (0.026, -0.03, -0.11)
    bpy.context.scene.collection.objects.link(piv)
    bpy.context.view_layer.update()                               # ebeveyn dönüşümü güncel olsun
    for o in shackle_parts:
        o.parent = piv
        o.matrix_parent_inverse = piv.matrix_world.inverted()
    body.pass_index = 5
    sc = bpy.context.scene
    for f in range(n_open + 1):                                  # dil yukarı fırlar ve döner
        u = f / n_open
        e = 1 - (1 - u) ** 3
        piv.location = (0.026, -0.03, -0.11 + 0.024 * e)
        piv.rotation_euler = (0, 0, math.radians(-100 * max(0, (u - 0.35) / 0.65) ** 1.2))
        piv.keyframe_insert("location", frame=f)
        piv.keyframe_insert("rotation_euler", frame=f)
    bokeh_background(rng, 60, (3, 9))
    T.world((0.01, 0.012, 0.02), 1.0)
    T.area_light("anahtar_isik", (-0.8, -0.9, 0.6), (0.8, 0.8), 60, T.kelvin(3200), rot=(60, 0, -40))
    T.area_light("dolgu", (0.9, -0.6, -0.1), (1.0, 1.0), 8, (0.6, 0.7, 1.0), rot=(80, 0, 55))
    T.area_light("arka", (0.2, 0.8, 0.6), (1.0, 0.4), 40, T.kelvin(2600), rot=(-60, 0, 0))
    T.render_setup(samples=64, pct=pct, clamp=8)
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    cam = T.camera((0.16, -0.42, -0.06), (0.0, -0.03, -0.12), lens=70, fstop=2.4)
    b = T.border_for([(x, -0.03, z) for x in (-0.06, 0.1) for z in (-0.12, -0.02)], cam, 0.05)
    for f in frames:
        T.set_border(None if f == 0 else b)
        T.render(f"kilit_{f:04d}", frame=f)


def screen_image(path, w=512, h=400):
    """Bankamatik ekranı: uyarı üçgeni + üstü çizili kart simgesi (yazısız, evrensel)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (8, 20, 45))
    d = ImageDraw.Draw(im)
    for y in range(h):
        c = int(8 + 18 * y / h)
        d.line([(0, y), (w, y)], fill=(c // 2, c, 45 + c))
    cx, cy, s = w // 2, int(h * 0.4), 90
    d.polygon([(cx, cy - s), (cx - s * 1.1, cy + s * 0.75), (cx + s * 1.1, cy + s * 0.75)], fill=(245, 180, 20))
    d.polygon([(cx, cy - s + 22), (cx - s * 0.9, cy + s * 0.62), (cx + s * 0.9, cy + s * 0.62)], fill=(20, 16, 10))
    d.rectangle([cx - 8, cy - 40, cx + 8, cy + 20], fill=(245, 180, 20))
    d.ellipse([cx - 10, cy + 30, cx + 10, cy + 50], fill=(245, 180, 20))
    x0, y0 = cx - 70, int(h * 0.74)
    d.rounded_rectangle([x0, y0, x0 + 140, y0 + 80], 10, outline=(200, 210, 225), width=6)
    d.rectangle([x0, y0 + 16, x0 + 140, y0 + 30], fill=(200, 210, 225))
    d.line([(x0 - 15, y0 + 95), (x0 + 155, y0 - 15)], fill=(230, 60, 50), width=12)
    im.save(path)
    return path


def atm(pct=50, frames=(0,)):
    rng = random.Random(8)
    T.reset(8)
    stone = T.mat("duvar", (0.5, 0.45, 0.38), rough=0.9, var=0.4, var_scale=3, bump=0.3, bump_scale=6)
    body = T.mat("atm_govde", (0.16, 0.17, 0.19), rough=0.3, metal=0.7, var=0.15, var_scale=10)
    trim = T.mat("atm_cerceve", (0.55, 0.56, 0.58), rough=0.2, metal=1.0)
    black = T.mat("siyah", (0.01, 0.01, 0.012), rough=0.25)
    key = T.mat("tus", (0.62, 0.62, 0.64), rough=0.25, metal=0.9)
    T.plane("kaldirim", (8, 8), (0, 0, 0), T.mat("kaldirim", (0.2, 0.19, 0.18), rough=0.8, var=0.4, bump=0.3))
    T.box("duvar", (4, 0.4, 3.2), (0, 0.45, 1.6), stone)
    T.box("kasa", (0.86, 0.3, 1.75), (0, 0.18, 0.875), body, bevel=0.02)
    T.box("cerceve", (0.7, 0.02, 0.9), (0, 0.025, 1.2), trim, bevel=0.01)
    img = bpy.data.images.load(screen_image(os.path.join(T.OUT, "atm_ekran.png")))
    scr = bpy.data.materials.new("ekran")
    scr.use_nodes = True
    nt = scr.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 2.2
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.012, 1.42), rotation=(math.radians(80), 0, 0))
    s = bpy.context.object
    s.scale = (0.36, 0.28, 1)
    s.data.materials.append(scr)
    s.pass_index = 7
    T.box("ekran_catisi", (0.5, 0.12, 0.03), (0, -0.04, 1.62), body, bevel=0.005)
    T.box("tus_paneli", (0.3, 0.2, 0.02), (0.02, -0.06, 1.05), black, rot=(35, 0, 0))
    for i in range(4):
        for j in range(3):
            T.box("tus", (0.05, 0.035, 0.012), (-0.05 + j * 0.065, -0.07 - i * 0.03, 1.08 - i * 0.02 + 0.002), key,
                  rot=(35, 0, 0), bevel=0.003)
    T.box("kart_yuvasi", (0.09, 0.02, 0.012), (0.24, 0.01, 1.2), black)
    T.box("kart_isik", (0.1, 0.01, 0.004), (0.24, 0.0, 1.21), T.emission("yesil", (0.1, 1.0, 0.3), 1.0))
    T.box("para_yuvasi", (0.3, 0.02, 0.03), (0, 0.01, 0.86), black)
    T.box("tabela", (1.2, 0.08, 0.35), (0, 0.2, 2.35), T.emission("tabela", (0.25, 0.55, 0.9), 1.2), bevel=0.02)
    T.box("kepenk", (1.4, 0.05, 2.4), (1.3, 0.24, 1.2), T.mat("kepenk", (0.3, 0.31, 0.33), rough=0.4, metal=0.8,
                                                                  var=0.4, var_scale=4))
    bokeh_background(rng, 40, (-6, -14))
    T.world((0.006, 0.008, 0.014), 1.0)
    T.point_light("sokak", (-1.5, -2.5, 3.2), 120, T.kelvin(2200), radius=0.2)
    T.area_light("tabela_isik", (0, -0.15, 2.2), (1.0, 0.2), 6, (0.4, 0.65, 1.0), rot=(0, 0, 0))
    T.render_setup(samples=64, pct=pct, clamp=8)
    T.camera((-0.75, -1.25, 1.62), (0.02, 0.05, 1.3), lens=38, fstop=2.2)
    for f in frames:
        T.render(f"atm_{f:04d}", frame=f)


if __name__ == "__main__":
    mode = sys.argv[1]
    pct = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    frames = [int(a) for a in sys.argv[3:]] or [0]
    {"kilit": kilit, "atm": atm}[mode](pct, frames)
