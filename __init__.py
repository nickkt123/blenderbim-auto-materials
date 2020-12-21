import bpy

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

        convert_blenderBIM_materials()
        auto_assign_empty_material()
        auto_assign_wall_material()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


def auto_assign_wall_material():
    """
    Assign a wall material from Blenderkit to walls.
    TODO: only assign to outside faces
    """
    bpy.context.scene.blenderkitUI.asset_type = 'MATERIAL'
    bpy.context.scene.blenderkit_mat.search_keywords = "wall"
    for obj in bpy.context.selected_objects:
        if obj.type != 'MESH':
            continue
        if 'IfcWall' not in obj.name or 'Exterior' not in obj.name:
            continue
        bpy.ops.mesh.uv_texture_add()
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.material_slot_select()
        bpy.ops.uv.cube_project(cube_size=2, correct_aspect=False)
        bpy.ops.object.editmode_toggle()
        bpy.ops.scene.blenderkit_download(asset_type='MATERIAL', asset_index=2, target_object=obj.name, material_target_slot=0, model_location=obj.location, model_rotation=(0, 0, 0))


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


def register():
    bpy.utils.register_class(BIMAutoMaterials)


def unregister():
    bpy.utils.unregister_class(BIMAutoMaterials)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
