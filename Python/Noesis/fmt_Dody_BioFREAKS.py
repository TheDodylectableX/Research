#--------------------------------------------------------------------------------------------------------------
#--- Bio F.R.E.A.K.S. archive and model plugin for Rich Whitehouse's Noesis
#
#      File: fmt_BioFREAKS.py
#    Author: Dodylectable
#   Version: 1.0
#   Purpose: To extract assets from Bio F.R.E.A.K.S. PC version
#      Note: A lot of the formats don't have actual file extensions so I made them up
#          : Model format research is incomplete!
#--------------------------------------------------------------------------------------------------------------

from inc_noesis import *

# -----------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------

def registerNoesisTypes():
    arcHandle = noesis.register("Bio F.R.E.A.K.S. MUK Archive", ".MUK")
    noesis.setHandlerTypeCheck(arcHandle, bfArchiveCheck)
    noesis.setHandlerExtractArc(arcHandle, bfArchiveExtract)

    mdlHandle = noesis.register("Bio F.R.E.A.K.S. Model", ".SKELETAL_MESH_CHARACTER;.SKELETAL_MESH_BASIC")
    noesis.setHandlerTypeCheck(mdlHandle, bfModelCheck)
    noesis.setHandlerLoadModel(mdlHandle, bfLoadModel)

    return 1

# -----------------------------------------------------------------------
# MUK Archive Handler
# -----------------------------------------------------------------------

_ASSET_TYPES = {
    2:   "SKELETAL_MESH_CHARACTER",
    3:   "GAME_ASSET_1",
    4:   "GAME_ASSET_2",
    5:   "SKELETAL_MESH_BASIC",
    10:  "GAME_ASSET_3",
    11:  "VISUAL_EFFECT_MAYBE",
    12:  "GAME_ASSET_4",
    255: "GAME_ASSET_UNKNOWN",
}

def bfArchiveCheck(data):
    if len(data) < 8: return 0
    bs = NoeBitStream(data)
    version     = bs.readUShort()
    fileCount   = bs.readUShort()
    fileNameLen = bs.readUInt()
    if fileNameLen != 8: return 0
    if version == 0 or version > 100: return 0
    return 1

def bfArchiveExtract(fileName, fileLen, justChecking):
    if justChecking: return 1

    with open(fileName, "rb") as f:
        bs = NoeBitStream(f.read())

    version     = bs.readUShort()
    fileCount   = bs.readUShort()
    fileNameLen = bs.readUInt()

    remaining = fileCount
    while remaining > 0:
        chunkCount = min(remaining, 256)
        for _ in range(chunkCount):
            rawName    = bs.readBytes(fileNameLen)
            nameStr    = rawName.split(b"\x00")[0].decode("ascii", errors="replace")
            assetType  = bs.readUInt()
            fileSize   = bs.readUInt()
            fileOffset = bs.readUInt()

            if fileSize > 0:
                ext      = _ASSET_TYPES.get(assetType, "ASSET_%02X" % assetType)
                outName  = "%s.%s" % (nameStr, ext)
                savedPos = bs.tell()
                bs.seek(fileOffset, NOESEEK_ABS)
                fileData = bs.readBytes(fileSize)
                bs.seek(savedPos, NOESEEK_ABS)
                rapi.exportArchiveFile(outName, fileData)

        bs.readUInt()
        remaining -= chunkCount

    return 1

# -----------------------------------------------------------------------
# Model Constants
# -----------------------------------------------------------------------
_BONE_REC_SIZE = 200
_PROBE_OFFSET  = 60          # restPose[3][3]: always 1.0f in a valid affine matrix
_PROBE_VALUE   = 0x3F800000  # IEEE 754 bit-pattern for 1.0f
_WORLD_OFFSET  = 128
_LINKB_OFFSET  = 196

def bfModelCheck(data):
    if len(data) < 8: return 0
    bs = NoeBitStream(data)
    faceCount = bs.readUShort()
    vertCount = bs.readUShort()
    if faceCount == 0 or vertCount == 0: return 0
    return 1

def bfLoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    bs  = NoeBitStream(data)

    faceCount  = bs.readUShort()
    vertCount  = bs.readUShort()
    attrCount  = bs.readUShort()
    totalIndexCount = bs.readUShort()
    boneCount  = bs.readUShort()
    hiResCount = bs.readUShort()
    loResCount = bs.readUInt()
    bs.readUInt() # Reserved
    bs.readUInt() # Reserved

    noesis.logPopup()
    print("faceCount=%d vertCount=%d attrCount=%d boneCount=%d hi=%d lo=%d" % (faceCount, vertCount, attrCount, boneCount, hiResCount, loResCount))

    FACE_SIZE = 56
    faceStart = 0x18
    faces = []

    for fi in range(faceCount):
        base = faceStart + fi * FACE_SIZE

        bs.seek(base + 0x0C, NOESEEK_ABS)
        u0 = bs.readFloat(); v0 = bs.readFloat()
        u1 = bs.readFloat(); v1 = bs.readFloat()
        u2 = bs.readFloat(); v2 = bs.readFloat()

        bs.seek(base + 0x24, NOESEEK_ABS)
        pi0 = bs.readUShort(); pi1 = bs.readUShort(); pi2 = bs.readUShort()

        bs.seek(base + 0x2A, NOESEEK_ABS)
        ai0 = bs.readUShort(); ai1 = bs.readUShort(); ai2 = bs.readUShort()

        bs.seek(base + 0x30, NOESEEK_ABS)
        matID = bs.readUShort()

        faces.append((pi0,pi1,pi2, ai0,ai1,ai2, u0,v0, u1,v1, u2,v2, matID))

    # -----------------------------------------------------------------------

    VPOS_SIZE = 16
    vposStart = faceStart + faceCount * FACE_SIZE
    realBase  = vposStart + 2 * VPOS_SIZE # Skip bounding box values

    verts_pos  = [] # bone-local positions (NOT world-space)
    verts_bone = [] # bone index per vertex
    for vi in range(vertCount + 1):
        bs.seek(realBase + vi * VPOS_SIZE, NOESEEK_ABS)
        boneRef = bs.readUInt()
        x = bs.readFloat(); y = bs.readFloat(); z = bs.readFloat()
        verts_pos.append((x, y, z))
        verts_bone.append(boneRef & 0xFF)

    # -----------------------------------------------------------------------

    VNRM_SIZE  = 12
    vnrmStart  = vposStart + (vertCount + 3) * VPOS_SIZE
    nrmReadCnt = max(vertCount, attrCount) + 1

    verts_nrm = []
    for vi in range(nrmReadCnt):
        off = vnrmStart + vi * VNRM_SIZE
        if off + 12 > len(data):
            break
        bs.seek(off, NOESEEK_ABS)
        nx = bs.readFloat(); ny = bs.readFloat(); nz = bs.readFloat()
        verts_nrm.append((nx, ny, nz))
    verts_nrm.append((0.0, 1.0, 0.0)) # Fallback for out-of-range indices

    print("[normal entries read: %d (attrCount=%d)" % (len(verts_nrm) - 1, attrCount))

    # -----------------------------------------------------------------------

    skelStart = vnrmStart + vertCount * VNRM_SIZE
    nodeCount = boneCount - 1 if boneCount > 0 else 0
    recBase   = skelStart + 24 + nodeCount * 36

    print("[BF] skelStart=0x%X recBase=0x%X nodeCount=%d" % (skelStart, recBase, nodeCount))

    boneRecords = []   # list of (parentIdx, restFlat:[16f], worldFlat:[16f])
    recIdx = 0
    while True:
        probeOff = recBase + recIdx * _BONE_REC_SIZE + _PROBE_OFFSET
        if probeOff + 4 > len(data): break
        bs.seek(probeOff, NOESEEK_ABS)
        if bs.readUInt() != _PROBE_VALUE: break

        base = recBase + recIdx * _BONE_REC_SIZE

        bs.seek(base, NOESEEK_ABS)
        restFlat  = [bs.readFloat() for _ in range(16)]

        bs.seek(base + _WORLD_OFFSET, NOESEEK_ABS)
        worldFlat = [bs.readFloat() for _ in range(16)]

        bs.seek(base + _LINKB_OFFSET, NOESEEK_ABS)
        parentRaw = bs.readUInt()
        parentIdx = parentRaw & 0xFFFF

        boneRecords.append((parentIdx, restFlat, worldFlat))

        wf = worldFlat
        print("[BF] bone %d parent=0x%04X worldPos=(%.3f, %.3f, %.3f)" % (recIdx, parentIdx, wf[12], wf[13], wf[14]))
        recIdx += 1

    numBones = len(boneRecords)
    texStart = recBase + numBones * _BONE_REC_SIZE
    print("numBones=%d texStart=0x%X dataLen=0x%X" % (numBones, texStart, len(data)))

    # -----------------------------------------------------------------------

    textures = []
    texDims  = []

    bs.seek(texStart, NOESEEK_ABS)
    for imgIdx in range(hiResCount + loResCount):
        if bs.tell() + 16 > len(data):
            break

        imgFmt = bs.readUInt()
        bs.readUInt()
        w = bs.readUInt()
        h = bs.readUInt()

        print("[BF] tex %d: fmt=%d %dx%d" % (imgIdx, imgFmt, w, h))

        if w == 0 or h == 0: break

        pixCount = w * h
        if imgFmt == 1:
            pixData = bs.readBytes(pixCount * 4)
        else:
            rgbRaw = bytearray(bs.readBytes(pixCount * 3))
            rgba   = bytearray(pixCount * 4)
            for pi in range(pixCount):
                rgba[pi*4]     = rgbRaw[pi*3]
                rgba[pi*4 + 1] = rgbRaw[pi*3 + 1]
                rgba[pi*4 + 2] = rgbRaw[pi*3 + 2]
                rgba[pi*4 + 3] = 0xFF
            pixData = bytes(rgba)

        texName = rapi.getOutputName() + "_tex%02d" % imgIdx
        textures.append(NoeTexture(texName, w, h, pixData, noesis.NOESISTEX_RGBA32))
        texDims.append((w, h))

    # -----------------------------------------------------------------------
    # MATERIALS
    # Bit 0 of materialID selects between the two hi-res textures.
    # -----------------------------------------------------------------------

    def _texIdxForMat(matID):
        return (matID & 0x1) if hiResCount >= 2 else 0

    matIDs    = sorted(set(f[12] for f in faces))
    materials = []
    matNames  = {}

    for matID in matIDs:
        texIdx  = _texIdxForMat(matID)
        matName = "mat_%04X" % matID
        mat     = NoeMaterial(matName, "")
        if texIdx < len(textures): mat.setTexture(textures[texIdx].name)
        materials.append(mat)
        matNames[matID] = matName

    # -----------------------------------------------------------------------

    noeBones = []
    for bi in range(numBones):
        parentIdx, restFlat, _ = boneRecords[bi]
        noesisParent = -1 if parentIdx == 0xFFFF else int(parentIdx)
        rf = restFlat
        localMat = NoeMat43([
            NoeVec3([rf[0],  rf[1],  rf[2]]),
            NoeVec3([rf[4],  rf[5],  rf[6]]),
            NoeVec3([rf[8],  rf[9],  rf[10]]),
            NoeVec3([rf[12], rf[13], rf[14]]),
        ])
        noeBones.append(NoeBone(bi, "bone_%02d" % bi, localMat, None, noesisParent))

    if noeBones: noeBones = rapi.multiplyBones(noeBones)

    # -----------------------------------------------------------------------

    for matID in matIDs:
        texIdx   = _texIdxForMat(matID)
        tw, th   = texDims[texIdx] if texIdx < len(texDims) else (256, 256)
        matFaces = [f for f in faces if f[12] == matID]

        localPos  = []
        localNrm  = []
        localUV   = []
        localBone = []
        localWgt  = []
        localIdx  = []
        vertCache = {}

        for face in matFaces:
            pi0,pi1,pi2 = face[0], face[1], face[2]
            ai0,ai1,ai2 = face[3], face[4], face[5]
            u0,v0       = face[6], face[7]
            u1,v1       = face[8], face[9]
            u2,v2       = face[10],face[11]

            faceVerts = (
                (pi0, ai0, u0, v0),
                (pi1, ai1, u1, v1),
                (pi2, ai2, u2, v2),
            )
            triIdx = []
            for (pi, ai, uRaw, vRaw) in faceVerts:
                key = (pi, ai, uRaw, vRaw)
                if key not in vertCache:
                    safePi     = pi if pi < len(verts_pos) else 0
                    lx, ly, lz = verts_pos[safePi]
                    boneIdx    = verts_bone[safePi] if safePi < len(verts_bone) else 0
                    boneIdx    = boneIdx if boneIdx < numBones else 0

                    safeAi     = ai if ai < len(verts_nrm) else len(verts_nrm) - 1
                    nx, ny, nz = verts_nrm[safeAi]

                    # Texel-space UVs: divide by texture dimension to normalise.
                    # Flip V: file origin is top-left, OpenGL is bottom-left.
                    uN = uRaw / float(tw)
                    vN = 1.0 - (vRaw / float(th))

                    vertCache[key] = len(localPos)
                    localPos.append((lx, ly, lz))
                    localNrm.append((nx, ny, nz))
                    localUV.append((uN, vN))
                    localBone.append(boneIdx)
                    localWgt.append(1.0)

                triIdx.append(vertCache[key])

            localIdx.extend(triIdx)

        numLocalVerts = len(localPos)

    # -----------------------------------------------------------------------

        posBuf  = bytearray(numLocalVerts * 12)
        nrmBuf  = bytearray(numLocalVerts * 12)
        uvBuf   = bytearray(numLocalVerts * 8)
        boneBuf = bytearray(numLocalVerts * 2)
        wgtBuf  = bytearray(numLocalVerts * 4)
        idxBuf  = bytearray(len(localIdx)  * 2)

        for i in range(numLocalVerts):
            struct.pack_into("<3f", posBuf,  i * 12, *localPos[i])
            struct.pack_into("<3f", nrmBuf,  i * 12, *localNrm[i])
            struct.pack_into("<2f", uvBuf,   i * 8,  *localUV[i])
            struct.pack_into("<H",  boneBuf, i * 2,  localBone[i])
            struct.pack_into("<f",  wgtBuf,  i * 4,  localWgt[i])

        for i, idx in enumerate(localIdx): struct.pack_into("<H", idxBuf, i * 2, idx)

        rapi.rpgSetMaterial(matNames[matID])
        rapi.rpgBindPositionBuffer(bytes(posBuf),   noesis.RPGEODATA_FLOAT,  12)
        rapi.rpgBindNormalBuffer(bytes(nrmBuf),     noesis.RPGEODATA_FLOAT,  12)
        rapi.rpgBindUV1Buffer(bytes(uvBuf),         noesis.RPGEODATA_FLOAT,  8)
        rapi.rpgBindBoneIndexBuffer(bytes(boneBuf), noesis.RPGEODATA_USHORT, 2,  1)
        rapi.rpgBindBoneWeightBuffer(bytes(wgtBuf), noesis.RPGEODATA_FLOAT,  4,  1)
        rapi.rpgCommitTriangles(bytes(idxBuf), noesis.RPGEODATA_USHORT, len(localIdx), noesis.RPGEO_TRIANGLE, 1) # Flip reverseWinding to 0 if mesh appears inside-out

    # -----------------------------------------------------------------------
    try:
        mdl = rapi.rpgConstructModel()
    except:
        mdl = NoeModel()

    mdl.setModelMaterials(NoeModelMaterials(textures, materials))
    mdl.setBones(noeBones)
    mdlList.append(mdl)

    return 1
