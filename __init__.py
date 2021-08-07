bl_info = {
    "name": "Mesh History",
    "author": "Nico Zevallos <gnastacast@gmail.com>",
    "version": (1,0),
    "blender": (2, 93, 1),
    "category": "Mesh",
    "location": "3D View > Sidebar",
    "description": "Saves versions of mesh data in a hidden collection",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
}
import bpy
import datetime

__time_str__ = "%Y-%m-%d %H:%M:%S.%f"

def add_items_from_history_callback(self, context):
    items = [("current", "Current", "")]
    names = context.active_object['history_collection'].objects.items()
    names.sort()
    names.reverse()
    item_no = len(names)
    times = []
    ids = []
    
    for ob in context.active_object['history_collection'].objects.values():
        times.append(ob.data.name)
        ids.append(ob.name)
        
    for time, name in sorted(zip(times, ids)):
        t = datetime.datetime.strptime(time, __time_str__)
        item_str = t.strftime("%H:%M:%S %m-%d-%Y")
        items.append((time, name, item_str))
        item_no -= 1
        
    return items

def get_version_name(self, context):
    ob = context.active_object
    n_versions = len(ob['history_collection'].objects)
    return "%s V%s" % (ob.name, str(n_versions).zfill(4))
    

class MESH_HISTORY_OT_initialize(bpy.types.Operator):
    """Initializes sculpt versioning"""
    bl_idname = "mesh_history.initialize"
    bl_label = "Initialize history"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not context.active_object.select_get():
            return False
        return 'history_collection' not in context.active_object.keys()
        
    def execute(self, context):
        coll_name = context.active_object.name + "_versions"
        try:
            coll = bpy.data.collections[coll_name]
        except KeyError:
            coll = bpy.data.collections.new(coll_name)

        context.active_object['history_collection'] = coll
        bpy.ops.mesh_history.save()
        return {"FINISHED"}

class MESH_HISTORY_OT_obliterate(bpy.types.Operator):
    """Deletes mesh version history"""
    bl_idname = "mesh_history.obliterate"
    bl_label = "Delete history"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not context.active_object.select_get():
            return False
        return 'history_collection' in context.active_object.keys()
    
    def execute(self, context):
        ob = context.active_object
        coll = ob["history_collection"]
        del ob["history_collection"]
        for obj in coll.objects:
            obj.name = obj.data.name
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(coll)
        return {"FINISHED"}
    

class MESH_HISTORY_OT_save(bpy.types.Operator):
    """Saves a version of a sculpt as a seperate object"""
    bl_idname = "mesh_history.save"
    bl_label = "Save version"
    bl_options = {'REGISTER', 'UNDO'}
    
    version_name: bpy.props.StringProperty(
        name = "Version name",
        description = "Name of version",
        default = "",
    )
    
    @classmethod
    def poll(cls, context):
        if not context.active_object.select_get():
            return False
        return 'history_collection' in context.active_object.keys()
    
    def execute(self, context):
        if not self.version_name:
            self.version_name = get_version_name(self, context)
        old_ob = context.active_object
        stamp = datetime.datetime.now().strftime(__time_str__)
        new_ob = bpy.data.objects.new(self.version_name, old_ob.data.copy())
        new_ob.data.name = stamp
        new_ob.name = self.version_name
        print(new_ob.name, self.version_name)
        # Unlink from all collections, since this object should only
        # exist in the versions collection
        old_ob['history_collection'].objects.link(new_ob)
        bpy.context.view_layer.objects.active = old_ob
        self.version_name = ""
        return {"FINISHED"}
    
class MESH_HISTORY_OT_get(bpy.types.Operator):
    bl_idname = "mesh_history.get"
    bl_label = "Get version"
    bl_options = {'REGISTER', 'UNDO'}
    
    version_enum : bpy.props.EnumProperty(
        name = "Versions",
        description = "Which version to fetch",
        items = add_items_from_history_callback,
        default = 0,
    )
    
    @classmethod
    def poll(cls, context):
        if not context.active_object.select_get():
            return False
        return 'history_collection' in context.active_object.keys()
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def execute(self, context):
        mode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        if self.version_enum == "current":
            return {"CANCELLED"}
        name = self.version_enum
        data_name = context.active_object.data.name
        context.active_object.data = bpy.data.meshes[name].copy()
        context.active_object.data.name = data_name
        bpy.ops.object.mode_set(mode=mode)
        return {"FINISHED"}        

class VIEW_3D_PT_mesh_history(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh history"
    bl_label = "Mesh history"

    def draw(self, context):
        col = self.layout.column(align = True)
        props = col.operator("mesh_history.initialize",
                             icon = 'DOCUMENTS')
        props = col.operator("mesh_history.obliterate",
                             icon = 'TRASH')
        props = col.operator("mesh_history.save",
                             icon = 'FILE_NEW')
        props = col.operator("mesh_history.get",
                             icon = 'FILE_TICK')
            
class VIEW3D_MT_mesh_history(bpy.types.Menu):
    bl_label = "Mesh History"
    
    def draw(self, _context):
        self.layout.operator("mesh_history.initialize", icon='DOCUMENTS')
        self.layout.operator("mesh_history.obliterate", icon='TRASH')
        self.layout.operator("mesh_history.save", icon='FILE_NEW')
        self.layout.operator("mesh_history.get", icon='FILE_TICK')

def mesh_history_menu_draw(self, context):
    self.layout.separator()
    self.layout.menu("VIEW3D_MT_mesh_history")

classes = (
    MESH_HISTORY_OT_save,
    MESH_HISTORY_OT_initialize,
    MESH_HISTORY_OT_obliterate,
    MESH_HISTORY_OT_get,
    VIEW_3D_PT_mesh_history,
    VIEW3D_MT_mesh_history,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_sculpt.append(mesh_history_menu_draw)
    bpy.types.VIEW3D_MT_object.append(mesh_history_menu_draw)
    bpy.types.VIEW3D_MT_edit_mesh.append(mesh_history_menu_draw)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_sculpt.remove(mesh_history_menu_draw)
    bpy.types.VIEW3D_MT_object.remove(mesh_history_menu_draw)
    bpy.types.VIEW3D_MT_edit_mesh.remove(mesh_history_menu_draw)
