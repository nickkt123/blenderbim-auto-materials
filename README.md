# blenderBIM Auto Materials

## Overview
This plugin uses the information from BIM materials to search for materials on blenderkit and apply them to the models.
It is also possible to create a custom material mapping with hand-picked materials.
The mapping can also be used in other files, e.g. when a new version of the BIM model is imported.


## Installation
To import the plugin into blender, go to 'Blender Preferences > Add-ons > Install...', and select a zipped version of the plugin folder.
The plugins BlenderKit and blenderBIM need to be installed as well.

![Screenshot of plugin](assets/settings.png?raw=true "Plugin Overview")

## Usage
First, an IFC model has to be imported:

![Ifc import](assets/ifc_import.png?raw=true "Import an IFC model")

The plugin can be found in the sidebar under 'Auto Materials'.
It has 3 main functions:

![Screenshot of plugin](assets/plugin_overview.png?raw=true "Plugin Overview")

### Convert all materials to blender
The imported IFC model can have materials and textures, and transparent glass.
However the materials do not use the blender nodes, so they cannot be used with the Cycles or Evee rendering engine.
This function converts the materials so the transparency and colors work with these rendering engines.

### Generate Materials from BIM
The plugin checks what material is specified in the IFC bim properties of the object. Then it searches for a material on blenderkit that has the same name, and applies it to the object.

### Map selected material to BIM
Instead of relying on the blenderkit search, a custom blenderkit material can be mapped to the IFC material.
The next time the 'Generate Materials from BIM' function is used, it first checks for a custom mapping.
The mapping is saved in a json in the project folder under ```bim_auto_mat/bim_blenderkit_map.json```.

### Empty materials for interior faces
When this is checked, any objects that have the keyword 'exterior' in their name will not have a material on interior faces.
This is useful for walls which should only have the wall material on the outside.
