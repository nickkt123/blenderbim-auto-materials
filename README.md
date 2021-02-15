# BlenderBIM Auto Materials

## Overview
BlenerBIM is a great tool that allows us to import IFC models to Blender. It especially also imports the IFC materials of the model. However, there is a big difference between IFC materials and Blender materials: They describe the specifications of a construction material, but are of course not useful for rendering the architecture model in Blender. This plugin uses IFC materials to search for similar materials on BlenderKit so that a model can be quickly prepared for rendering.

### Walkthrough Video
[![Walkthrough](http://img.youtube.com/vi/M4i9tVeH0ZE/0.jpg)](https://youtu.be/M4i9tVeH0ZE "BlenderBIM Auto Materials")

## Installation
To install the plugin in blender, go to 'Blender Preferences > Add-ons > Install...', and select a zipped version of the plugin folder.
The plugins BlenderKit and BlenderBIM need to be installed as well.

![Screenshot of plugin](assets/settings.png?raw=true "Plugin Overview")

## Usage

First, an IFC model has to be imported via File > Import > Industry Foundation Classes:

![Ifc import](assets/ifc_import.png?raw=true "Import an IFC model")

The BlenderBIM Auto-Materials plugin can be found in the properties sidebar under 'Auto Materials':

![Screenshot of plugin](assets/plugin_overview.png?raw=true "Plugin Overview")

The IFC model may have some basic materials already. But transparency will not be rendered correctly at first. To fix this, press *Convert All Materials to Use Nodes* in the *Convert Materials* tab.

To generate materials for the whole IFC model, simply select everything and press *Generate Materials for Selection*. If there are many objects selected, this may take a while.

The plugin uses the first search result from BlenderKit. To use a different material in the future, you can manually download a material from BlenderKit to a model. Then, select the material and press *Map Selected Material to IFC Material*. In the future, *Genrate Materials for Selection* will apply this selected material to all objects with the same IFC material.

## Complete Function Documentation

### Generate Materials
#### Generate Materials for Selection
The plugin checks what material is specified in the IFC properties of the object. Then it searches for a material on BlenderKit that has the same name, and applies it to the object.

#### Map Selected Material to IFC Material
Maps the selected BlenderKit material to the IFC material of the object.
The next time the 'Generate Materials from BIM' function is used on any object, it first checks for a custom mapping.
The mapping is saved in a json in the project folder under ```bim_auto_mat_data/bim_blenderkit_map.json```.

#### Empty Material for Interior Faces
When this is checked, any objects that have the keyword 'exterior' in their name will not have a material on interior faces.
This is useful for walls which should only have the wall material on the outside. *Note: This function does not work correctly on all models and may determine that some exterior faces are interior*

#### Missing Material Color
The color that is applied to objects with no IFC material. The bright pink color is useful for quickly spotting such objects in the scene, however it can be changed to a different color that is less offensive.


### Convert Materials
#### Convert All Materials to Use Nodes
The imported IFC model can have colors and tranparency.
However the materials do not use the blender nodes, so they cannot be used with the Cycles or Evee rendering engine.
This function converts the materials so the transparency and colors work with these rendering engines.

### Status
Status of the last action that was performed.
