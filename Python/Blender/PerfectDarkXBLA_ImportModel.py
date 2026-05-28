# ---------------------------------------------------------------------------------------------------
# Perfect Dark (Xbox 360 Remastered) Model Import Script
# Supports rigged and static models
# ---------------------------------------------------------------------------------------------------
import os, bpy, struct, random, mathutils
# ---------------------------------------------------------------------------------------------------
# Open this in Blender's scripting tab then run it depending on the configurations you've set
# ---------------------------------------------------------------------------------------------------

# --- CONFIGURATION ---
# Set to "FILE" for a single model or "FOLDER" for batch processing
IMPORT_MODE = "FOLDER"
# IMPORT_MODE = "FILE" 

# Point this to either a specific .bin file or the extracted folder
TARGET_PATH = r"D:\noesisv4442\imperfect light\PackedSegFile_files"
# TARGET_PATH = r"D:\noesisv4442\imperfect light\PackedSegFile_files\seg_2612_parent_4294967295.bin"

# ---------------------------------------------------------------------------------------------------

MAGIC_SKINNED = (0x447A0000, 0x43480000, 0x443B8000
MAGIC_STATIC  = 0x42C80000

def import_pd_model(filepath):
    with open(filepath, 'rb') as f: # File size sanity check
        f.seek(0, 2)
        if f.tell() < 32: return False
        f.seek(0)

        # 1. Parse Header
        header_data = f.read(32)
        (vertexCount, vertexDataOffset, faceDataOffset, meshCount, meshDataOffset, boneCount, assetType, vertexDataRelatedOffset) = struct.unpack('>8I', header_data)

        # Check for the model type imported by the user
        if assetType not in MAGIC_SKINNED and assetType != MAGIC_STATIC: return False # Not a recognized model, Silently skip
        if vertexCount == 0 or meshCount == 0: return False

        # 2. Parse Skeleton for Skeletal Meshes
        bone_matrices = []
        if assetType in MAGIC_SKINNED and boneCount > 0:
            f.seek(32)
            for (_) in range(boneCount):
                mat_data = struct.unpack('>12f', f.read(48))
                b_mat = mathutils.Matrix((
                    (mat_data[0], mat_data[1], mat_data[2], 0.0),
                    (mat_data[3], mat_data[4], mat_data[5], 0.0),
                    (mat_data[6], mat_data[7], mat_data[8], 0.0),
                    (mat_data[9], mat_data[10], mat_data[11], 1.0)
                ))
                b_mat.transpose()
                bone_matrices.append(b_mat)

        # 3. Parse SubMeshes
        f.seek(meshDataOffset)
        submeshes = []
        for _ in range(meshCount):
            start_face, face_count, mat_flag = struct.unpack('>3I', f.read(12))
            submeshes.append({'start': start_face, 'count': face_count, 'mat_flag': mat_flag})

        # 4. Parse Vertices (Dynamic Stride)
        f.seek(vertexDataOffset)
        verts = []
        uvs = []
        normals = []
        skin_data = []
        # v_colors = [] # Not sure about them yet
        
        vertex_stride = 48 if assetType in MAGIC_SKINNED else 36

        for (_) in range(vertexCount):
            v_data = f.read(vertex_stride)

            px, py, pz, u, v, nx, ny, nz = struct.unpack('>3f 2f 3f', v_data[:32])
            
            verts.append((px, py, pz))
            uvs.append((u, 1.0 - v)) 
            normals.append((nx, ny, nz))

            if assetType in MAGIC_SKINNED:
                w1, w2, w3, w4 = struct.unpack('>4B', v_data[32:36])
                i1, i2, i3, i4 = struct.unpack('>4B', v_data[44:48])
                skin_data.append(((i1, i2, i3, i4), (w1, w2, w3, w4)))
            elif assetType == MAGIC_STATIC:
                r, g, b, a = struct.unpack('>4B', v_data[32:36])
                # v_colors.append((r/255.0, g/255.0, b/255.0, a/255.0))

        # 5. Parse Faces
        total_faces = submeshes[-1]['start'] + submeshes[-1]['count']
        f.seek(faceDataOffset)
        faces = []
        for (_) in range(total_faces):
            idx1, idx2, idx3 = struct.unpack('>3H', f.read(6))
            if idx1 < vertexCount and idx2 < vertexCount and idx3 < vertexCount: faces.append((idx1, idx3, idx2)) # CCW Winding Order

    #-- CONSTRUCT GEOMETRY
    mesh_name = os.path.basename(filepath)
    mesh = bpy.data.meshes.new(f"{mesh_name}")
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.collection.objects.link(obj)
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    #-- CONSTRUCT ARMATURE
    armature_obj = None
    if assetType in MAGIC_SKINNED and boneCount > 0:
        armature_data = bpy.data.armatures.new(f"{mesh_name}_Armature")
        armature_obj = bpy.data.objects.new(f"{mesh_name}_Armature", armature_data)
        bpy.context.collection.objects.link(armature_obj)

        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for b, matrix in enumerate(bone_matrices):
            edit_bone = armature_data.edit_bones.new(f"bone_{b}")
            edit_bone.head = (0, 0, 0)
            edit_bone.tail = (0, 0.05, 0)
            edit_bone.matrix = matrix

        bpy.ops.object.mode_set(mode='OBJECT')

        obj.parent = armature_obj
        modifier = obj.modifiers.new(type='ARMATURE', name='Armature')
        modifier.object = armature_obj

    #--- NORMALS
    for poly in mesh.polygons: poly.use_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals)
    if hasattr(mesh, "use_auto_smooth"): mesh.use_auto_smooth = True

    #--- UV MAP
    if not mesh.uv_layers: mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            loop = mesh.loops[loop_index]
            uv_layer[loop_index].uv = uvs[loop.vertex_index]

    #--- WEIGHTS
    if assetType in MAGIC_SKINNED and boneCount > 0:
        vertex_groups = {}
        for b in range(boneCount): vertex_groups[b] = obj.vertex_groups.new(name=f"bone_{b}")
            
        for v_idx, (indices, weights) in enumerate(skin_data):
            for i in range(4):
                weight = weights[i] / 255.0 
                if weight > 0.0:
                    bone_idx = indices[i]
                    if bone_idx in vertex_groups: vertex_groups[bone_idx].add([v_idx], weight, 'REPLACE')

    #--- MATERIALS
    for sm in submeshes:
        mat_name = f"Material_{sm['mat_flag']:08X}"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.diffuse_color = [random.uniform(.4, 1) for _ in range(3)] + [1.0]
        obj.data.materials.append(mat)

    mat_index = 0
    for sm in submeshes:
        start_idx = sm['start']
        end_idx = start_idx + sm['count']
        for i in range(start_idx, end_idx):
            if i < len(mesh.polygons): mesh.polygons[i].material_index = mat_index
        mat_index += 1

    return True

def execute_importer():
    print(f"[*] Starting Perfect Dark Importer (Mode: {IMPORT_MODE})")
    
    if IMPORT_MODE == "FILE":
        if os.path.isfile(TARGET_PATH):
            if import_pd_model(TARGET_PATH):
                print(f"[*] Successfully imported single file: {os.path.basename(TARGET_PATH)}")
            else: print(f"[!] Failed to import or unrecognized format: {TARGET_PATH}")
        else: print(f"[!] Invalid file path: {TARGET_PATH}")

    elif IMPORT_MODE == "FOLDER":
        if os.path.isdir(TARGET_PATH):
            success_count = 0
            for filename in os.listdir(TARGET_PATH):
                filepath = os.path.join(TARGET_PATH, filename)
                if os.path.isfile(filepath):
                    try:
                        if import_pd_model(filepath):
                            success_count += 1
                            print(f" [+] Imported: {filename}")
                    except Exception as e:
                        print(f" [!] Error importing {filename}: {e}")
            print(f"[*] Batch complete. Imported {success_count} models.")
        else: print(f"[!] Invalid folder path: {TARGET_PATH}")

# Run!
execute_importer()

# ---------------------------------------------------------------------------------------------------
