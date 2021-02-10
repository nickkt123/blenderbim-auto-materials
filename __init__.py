"""Convert BIM Materials to Cycles Materials."""

import bpy
import mathutils
import math
import functools
import queue
import json
import ast
import idprop
import os.path
from bpy.types import Panel, PropertyGroup, Operator
from bpy.props import BoolProperty, PointerProperty, FloatVectorProperty

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

asset_path = '//bim_auto_mat'
json_mapping = 'bim_blenderkit_map.json'

execution_queue = queue.LifoQueue()

report = 'Ready'

class BIMConvertMaterials(Operator):
    """Checks 'use nodes' for all materials and enables transparency."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_convert_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Convert all materials to Blender"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        convert_blenderBIM_materials()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


class BIMAutoMaterials(Operator):
    """Uses the BIM properties and custom mapping to get materials from blenderKit."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_auto_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Generate Materials from BIM"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        auto_assign_materials_to_selected()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class BIMCustomMaterials(Operator):
    """Maps the current (top) blenderKit material to the (top) BIM material."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "bim.bim_custom_materials"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Map selected material to BIM"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        map_selected_material_to_BIM_material()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


class VIEW3D_PT_UI(Panel):

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Materials"
    bl_label = "Auto Materials"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator("bim.bim_convert_materials")
        col.operator("bim.bim_auto_materials")
        col.operator("bim.bim_custom_materials")

        bim_auto_mat = context.scene.bim_auto_mat
        layout.prop(bim_auto_mat, 'interior_walls_empty_material', text='Empty materials for interior faces')
        layout.prop(bim_auto_mat, 'empty_color', text='Empty Color')

        layout.label(text=f"Status: {report}")


class AutoMatSettings(PropertyGroup):
    interior_walls_empty_material : BoolProperty(
        name="interior_walls_empty_material",
        description="When a BIM object has the keyword 'exterior', the material is not applied to interior faces.",
        default = True
        )
    empty_color: FloatVectorProperty(
        name="Empty Colour", subtype="COLOR", default=(1, 0, 1, 1), min=0.0, max=1.0, size=4
    )


def report_to_ui(report_text):
    global report
    report = report_text
    print(report)


def map_selected_material_to_BIM_material():
    obj = bpy.context.active_object
    if len(obj.data.materials) == 0:
        report_to_ui('Object has no material')
        return

    index = obj.active_material_index
    if len(obj.data.materials) <= index:
        index = 0

    mat = obj.data.materials[index]
    if mat is None:
        report_to_ui('Material is empty')
        return
    raw_asset_data = mat.get('asset_data')
    if raw_asset_data is None:
        report_to_ui('Material is not from blenderkit')
        return
    asset_data = get_asset_data_as_dict(raw_asset_data)
    map_material_to_BIM_obj(asset_data, obj)


def map_material_to_BIM_obj(asset_data, obj):
    ddir = bpy.path.abspath(asset_path)
    try:
        if not os.path.exists(ddir):
            os.makedirs(ddir)
            bim_mat_to_blenderkit = {}
            report_to_ui('Created new Material Mapping in the plugin folder')
        with open(os.path.join(ddir, json_mapping), 'r') as json_file:
            bim_mat_to_blenderkit = json.load(json_file)
    except:
        bim_mat_to_blenderkit = {}

    bim_materials = get_bim_materials(obj)
    if len(bim_materials) > 0:
        main_bim_material = bim_materials[0]
        bim_mat_to_blenderkit[main_bim_material] = asset_data
        with open(os.path.join(ddir, json_mapping), 'w+') as json_file:
            json.dump(bim_mat_to_blenderkit, json_file)

        report_to_ui(f'Mapped "{asset_data["name"]}" to "{main_bim_material}"')
    else:
        report_to_ui('Object has no IFC material')


def get_asset_data_as_dict(asset_data):
    """Returns the blenderKit asset data as a dict"""
    # the same asset data of the same materials switches between these two types for an unknown reason.
    if type(asset_data) is str:
        # sometimes the end bracket is missing
        if asset_data[-1] != '}':
            asset_data = asset_data + '}'
        return ast.literal_eval(asset_data_string)
    if type(asset_data) is idprop.types.IDPropertyGroup:
        return asset_data.to_dict()
    
    return {}


def auto_assign_materials_to_selected():
    """Assign a wall material from Blenderkit to walls."""
    if "bpy" in locals():
        import importlib
        utils = importlib.reload(utils)
        search = importlib.reload(search)
    else:
        from blenderkit import utils, search

    report_to_ui('Generating materials...')

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
            if len(obj.data.materials) == 0:
                assign_empty_material(obj)
            continue

        for bim_material in bim_materials:
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
    scene = bpy.context.scene
    props = scene.blenderkit_mat
    if props.is_downloading:
        return 0.5

    if current_material is not None:
        if current_material.get('downloaded'):
            if int(current_material.get('downloaded', 0)) < 100:
                return 0.5

    if execution_queue.empty():
        report_to_ui('Applied all materials')
    else:
        bpy.app.timers.register(execution_queue.get())


def get_existing_material_slot(obj, asset_data):
    """If object already has material, return the material slot of the material."""
    for index, mat in enumerate(obj.data.materials):
        if mat is None:
            continue
        raw_asset_data = mat.get('asset_data')
        existing_asset_data = get_asset_data_as_dict(raw_asset_data)
        if existing_asset_data.get('id') == asset_data.get('id'):
            return index
    return None


def get_material_from_mapping(bim_material):
    ddir = bpy.path.abspath(asset_path)
    try:
        if not os.path.exists(ddir):
            return None
        with open(os.path.join(ddir, json_mapping), 'r') as json_file:
            bim_mat_to_blenderkit = json.load(json_file)
        return bim_mat_to_blenderkit.get(bim_material)
    except:
        return None

def search_and_download_to_object(obj, bim_material):
    if "bpy" in locals():
        import importlib
        search = importlib.reload(search)
    else:
        from blenderkit import search

    report_to_ui(f'Checking "{obj.name}"...')

    mapped_material = get_material_from_mapping(bim_material)
    if mapped_material is not None:
        # download material directly without having to wait for search
        target_slot = get_existing_material_slot(obj, mapped_material)
        if target_slot is not None:
            # the material already belongs to the object, it does not have to download
            assign_material_to_object(obj, target_slot)
            bpy.app.timers.register(functools.partial(execute_next_in_queue, mapped_material))
            return None
        from blenderkit import download

        # the material has to be downloaded
        target_slot = len(obj.data.materials.keys())
        kwargs = {
            'target_object': obj.name,
            'material_target_slot': target_slot,
            'model_location': obj.location,
            'model_rotation': (0, 0, 0),
            'replace': False
        }
        if len(obj.data.materials) == 0:
            assign_empty_material(obj)
        elif obj.data.materials[-1] is not None:
            assign_empty_material(obj)

        assign_material_to_object(obj, target_slot)
        download.start_download(mapped_material, **kwargs)
        bpy.app.timers.register(functools.partial(execute_next_in_queue))
        return None

    # no material was mapped, so we have to search for it
    scene = bpy.context.scene
    props = scene.blenderkit_mat
    if props.is_searching:
        return 0.5

    if props.search_keywords != bim_material:
        props.search_keywords = bim_material
        search.search(category='')
    report_to_ui(f'Searching for "{props.search_keywords}"')
    bpy.app.timers.register(functools.partial(download_to_object, obj, bim_material))
    return None

def download_to_object(obj, search_keywords):
    scene = bpy.context.scene
    props = scene.blenderkit_mat

    if props.is_searching:
            return 0.5

    if props.search_keywords != search_keywords:
        report_to_ui(f'Current search "{props.search_keywords}" was altered by a different thread searching for "{search_keywords}". Will retry')
        execution_queue.put(functools.partial(search_and_download_to_object, obj, search_keywords))
        bpy.app.timers.register(execute_next_in_queue)
        return None

    sr = scene.get('search results')
    if not sr or len(sr) == 0:
        report_to_ui(f'Blenderkit could not find any material for "{search_keywords}"')
        if len(obj.data.materials) == 0:
            assign_empty_material(obj)
        bpy.app.timers.register(execute_next_in_queue)
        return None


    asset_search_index = 0
    asset_data = sr[asset_search_index]

    asset_data_dict = get_asset_data_as_dict(asset_data)
    map_material_to_BIM_obj(asset_data_dict, obj)    # save this material in the mapping so it will not be searched again
    target_slot = get_existing_material_slot(obj, asset_data)    # check if it was already added to object
    if target_slot is not None:
        assign_material_to_object(obj, target_slot)
        bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
        return None

    target_object = obj.name
    if obj.data.materials[-1] is not None:
        obj.data.materials.append(None)
    target_slot = len(obj.data.materials.keys()) - 1
    bpy.ops.scene.blenderkit_download(True,
                                      asset_type='MATERIAL',
                                      asset_index=asset_search_index,
                                      target_object=target_object,
                                      material_target_slot=target_slot,
                                      model_location=obj.location,
                                      model_rotation=(0, 0, 0))
    
    assign_material_to_object(obj, target_slot)

    report_to_ui(f'Applied "{asset_data.get("name")}" to "{target_object}"')

    bpy.app.timers.register(functools.partial(execute_next_in_queue, asset_data))
    return None


def assign_material_to_object(obj, target_slot):
    interior_walls_empty_material = bpy.context.scene.bim_auto_mat.interior_walls_empty_material
    if 'Exterior' in obj.name and interior_walls_empty_material:
        materials = obj.data.materials
        if materials[target_slot] is None or materials[-1] is not None:
            materials.append(None)

        empty_slot = len(materials) - 1
        for face in obj.data.polygons:
            if face_is_exterior(obj, face, offset=1):
                face.material_index = target_slot
            else:
                face.material_index = empty_slot
    else:
        for face in obj.data.polygons:
            face.material_index = target_slot


def assign_empty_material(obj):
    """Assign a bright pink material to unstyled objects."""
    empty_color = bpy.context.scene.bim_auto_mat.empty_color
    empty_mat = bpy.data.materials.new('Empty Material')
    empty_mat.use_nodes = True
    node = empty_mat.node_tree.nodes.get("Principled BSDF")
    node.inputs['Base Color'].default_value = empty_color

    if obj.type == 'MESH':
        obj.data.materials.append(empty_mat)


def convert_blenderBIM_materials():
    """Convert basic blenderBIM materials to cycles materials."""
    report_to_ui('Converting materials...')

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

    report_to_ui('Converted all materials')

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

classes = (
    BIMConvertMaterials,
    BIMAutoMaterials,
    BIMCustomMaterials,
    VIEW3D_PT_UI,
    AutoMatSettings
)


def register():
    """Register the class in Blender."""
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.bim_auto_mat = PointerProperty(type=AutoMatSettings)


def unregister():
    """Unregister the class in Blender."""
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.bim_auto_mat

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
