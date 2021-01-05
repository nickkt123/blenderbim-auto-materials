"""Convert BIM Materials to Cycles Materials."""

import bpy
import mathutils
import math
import time

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


class BIMAutoMaterials(bpy.types.Operator):
    """Convert BIM Materials to Cycles Materials."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "object.move_x"        # Unique identifier for buttons and menu items to reference.
    bl_label = "BlenderBIM Auto-materials"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        """Run the plugin."""
        convert_blenderBIM_materials()
        auto_assign_empty_material()
        auto_assign_wall_material()

        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


def auto_assign_wall_material():
    """Assign a wall material from Blenderkit to walls."""
    if "bpy" in locals():
        import importlib
        utils = importlib.reload(utils)
        search = importlib.reload(search)
    else:
        from blenderkit import utils, search

    bpy.context.scene.blenderkitUI.asset_type = 'MATERIAL'
    bpy.context.scene.blenderkit_mat.search_keywords = "red brick wall"
    search.search(category='')

    sr = bpy.context.scene.get('search results')
    if sr is None:
        bpy.context.scene['search results'] = []

    tmp_mat = bpy.data.materials.new('tmp')
    selected_objects = bpy.context.selected_objects

    for obj in selected_objects:
        if obj.type != 'MESH':
            continue
        if 'IfcWall' not in obj.name or 'Exterior' not in obj.name:
            continue

        bpy.context.view_layer.objects.active = obj

        target_slot = len(obj.data.materials.keys())
        target_object = obj.name
        obj.data.materials.append(tmp_mat)

        bpy.ops.mesh.uv_texture_remove()
        # bpy.ops.mesh.uv_texture_add()
        # bpy.ops.object.editmode_toggle()
        # bpy.ops.mesh.select_all(action='DESELECT')
        # bpy.ops.object.material_slot_select()
        # bpy.ops.uv.cube_project(cube_size=2, correct_aspect=False)
        # bpy.ops.object.editmode_toggle()

        asset_search_index = 0
        asset_data = sr[asset_search_index]
        utils.automap(target_object, target_slot=target_slot,
                      tex_size=asset_data.get('texture_size_meters', 1.0))
        bpy.ops.scene.blenderkit_download(True,
                                          asset_type='MATERIAL',
                                          asset_index=0,
                                          target_object=target_object,
                                          material_target_slot=target_slot,
                                          model_location=obj.location,
                                          model_rotation=(0, 0, 0))

        for face in obj.data.polygons:
            if face_is_exterior(obj, face, offset=1):
                face.material_index = target_slot


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
    sel_obj = bpy.context.active_object
    offset = 1

    face_local = selected_face.center.copy()
    face_local.rotate(sel_obj.rotation_euler)

    face_origin = sel_obj.location + face_local
    face_normal = selected_face.normal.copy()
    face_normal.rotate(sel_obj.rotation_euler)

    for object in bpy.data.objects:
        if object.type != 'MESH':
            continue
        if object.name == sel_obj.name:
            continue

        v1 = object.location
        v3 = v1 + mathutils.Vector((0, 0, 1))

        orig_v1 = mathutils.Vector(face_origin + (offset * face_normal) - v1)
        eul_z = mathutils.Euler((0.0, 0.0, math.radians(90.0)), 'XYZ')
        rotated_vec = orig_v1.copy()
        rotated_vec.rotate(eul_z)
        v2 = v1 + rotated_vec

        res = mathutils.geometry.intersect_ray_tri(v1, v2, v3, face_normal, face_origin, False)
        if res:
            return False
    return True


def register():
    """Register the class in Blender."""
    bpy.utils.register_class(BIMAutoMaterials)


def unregister():
    """Unregister the class in Blender."""
    bpy.utils.unregister_class(BIMAutoMaterials)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
