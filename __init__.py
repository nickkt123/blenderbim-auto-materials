import bpy

bl_info = {
    "name": "BlenderBIM Auto-materials",
    "blender": (2, 80, 0),
    "category": "Object",
}


class ObjectMoveX(bpy.types.Operator):
    """Convert BIM Materials to Cycles Materials."""      # Use this as a tooltip for menu items and buttons.

    bl_idname = "object.move_x"        # Unique identifier for buttons and menu items to reference.
    bl_label = "BlenderBIM Auto-materials"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.

        materials = bpy.data.materials
        for material in materials:
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

        empty_mat = bpy.data.materials.new('Empty Material')
        empty_mat.use_nodes = True
        node = empty_mat.node_tree.nodes.get("Principled BSDF")
        node.inputs['Base Color'].default_value = (1, 0, 1, 1)

        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                materials = obj.material_slots
                obj.data.materials.append(empty_mat)
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


def register():
    bpy.utils.register_class(ObjectMoveX)


def unregister():
    bpy.utils.unregister_class(ObjectMoveX)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
