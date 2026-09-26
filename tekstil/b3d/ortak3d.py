"""Blender (bpy) yardımcıları: sahne kurulumu, malzemeler, basit modeller, kamera, çizim.

Çizimler çok katmanlı EXR olarak kaydedilir (renk + derinlik + nesne numarası); montaj tarafı
bunları `exr_oku` ile okur ve renk işlemini kendisi yapar.
"""
import math, os, random
import bpy
from mathutils import Vector

OUT = os.environ.get("TEKSTIL_3D_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plakalar"))


def reset(seed=1):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    random.seed(seed)
    return bpy.context.scene


def render_setup(samples=64, res=(1080, 1920), pct=100, clamp=6.0, bounces=6):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.use_light_tree = True
    c.max_bounces = bounces
    c.sample_clamp_indirect = clamp
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = pct
    sc.render.film_transparent = False
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_object_index = True
    s = sc.render.image_settings
    if hasattr(s, "media_type"):                  # Blender 5: çok katmanlı görüntü ayrı bir ortam türü
        s.media_type = "MULTI_LAYER_IMAGE"
    s.file_format = "OPEN_EXR_MULTILAYER"
    s.color_depth = "16"
    s.exr_codec = "ZIP"
    return sc


def world(color=(0.02, 0.02, 0.025), strength=1.0):
    w = bpy.data.worlds.new("dunya")
    bpy.context.scene.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def sky_world(sun_elev=8.0, sun_rot=40.0, strength=1.0, air=1.0, dust=1.0):
    """Gerçekçi gökyüzü (Nishita)."""
    w = bpy.data.worlds.new("gok")
    bpy.context.scene.world = w
    nt = w.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    for attr, val in (("sky_type", "NISHITA"), ("sun_elevation", math.radians(sun_elev)),
                      ("sun_rotation", math.radians(sun_rot)), ("air_density", air), ("dust_density", dust)):
        if hasattr(sky, attr):
            try:
                setattr(sky, attr, val)
            except TypeError:
                pass
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    return w


# ------------------------------------------------------------------ malzemeler
def mat(name, color, rough=0.5, metal=0.0, spec=0.5, emit=None, emit_strength=0.0, var=0.0, var_scale=6.0,
        bump=0.0, bump_scale=40.0, coat=0.0, sheen=0.0, alpha=1.0):
    """Principled malzeme. var: renkte gürültüyle doğal ton farkı, bump: yüzey pürüzü."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Alpha"].default_value = alpha
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    tc = None
    if var > 0 or bump > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
    if var > 0:
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = var_scale
        nz.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["Factor"].default_value = 1.0
        mix.blend_type = "MULTIPLY"
        mix.inputs["A"].default_value = (*color, 1)
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.3
        ramp.inputs["From Max"].default_value = 0.7
        ramp.inputs["To Min"].default_value = 1 - var
        ramp.inputs["To Max"].default_value = 1 + var * 0.5
        nt.links.new(nz.outputs["Fac"], ramp.inputs["Value"])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        for k in ("Red", "Green", "Blue"):
            nt.links.new(ramp.outputs["Result"], comb.inputs[k])
        nt.links.new(comb.outputs["Color"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = max(0.02, rough - 0.15)
        rr.inputs["To Max"].default_value = min(1.0, rough + 0.15)
        nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    if bump > 0:
        nz2 = nt.nodes.new("ShaderNodeTexNoise")
        nz2.inputs["Scale"].default_value = bump_scale
        nz2.inputs["Detail"].default_value = 10
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.02
        nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def kelvin(k):
    """Renk sıcaklığından yaklaşık doğrusal RGB."""
    t = k / 100
    r = 255 if t <= 66 else 329.7 * (t - 60) ** -0.1332
    g = 99.47 * math.log(t) - 161.1 if t <= 66 else 288.1 * (t - 60) ** -0.0755
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5 * math.log(t - 10) - 305.0)
    srgb = [min(255, max(0, v)) / 255 for v in (r, g, b)]
    return tuple(c ** 2.2 for c in srgb)


# ------------------------------------------------------------------ geometri
def _finish(o, m=None, bevel=0.0, seg=2, smooth=False, index=0):
    if m is not None:
        o.data.materials.clear()
        o.data.materials.append(m)
    if bevel > 0:
        md = o.modifiers.new("pah", "BEVEL")
        md.width = bevel
        md.segments = seg
        md.limit_method = "ANGLE"
        md.harden_normals = False
    if smooth:
        bpy.ops.object.shade_smooth()
    o.pass_index = index
    return o


def box(name, size, loc, m=None, rot=(0, 0, 0), bevel=0.0, seg=2, index=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, m, bevel, seg, index=index)


def cyl(name, r, depth, loc, m=None, rot=(0, 0, 0), verts=32, bevel=0.0, index=0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts,
                                        rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    return _finish(o, m, bevel, 2, smooth=True, index=index)


def cone(name, r1, r2, depth, loc, m=None, rot=(0, 0, 0), verts=32, index=0):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, vertices=verts,
                                    rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    return _finish(o, m, 0, 2, smooth=True, index=index)


def sphere(name, r, loc, m=None, scale=(1, 1, 1), seg=24, index=0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    return _finish(o, m, 0, 2, smooth=True, index=index)


def torus(name, R, r, loc, m=None, rot=(0, 0, 0), index=0, maj=40, mino=14):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, major_segments=maj,
                                     minor_segments=mino, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    return _finish(o, m, 0, 2, smooth=True, index=index)


def plane(name, size, loc, m=None, rot=(0, 0, 0), index=0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
    o = bpy.context.object
    o.name = name
    o.scale = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, m, index=index)


def join(objs, name):
    """Parçaları tek nesnede birleştir (değiştiricileri uygulayarak)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        for md in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    return o


def collect(objs, name):
    """Nesneleri bir koleksiyona taşı (örnekleme/instancing için)."""
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    for o in objs:
        for c in o.users_collection:
            c.objects.unlink(o)
        col.objects.link(o)
    return col


def instance(col, loc, rot_z=0.0, name="kopya", index=0, scale=1.0):
    """Koleksiyonun hafif kopyası (bellek ve süre dostu)."""
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = col
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rot_z))
    e.scale = (scale, scale, scale)
    e.pass_index = index
    bpy.context.scene.collection.objects.link(e)
    return e


def hide_source(col):
    """Kaynak koleksiyonu çizimden çıkar (yalnız kopyaları görünür)."""
    lc = bpy.context.view_layer.layer_collection.children[col.name]
    lc.exclude = True


def curve(name, pts, radius, m=None, res=12, index=0):
    """Noktalardan geçen kalın eğri (kablo, iplik)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.resolution_u = res
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    if m is not None:
        o.data.materials.append(m)
    o.pass_index = index
    return o


def area_light(name, loc, size, energy, color=(1, 1, 1), rot=(0, 0, 0), shape="RECTANGLE", spread=180):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    if shape in ("RECTANGLE", "ELLIPSE"):
        ld.size, ld.size_y = size
    else:
        ld.size = size[0]
    ld.energy = energy
    ld.color = color
    ld.spread = math.radians(spread)
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(o)
    return o


def point_light(name, loc, energy, color=(1, 1, 1), radius=0.05):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def spot_light(name, loc, energy, target, color=(1, 1, 1), size_deg=60, blend=0.4, radius=0.05):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.energy = energy
    ld.color = color
    ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    look_at(o, target)
    return o


def sun(name, elev, azim, energy, color=(1, 1, 1), angle=0.5):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = energy
    ld.color = color
    ld.angle = math.radians(angle)
    o = bpy.data.objects.new(name, ld)
    o.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    bpy.context.scene.collection.objects.link(o)
    return o


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=32, fstop=None, focus=None, sensor=36):
    cd = bpy.data.cameras.new("kamera")
    cd.lens = lens
    cd.sensor_width = sensor
    cd.sensor_fit = "HORIZONTAL"
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    o = bpy.data.objects.new("kamera", cd)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    look_at(o, target)
    bpy.context.scene.camera = o
    return o


def render(name, frame=None):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    sc.render.filepath = os.path.join(OUT, name + ".exr")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


def border_for(points, cam, pad=0.04):
    """Verilen dünya noktalarını kapsayan ekran bölgesi; yalnız o bölge çizilir (hızlı kısmi çizim)."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()                     # yeni kameranın dönüşüm matrisi hesaplansın
    uv = [world_to_camera_view(sc, cam, Vector(p)) for p in points]
    b = (max(0, min(v.x for v in uv) - pad), min(1, max(v.x for v in uv) + pad),
         max(0, min(v.y for v in uv) - pad), min(1, max(v.y for v in uv) + pad))
    return b


def set_border(b):
    sc = bpy.context.scene
    if b is None:
        sc.render.use_border = False
        return
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = b
