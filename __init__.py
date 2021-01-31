"""Convert BIM Materials to Cycles Materials."""

import bpy
import mathutils
import math
import time
import functools
import queue
import json

bl_info = {
    "name": "BlenderBIM Auto-materials",
    "blender": (2, 83, 10),
    "category": "Object",
    "author": "Nick Kleine-Tebbe",
    "version": (0, 0, 1),
    "location": "3D view search: BlenderBIM Auto-materials",
    "description": "Uses BlenderKit to generate materials for models which were imported with BlenderBIM",
    "warning": ""
}

search_terms = {
    'brick': 'modern brick wall',
    'foundation': 'rough concrete',
    'concrete': 'rough concrete',
    'floor - wood': 'wood floor'
}

bim_mat_to_blenderkit = {}

execution_queue = queue.LifoQueue()

class BIMConvertMaterials(bpy.types.Operator):
    """Convert BIM Materials to Cycles Materials."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_convert_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "BlenderBIM convert materials"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        convert_blenderBIM_materials()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class BIMAutoMaterials(bpy.types.Operator):
    """Automatically select materials from Blenderkit."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_auto_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "BlenderBIM Auto-materials"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        auto_assign_empty_material()
        auto_assign_materials_to_selected()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class BIMCustomMaterials(bpy.types.Operator):
    """Map a Blenderkit Material to a BIM Material."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_custom_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "BlenderBIM Custom material"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        map_material_to_BIM_material()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


def map_material_to_BIM_material():
    
    obj = bpy.context.active_object
    mat = obj.data.materials[0]
    
    asset_data = mat.get('asset_data')

    bim_materials = get_bim_materials(obj)

    main_bim_material = bim_materials[0]
    bim_mat_to_blenderkit[main_bim_material] = asset_data
    print(f'Mapped "{mat.name}" to "{main_bim_material}"')


def auto_assign_materials_to_selected():
    """Assign a wall material from Blenderkit to walls."""
    if "bpy" in locals():
        import importlib
        utils = importlib.reload(utils)
        search = importlib.reload(search)
    else:
        from blenderkit import utils, search
    scene = bpy.context.scene
    ui_props = scene.blenderkitUI
    props = scene.blenderkit_mat
    ui_props.asset_type = 'MATERIAL'

    selected_objects = bpy.context.selected_objects
    bim_material_to_object = {}
    for obj in selected_objects:
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj

        bim_materials = get_bim_materials(obj)
        if not bim_materials:
            continue

        for bim_material in bim_materials:
            # bpy.ops.object.material_slot_add()
            if bim_material_to_object.get(bim_material):
                bim_material_to_object[bim_material].append(obj)
            else:
                bim_material_to_object[bim_material] = [obj]

        bpy.context.view_layer.objects.active = obj

        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=2, correct_aspect=False)
        bpy.ops.object.editmode_toggle()

        target_object = obj.name
        target_slot = len(obj.data.materials.keys())

        utils.automap(obj.name, target_slot=target_slot,
                    tex_size=1.0)

    for search_keywords, objects in bim_material_to_object.items():
        for obj in objects:
            execution_queue.put(functools.partial(search_and_download_to_object, obj, search_keywords))

    bpy.app.timers.register(execute_next_in_queue)


def get_bim_materials(obj):
    bop = obj.BIMObjectProperties
    if bop.material_type == 'IfcMaterial':
        material_name = bop.material.name
        return [material_name]
    if bop.material_type == 'IfcMaterialLayerSet':
        material_name_front = bop.material_set.material_layers[0].material.name
        material_name_back = bop.material_set.material_layers[-1].material.name

        return [material_name_front] #, material_name_back]
    return None

def execute_next_in_queue(current_material=None):
    if current_material is not None:
        if current_material.get('downloaded'):
            if int(current_material.get('downloaded', 0)) < 100:
                return 0.5

    if execution_queue.empty():
        print('finished applying materials.')
    else:
        bpy.app.timers.register(execution_queue.get())


def has_material(obj, asset_data):
    for mat in obj.data.materials.keys():
        if mat == asset_data.get('name'):
            return True
    return False

def search_and_download_to_object(obj, bim_material):
    if "bpy" in locals():
        import importlib
        search = importlib.reload(search)
    else:
        from blenderkit import search
    print(f'working on {obj.name}')
    asset_data = bim_mat_to_blenderkit.get(bim_material)
    if asset_data is not None:
        if has_material(obj, asset_data):
            bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
            return None
        from blenderkit import download
        target_slot = len(obj.data.materials.keys())
        kwargs = {
            'target_object': obj.name,
            'material_target_slot': target_slot,
            'model_location': obj.location,
            'model_rotation': (0, 0, 0),
            'replace': False
        }
        obj.data.materials.append(None)
        for face in obj.data.polygons:
            face.material_index = target_slot
        download.start_download(asset_data, **kwargs)
        bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
        return None

    scene = bpy.context.scene
    props = scene.blenderkit_mat
    if props.is_searching:
        return 0.5

    if props.search_keywords != bim_material:
        props.search_keywords = bim_material
        search.search(category='')
        print(f'searching for {props.search_keywords}')

    bpy.app.timers.register(functools.partial(download_to_object, obj, bim_material))
    return None

def download_to_object(obj, search_keywords):
    scene = bpy.context.scene
    props = scene.blenderkit_mat

    if props.is_searching:
            return 0.5

    if props.search_keywords != search_keywords:
        print(f'Cannot apply material. Current search "{props.search_keywords}" was altered by different thread searching for "{search_keywords}". Will retry')
        execution_queue.put(functools.partial(search_and_download_to_object, obj, search_keywords))
        bpy.app.timers.register(execute_next_in_queue)
        return None

    sr = scene.get('search results')
    if not sr or len(sr) == 0:
        print(f'Blenderkit could not find any material for {search_keywords}.')
        bpy.app.timers.register(execute_next_in_queue)
        return None

    target_object = obj.name
    target_slot = len(obj.data.materials.keys())

    asset_search_index = 0
    asset_data = sr[asset_search_index]
    if has_material(obj, asset_data):
            bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
            return None

    obj.data.materials.append(None)
    bpy.ops.scene.blenderkit_download(True,
                                      asset_type='MATERIAL',
                                      asset_index=asset_search_index,
                                      target_object=target_object,
                                      material_target_slot=target_slot,
                                      model_location=obj.location,
                                      model_rotation=(0, 0, 0))


    # TODO: reimplement exterior check with support for custom materials
    # if 'Exterior' in obj.name:
    #     for face in obj.data.polygons:
    #         if face_is_exterior(obj, face, offset=1):
    #             face.material_index = target_slot
    # else:
    for face in obj.data.polygons:
        face.material_index = target_slot
    print(f"applied {asset_data.get('name')} to {target_object}")
    bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
    return None


def auto_assign_empty_material():
    """Assign a bright pink material to unstyled objects."""
    empty_mat = bpy.data.materials.new('Empty Material')
    empty_mat.use_nodes = True
    node = empty_mat.node_tree.nodes.get("Principled BSDF")
    node.inputs['Base Color'].default_value = (1, 0, 1, 1)

    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            if not obj.material_slots:
                obj.data.materials.append(empty_mat)


def convert_blenderBIM_materials():
    """Convert basic blenderBIM materials to cycles materials."""
    materials = bpy.data.materials
    for material in materials:
        if material.use_nodes:
            continue
        diffuse_color = material.diffuse_color

        material.use_nodes = True
        node = material.node_tree.nodes.get("Principled BSDF")
        node.inputs['Base Color'].default_value = (
            diffuse_color[0],
            diffuse_color[1],
            diffuse_color[2],
            diffuse_color[3]
        )
        transparency = diffuse_color[3] < 1.0
        if transparency:
            material.use_screen_refraction = True
            node.inputs['Roughness'].default_value = 0
            node.inputs['Transmission'].default_value = 1 - diffuse_color[3]


def face_is_exterior(sel_obj, selected_face, offset=1):
    """Determine if the selected face lies inside the building."""
    offset = 1

    face_local = selected_face.center.copy()
    face_local.rotate(sel_obj.rotation_euler)

    face_origin = sel_obj.location + face_local
    face_normal = selected_face.normal.copy()
    face_normal.rotate(sel_obj.rotation_euler)

    for intersect_object in bpy.data.objects:
        if intersect_object.type != 'MESH':
            continue
        if intersect_object.name == sel_obj.name:
            continue

        v1 = intersect_object.location
        v3 = v1 + mathutils.Vector((0, 0, 1))

        orig_v1 = mathutils.Vector(face_origin + (offset * face_normal) - v1)
        eul_z = mathutils.Euler((0.0, 0.0, math.radians(90.0)), 'XYZ')
        rotated_vec = orig_v1.copy()
        rotated_vec.rotate(eul_z)
        v2 = v1 + rotated_vec

        res = mathutils.geometry.intersect_ray_tri(v1, v2, v3, face_normal, (face_origin + (offset * face_normal)), False)
        if res:
            return False
    return True


def register():
    """Register the class in Blender."""
    bpy.utils.register_class(BIMConvertMaterials)
    bpy.utils.register_class(BIMAutoMaterials)
    bpy.utils.register_class(BIMCustomMaterials)


def unregister():
    """Unregister the class in Blender."""
    bpy.utils.unregister_class(BIMConvertMaterials)
    bpy.utils.unregister_class(BIMAutoMaterials)
    bpy.utils.unregister_class(BIMCustomMaterials)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
