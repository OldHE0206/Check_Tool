# _*_ coding:utf-8 _*_
__author__ = 'Old_He'
################################################################################
# 这是一个全面的Maya场景检查和处理工具，包含7大功能模块：
# 场景大纲、模型拓补、模型UV、材质、灯光渲染、骨骼绑定和动画。
# 工具提供自动化检查和一键处理功能，帮助用户快速发现和修复场景中的问题。
################################################################################

import maya.cmds as cmds
import maya.api.OpenMaya as om
import pymel.core as pm
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Qt
import math
import os
import re
from datetime import datetime

# 内部工具函数
def _getNodeName(uuid):
    try:
        nodes = cmds.ls(uuid)
        if nodes and cmds.objExists(nodes[0]):
            return nodes[0]
        return None
    except:
        return None

def getNodeNameFromUUID(uuid):
    """正确地从UUID获取节点名称"""
    nodes = cmds.ls(uuid)
    if nodes:
        return nodes[0]
    return None

# 检查函数
def trailingNumbers(nodes, _):
    trailingNumbers = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and nodeName[-1].isdigit():
                trailingNumbers.append(node)
    return "nodes", trailingNumbers

def duplicatedNames(nodes, _):
    nodesByShortName = {}
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName:
            name = nodeName.rsplit('|', 1)[-1]
            if name not in nodesByShortName:
                nodesByShortName[name] = []
            nodesByShortName[name].append(node)
    invalid = []
    for name, shortNameNodes in nodesByShortName.items():
        if len(shortNameNodes) > 1:
            invalid.extend(shortNameNodes)
    return "nodes", invalid

def namespaces(nodes, _):
    namespaces = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and ':' in nodeName:
            namespaces.append(node)
    return "nodes", namespaces

def shapeNames(nodes, _):
    shapeNames = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            new = nodeName.split('|')
            # 只获取非中间体形状节点
            shapes = cmds.listRelatives(nodeName, shapes=True, noIntermediate=True)
            if shapes:
                shapename = new[-1] + "Shape"
                if shapes[0] != shapename:
                    shapeNames.append(node)
    return "nodes", shapeNames

def triangles(_, SLMesh):
    triangles = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                numOfEdges = faceIt.getEdges()
                if len(numOfEdges) == 3:
                    if uuid not in triangles:
                        triangles[uuid] = []
                    triangles[uuid].append(faceIt.index())
                faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", triangles

def ngons(_, SLMesh):
    ngons = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                numOfEdges = faceIt.getEdges()
                if len(numOfEdges) > 4:
                    if uuid not in ngons:
                        ngons[uuid] = []
                    ngons[uuid].append(faceIt.index())
                faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", ngons

def hardEdges(_, SLMesh):
    hardEdges = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            edgeIt = om.MItMeshEdge(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not edgeIt.isDone():
                if edgeIt.isSmooth is False and edgeIt.onBoundary() is False:
                    if uuid not in hardEdges:
                        hardEdges[uuid] = []
                    hardEdges[uuid].append(edgeIt.index())
                edgeIt.next()
            selIt.next()
    except:
        pass
    return "edge", hardEdges

def lamina(_, SLMesh):
    lamina = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                laminaFaces = faceIt.isLamina()
                if laminaFaces is True:
                    if uuid not in lamina:
                        lamina[uuid] = []
                    lamina[uuid].append(faceIt.index())
                faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", lamina

def zeroAreaFaces(_, SLMesh):
    zeroAreaFaces = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                faceArea = faceIt.getArea()
                if faceArea <= 0.00000001:
                    if uuid not in zeroAreaFaces:
                        zeroAreaFaces[uuid] = []
                    zeroAreaFaces[uuid].append(faceIt.index())
                faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", zeroAreaFaces

def zeroLengthEdges(_, SLMesh):
    zeroLengthEdges = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            edgeIt = om.MItMeshEdge(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not edgeIt.isDone():
                if edgeIt.length() <= 0.00001:
                    if uuid not in zeroLengthEdges:
                        zeroLengthEdges[uuid] = []
                    zeroLengthEdges[uuid].append(edgeIt.index())
                edgeIt.next()
            selIt.next()
    except:
        pass
    return "edge", zeroLengthEdges

def selfPenetratingUVs(transformNodes, _):
    selfPenetratingUVs = {}
    for node in transformNodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            shapes = cmds.listRelatives(
                nodeName,
                shapes=True,
                type="mesh",
                noIntermediate=True)
            if shapes and cmds.objExists(shapes[0]):
                overlapping = cmds.polyUVOverlap("{}.f[*]".format(shapes[0]), oc=True)
                if overlapping:
                    # 修复字符串格式化错误
                    base_str = "{}.f[".format(shapes[0])
                    formatted = [overlap.split(base_str)[1][:-1] for overlap in overlapping]
                    if node not in selfPenetratingUVs:
                        selfPenetratingUVs[node] = []
                    selfPenetratingUVs[node].extend(formatted)
    return "polygon", selfPenetratingUVs

def noneManifoldEdges(_, SLMesh):
    noneManifoldEdges = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            edgeIt = om.MItMeshEdge(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not edgeIt.isDone():
                if edgeIt.numConnectedFaces() > 2:
                    if uuid not in noneManifoldEdges:
                        noneManifoldEdges[uuid] = []
                    noneManifoldEdges[uuid].append(edgeIt.index())
                edgeIt.next()
            selIt.next()
    except:
        pass
    return "edge", noneManifoldEdges

def openEdges(_, SLMesh):
    openEdges = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            edgeIt = om.MItMeshEdge(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not edgeIt.isDone():
                if edgeIt.numConnectedFaces() < 2:
                    if uuid not in openEdges:
                        openEdges[uuid] = []
                    openEdges[uuid].append(edgeIt.index())
                edgeIt.next()
            selIt.next()
    except:
        pass
    return "edge", openEdges

def poles(_, SLMesh):
    poles = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            vertexIt = om.MItMeshVertex(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not vertexIt.isDone():
                if vertexIt.numConnectedEdges() > 5:
                    if uuid not in poles:
                        poles[uuid] = []
                    poles[uuid].append(vertexIt.index())
                vertexIt.next()
            selIt.next()
    except:
        pass
    return "vertex", poles

def starlike(_, SLMesh):
    noneStarlike = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            polyIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not polyIt.isDone():
                if polyIt.isStarlike() is False:
                    if uuid not in noneStarlike:
                        noneStarlike[uuid] = []
                    noneStarlike[uuid].append(polyIt.index())
                polyIt.next()
            selIt.next()
    except:
        pass
    return "polygon", noneStarlike

def missingUVs(_, SLMesh):
    missingUVs = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                if faceIt.hasUVs() is False:
                    if uuid not in missingUVs:
                        missingUVs[uuid] = []
                    missingUVs[uuid].append(faceIt.index())
                faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", missingUVs

def uvRange(_, SLMesh):
    uvRange = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            mesh = om.MFnMesh(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            Us, Vs = mesh.getUVs()
            for i in range(len(Us)):
                if Us[i] < 0 or Us[i] > 10 or Vs[i] < 0:
                    if uuid not in uvRange:
                        uvRange[uuid] = []
                    uvRange[uuid].append(i)
            selIt.next()
    except:
        pass
    return "uv", uvRange

def onBorder(_, SLMesh):
    onBorder = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            mesh = om.MFnMesh(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            Us, Vs = mesh.getUVs()
            for i in range(len(Us)):
                if abs(int(Us[i]) - Us[i]) < 0.00001 or abs(int(Vs[i]) - Vs[i]) < 0.00001:
                    if uuid not in onBorder:
                        onBorder[uuid] = []
                    onBorder[uuid].append(i)
            selIt.next()
    except:
        pass
    return "uv", onBorder

def crossBorder(_, SLMesh):
    crossBorder = {}
    try:
        selIt = om.MItSelectionList(SLMesh)
        while not selIt.isDone():
            faceIt = om.MItMeshPolygon(selIt.getDagPath())
            fn = om.MFnDependencyNode(selIt.getDagPath().node())
            uuid = fn.uuid().asString()
            while not faceIt.isDone():
                U, V = set(), set()
                try:
                    UVs = faceIt.getUVs()
                    Us, Vs, = UVs[0], UVs[1]
                    for i in range(len(Us)):
                        uAdd = int(Us[i]) if Us[i] > 0 else int(Us[i]) - 1
                        vAdd = int(Vs[i]) if Vs[i] > 0 else int(Vs[i]) - 1
                        U.add(uAdd)
                        V.add(vAdd)
                    if len(U) > 1 or len(V) > 1:
                        if uuid not in crossBorder:
                            crossBorder[uuid] = []
                        crossBorder[uuid].append(faceIt.index())
                    faceIt.next()
                except:
                    faceIt.next()
            selIt.next()
    except:
        pass
    return "polygon", crossBorder

def unfrozenTransforms(nodes, _):
    unfrozenTransforms = []
    # 默认摄像机列表，这些摄像机通常不需要检查
    default_cameras = ["persp", "top", "front", "side"]
    
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            # 跳过默认摄像机
            if nodeName in default_cameras:
                continue
                
            try:
                # 检查节点类型
                nodeType = cmds.nodeType(nodeName)
                
                # 对于关节(joint)类型，使用新的检查方法
                if nodeType == "joint":
                    # 获取关节的旋转和缩放属性值
                    rotate_x = cmds.getAttr(nodeName + '.rotateX')
                    rotate_y = cmds.getAttr(nodeName + '.rotateY')
                    rotate_z = cmds.getAttr(nodeName + '.rotateZ')

                    scale_x = cmds.getAttr(nodeName + '.scaleX')
                    scale_y = cmds.getAttr(nodeName + '.scaleY')
                    scale_z = cmds.getAttr(nodeName + '.scaleZ')

                    # 检查旋转是否不为0或缩放是否不为1
                    is_rotate_non_zero = (rotate_x != 0.0 or 
                                         rotate_y != 0.0 or 
                                         rotate_z != 0.0)

                    is_scale_non_one = (scale_x != 1.0 or 
                                       scale_y != 1.0 or 
                                       scale_z != 1.0)

                    # 如果旋转不为0或缩放不为1，则视为未冻结
                    if is_rotate_non_zero or is_scale_non_one:
                        unfrozenTransforms.append(node)
                else:
                    # 对于其他类型，检查所有变换属性
                    translation = cmds.xform(
                        nodeName, q=True, worldSpace=True, translation=True)
                    rotation = cmds.xform(nodeName, q=True, worldSpace=True, rotation=True)
                    scale = cmds.xform(nodeName, q=True, worldSpace=True, scale=True)
                    if translation != [0.0, 0.0, 0.0] or rotation != [0.0, 0.0, 0.0] or scale != [1.0, 1.0, 1.0]:
                        unfrozenTransforms.append(node)
            except Exception as e:
                print(f"检查未冻结变换时出错 {nodeName}: {str(e)}")
                continue
    return "nodes", unfrozenTransforms

def layers(nodes, _):
    layers = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            try:
                layer = cmds.listConnections(nodeName, type="displayLayer")
                if layer:
                    layers.append(node)
            except:
                continue
    return "nodes", layers

def shaders(transformNodes, _):
    shaders = []
    for node in transformNodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            try:
                shape = cmds.listRelatives(nodeName, shapes=True, fullPath=True)
                if shape and cmds.nodeType(shape[0]) == 'mesh' and cmds.objExists(shape[0]):
                    shadingGrps = cmds.listConnections(shape[0], type='shadingEngine')
                    if shadingGrps and shadingGrps[0] != 'initialShadingGroup':
                        shaders.append(node)
            except:
                continue
    return "nodes", shaders

def history(nodes, _):
    history = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            try:
                shape = cmds.listRelatives(nodeName, shapes=True, fullPath=True)
                if shape and cmds.nodeType(shape[0]) == 'mesh' and cmds.objExists(shape[0]):
                    historySize = len(cmds.listHistory(shape[0]))
                    if historySize > 1:
                        history.append(node)
            except:
                continue
    return "nodes", history

def uncenteredPivots(nodes, _):
    uncenteredPivots = []
    # 定义要跳过的默认摄像机列表
    default_cameras = ["persp", "top", "front", "side"]
    
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            try:
                # 获取节点的短名称（不含命名空间和路径）
                short_name = nodeName.split('|')[-1].split(':')[-1]
                
                # 跳过关节(joint)类型的节点和默认摄像机
                nodeType = cmds.nodeType(nodeName)
                if nodeType == "joint" or short_name in default_cameras:
                    continue
                    
                if cmds.xform(nodeName, q=1, ws=1, rp=1) != [0, 0, 0]:
                    uncenteredPivots.append(node)
            except:
                continue
    return "nodes", uncenteredPivots

def emptyGroups(nodes, _):
    emptyGroups = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName):
            try:
                # 只检查变换节点
                nodeType = cmds.nodeType(nodeName)
                if nodeType != "transform":
                    continue
                
                # 排除骨骼节点
                if cmds.objectType(nodeName) == 'joint':
                    continue
                    
                # 排除有连接的节点(如约束、表达式等)
                if cmds.listConnections(nodeName, connections=True, source=True, destination=False):
                    continue
                    
                # 排除有自定义属性的节点
                if cmds.listAttr(nodeName, userDefined=True):
                    continue
                
                # 检查是否是真正的空组(没有子节点)
                children = cmds.listRelatives(nodeName, children=True, fullPath=True)
                if not children:
                    emptyGroups.append(node)
            except:
                continue
    return "nodes", emptyGroups

def parentGeometry(transformNodes, _):
    parentGeometry = []
    processed_nodes = set()  # 跟踪已处理的节点
    
    for node in transformNodes:
        nodeName = _getNodeName(node)
        if nodeName and cmds.objExists(nodeName) and node not in processed_nodes:
            try:
                parents = cmds.listRelatives(nodeName, p=True, fullPath=True)
                if parents:
                    for parent in parents:
                        children = cmds.listRelatives(parent, fullPath=True) or []
                        for child in children:
                            if cmds.nodeType(child) == 'mesh':
                                parentGeometry.append(node)
                                processed_nodes.add(node)
                                break  # 找到一个网格就跳出循环
            except:
                continue
    return "nodes", parentGeometry

def nonMap1UVSets(nodes, _):
    non_map1_uvsets = {}
    processed_nodes = set()  # 跟踪已处理的节点
    
    for node in nodes:
        if node in processed_nodes:
            continue
            
        node_name = _getNodeName(node)
        if not node_name or not cmds.objExists(node_name):
            continue
            
        try:
            shapes = cmds.listRelatives(node_name, shapes=True, type="mesh", fullPath=True) or []
            if not shapes:
                continue
                
            for shape in shapes:
                if not cmds.objExists(shape):
                    continue
                    
                uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
                
                if not uv_sets:
                    continue
                
                # 检查是否有非map1的UV集
                has_non_map1 = False
                for uv_set in uv_sets:
                    if uv_set != "map1":
                        has_non_map1 = True
                        if node not in non_map1_uvsets:
                            non_map1_uvsets[node] = []
                        non_map1_uvsets[node].append(uv_set)
                
                # 如果找到非map1 UV集，标记节点为已处理
                if has_non_map1:
                    processed_nodes.add(node)
                    break  # 找到一个形状有非map1 UV集就跳出循环
        except Exception as e:
            continue
    
    return "uvSets", non_map1_uvsets

def emptyLayers(nodes, _):
    """
    检查场景中空的显示层和动画层
    
    参数:
    nodes: 要检查的节点UUID列表
    _: 保留参数(未使用)
    
    返回:
    元组: ("nodes", 空层的UUID列表)
    """
    empty_layers = []
    
    # 获取所有显示层
    display_layers = cmds.ls(type="displayLayer")
    
    # 检查每个显示层是否为空
    for layer in display_layers:
        # 跳过默认显示层
        if layer == "defaultLayer":
            continue
            
        # 获取层中的成员 - 使用更可靠的方法
        try:
            members = cmds.editDisplayLayerMembers(layer, query=True, fullNames=True)
        except:
            members = []
            
        # 如果层中没有成员，则认为是空层
        if not members or len(members) == 0:
            # 获取层的UUID
            layer_uuid = cmds.ls(layer, uuid=True)
            if layer_uuid and layer_uuid[0]:
                empty_layers.append(layer_uuid[0])
    
    # 获取所有动画层
    anim_layers = cmds.ls(type="animLayer")
    
    # 检查每个动画层是否为空
    for layer in anim_layers:
        # 获取层中的动画曲线 - 使用更可靠的方法
        try:
            anim_curves = cmds.animLayer(layer, query=True, attribute=True)
        except:
            anim_curves = []
            
        # 如果层中没有动画曲线，则认为是空层
        if not anim_curves or len(anim_curves) == 0:
            # 获取层的UUID
            layer_uuid = cmds.ls(layer, uuid=True)
            if layer_uuid and layer_uuid[0]:
                empty_layers.append(layer_uuid[0])
    
    return "nodes", empty_layers

def checkLights(nodes, _):
    """检查场景中是否有灯光组件"""
    lights = []
    # 默认灯光列表，这些灯光通常不需要检查
    default_lights = ["defaultLightSet", "defaultLightList"]
    
    for node in nodes:
        nodeName = getNodeNameFromUUID(node)
        if nodeName and nodeName not in default_lights:
            # 检查节点是否为灯光类型
            node_type = cmds.nodeType(nodeName)
            if node_type in ["light", "areaLight", "spotLight", "pointLight", "directionalLight", "ambientLight"]:
                lights.append(node)
            else:
                # 检查节点是否有灯光形状子节点
                shapes = cmds.listRelatives(nodeName, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) in ["light", "areaLight", "spotLight", "pointLight", "directionalLight", "ambientLight"]:
                        lights.append(node)
                        break
    
    return "nodes", lights

def checkCameras(nodes, _):
    """检查场景中是否有摄像机"""
    cameras = []
    # 默认摄像机列表，这些摄像机通常不需要检查
    default_cameras = ["persp", "top", "front", "side"]
    
    for node in nodes:
        nodeName = getNodeNameFromUUID(node)
        if nodeName and nodeName not in default_cameras:
            # 检查节点是否为摄像机类型
            node_type = cmds.nodeType(nodeName)
            if node_type == "camera":
                cameras.append(node)
            else:
                # 检查节点是否有摄像机形状子节点
                shapes = cmds.listRelatives(nodeName, shapes=True, fullPath=True) or []
                for shape in shapes:
                    if cmds.nodeType(shape) == "camera":
                        cameras.append(node)
                        break
    
    return "nodes", cameras

def checkKeyframes(nodes, _):
    """检查场景中是否有关键帧"""
    nodes_with_keyframes = []
    
    for node in nodes:
        node_name = getNodeNameFromUUID(node)
        if node_name and cmds.objExists(node_name):
            try:
                # 检查节点是否有动画曲线连接
                anim_curves = cmds.listConnections(node_name, 
                                                type='animCurve', 
                                                source=True, 
                                                destination=False)
                
                if anim_curves:
                    # 获取关键帧数量
                    keyframe_count = 0
                    for curve in anim_curves:
                        keytimes = cmds.keyframe(curve, query=True, timeChange=True) or []
                        keyframe_count += len(keytimes)
                    
                    if keyframe_count > 0:
                        nodes_with_keyframes.append(node)
            except Exception as e:
                print(f"检查节点 '{node_name}' 的关键帧时出错: {e}")
    
    return "nodes", nodes_with_keyframes

def overlapping_vertices(nodes, params=None):
    """检查场景中的模型是否有重叠的顶点"""
    # 存储有重叠顶点的节点UUID
    nodes_with_overlaps = []
    # 从参数获取容差值，如果没有则使用默认值0.001
    tolerance = params.get('tolerance', 0.001) if params and isinstance(params, dict) else 0.001
    
    for node in nodes:
        try:
            # 获取节点名称
            node_name = getNodeNameFromUUID(node)
            if not node_name or not cmds.objExists(node_name):
                continue
            
            # 检查是否为有效的多边形网格
            if not pm.nodeType(node_name) == 'transform' or not pm.listRelatives(node_name, shapes=True, type='mesh'):
                continue
            
            # 获取所有顶点
            vertices = pm.ls(f"{node_name}.vtx[:]", flatten=True)
            if not vertices:
                continue
            
            # 存储顶点位置和字符串表示
            vertex_positions = []
            for vtx in vertices:
                pos = pm.xform(vtx, query=True, translation=True, worldSpace=True)
                vertex_str = str(vtx)
                vertex_positions.append((vertex_str, pos))
            
            # 检查重叠顶点
            checked = set()
            has_overlaps = False
            
            for i in range(len(vertex_positions)):
                if i in checked:
                    continue
                    
                _, pos1 = vertex_positions[i]
                group = [i]
                
                for j in range(i + 1, len(vertex_positions)):
                    if j in checked:
                        continue
                        
                    _, pos2 = vertex_positions[j]
                    
                    # 计算欧氏距离
                    distance = math.sqrt(
                        (pos1[0] - pos2[0])**2 +
                        (pos1[1] - pos2[1])** 2 +
                        (pos1[2] - pos2[2])**2
                    )
                    
                    if distance < tolerance:
                        group.append(j)
                        checked.add(j)
                        has_overlaps = True
                
                if len(group) > 1:
                    checked.add(i)
            
            # 如果发现重叠顶点，添加到结果列表
            if has_overlaps:
                nodes_with_overlaps.append(node)
                
        except Exception as e:
            print(f"检查节点 '{node}' 的重叠顶点时出错: {e}")
    
    return "nodes", nodes_with_overlaps

def is_selected_model_separated(nodes, _):
    """检查选中的模型是否由多个分离的部分组成"""
    separated_nodes = []
    
    for node in nodes:
        # 从节点获取名称（假设节点是UUID或节点名）
        # 这里使用节点本身作为名称，可根据实际情况替换为getNodeNameFromUUID
        node_name = getNodeNameFromUUID(node)
        
        if node_name and cmds.objExists(node_name):
            try:
                # 确保我们处理的是形状节点
                if cmds.nodeType(node_name) == 'transform':
                    # 获取变换节点下的网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True)
                    if not shapes:
                        print(f"模型 {node_name} 不包含网格形状，跳过检查")
                        continue
                    shape_node = shapes[0]
                else:
                    # 直接使用形状节点
                    shape_node = node_name
                    if cmds.nodeType(shape_node) != 'mesh':
                        print(f"{shape_node} 不是网格类型节点，跳过检查")
                        continue
                
                # 计算模型的壳数量
                shell_count = cmds.polyEvaluate(shape_node, shell=True)
                
                # 壳数量大于1表示是分离模型
                if shell_count > 1:
                    separated_nodes.append(node)
                    
            except Exception as e:
                print(f"检查节点 '{node_name}' 是否为分离模型时出错: {e}")
    
    return "nodes", separated_nodes

def checkModelSymmetry(nodes, _):
    """检查模型是否沿世界X轴对称
    
    参数:
        nodes: 要检查的节点列表
        _: 忽略的参数（保持与调用方式一致）
    """
    axis = 'X'  # 固定检查X轴对称
    space = 'world'  # 固定使用世界坐标系
    tolerance = 0.001  # 容差值
    
    asymmetric_models = []
    
    for node in nodes:
        node_name = getNodeNameFromUUID(node)
        if node_name and cmds.objExists(node_name):
            try:
                # 确保我们处理的是变换节点
                if cmds.nodeType(node_name) != 'transform':
                    # 如果是形状节点，获取其父变换节点
                    parent = cmds.listRelatives(node_name, parent=True, fullPath=True)
                    if parent:
                        node_name = parent[0]
                    else:
                        continue
                
                # 检查节点是否有网格形状
                shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True)
                if not shapes:
                    continue
                
                shape_node = shapes[0]
                
                # 获取网格的所有顶点位置
                vertices = cmds.ls(f"{shape_node}.vtx[*]", flatten=True)
                if not vertices:
                    continue
                
                # 获取顶点位置（世界坐标系）
                vertex_positions = []
                for vtx in vertices:
                    pos = cmds.xform(vtx, query=True, translation=True, worldSpace=True)
                    vertex_positions.append((vtx, pos))
                
                # 检查对称性
                symmetric = True
                checked = set()
                
                for i, (vtx1, pos1) in enumerate(vertex_positions):
                    if i in checked:
                        continue
                    
                    x1, y1, z1 = pos1
                    
                    # 计算X轴对称点坐标
                    sym_pos = [-x1, y1, z1]
                    
                    # 检查是否存在对称点
                    symmetric_point_found = False
                    for j, (vtx2, pos2) in enumerate(vertex_positions):
                        if j in checked or j == i:
                            continue
                        
                        x2, y2, z2 = pos2
                        
                        # 使用容差比较
                        if (abs(sym_pos[0] - x2) < tolerance and 
                            abs(sym_pos[1] - y2) < tolerance and 
                            abs(sym_pos[2] - z2) < tolerance):
                            symmetric_point_found = True
                            checked.add(j)
                            break
                    
                    # 如果找不到对称点，检查是否是中心点（自身对称）
                    if not symmetric_point_found:
                        # 检查是否是中心点（在X轴上）
                        if abs(x1) < tolerance:
                            symmetric_point_found = True
                    
                    if not symmetric_point_found:
                        symmetric = False
                        break
                
                if not symmetric:
                    # 获取显示名称
                    display_name = cmds.ls(node_name, shortNames=True)[0]
                    asymmetric_models.append({
                        "node": node,
                        "node_name": node_name,
                        "display_name": display_name
                    })
            except Exception as e:
                print(f"检查节点 '{node_name}' 的对称性时出错: {e}")
    
    return "nodes", asymmetric_models

def checkGroundAlignment(nodes, params=None):
    """检查模型最低顶点位置是否不等于地面"""
    misaligned_models = []
    
    # 从参数获取容差值，如果没有则使用默认值0.001
    tolerance = params.get('tolerance', 0.001) if params and isinstance(params, dict) else 0.001
    
    for node in nodes:
        node_name = getNodeNameFromUUID(node)
        if node_name and cmds.objExists(node_name):
            try:
                # 检查节点是否有网格形状
                shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True)
                if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                    shape_node = shapes[0]
                    
                    # 获取网格的所有顶点位置
                    vertices = cmds.xform(f"{shape_node}.vtx[*]", query=True, translation=True, worldSpace=True)
                    
                    # 找到最低的Y值
                    min_y = float('inf')
                    for i in range(0, len(vertices), 3):
                        y = vertices[i + 1]  # Y坐标在顶点数据中的位置
                        if y < min_y:
                            min_y = y
                    
                    # 使用参数传递的容差值
                    if abs(min_y) > tolerance:
                        misaligned_models.append(node)  # 直接添加节点的UUID
            except Exception as e:
                print(f"检查节点 '{node_name}' 的顶点位置时出错: {e}")
    
    return "nodes", misaligned_models  # 返回UUID列表


def checkModelFacesNum(nodes, params=None):
    """检查模型模型面数是否超过限定数值"""
    overFacesNum_models = []
    
    # 从参数获取面数上限，如果没有则使用默认值10000
    face_limit = params.get('face_limit', 10000) if params and isinstance(params, dict) else 10000
    
    for node in nodes:
        node_name = getNodeNameFromUUID(node)
        if node_name and cmds.objExists(node_name):
            try:
                # 检查节点是否有网格形状
                shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True)
                if shapes:
                    shape_node = shapes[0]
                    
                    # 计算三角面总数
                    triangle_count = cmds.polyEvaluate(shape_node, triangle=True)
                    
                    # 如果面数超过限制
                    if triangle_count > face_limit:
                        # 获取显示名称
                        display_name = cmds.ls(node_name, shortNames=True)[0]
                        overFacesNum_models.append({
                            "node": node,
                            "node_name": node_name,
                            "display_name": display_name,
                            "triangle_count": triangle_count,
                            "face_limit": face_limit
                        })
            except Exception as e:
                print(f"检查节点 '{node_name}' 的面数时出错: {e}")
    
    return "nodes", overFacesNum_models

def checkMissingMaterials(nodes, _):
    """
    检查指定节点或场景中所有模型是否没有材质，并返回没有材质的模型UUID列表
    """
    print("开始检查场景中的模型材质...")
    
    # 存储没有材质的模型的UUID
    models_without_materials = []
    
    # 如果没有指定节点，则获取场景中所有的网格(模型)
    if not nodes:
        all_meshes = cmds.ls(type='mesh')
    else:
        # 如果指定了节点，获取这些节点及其子节点中的所有网格
        all_meshes = []
        for node in nodes:
            node_name = getNodeNameFromUUID(node)
            if node_name and cmds.objExists(node_name):
                # 获取节点及其所有子节点中的网格
                meshes = cmds.listRelatives(node_name, allDescendents=True, type='mesh', fullPath=True) or []
                all_meshes.extend(meshes)
    
    if not all_meshes:
        print("没有找到任何网格模型。")
        return "nodes", models_without_materials
    
    print(f"共找到 {len(all_meshes)} 个网格模型。")
    
    for mesh in all_meshes:
        # 获取网格的父变换节点(模型名称)
        parents = cmds.listRelatives(mesh, parent=True, fullPath=True)
        if not parents:
            continue
            
        model_name = parents[0]
        
        # 检查网格是否有材质连接
        shading_groups = cmds.listConnections(mesh, type='shadingEngine') or []
        
        # 如果没有着色组，或者只有初始着色组但没有有效材质
        has_valid_material = False
        for sg in shading_groups:
            # 检查着色组是否有表面着色器连接
            surface_shaders = cmds.listConnections(sg + '.surfaceShader', source=True, destination=False) or []
            if surface_shaders:
                has_valid_material = True
                break
        
        if not shading_groups or not has_valid_material:
            # 获取模型的UUID
            model_uuid = cmds.ls(model_name, uuid=True)
            if model_uuid:
                models_without_materials.append(model_uuid[0])
    
    # 打印结果
    if models_without_materials:
        print("\n以下模型没有材质或材质无效:")
        for i, uuid in enumerate(models_without_materials, 1):
            node_name = getNodeNameFromUUID(uuid)
            print(f"{i}. {node_name}")
        print(f"\n总共发现 {len(models_without_materials)} 个模型没有材质。")
    else:
        print("\n所有模型都有有效的材质。")
    
    # 返回没有材质的模型UUID列表，格式与参考代码一致
    return "nodes", models_without_materials

def checkGeometrySuffix(nodes, params=None):
    """检查场景中所有模型的后缀名是否是指定的后缀"""
    # 从参数获取后缀，如果没有则使用默认值"_Geo"
    suffix = params.get('suffix', '_Geo') if params and isinstance(params, dict) else '_Geo'
    
    geometrySuffixIssues = {}
    
    # 获取所有变换节点（模型）
    if not nodes:
        # 如果没有传入节点，获取场景中所有变换节点
        all_transforms = cmds.ls(type='transform')
    else:
        # 处理传入的节点列表
        all_transforms = []
        for uuid in nodes:
            node_name = getNodeNameFromUUID(uuid)
            if node_name and cmds.objExists(node_name) and cmds.nodeType(node_name) == 'transform':
                all_transforms.append(node_name)
    
    for transform in all_transforms:
        try:
            # 检查节点是否有网格形状（确保是模型）
            shapes = cmds.listRelatives(transform, shapes=True, type='mesh')
            if not shapes:
                continue  # 跳过没有网格形状的变换节点
                
            # 检查变换节点名称是否以指定后缀结尾
            if not transform.endswith(suffix):
                # 获取节点的UUID
                try:
                    sel = om.MSelectionList()
                    sel.add(transform)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录问题信息
                    geometrySuffixIssues[uuid] = [f"模型名称 '{transform}' 不以'{suffix}'结尾"]
                except Exception as e:
                    # 如果无法获取UUID，使用节点名称作为键
                    geometrySuffixIssues[transform] = [f"模型名称 '{transform}' 不以'{suffix}'结尾"]
                        
        except Exception as e:
            # 如果处理模型时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(transform)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                geometrySuffixIssues[uuid] = [f"检查模型时出错: {str(e)}"]
            except:
                geometrySuffixIssues[transform] = [f"检查模型时出错: {str(e)}"]
    
    return "nodes", geometrySuffixIssues

def check_material_info(nodes, _):
    """检查场景中的材质信息并返回统计结果"""
    
    # 定义不可删除的默认节点
    PROTECTED_NODES = [
        "lambert1", 
        "standardSurface1", 
        "particleCloud1", 
        "shaderGlow1",
        "initialShadingGroup",
        "initialParticleSE"
    ]
    
    # 如果nodes为空，检查所有材质节点
    if not nodes:
        all_materials = cmds.ls(mat=True)
    else:
        # 只检查传入的节点中的材质节点
        all_materials = []
        for node in nodes:
            node_name = getNodeNameFromUUID(node)
            if node_name and cmds.objExists(node_name) and cmds.objectType(node_name, isType='material'):
                all_materials.append(node_name)
    
    # 过滤掉受保护的默认材质
    all_materials = [mat for mat in all_materials if mat not in PROTECTED_NODES]
    
    # 获取所有着色组
    all_shading_groups = cmds.ls(type='shadingEngine')
    # 过滤掉受保护的默认着色组
    all_shading_groups = [sg for sg in all_shading_groups if sg not in PROTECTED_NODES]
    
    # 按类型分类材质
    materials_by_type = {}
    for material in all_materials:
        try:
            material_type = cmds.objectType(material)
            if material_type not in materials_by_type:
                materials_by_type[material_type] = []
            materials_by_type[material_type].append(material)
        except:
            continue
    
    # 识别已使用和未使用的材质
    used_materials = []
    unused_materials = []
    
    for material in all_materials:
        # 检查材质是否连接到着色组
        shading_groups = cmds.listConnections(
            material + ".outColor", 
            type="shadingEngine"
        ) or []
        
        # 检查着色组是否有对象连接
        is_used = False
        for sg in shading_groups:
            objects = cmds.sets(sg, query=True) or []
            if objects:
                is_used = True
                break
        
        if is_used:
            used_materials.append(material)
        else:
            unused_materials.append(material)
    
    # 识别未使用的着色组
    unused_shading_groups = []
    
    for shading_group in all_shading_groups:
        # 检查着色组是否有对象连接
        objects = cmds.sets(shading_group, query=True) or []
        
        # 检查着色组是否有材质连接
        connected_materials = cmds.listConnections(
            shading_group + ".surfaceShader",
            source=True,
            destination=False
        ) or []
        
        # 如果既没有对象连接也没有材质连接，则认为是未使用的着色组
        if not objects and not connected_materials:
            unused_shading_groups.append(shading_group)
    
    # 构建返回的数据结构，使用UUID作为键
    material_info = {}
    
    # 添加所有材质信息
    for material in all_materials:
        try:
            sel = om.MSelectionList()
            sel.add(material)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if uuid not in material_info:
                material_info[uuid] = []
            material_info[uuid].append(f"material:{material}")
        except:
            if material not in material_info:
                material_info[material] = []
            material_info[material].append(f"material:{material}")
    
    # 添加材质类型信息
    for mat_type, materials in materials_by_type.items():
        for material in materials:
            try:
                sel = om.MSelectionList()
                sel.add(material)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                if uuid not in material_info:
                    material_info[uuid] = []
                material_info[uuid].append(f"type:{mat_type}")
            except:
                if material not in material_info:
                    material_info[material] = []
                material_info[material].append(f"type:{mat_type}")
    
    # 添加使用状态信息
    for material in used_materials:
        try:
            sel = om.MSelectionList()
            sel.add(material)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if uuid not in material_info:
                material_info[uuid] = []
            material_info[uuid].append("status:used")
        except:
            if material not in material_info:
                material_info[material] = []
            material_info[material].append("status:used")
    
    for material in unused_materials:
        try:
            sel = om.MSelectionList()
            sel.add(material)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if uuid not in material_info:
                material_info[uuid] = []
            material_info[uuid].append("status:unused")
        except:
            if material not in material_info:
                material_info[material] = []
            material_info[material].append("status:unused")
    
    # 添加着色组信息
    for sg in all_shading_groups:
        try:
            sel = om.MSelectionList()
            sel.add(sg)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if uuid not in material_info:
                material_info[uuid] = []
            material_info[uuid].append(f"shading_group:{sg}")
        except:
            if sg not in material_info:
                material_info[sg] = []
            material_info[sg].append(f"shading_group:{sg}")
    
    # 添加未使用着色组信息
    for sg in unused_shading_groups:
        try:
            sel = om.MSelectionList()
            sel.add(sg)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if uuid not in material_info:
                material_info[uuid] = []
            material_info[uuid].append("shading_group_status:unused")
        except:
            if sg not in material_info:
                material_info[sg] = []
            material_info[sg].append("shading_group_status:unused")
    
    return "material", material_info

def texturePathLost(_, SLMesh):
    """检查材质贴图的贴图路径是否丢失"""
    textureErrors = {}
    
    # 获取所有文件纹理节点
    file_nodes = cmds.ls(type="file")
    
    for file_node in file_nodes:
        # 获取文件纹理节点的贴图路径
        texture_path = cmds.getAttr(file_node + ".fileTextureName")
        
        # 检查路径是否存在
        if texture_path and not os.path.exists(texture_path):
            # 获取文件纹理节点的UUID
            try:
                sel = om.MSelectionList()
                sel.add(file_node)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录错误信息
                if uuid not in textureErrors:
                    textureErrors[uuid] = []
                textureErrors[uuid].append(texture_path)
            except:
                # 如果无法获取UUID，使用节点名称作为键
                if file_node not in textureErrors:
                    textureErrors[file_node] = []
                textureErrors[file_node].append(texture_path)
    
    return "texture", textureErrors

def checkSkyDomeLight(_, SLMesh):
    """检查场景中是否有SkyDomeLight"""
    skydomeLights = {}
    
    # 获取所有灯光
    allLights = cmds.ls(type='aiSkyDomeLight')
    
    # 获取所有灯光的UUID
    for light in allLights:
        try:
            sel = om.MSelectionList()
            sel.add(light)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            skydomeLights[uuid] = []  # 使用空列表作为值
        except:
            # 如果无法获取UUID，使用节点名称作为键
            skydomeLights[light] = []  # 使用空列表作为值
    
    # 如果没有找到任何天空灯，则返回错误信息
    if not skydomeLights:
        try:
            # 对于非DAG节点使用不同的方法
            sel = om.MSelectionList()
            sel.add("defaultRenderGlobals")
            node_obj = sel.getDependNode(0)  # 获取依赖节点而非DAG节点
            fn = om.MFnDependencyNode(node_obj)
            uuid = fn.uuid().asString()
            skydomeLights[uuid] = ["未创建HDRI环境光"]
        except:
            skydomeLights["defaultRenderGlobals"] = ["未创建HDRI环境光"]
    
    return "skydomeLights", skydomeLights

def checkRenderLayer(_, SLMesh):
    """检查当前渲染层是否是masterLayer"""
    renderLayerErrors = {}
    
    # 获取当前渲染层
    current_render_layer = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
    
    # 检查是否是masterLayer (defaultRenderLayer)
    if current_render_layer != "defaultRenderLayer":
        # 获取当前渲染层的UUID
        try:
            sel = om.MSelectionList()
            sel.add(current_render_layer)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            # 记录错误信息
            renderLayerErrors[uuid] = [current_render_layer]
        except:
            # 如果无法获取UUID，使用节点名称作为键
            renderLayerErrors[current_render_layer] = [current_render_layer]
    
    return "renderLayer", renderLayerErrors

def checkAOVs(_, SLMesh):
    """检查渲染设置中是否有AOV分层"""
    aovErrors = {}
    
    # 检查当前渲染器
    current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    
    # 根据不同的渲染器检查AOV设置
    if current_renderer == "arnold":
        # 检查Arnold AOVs
        aov_nodes = cmds.ls(type="aiAOV")
        if not aov_nodes:
            # 获取默认渲染设置节点的UUID
            try:
                sel = om.MSelectionList()
                sel.add("defaultRenderGlobals")
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录错误信息
                aovErrors[uuid] = ["No AOVs found in Arnold render settings"]
            except:
                # 如果无法获取UUID，使用节点名称作为键
                aovErrors["defaultRenderGlobals"] = ["No AOVs found in Arnold render settings"]
    
    elif current_renderer == "vray":
        # 检查VRay AOVs
        vray_aovs = cmds.ls(type="VRayExtraTex")
        if not vray_aovs:
            try:
                sel = om.MSelectionList()
                sel.add("defaultRenderGlobals")
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                aovErrors[uuid] = ["No AOVs found in VRay render settings"]
            except:
                aovErrors["defaultRenderGlobals"] = ["No AOVs found in VRay render settings"]
    
    else:
        # 对于其他渲染器，尝试检查常见的AOV节点类型
        aov_types = ["redshiftAOV", "renderPass", "mentalrayAOV"]
        has_aovs = False
        
        for aov_type in aov_types:
            if cmds.ls(type=aov_type):
                has_aovs = True
                break
        
        if not has_aovs:
            try:
                sel = om.MSelectionList()
                sel.add("defaultRenderGlobals")
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                aovErrors[uuid] = [f"No AOVs found for {current_renderer} renderer"]
            except:
                aovErrors["defaultRenderGlobals"] = [f"No AOVs found for {current_renderer} renderer"]
    
    return "aov", aovErrors

def checkCPURendering(_, SLMesh, params=None):
    """检查渲染设置中是否是CPU渲染"""
    cpuRenderingErrors = {}
    
    # 从参数获取设备选择，如果没有则默认检查CPU渲染
    device_choice = params.get('device', 'CPU渲染') if params and isinstance(params, dict) else 'CPU渲染'
    
    # 检查当前渲染器
    current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    
    # 根据不同渲染器检查CPU/GPU渲染设置
    if current_renderer == "arnold":
        # 检查Arnold渲染器是否使用CPU渲染
        if cmds.objExists("defaultArnoldRenderOptions"):
            render_device = cmds.getAttr("defaultArnoldRenderOptions.renderDevice")
            
            # 根据用户选择的设备进行检查
            if device_choice == "CPU渲染":
                # 用户选择检查CPU渲染，如果使用CPU渲染则正常，使用GPU渲染则报错
                if render_device != 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("defaultArnoldRenderOptions")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录错误信息
                        cpuRenderingErrors[uuid] = ["Arnold渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
                    except:
                        cpuRenderingErrors["defaultArnoldRenderOptions"] = ["Arnold渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
            else:  # GPU渲染
                # 用户选择检查GPU渲染，如果使用GPU渲染则正常，使用CPU渲染则报错
                if render_device == 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("defaultArnoldRenderOptions")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录错误信息
                        cpuRenderingErrors[uuid] = ["Arnold渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
                    except:
                        cpuRenderingErrors["defaultArnoldRenderOptions"] = ["Arnold渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
    
    elif current_renderer == "vray":
        # 检查VRay渲染器是否使用CPU渲染
        if cmds.objExists("vraySettings"):
            engine_type = cmds.getAttr("vraySettings.engine")
            
            # 根据用户选择的设备进行检查
            if device_choice == "CPU渲染":
                # 用户选择检查CPU渲染，如果使用CPU渲染则正常，使用GPU渲染则报错
                if engine_type != 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("vraySettings")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        cpuRenderingErrors[uuid] = ["VRay渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
                    except:
                        cpuRenderingErrors["vraySettings"] = ["VRay渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
            else:  # GPU渲染
                # 用户选择检查GPU渲染，如果使用GPU渲染则正常，使用CPU渲染则报错
                if engine_type == 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("vraySettings")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        cpuRenderingErrors[uuid] = ["VRay渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
                    except:
                        cpuRenderingErrors["vraySettings"] = ["VRay渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
    
    elif current_renderer == "redshift":
        # 检查Redshift渲染器是否使用CPU渲染
        if cmds.objExists("redshiftOptions"):
            device_type = cmds.getAttr("redshiftOptions.deviceType")
            
            # 根据用户选择的设备进行检查
            if device_choice == "CPU渲染":
                # 用户选择检查CPU渲染，如果使用CPU渲染则正常，使用GPU渲染则报错
                if device_type != 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("redshiftOptions")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        cpuRenderingErrors[uuid] = ["Redshift渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
                    except:
                        cpuRenderingErrors["redshiftOptions"] = ["Redshift渲染器设置为GPU渲染模式，但期望使用CPU渲染"]
            else:  # GPU渲染
                # 用户选择检查GPU渲染，如果使用GPU渲染则正常，使用CPU渲染则报错
                if device_type == 0:  # 0表示CPU渲染
                    try:
                        sel = om.MSelectionList()
                        sel.add("redshiftOptions")
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        cpuRenderingErrors[uuid] = ["Redshift渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
                    except:
                        cpuRenderingErrors["redshiftOptions"] = ["Redshift渲染器设置为CPU渲染模式，但期望使用GPU渲染"]
    
    else:
        # 对于其他渲染器，根据用户选择进行检查
        try:
            sel = om.MSelectionList()
            sel.add("defaultRenderGlobals")
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            if device_choice == "CPU渲染":
                # 对于其他渲染器，如果用户选择检查CPU渲染，则认为正常（因为大多数渲染器默认使用CPU）
                pass  # 不记录错误
            else:  # GPU渲染
                # 如果用户选择检查GPU渲染，但对于其他渲染器无法确定，则提示信息
                cpuRenderingErrors[uuid] = [f"{current_renderer}渲染器默认使用CPU渲染，但期望使用GPU渲染"]
        except:
            if device_choice == "GPU渲染":
                cpuRenderingErrors["defaultRenderGlobals"] = [f"{current_renderer}渲染器默认使用CPU渲染，但期望使用GPU渲染"]
    
    return "cpu_rendering", cpuRenderingErrors

def checkArnoldRenderer(_, SLMesh, params=None):
    """检查渲染设置中是否使用指定的渲染器"""
    rendererErrors = {}
    
    # 从参数获取目标渲染器，如果没有则默认为Arnold
    target_renderer = params.get('renderer', 'Arnold') if params and isinstance(params, dict) else 'Arnold'
    
    # 映射渲染器名称到Maya内部名称
    renderer_map = {
        'Arnold': 'arnold',
        'Vray': 'vray', 
        'Redshift': 'redshift'
    }
    
    target_renderer_internal = renderer_map.get(target_renderer, 'arnold')
    
    # 检查当前渲染器
    current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    
    # 检查是否是指定的渲染器
    if current_renderer != target_renderer_internal:
        # 获取默认渲染设置节点的UUID
        try:
            sel = om.MSelectionList()
            sel.add("defaultRenderGlobals")
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            # 记录错误信息
            rendererErrors[uuid] = [f"当前渲染器是 '{current_renderer}' 而不是 '{target_renderer}'"]
        except:
            # 如果无法获取UUID，使用节点名称作为键
            rendererErrors["defaultRenderGlobals"] = [f"当前渲染器是 '{current_renderer}' 而不是 '{target_renderer}'"]
    
    return "renderer", rendererErrors

def checkBoundModelIssues(nodes, _):
    """检查已绑定模型的建模历史、未冻结变换和未居中轴心"""
    modelIssues = {}
    
    # 如果传入了节点列表，则只检查这些节点
    if nodes:
        meshes_to_check = []
        for node in nodes:
            node_name = _getNodeName(node)
            if node_name and cmds.objExists(node_name):
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    meshes_to_check.append(node_name)
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    meshes_to_check.extend(shapes)
    else:
        # 如果没有传入节点列表，则获取所有网格
        meshes_to_check = cmds.ls(type='mesh')
    
    for mesh in meshes_to_check:
        try:
            # 获取网格的变换节点
            parents = cmds.listRelatives(mesh, parent=True, fullPath=True)
            if not parents:
                continue  # 跳过没有父节点的网格
                
            transform = parents[0]
            
            # 检查网格是否有蒙皮
            history = cmds.listHistory(mesh)
            if not history:
                continue  # 跳过没有历史的网格
                
            skin_clusters = cmds.ls(history, type='skinCluster')
            
            # 只有有蒙皮的模型才检查
            if skin_clusters:
                # 获取模型的UUID
                try:
                    sel = om.MSelectionList()
                    sel.add(transform)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                except:
                    # 如果无法获取UUID，使用节点名称作为键
                    uuid = transform
                
                issues = []
                
                # 1. 检查是否有建模历史记录
                deformers_to_keep = ['skinCluster', 'blendShape', 'cluster', 'tweak']
                modeling_history = []
                
                for node in history:
                    try:
                        node_type = cmds.objectType(node)
                        
                        # 检查是否是应该忽略的节点类型
                        should_ignore = False
                        
                        # 忽略Orig节点（绑定过程中正常生成的节点）
                        if 'Orig' in node:
                            should_ignore = True
                        
                        # 忽略骨骼节点（绑定骨骼是正常的）
                        if node_type == 'joint':
                            should_ignore = True
                            
                        # 忽略其他绑定相关的节点
                        if node_type in ['dagPose', 'skinCluster', 'blendShape']:
                            should_ignore = True
                            
                        # 如果节点应该被忽略，跳过检查
                        if should_ignore:
                            continue
                            
                        if node_type not in deformers_to_keep and not node_type.startswith('poly') and not node_type.startswith('subdiv'):
                            # 检查节点是否与模型直接相关
                            connections = cmds.listConnections(node, source=True, destination=False)
                            if not connections:
                                modeling_history.append(node)
                            else:
                                # 检查连接是否与当前网格相关
                                for conn in connections:
                                    if mesh == conn or (cmds.objectType(conn) == 'transform' and 
                                                    cmds.listRelatives(conn, shapes=True) and 
                                                    mesh == cmds.listRelatives(conn, shapes=True)[0]):
                                        modeling_history.append(node)
                                        break
                    except:
                        continue  # 跳过无法处理的节点
                
                if modeling_history:
                    # 只记录前5个建模历史节点
                    history_list = modeling_history[:5]
                    history_str = ", ".join(history_list)
                    if len(modeling_history) > 5:
                        history_str += f" 等 {len(modeling_history)} 个节点"
                    issues.append(f"建模历史: {history_str}")
                
                # 2. 检查是否未冻结变换
                try:
                    translate = cmds.getAttr(transform + '.translate')[0]
                    rotate = cmds.getAttr(transform + '.rotate')[0]
                    scale = cmds.getAttr(transform + '.scale')[0]
                    
                    if (abs(translate[0]) > 0.001 or abs(translate[1]) > 0.001 or abs(translate[2]) > 0.001 or
                        abs(rotate[0]) > 0.001 or abs(rotate[1]) > 0.001 or abs(rotate[2]) > 0.001 or
                        abs(scale[0] - 1.0) > 0.001 or abs(scale[1] - 1.0) > 0.001 or abs(scale[2] - 1.0) > 0.001):
                        issues.append("未冻结变换")
                except:
                    issues.append("无法获取变换属性")
                
                # 3. 检查是否未居中模型轴心到世界轴原点
                try:
                    pivot = cmds.xform(transform, query=True, worldSpace=True, rotatePivot=True)
                    if (abs(pivot[0]) > 0.001 or abs(pivot[1]) > 0.001 or abs(pivot[2]) > 0.001):
                        issues.append("轴心未居中到世界原点")
                except:
                    issues.append("无法获取轴心位置")
                
                # 如果有问题，记录到结果中
                if issues:
                    modelIssues[uuid] = issues
                    
        except Exception as e:
            # 如果处理模型时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(mesh)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                modelIssues[uuid] = [f"检查模型时出错: {str(e)}"]
            except:
                modelIssues[mesh] = [f"检查模型时出错: {str(e)}"]
    
    return "model_issues", modelIssues

def checkBlendShape(_, SLMesh, check_bound=None):
    """检查模型上是否有blendshape（可选择已绑定或未绑定）"""
    blendShapeIssues = {}
    
    # 获取所有网格
    meshes = cmds.ls(type='mesh')
    
    for mesh in meshes:
        try:
            # 获取网格的变换节点
            parents = cmds.listRelatives(mesh, parent=True, fullPath=True)
            if not parents:
                continue  # 跳过没有父节点的网格
                
            transform = parents[0]
            
            # 检查是否根据选择条件过滤模型
            if check_bound is not None:
                # 检查网格是否有蒙皮
                history = cmds.listHistory(mesh)
                if not history:
                    if check_bound:  # 如果需要检查已绑定模型，跳过没有历史的网格
                        continue
                else:
                    skin_clusters = cmds.ls(history, type='skinCluster')
                    has_skin = bool(skin_clusters)
                    
                    if check_bound and not has_skin:  # 如果需要检查已绑定模型，跳过未绑定的
                        continue
                    if not check_bound and has_skin:  # 如果需要检查未绑定模型，跳过已绑定的
                        continue
            
            # 检查网格是否有blendShape
            history = cmds.listHistory(mesh)
            if not history:
                continue  # 跳过没有历史的网格
                
            blend_shapes = cmds.ls(history, type='blendShape')
            
            # 如果有blendShape，记录问题
            if blend_shapes:
                # 获取模型的UUID
                sel = om.MSelectionList()
                sel.add(transform)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录blendShape信息
                blend_shape_info = []
                for bs in blend_shapes:
                    # 获取blendShape的目标数量
                    try:
                        target_count = cmds.blendShape(bs, query=True, target=True)
                        if target_count:
                            blend_shape_info.append(f"{bs} ({len(target_count)} 个目标)")
                        else:
                            blend_shape_info.append(f"{bs} (0 个目标)")
                    except:
                        blend_shape_info.append(f"{bs} (无法获取目标信息)")
                
                blendShapeIssues[uuid] = blend_shape_info
                    
        except Exception as e:
            # 如果处理模型时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(mesh)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                blendShapeIssues[uuid] = [f"检查模型时出错: {str(e)}"]
            except:
                blendShapeIssues[mesh] = [f"检查模型时出错: {str(e)}"]
    
    return "blendshape", blendShapeIssues

def checkUnboundJointsTransforms(_, SLMesh):
    """检查场景中未绑定的骨骼上变换节点是否已冻结"""
    unboundJointIssues = {}
    
    # 获取所有骨骼
    joints = cmds.ls(type='joint')
    
    for joint in joints:
        try:
            # 检查骨骼是否已绑定（是否有skinCluster连接）
            history = cmds.listHistory(joint)
            is_bound = False
            
            if history:
                skin_clusters = cmds.ls(history, type='skinCluster')
                if skin_clusters:
                    # 检查这个skinCluster是否连接到当前骨骼
                    for skin_cluster in skin_clusters:
                        influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
                        if joint in influences:
                            is_bound = True
                            break
            
            # 只处理未绑定的骨骼
            if not is_bound:
                # 检查变换是否已冻结
                translate = cmds.getAttr(joint + '.translate')[0]
                rotate = cmds.getAttr(joint + '.rotate')[0]
                scale = cmds.getAttr(joint + '.scale')[0]
                
                # 检查旋转是否为0，缩放是否为1
                rotation_not_zero = (abs(rotate[0]) > 0.001 or abs(rotate[1]) > 0.001 or abs(rotate[2]) > 0.001)
                scale_not_one = (abs(scale[0] - 1.0) > 0.001 or abs(scale[1] - 1.0) > 0.001 or abs(scale[2] - 1.0) > 0.001)
                
                if rotation_not_zero or scale_not_one:
                    # 获取骨骼的UUID
                    sel = om.MSelectionList()
                    sel.add(joint)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录问题信息
                    issues = []
                    if rotation_not_zero:
                        issues.append(f"旋转未冻结: {rotate[0]:.3f}, {rotate[1]:.3f}, {rotate[2]:.3f}")
                    if scale_not_one:
                        issues.append(f"缩放未冻结: {scale[0]:.3f}, {scale[1]:.3f}, {scale[2]:.3f}")
                    
                    unboundJointIssues[uuid] = issues
                    
        except Exception as e:
            # 如果处理骨骼时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(joint)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                unboundJointIssues[uuid] = [f"检查骨骼时出错: {str(e)}"]
            except:
                unboundJointIssues[joint] = [f"检查骨骼时出错: {str(e)}"]
    
    return "unbound_joints", unboundJointIssues

def find_redundant_joints(_, SLMesh):
    """
    检查场景中是否有多余的骨骼（没有和模型绑定的骨骼）
    返回冗余骨骼列表
    """
    # 获取场景中所有关节
    all_joints = cmds.ls(type='joint', long=True)
    
    if not all_joints:
        print("场景中没有找到骨骼")
        return "nodes", []  # 修改这里，返回元组
    
    # 获取所有皮肤簇
    skin_clusters = cmds.ls(type='skinCluster', long=True)
    
    # 收集所有被皮肤簇使用的关节
    used_joints = set()
    for skin_cluster in skin_clusters:
        influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
        if influences:
            # 转换为长名称以确保比较准确性
            influences_long = cmds.ls(influences, long=True)
            used_joints.update(influences_long)
    
    # 找出未使用的关节
    redundant_joints = [joint for joint in all_joints if joint not in used_joints]
    
    return "nodes", redundant_joints  # 修改这里，返回元组

def checkOverlappingJoints(_, SLMesh):
    """检查场景中是否有重叠的骨骼"""
    overlappingJointIssues = {}
    
    # 获取所有骨骼
    joints = cmds.ls(type='joint')
    
    # 存储骨骼位置信息
    joint_positions = {}
    
    for joint in joints:
        try:
            # 获取骨骼的世界空间位置
            pos = cmds.xform(joint, query=True, worldSpace=True, translation=True)
            pos_key = f"{pos[0]:.3f}_{pos[1]:.3f}_{pos[2]:.3f}"  # 使用精度为3位小数的字符串作为位置键
            
            # 获取骨骼的UUID
            sel = om.MSelectionList()
            sel.add(joint)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            
            # 记录位置信息
            if pos_key not in joint_positions:
                joint_positions[pos_key] = []
            joint_positions[pos_key].append((uuid, joint, pos))
                    
        except Exception as e:
            # 如果处理骨骼时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(joint)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                overlappingJointIssues[uuid] = [f"检查骨骼时出错: {str(e)}"]
            except:
                overlappingJointIssues[joint] = [f"检查骨骼时出错: {str(e)}"]
    
    # 检查重叠的骨骼
    tolerance = 0.001  # 位置容差值
    for pos_key, joints_at_position in joint_positions.items():
        if len(joints_at_position) > 1:
            # 这个位置有多个骨骼，检查它们是否真的重叠
            for i, (uuid1, joint1, pos1) in enumerate(joints_at_position):
                for j, (uuid2, joint2, pos2) in enumerate(joints_at_position[i+1:], i+1):
                    # 计算距离
                    distance = ((pos1[0] - pos2[0])**2 + 
                            (pos1[1] - pos2[1])**2 + 
                            (pos1[2] - pos2[2])**2)**0.5
                    
                    if distance < tolerance:
                        # 骨骼重叠
                        if uuid1 not in overlappingJointIssues:
                            overlappingJointIssues[uuid1] = []
                        overlappingJointIssues[uuid1].append(f"与 '{joint2}' 重叠 (距离: {distance:.4f})")
                        
                        if uuid2 not in overlappingJointIssues:
                            overlappingJointIssues[uuid2] = []
                        overlappingJointIssues[uuid2].append(f"与 '{joint1}' 重叠 (距离: {distance:.4f})")
    
    return "overlapping_joints", overlappingJointIssues

def checkJointSuffix(_, SLMesh, params=None):
    """检查骨骼的后缀名是否是指定的后缀"""
    # 从参数获取后缀，如果没有则使用默认值"_Jnt"
    suffix = params.get('suffix', '_Jnt') if params and isinstance(params, dict) else '_Jnt'
    
    jointSuffixIssues = {}
    
    # 获取所有骨骼
    joints = cmds.ls(type='joint')
    
    for joint in joints:
        try:
            # 检查骨骼名称是否以指定后缀结尾
            if not joint.endswith(suffix):
                # 获取骨骼的UUID
                sel = om.MSelectionList()
                sel.add(joint)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录问题信息
                jointSuffixIssues[uuid] = [f"骨骼名称 '{joint}' 不以'{suffix}'结尾"]
                    
        except Exception as e:
            # 如果处理骨骼时出错，记录错误信息
            try:
                sel = om.MSelectionList()
                sel.add(joint)
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                jointSuffixIssues[uuid] = [f"检查骨骼时出错: {str(e)}"]
            except:
                jointSuffixIssues[joint] = [f"检查骨骼时出错: {str(e)}"]
    
    return "joint_suffix", jointSuffixIssues

# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
def check_joint_alignment_XYZ(nodes, params):
    """
    检查场景内所有骨骼（包括已绑定骨骼）的旋转顺序是否符合目标旋转顺序
    只返回不符合目标旋转顺序的骨骼结果
    """
    # 初始化结果字典，仅存储不符合目标旋转顺序的骨骼
    results = {}
    
    # 从参数获取目标旋转顺序，默认为XYZ(0)
    target_rotate_order = params.get('target_rotate_order', 0)
    rotate_orders = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
    target_name = rotate_orders[target_rotate_order]
    
    def get_all_joints():
        """
        获取场景中所有骨骼（包括已绑定骨骼）
        返回需要检查的骨骼列表
        """
        try:
            # 获取场景中所有骨骼
            all_joints = cmds.ls(type='joint')
            
            if not all_joints:
                print("场景中没有找到任何骨骼")
                return []
            
            # 不再过滤末端骨骼，检查所有骨骼
            joints_to_check = []
            
            for joint in all_joints:
                try:
                    # 不再检查是否是末端骨骼，也不再检查是否已绑定
                    # 直接添加所有骨骼到检查列表
                    joints_to_check.append(joint)
                except Exception as e:
                    print(f"处理骨骼 {joint} 时出错: {e}")
                    continue
            
            return joints_to_check
        except Exception as e:
            print(f"查找需要检查的骨骼时出错: {e}")
            return []

    def check_joint_rotation_order(joint):
        """
        检查骨骼的旋转顺序是否为目标旋转顺序
        返回布尔值表示是否符合目标旋转顺序
        """
        try:
            # 获取骨骼的旋转顺序属性
            rotate_order = cmds.getAttr(joint + ".rotateOrder")
            
            # 比较当前旋转顺序与目标旋转顺序
            return rotate_order == target_rotate_order
        except Exception as e:
            print(f"检查骨骼 {joint} 旋转顺序时出错: {e}")
            return False

    def get_joint_uuid(joint_name):
        """获取骨骼的UUID"""
        try:
            sel = om.MSelectionList()
            sel.add(joint_name)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            return fn.uuid().asString()
        except Exception as e:
            print(f"获取骨骼 {joint_name} 的UUID时出错: {e}")
            return joint_name  # 如果获取UUID失败，使用骨骼名作为备用键

    try:
        # 获取需要检查的骨骼（场景中所有骨骼）
        joints_to_check = get_all_joints()
        total_checked = len(joints_to_check)
        
        if not joints_to_check:
            print(f"场景中没有找到任何骨骼（目标旋转顺序: {target_name}）")
            return "joint_alignment_xyz", results
        
        print(f"开始检查 {total_checked} 个骨骼的旋转顺序（目标: {target_name}）...")
        
        # 检查每个骨骼的旋转顺序，只记录不符合目标的结果
        for joint in joints_to_check:
            if not check_joint_rotation_order(joint):
                # 获取旋转顺序的具体名称
                rotate_order = cmds.getAttr(joint + ".rotateOrder")
                rotate_order_name = rotate_orders[rotate_order]
                
                # 获取骨骼UUID
                joint_uuid = get_joint_uuid(joint)
                
                # 记录不符合目标旋转顺序的骨骼信息
                error_msg = f"骨骼 '{joint}' 的旋转顺序不是{target_name} (当前: {rotate_order_name})"
                results[joint_uuid] = [error_msg]
                
                print(f"[ERR] {error_msg}")
            else:
                print(f"[OK] 骨骼 '{joint}' 的旋转顺序是{target_name}")
        
        # 打印检查结果总结
        print("=" * 60)
        print(f"旋转顺序检查完成总结 (目标: {target_name}):")
        print("=" * 60)
        print(f"  总共检查了 {total_checked} 个骨骼")
        correct_count = total_checked - len(results)
        print(f"  {target_name}旋转顺序: {correct_count} 个骨骼")
        print(f"  非{target_name}旋转顺序: {len(results)} 个骨骼")
        
        if results:
            print("\n非目标旋转顺序的骨骼详情:")
            for i, (joint_uuid, error_msgs) in enumerate(results.items(), 1):
                print(f"  {i}. {error_msgs[0]}")
        else:
            print(f"\n[OK] 所有骨骼的旋转顺序都是{target_name}")
        
        print("=" * 60)
        
    except Exception as e:
        error_msg = f"检查骨骼旋转顺序时出错: {e}"
        print(error_msg)
        results["joint_alignment_xyz_error"] = [error_msg]
    
    return "joint_alignment_xyz", results
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

def check_joint_parent_child(nodes, params):
    """
    检查所有骨骼（包括已绑定骨骼）的父级骨骼是否指向子级骨骼
    根据主轴向参数决定检查的轴向，只返回不符合要求的项
    """
    # 从参数获取目标轴向，默认为'x'
    target_axis = params.get('orientJoint', 'xyz')[0].lower() if params and isinstance(params, dict) else 'x'
    
    # 轴向映射到矩阵索引
    axis_indices = {
        'x': [0, 1, 2],    # X轴在世界矩阵中的索引
        'y': [4, 5, 6],    # Y轴在世界矩阵中的索引  
        'z': [8, 9, 10]    # Z轴在世界矩阵中的索引
    }
    
    results = {}  # 用于存储检查结果的字典
    
    def check_joint_orientation():
        """
        检查所有骨骼的父级骨骼是否朝向子骨骼，返回有问题的骨骼元组
        """
        # 获取场景中所有骨骼
        all_joints = cmds.ls(type='joint')
        if not all_joints:
            return tuple()  # 无骨骼时返回空元组
        
        problem_joints = []
        angle_threshold = 10  # 角度阈值（超过此值认为有问题，可调整）
        rad_threshold = math.radians(angle_threshold)  # 转换为弧度
        
        for child_joint in all_joints:
            # 获取当前骨骼的父级（仅保留骨骼类型的父级）
            parent_joint = cmds.listRelatives(child_joint, parent=True, type='joint')
            if not parent_joint:
                continue  # 无父骨骼（根骨骼）跳过
            parent_joint = parent_joint[0]  # 从列表中提取父骨骼名称
            
            # 获取父骨骼和子骨骼的世界空间位置
            try:
                parent_pos = cmds.xform(parent_joint, query=True, worldSpace=True, translation=True)
                child_pos = cmds.xform(child_joint, query=True, worldSpace=True, translation=True)
            except:
                continue  # 位置获取失败时跳过
            
            # 计算父到子的方向向量（并归一化）
            dir_vec = [child_pos[0] - parent_pos[0],
                       child_pos[1] - parent_pos[1],
                       child_pos[2] - parent_pos[2]]
            vec_length = math.sqrt(dir_vec[0]**2 + dir_vec[1]** 2 + dir_vec[2]**2)
            if vec_length < 0.0001:  # 父子骨骼位置重合（异常情况）
                problem_joints.append(parent_joint)
                continue
            dir_vec_normalized = [v / vec_length for v in dir_vec]
            
            # 获取父骨骼指定轴向的世界空间方向
            parent_matrix = cmds.xform(parent_joint, query=True, worldSpace=True, matrix=True)
            
            # 根据选择的轴向获取对应的向量
            axis_index = axis_indices.get(target_axis, axis_indices['x'])  # 默认使用X轴
            axis_vec = [parent_matrix[axis_index[0]], parent_matrix[axis_index[1]], parent_matrix[axis_index[2]]]
            axis_length = math.sqrt(axis_vec[0]** 2 + axis_vec[1]**2 + axis_vec[2]** 2)
            if axis_length < 0.0001:  # 矩阵异常（理论上不会发生）
                continue
            axis_normalized = [v / axis_length for v in axis_vec]
            
            # 计算两个向量的夹角（点积公式）
            dot_product = sum(a * b for a, b in zip(dir_vec_normalized, axis_normalized))
            dot_product = max(min(dot_product, 1.0), -1.0)  # 避免数值误差导致的范围溢出
            angle = math.acos(dot_product)  # 弧度
            
            # 若夹角超过阈值，记录父骨骼
            if angle > rad_threshold:
                problem_joints.append(parent_joint)
        
        # 去重并转换为元组（同一父骨骼可能有多个子骨骼，需去重）
        unique_problems = list(set(problem_joints))
        return tuple(unique_problems)

    # 执行检查并打印结果
    problem_joints = check_joint_orientation()
    
    # 修改：将问题骨骼转换为UUID格式，与其他检查函数保持一致
    problem_uuids = []
    for joint in problem_joints:
        try:
            sel = om.MSelectionList()
            sel.add(joint)
            dag = sel.getDagPath(0)
            fn = om.MFnDependencyNode(dag.node())
            uuid = fn.uuid().asString()
            problem_uuids.append(uuid)
        except:
            # 如果无法获取UUID，使用节点名称作为备用
            problem_uuids.append(joint)
    
    if problem_joints:
        print(f"发现 {len(problem_joints)} 个朝向异常的骨骼（检查轴向: {target_axis.upper()}）:")
        for joint in problem_joints:
            print(f"  - {joint}")
    else:
        print(f"所有骨骼父级朝向均正常（检查轴向: {target_axis.upper()}）")
    
    # 修改：返回格式与其他检查函数保持一致
    return "nodes", problem_uuids

def check_end_joint_alignment(nodes, _):
    """
    检查末端骨骼与父级轴向一致性
    
    参数:
        nodes: 要检查的节点列表
        _: 忽略的参数
        
    返回:
        元组: (结果类型字符串, 包含对齐问题的字典)
    """
    
    def check_end_joint_axis_alignment():
        """检查末端骨骼与父级轴向一致性，返回不一致的末端骨骼信息"""
        # 1. 筛选末端骨骼（无子代骨骼的骨骼）
        all_joints = cmds.ls(type='joint', long=True)  # 全路径名称避免重名
        end_joints = [j for j in all_joints if not cmds.listRelatives(j, children=True, type='joint')]
        
        if not end_joints:
            print("场景中无末端骨骼（无子代的骨骼）")
            return {}
        
        # 2. 轴向对应的矩阵索引（Maya列主序矩阵）
        axis_indices = {
            'x': [0, 1, 2],
            'y': [4, 5, 6],
            'z': [8, 9, 10]
        }
        
        # 3. 检查参数（角度阈值：超过5度视为不一致）
        angle_threshold = 5.0
        rad_threshold = math.radians(angle_threshold)
        
        # 4. 存储不一致的末端骨骼信息
        inconsistent_joints = {}
        
        for end_joint in end_joints:
            # 获取父级骨骼（仅骨骼类型）
            parent_joint = cmds.listRelatives(end_joint, parent=True, type='joint', fullPath=True)
            if not parent_joint:
                continue  # 无父级（根骨骼）跳过
            parent_joint = parent_joint[0]
            
            # 获取父子骨骼世界矩阵
            try:
                parent_matrix = cmds.xform(parent_joint, q=True, ws=True, matrix=True)
                end_matrix = cmds.xform(end_joint, q=True, ws=True, matrix=True)
            except:
                continue  # 矩阵获取失败跳过
            
            # 检查各轴向是否一致
            axis_issues = []
            for axis_name, axis in axis_indices.items():
                # 父级轴向向量归一化
                parent_vec = [parent_matrix[axis[0]], parent_matrix[axis[1]], parent_matrix[axis[2]]]
                parent_len = math.sqrt(sum(v**2 for v in parent_vec))
                if parent_len < 0.0001:
                    continue
                parent_norm = [v / parent_len for v in parent_vec]
                
                # 末端骨骼轴向向量归一化
                end_vec = [end_matrix[axis[0]], end_matrix[axis[1]], end_matrix[axis[2]]]
                end_len = math.sqrt(sum(v**2 for v in end_vec))
                if end_len < 0.0001:
                    continue
                end_norm = [v / end_len for v in end_vec]
                
                # 计算夹角
                dot = sum(a*b for a, b in zip(parent_norm, end_norm))
                dot = max(min(dot, 1.0), -1.0)  # 修正数值误差
                angle = math.acos(dot)
                angle_degrees = math.degrees(angle)
                
                if angle > rad_threshold:
                    axis_issues.append(f"{axis_name.upper()}轴偏差: {angle_degrees:.2f}度")
            
            if axis_issues:
                # 获取节点的UUID
                try:
                    # 使用Maya API获取UUID
                    import maya.api.OpenMaya as om
                    sel = om.MSelectionList()
                    sel.add(end_joint)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 存储问题信息
                    short_name = cmds.ls(end_joint, shortNames=True)[0]
                    parent_short_name = cmds.ls(parent_joint, shortNames=True)[0]
                    
                    inconsistent_joints[uuid] = [
                        f"末端骨骼: {short_name}"
                    ]
                except Exception as e:
                    # 如果无法获取UUID，使用节点名称作为键
                    short_name = cmds.ls(end_joint, shortNames=True)[0]
                    inconsistent_joints[short_name] = [
                        f"末端骨骼: {short_name}",
                        f"父级骨骼: {cmds.ls(parent_joint, shortNames=True)[0]}",
                        f"问题: {', '.join(axis_issues)}",
                        f"错误: 无法获取UUID - {str(e)}"
                    ]
        
        return inconsistent_joints

    # 执行检查
    results = check_end_joint_axis_alignment()
    
    # 返回结果
    return "joint_end_alignment", results

def check_joint_symmetry_x_axis(nodes, params=None):
    """
    检查场景中所有遵循左侧骨骼后缀名参数和右侧骨骼后缀名参数命名约定的骨骼是否沿X轴对称。
    仅返回存在不对称或未找到对应骨骼的问题骨骼信息，所有对称且无缺失时返回空结果。
    
    参数:
        nodes: 要检查的节点UUID列表
        params: 包含左右后缀名参数的字典，如 {'left_suffix': '_L_Jnt', 'right_suffix': '_R_Jnt'}
        tolerance (float): 允许的数值误差容差，默认为0.001
        
    返回:
        元组: (结果类型字符串, 包含问题骨骼信息的字典) 若无误则第二个元素为空字典
    """
    tolerance = 0.001  # 默认容差值
    
    # 从参数获取左右后缀名，如果没有则使用默认值
    if params and isinstance(params, dict):
        left_suffix = params.get('left_suffix', '_L_Jnt')
        right_suffix = params.get('right_suffix', '_R_Jnt')
    else:
        left_suffix = '_L_Jnt'
        right_suffix = '_R_Jnt'
    
    results = {}
    problem_joints = {}  # 存储有问题的骨骼信息
    
    # 从传入的节点UUID列表中获取所有关节
    all_joints = []
    for node in nodes:
        node_name = _getNodeName(node)
        if node_name and cmds.objExists(node_name) and cmds.objectType(node_name) == 'joint':
            all_joints.append((node, node_name))  # 存储(UUID, 名称)对
    
    # 找出所有左侧和右侧的骨骼
    left_joints = [(uuid, name) for uuid, name in all_joints if name.endswith(left_suffix)]
    right_joints = [(uuid, name) for uuid, name in all_joints if name.endswith(right_suffix)]
    
    # 创建右侧关节名称到UUID的映射
    right_joint_map = {name: uuid for uuid, name in right_joints}
    
    for l_uuid, l_joint in left_joints:
        # 找到对应的右侧骨骼名称
        r_joint = l_joint.replace(left_suffix, right_suffix)
        
        if r_joint not in right_joint_map:
            # 没有找到对应的右侧关节 - 记录问题
            issue_info = [
                f"关节名称: {l_joint}",
                f"问题: 未找到对应右侧关节 {r_joint}"
            ]
            problem_joints[l_uuid] = issue_info
            continue
            
        r_uuid = right_joint_map[r_joint]
        
        # 获取世界空间平移坐标
        try:
            l_pos = cmds.xform(l_joint, query=True, translation=True, worldSpace=True)
            r_pos = cmds.xform(r_joint, query=True, translation=True, worldSpace=True)
            
            # 检查X轴对称: l_pos.x 应该近似于 -r_pos.x, 且 l_pos.y/z 应该近似于 r_pos.y/z
            x_symmetric = abs(l_pos[0] + r_pos[0]) < tolerance
            y_symmetric = abs(l_pos[1] - r_pos[1]) < tolerance
            z_symmetric = abs(l_pos[2] - r_pos[2]) < tolerance
            is_symmetric = x_symmetric and y_symmetric and z_symmetric
            
            if not is_symmetric:
                # 不对称 - 记录问题
                asymmetry_details = []
                if not x_symmetric:
                    asymmetry_details.append(f"X轴: 左侧{l_pos[0]:.3f} vs 预期{-r_pos[0]:.3f} (差异{abs(l_pos[0] + r_pos[0]):.3f})")
                if not y_symmetric:
                    asymmetry_details.append(f"Y轴: 左侧{l_pos[1]:.3f} vs 右侧{r_pos[1]:.3f} (差异{abs(l_pos[1] - r_pos[1]):.3f})")
                if not z_symmetric:
                    asymmetry_details.append(f"Z轴: 左侧{l_pos[2]:.3f} vs 右侧{r_pos[2]:.3f} (差异{abs(l_pos[2] - r_pos[2]):.3f})")
                
                # 左侧关节问题信息
                l_issue = [
                    f"关节名称: {l_joint}",
                    f"对应右侧关节: {r_joint}",
                    f"问题: 沿X轴不对称",
                    f"详细差异: {'; '.join(asymmetry_details)}"
                ]
                problem_joints[l_uuid] = l_issue
                
                # 右侧关节问题信息
                r_issue = [
                    f"关节名称: {r_joint}",
                    f"对应左侧关节: {l_joint}",
                    f"问题: 沿X轴不对称",
                    f"详细差异: {'; '.join(asymmetry_details)}"
                ]
                problem_joints[r_uuid] = r_issue
                
        except Exception as e:
            # 检查过程出错 - 记录问题
            error_msg = f"检查时出错: {str(e)}"
            problem_joints[l_uuid] = [f"关节名称: {l_joint}", error_msg]
            if r_joint in right_joint_map:
                problem_joints[r_uuid] = [f"关节名称: {r_joint}", error_msg]
    
    # 只返回存在问题的结果，无问题则返回空字典
    return "joint_symmetry", problem_joints if problem_joints else {}

def check_joint_limit(nodes, params=None):
    """
    检查场景中骨骼的数量是否超过限制
    
    参数:
        nodes: 要检查的节点UUID列表
        params: 包含限制参数的字典，如 {'limit': 35}
        
    返回:
        元组: (结果类型字符串, 包含关节限制检查结果的字典)
    """
    # 从参数获取限制值，如果没有则使用默认值35
    limit = params.get('limit', 35) if params and isinstance(params, dict) else 35
    
    results = {}
    
    # 从传入的节点UUID列表中筛选出关节
    joint_count = 0
    joint_nodes = []
    
    for node in nodes:
        node_name = _getNodeName(node)
        if node_name and cmds.objExists(node_name) and cmds.objectType(node_name) == 'joint':
            joint_count += 1
            joint_nodes.append((node, node_name))
    
    # 检查关节数量是否超过限制
    exceeds_limit = joint_count > limit
    
    # 只有当关节数量超过限制时，才在结果中添加错误信息
    if exceeds_limit:
        # 为每个关节节点添加限制检查结果
        for node, node_name in joint_nodes:
            if node not in results:
                results[node] = []
            
            results[node].append(f"joint_count:{joint_count}")

    return "joint_limit", results

def check_missing_weights(nodes, _):
    """
    检查已有绑定信息的模型和骨骼上的权重是否丢失
    
    参数:
        nodes: 要检查的节点UUID列表
        _: 忽略的参数
        
    返回:
        元组: (结果类型字符串, 包含权重检查结果的字典)
    """
    models_with_missing_weights = 0  # 记录有权重丢失的模型数量
    total_vertices_checked = 0
    total_missing_weights = 0
    
    # 获取场景中所有的skinCluster节点
    skin_clusters = cmds.ls(type='skinCluster')
    
    if not skin_clusters:
        # 没有skinCluster节点，直接返回空结果
        return "skin_weights", {}, 0
    
    # 处理每个skinCluster
    for skin_cluster in skin_clusters:
        # 获取skinCluster影响的几何体
        geometries = cmds.skinCluster(skin_cluster, query=True, geometry=True)
        
        if not geometries:
            continue
            
        for geometry in geometries:
            # 获取几何体的变换节点（通常是我们关心的节点）
            transform_node = cmds.listRelatives(geometry, parent=True, fullPath=True)
            if not transform_node:
                continue
                
            transform_node = transform_node[0]
            
            # 检查这个变换节点是否在我们要检查的节点列表中
            transform_uuid = None
            for node in nodes:
                node_name = _getNodeName(node)
                if node_name == transform_node:
                    transform_uuid = node
                    break
                    
            if not transform_uuid:
                continue  # 不在检查列表中，跳过
            
            # 获取几何体的顶点数量
            try:
                vertex_count = cmds.polyEvaluate(geometry, vertex=True)
            except:
                # 遇到错误，增加问题计数
                models_with_missing_weights += 1
                continue
            
            geometry_missing_count = 0
            
            # 检查每个顶点是否有权重
            for vertex_index in range(vertex_count):
                vertex_name = "{}.vtx[{}]".format(geometry, vertex_index)
                
                # 获取该顶点的权重值
                try:
                    weights = cmds.skinPercent(skin_cluster, vertex_name, query=True, value=True)
                    
                    # 计算权重总和
                    weight_sum = sum(weights)
                    
                    # 如果权重总和为0或接近0，表示权重丢失
                    if weight_sum < 0.001:
                        geometry_missing_count += 1
                        total_missing_weights += 1
                            
                except Exception as e:
                    # 遇到错误，增加问题计数
                    models_with_missing_weights += 1
                    break  # 跳出当前几何体的顶点循环
                
                total_vertices_checked += 1
            
            # 如果该几何体有权重丢失，增加问题计数
            if geometry_missing_count > 0:
                models_with_missing_weights += 1
    
    # 构建返回结果
    if models_with_missing_weights == 0:
        # 没有发现问题，返回空字典
        return "skin_weights", {}, 0
    else:
        # 发现问题，返回包含统计信息的结果
        return "skin_weights", {
            "issue_count": models_with_missing_weights,
            "global_stats": [
                f"total_vertices_checked:{total_vertices_checked}",
                f"total_missing_weights:{total_missing_weights}", 
                f"skin_clusters_count:{len(skin_clusters)}",
                f"models_with_missing_weights:{models_with_missing_weights}"
            ]
        }, models_with_missing_weights

def check_weight_symmetry(nodes, _):
    """
    检查已有绑定信息的模型和骨骼上的权重是否对称
    
    参数:
    nodes: 要检查的节点列表
    _: 包含对称轴信息的字典，如 {'axis': 'X'}
    
    返回:
    元组，包含检查类型和结果字典
    """
    def is_mesh_symmetric(mesh_name, axis='X'):
        """
        粗略检查网格是否对称（关于指定轴对称）
        
        参数:
        mesh_name: 网格名称
        axis: 对称轴，可选 'X', 'Y', 'Z'
        
        返回:
        布尔值，表示网格是否可能对称
        """
        # 获取网格的边界框
        bbox = cmds.exactWorldBoundingBox(mesh_name)
        
        # 根据轴计算中心点
        if axis == 'X':
            center = (bbox[0] + bbox[3]) / 2
        elif axis == 'Y':
            center = (bbox[1] + bbox[4]) / 2
        else:  # Z轴
            center = (bbox[2] + bbox[5]) / 2
        
        # 如果网格中心不在0附近，可能不是对称模型
        if abs(center) > 0.1:
            return False
            
        return True

    def find_symmetric_vertex(mesh_name, vertex_index, axis='X'):
        """
        查找给定顶点的对称顶点（关于指定轴对称）
        
        参数:
        mesh_name: 网格名称
        vertex_index: 顶点索引
        axis: 对称轴，可选 'X', 'Y', 'Z'
        
        返回:
        对称顶点的索引，如果找不到返回None
        """
        # 获取顶点位置
        vertex_name = "{}.vtx[{}]".format(mesh_name, vertex_index)
        pos = cmds.pointPosition(vertex_name, world=True)
        
        # 计算对称位置（指定轴坐标取反）
        if axis == 'X':
            symmetric_pos = [-pos[0], pos[1], pos[2]]
        elif axis == 'Y':
            symmetric_pos = [pos[0], -pos[1], pos[2]]
        else:  # Z轴
            symmetric_pos = [pos[0], pos[1], -pos[2]]
        
        # 查找最接近对称位置的顶点
        closest_vertex = None
        min_distance = float('inf')
        
        # 获取所有顶点
        vertex_count = cmds.polyEvaluate(mesh_name, vertex=True)
        
        for i in range(vertex_count):
            if i == vertex_index:
                continue
                
            v_name = "{}.vtx[{}]".format(mesh_name, i)
            v_pos = cmds.pointPosition(v_name, world=True)
            
            # 计算距离
            distance = ((v_pos[0] - symmetric_pos[0])**2 + 
                        (v_pos[1] - symmetric_pos[1])**2 + 
                        (v_pos[2] - symmetric_pos[2])** 2)
            
            if distance < min_distance and distance < 0.1:  # 容差
                min_distance = distance
                closest_vertex = i
        
        return closest_vertex

    def are_weights_symmetric(weights1, weights2, influences, axis='X'):
        """
        比较两组权重是否对称
        
        参数:
        weights1: 第一组权重
        weights2: 第二组权重
        influences: 影响骨骼列表
        axis: 对称轴，可选 'X', 'Y', 'Z'
        
        返回:
        布尔值，表示权重是否对称
        """
        # 如果权重数量不同，肯定不对称
        if len(weights1) != len(weights2):
            return False
            
        # 检查每个骨骼的权重是否对称
        for i, influence in enumerate(influences):
            # 检查骨骼名称是否对称（例如_L和_R结尾）
            if influence.endswith("_L_Jnt"):
                symmetric_influence = influence[:-2] + "_R_Jnt"
                if symmetric_influence in influences:
                    j = influences.index(symmetric_influence)
                    if abs(weights1[i] - weights2[j]) > 0.01:  # 容差
                        return False
            elif influence.endswith("_R_Jnt"):
                symmetric_influence = influence[:-2] + "_L_Jnt"
                if symmetric_influence in influences:
                    j = influences.index(symmetric_influence)
                    if abs(weights1[i] - weights2[j]) > 0.01:  # 容差
                        return False
            elif influence.endswith("_Lf_Jnt"):
                symmetric_influence = influence[:-3] + "_Rt"
                if symmetric_influence in influences:
                    j = influences.index(symmetric_influence)
                    if abs(weights1[i] - weights2[j]) > 0.01:  # 容差
                        return False
            elif influence.endswith("_Rt_Jnt"):
                symmetric_influence = influence[:-3] + "_Lf"
                if symmetric_influence in influences:
                    j = influences.index(symmetric_influence)
                    if abs(weights1[i] - weights2[j]) > 0.01:  # 容差
                        return False
            else:
                # 对于非对称命名的骨骼，权重应该相同
                if abs(weights1[i] - weights2[i]) > 0.01:  # 容差
                    return False
                    
        return True

    # 主检查函数
    def perform_check(axis='X'):
        """
        检查已有绑定信息的模型和骨骼上的权重是否对称
        
        参数:
        axis: 对称轴，可选 'X', 'Y', 'Z'，默认为 'X'
        
        返回:
        检查结果的详细报告
        """
        # 验证轴参数
        axis = axis.upper()
        if axis not in ['X', 'Y', 'Z']:
            print("错误: 轴参数必须是 'X', 'Y' 或 'Z'")
            return None
        
        print("=" * 80)
        print("开始检查权重对称性 (对称轴: {})".format(axis))
        print("=" * 80)
        
        # 获取场景中所有的skinCluster节点
        skin_clusters = cmds.ls(type='skinCluster')
        
        if not skin_clusters:
            print("场景中没有找到skinCluster节点，无需检查权重对称性")
            return {"axis": axis, "total_pairs": 0, "asymmetric_pairs": 0, "details": []}
        
        # 存储权重不对称的信息
        asymmetric_weights_info = []
        total_vertices_checked = 0
        total_asymmetric_weights = 0
        
        for skin_cluster in skin_clusters:
            print("检查skinCluster: {}".format(skin_cluster))
            
            # 获取skinCluster影响的几何体
            geometries = cmds.skinCluster(skin_cluster, query=True, geometry=True)
            
            if not geometries:
                print("  - 没有找到受影响的几何体")
                continue
                
            for geometry in geometries:
                print("  - 检查几何体: {}".format(geometry))
                
                # 检查几何体是否对称
                if not is_mesh_symmetric(geometry, axis):
                    print("    ! 几何体可能不对称，跳过对称性检查")
                    continue
                    
                # 获取几何体的顶点数量
                try:
                    vertex_count = cmds.polyEvaluate(geometry, vertex=True)
                except:
                    print("    ! 无法获取顶点数量，跳过此几何体")
                    continue
                    
                geometry_asymmetric_count = 0
                
                # 获取所有影响骨骼
                influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
                
                # 检查每个顶点与其对称顶点的权重是否一致
                for vertex_index in range(vertex_count):
                    vertex_name = "{}.vtx[{}]".format(geometry, vertex_index)
                    
                    # 查找对称顶点
                    symmetric_vertex_index = find_symmetric_vertex(geometry, vertex_index, axis)
                    if symmetric_vertex_index is None:
                        continue
                        
                    symmetric_vertex_name = "{}.vtx[{}]".format(geometry, symmetric_vertex_index)
                    
                    # 获取两个顶点的权重
                    try:
                        weights = cmds.skinPercent(skin_cluster, vertex_name, query=True, value=True)
                        symmetric_weights = cmds.skinPercent(skin_cluster, symmetric_vertex_name, query=True, value=True)
                        
                        # 比较权重是否对称
                        if not are_weights_symmetric(weights, symmetric_weights, influences, axis):
                            asymmetric_weights_info.append("顶点 {} 和 {} 权重不对称".format(vertex_name, symmetric_vertex_name))
                            geometry_asymmetric_count += 1
                            total_asymmetric_weights += 1
                            
                    except Exception as e:
                        print("    ! 检查顶点 {} 时出错: {}".format(vertex_name, str(e)))
                    
                    total_vertices_checked += 1
                    
                if geometry_asymmetric_count > 0:
                    print("    ! 发现 {} 对顶点权重不对称".format(geometry_asymmetric_count))
                else:
                    print("    [OK] 所有顶点权重对称")
        
        # 打印检查结果总结
        print("=" * 80)
        print("权重对称性检查完成总结 (对称轴: {}):".format(axis))
        print("=" * 80)
        print("  总共检查了 {} 对顶点".format(total_vertices_checked))
        print("  发现 {} 对顶点权重不对称".format(total_asymmetric_weights))
        
        if asymmetric_weights_info:
            print("\n权重不对称的顶点详情:")
            for i, info in enumerate(asymmetric_weights_info[:20]):  # 只显示前20个错误
                print("  {}. {}".format(i+1, info))
            
            if len(asymmetric_weights_info) > 20:
                print("  ... 还有 {} 个错误未显示".format(len(asymmetric_weights_info) - 20))
        else:
            print("\n[OK] 所有顶点权重对称，未发现不对称情况")
        
        print("=" * 80)
        
        return {
            "axis": axis,
            "total_pairs": total_vertices_checked,
            "asymmetric_pairs": total_asymmetric_weights,
            "details": asymmetric_weights_info
        }

    # 执行检查
    # 从参数获取对称轴，默认为X轴
    axis = _.get('axis', 'X') if _ and isinstance(_, dict) else 'X'
    summary = perform_check(axis)

    result_dict = {
        'summary': summary,
        'details': summary['details']  # 存储详细信息
    }
    
    return "weight_symmetry", result_dict

def check_frame_rate(nodes, params=None):
    """检查动画帧率设置是否符合目标设置"""
    
    # 初始化结果字典
    result = {}
    
    # 从参数获取目标帧率，如果没有则默认30 FPS
    target_fps = params.get('fps', 30) if params and isinstance(params, dict) else 30
    
    # 映射时间单位到帧率
    time_unit_to_fps = {
        'game': 15,
        'film': 24,
        'pal': 25,
        'ntsc': 30,
        'show': 48,
        'palf': 50,
        'ntscf': 60,
        'millisecond': 1000,
        'second': 1,
        'minute': 1/60,
        'hour': 1/3600
    }
    
    try:
        # 获取当前帧率设置
        current_time_unit = cmds.currentUnit(query=True, time=True)
        
        # 获取当前帧率
        current_fps = time_unit_to_fps.get(current_time_unit, 0)
        
        # 检查是否为目标帧率
        if abs(current_fps - target_fps) < 0.1:  # 容差
            # 帧率正确，不记录错误
            pass
        else:
            # 帧率不正确，记录错误信息
            try:
                # 尝试获取默认渲染设置节点的UUID作为键
                sel = om.MSelectionList()
                sel.add("defaultRenderGlobals")
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录错误信息
                result[uuid] = [f"当前帧率是 {current_fps} FPS ({current_time_unit}) 而不是 {target_fps} FPS"]
            except:
                # 如果无法获取UUID，使用固定字符串作为键
                result["timeUnit_settings"] = [f"当前帧率是 {current_fps} FPS ({current_time_unit}) 而不是 {target_fps} FPS"]
                
    except Exception as e:
        # 捕获检查过程中的异常
        result["frame_rate_check_error"] = [f"检查帧率时出错: {str(e)}"]
    
    return "frame_rate", result

def check_timeline_range(nodes, params=None):
    """检查时间轴范围是否符合规范"""
    
    # 初始化结果字典
    result = {}
    
    # 从参数获取目标范围，如果没有则使用默认值
    if params and isinstance(params, dict):
        target_start_frame = params.get('start_frame', 0)
        target_end_frame = params.get('end_frame', 150)
    else:
        target_start_frame = 0
        target_end_frame = 150
    
    try:
        # 获取当前时间轴设置
        current_start_time = cmds.playbackOptions(query=True, minTime=True)
        current_end_time = cmds.playbackOptions(query=True, maxTime=True)
        current_animation_start = cmds.playbackOptions(query=True, animationStartTime=True)
        current_animation_end = cmds.playbackOptions(query=True, animationEndTime=True)
        
        # 检查所有时间轴设置是否符合规范
        errors = []
        
        if current_start_time != target_start_frame:
            errors.append(f"播放开始时间应为 {target_start_frame} 帧，当前为 {current_start_time} 帧")
        
        if current_end_time != target_end_frame:
            errors.append(f"播放结束时间应为 {target_end_frame} 帧，当前为 {current_end_time} 帧")
        
        if current_animation_start != target_start_frame:
            errors.append(f"动画开始时间应为 {target_start_frame} 帧，当前为 {current_animation_start} 帧")
        
        if current_animation_end != target_end_frame:
            errors.append(f"动画结束时间应为 {target_end_frame} 帧，当前为 {current_animation_end} 帧")
        
        # 如果有错误，记录到结果中；如果没有错误，返回空字典
        if errors:
            try:
                # 尝试获取默认渲染设置节点的UUID作为键
                sel = om.MSelectionList()
                sel.add("defaultRenderGlobals")
                dag = sel.getDagPath(0)
                fn = om.MFnDependencyNode(dag.node())
                uuid = fn.uuid().asString()
                
                # 记录错误信息
                result[uuid] = errors
            except:
                # 如果无法获取UUID，使用固定字符串作为键
                result["timeline_settings"] = errors
        # 如果没有错误，result保持为空字典
                
    except Exception as e:
        # 捕获检查过程中的异常
        result["timeline_check_error"] = [f"检查时间轴范围时出错: {str(e)}"]
    
    return "timeline_range", result

def check_joint_keyframes_in_range(nodes, params=None):
    """检查所有物体上的关键帧是否在时间轴设置范围内"""
    
    # 初始化结果字典
    result = {}
    
    # 从参数获取目标范围，如果没有则使用默认值
    if params and isinstance(params, dict):
        start_frame = params.get('start_frame', 0)
        end_frame = params.get('end_frame', 150)
    else:
        start_frame = 0
        end_frame = 150
    
    try:
        # 获取场景中所有动画曲线（不限于骨骼）
        anim_curves = cmds.ls(type='animCurve')
        
        if not anim_curves:
            # 没有动画曲线，返回空结果
            return "joint_keyframes_in_range", result
        
        # 检查每个动画曲线的关键帧
        for anim_curve in anim_curves:
            # 获取动画曲线的所有关键帧
            try:
                keyframes = cmds.keyframe(anim_curve, query=True, timeChange=True)
                
                if not keyframes:
                    continue
                
                # 存储该动画曲线超出范围的关键帧信息
                curve_errors = []
                
                for frame in keyframes:
                    # 检查关键帧是否在范围内
                    if frame < start_frame or frame > end_frame:
                        curve_errors.append(f"关键帧在 {frame} 帧")
                
                # 如果该动画曲线有关键帧超出范围，记录到结果中
                if curve_errors:
                    try:
                        # 尝试获取动画曲线节点的UUID作为键
                        sel = om.MSelectionList()
                        sel.add(anim_curve)
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录错误信息
                        result[uuid] = curve_errors
                    except:
                        # 如果无法获取UUID，使用动画曲线名称作为键
                        result[anim_curve] = curve_errors
                        
            except Exception as e:
                # 记录检查动画曲线时的错误
                try:
                    # 尝试获取动画曲线节点的UUID作为键
                    sel = om.MSelectionList()
                    sel.add(anim_curve)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录错误信息
                    result[uuid] = [f"检查动画曲线时出错: {str(e)}"]
                except:
                    # 如果无法获取UUID，使用动画曲线名称作为键
                    result[anim_curve] = [f"检查动画曲线时出错: {str(e)}"]
                
    except Exception as e:
        # 捕获检查过程中的异常
        result["keyframe_check_error"] = [f"检查关键帧范围时出错: {str(e)}"]
    
    return "joint_keyframes_in_range", result

def check_missing_references(nodes, _):
    """检查场景中的动画文件引用路径是否丢失"""
    
    # 初始化结果字典
    result = {}
    
    try:
        # 获取场景中的所有引用
        references = cmds.file(query=True, reference=True)
        
        if not references:
            # 没有引用，返回空结果
            return "missing_references", result
        
        # 检查每个引用
        for ref in references:
            # 获取引用的文件路径
            try:
                ref_path = cmds.referenceQuery(ref, filename=True, withoutCopyNumber=True)
                
                # 检查文件是否存在
                if not os.path.exists(ref_path):
                    # 记录丢失的引用信息
                    try:
                        # 尝试获取引用节点的UUID作为键
                        sel = om.MSelectionList()
                        sel.add(ref)
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录错误信息
                        result[uuid] = [f"引用 '{ref}' 的文件路径不存在: {ref_path}"]
                    except:
                        # 如果无法获取UUID，使用引用名称作为键
                        result[ref] = [f"引用 '{ref}' 的文件路径不存在: {ref_path}"]
                        
            except Exception as e:
                # 记录检查引用时的错误
                try:
                    # 尝试获取引用节点的UUID作为键
                    sel = om.MSelectionList()
                    sel.add(ref)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录错误信息
                    result[uuid] = [f"检查引用 '{ref}' 时出错: {str(e)}"]
                except:
                    # 如果无法获取UUID，使用引用名称作为键
                    result[ref] = [f"检查引用 '{ref}' 时出错: {str(e)}"]
                
    except Exception as e:
        # 捕获检查过程中的异常
        result["reference_check_error"] = [f"检查引用路径时出错: {str(e)}"]
    
    return "missing_references", result

def check_integer_keyframes(nodes, _):
    """检查场景中的关键帧是否都在整数帧上"""
    
    # 初始化结果字典
    result = {}
    
    try:
        # 获取所有动画曲线
        anim_curves = cmds.ls(type='animCurve')
        
        if not anim_curves:
            # 没有动画曲线，返回空结果
            return "integer_keyframes", result
        
        # 检查每个动画曲线
        for anim_curve in anim_curves:
            # 获取动画曲线的所有关键帧时间
            try:
                key_times = cmds.keyframe(anim_curve, query=True, timeChange=True)
                
                if not key_times:
                    continue
                
                # 检查每个关键帧时间是否为整数
                non_integer_frames = []
                for time in key_times:
                    # 检查是否为整数（允许一定的浮点误差）
                    if abs(time - round(time)) > 0.001:
                        non_integer_frames.append(time)
                
                # 如果有关键帧不是整数帧，记录错误信息
                if non_integer_frames:
                    try:
                        # 尝试获取动画曲线节点的UUID作为键
                        sel = om.MSelectionList()
                        sel.add(anim_curve)
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录错误信息
                        result[uuid] = [f"动画曲线 '{anim_curve}' 有 {len(non_integer_frames)} 个非整数关键帧: {non_integer_frames}"]
                    except:
                        # 如果无法获取UUID，使用动画曲线名称作为键
                        result[anim_curve] = [f"动画曲线 '{anim_curve}' 有 {len(non_integer_frames)} 个非整数关键帧: {non_integer_frames}"]
                        
            except Exception as e:
                # 记录检查动画曲线时的错误
                try:
                    # 尝试获取动画曲线节点的UUID作为键
                    sel = om.MSelectionList()
                    sel.add(anim_curve)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录错误信息
                    result[uuid] = [f"检查动画曲线 '{anim_curve}' 时出错: {str(e)}"]
                except:
                    # 如果无法获取UUID，使用动画曲线名称作为键
                    result[anim_curve] = [f"检查动画曲线 '{anim_curve}' 时出错: {str(e)}"]
                
    except Exception as e:
        # 捕获检查过程中的异常
        result["integer_keyframe_check_error"] = [f"检查整数关键帧时出错: {str(e)}"]
    
    return "integer_keyframes", result

# 主UI类
class ModelCheckerUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ModelCheckerUI, self).__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("Maya检查工具[V.1.03]")
        self.setMinimumSize(1250, 700)  # 增加整体宽度以适应左侧UI的扩展
        
        # 设置窗口标志，参考Maya窗口设计
        self.setWindowFlags(QtCore.Qt.Window | 
                        QtCore.Qt.WindowMinimizeButtonHint | 
                        QtCore.Qt.WindowMaximizeButtonHint | 
                        QtCore.Qt.WindowCloseButtonHint)

        # 添加置顶标志
        self.always_on_top = False
        
        # 项目数据存储
        self.project_data = {}  # 存储项目配置 {项目名: {检查项配置}}

        # 呼吸灯效果相关属性
        self.breathing_active = False
        self.breathing_timer = QtCore.QTimer()
        self.breathing_phase = 0  # 呼吸相位
        self.breathing_speed = 0.05  # 呼吸速度
        self.original_styles = {}  # 保存原始样式
        self.breathing_buttons = []    # 存储所有需要应用效果的按钮

        # 按照分组顺序定义检查功能
        self.check_functions = {
            # 场景大纲组
            "显示层": layers,
            "空层": emptyLayers,
            "着色器": shaders,
            "构造历史": history,
            "未冻结变换": unfrozenTransforms,
            "未居中轴点": uncenteredPivots,
            "空组": emptyGroups,
            "父级几何体": parentGeometry,
            "尾部数字": trailingNumbers,
            "重复名称": duplicatedNames,
            "命名空间": namespaces,
            "形状名称": shapeNames,
            "多余灯光": checkLights,
            "多余摄像机": checkCameras,
            "多余关键帧": checkKeyframes,
            
            # 模型拓补组
            "三角形面": triangles,
            "多边面": ngons,
            "硬边": hardEdges,
            "重叠面": lamina,
            "零面积面": zeroAreaFaces,
            "零长度边": zeroLengthEdges,
            "非流形边": noneManifoldEdges,
            "开放边": openEdges,
            "极点": poles,
            "非星形面": starlike,
            "重叠顶点": overlapping_vertices,
            "分离模型": is_selected_model_separated,
            "模型对称": checkModelSymmetry,
            "模型高/低于地面": checkGroundAlignment,
            "模型面数": checkModelFacesNum,
            "模型命名": checkGeometrySuffix,

            # 模型UV组
            "缺少UV": missingUVs,
            "UV范围": uvRange,
            "UV边界": onBorder,
            "跨界UV": crossBorder,
            "非map1 UV集": nonMap1UVSets,
            "自重叠UV": selfPenetratingUVs,
            
            # 材质组
            "材质丢失": checkMissingMaterials,
            "未使用材质": check_material_info,
            "贴图路径丢失": texturePathLost,
            
            # 灯光渲染
            "未创建HDRI": checkSkyDomeLight,
            "渲染层masterLayer": checkRenderLayer,
            "AOV分层": checkAOVs,
            "渲染硬件": checkCPURendering,
            "渲染软件": checkArnoldRenderer,
            
            # 骨骼绑定
            "历史记录检查": checkBoundModelIssues,
            "blendshape": checkBlendShape,
            "骨骼未冻结变换": checkUnboundJointsTransforms,
            "未绑定骨骼": find_redundant_joints,
            "重叠骨骼": checkOverlappingJoints,
            "骨骼命名": checkJointSuffix,
            "骨骼旋转方向": check_joint_alignment_XYZ,
            "父骨未朝子": check_joint_parent_child,
            "末端骨骼轴向不一致": check_end_joint_alignment,
            "镜像骨骼": check_joint_symmetry_x_axis,
            "骨骼数量": check_joint_limit,
            "权重丢失": check_missing_weights,
            "镜像权重": check_weight_symmetry,

            # 动画
            "帧率设置": check_frame_rate,
            "时间轴设置": check_timeline_range,
            "关键帧动画范围": check_joint_keyframes_in_range,
            "文件引用丢失": check_missing_references,
            "关键帧不在整数帧上": check_integer_keyframes

        }
        
        self.results = {}
        self.create_ui()
        
    def create_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # === 新增：顶部隐藏式按钮（修改后） ===
        top_layout = QtWidgets.QHBoxLayout()
        self.old_he_btn = QtWidgets.QPushButton("==================================================== Old_He荣誉出品 ====================================================")
        # 设置样式：居中显示、增大文字、无下划线
        self.old_he_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #666666;
                font-size: 14px;  /* 增大文字大小 */
                padding: 1px;
            }
            QPushButton:hover {
                color: #000000;  /* 取消下划线效果 */
            }
        """)
        # 按钮居中对齐（通过两侧添加拉伸实现）
        top_layout.addStretch()
        top_layout.addWidget(self.old_he_btn)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # 连接呼吸灯效果
        self.old_he_btn.clicked.connect(self.toggle_breathing_effect)

        # 主内容布局
        content_layout = QtWidgets.QHBoxLayout()
        
        # 左侧按钮区域
        left_widget = QtWidgets.QWidget()
        # 设置左侧整体区域的大小策略，使其在水平方向可以拉伸
        left_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setAlignment(QtCore.Qt.AlignTop)

        # 工具管理UI
        project_group = QtWidgets.QGroupBox("工具管理")
        project_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        project_layout = QtWidgets.QVBoxLayout(project_group)

        # 添加工具说明按钮
        self.tool_info_btn = QtWidgets.QPushButton("工具说明")
        self.tool_info_btn.clicked.connect(self.show_tool_info)
        project_layout.addWidget(self.tool_info_btn)

        # 项目按钮
        self.project_btn = QtWidgets.QPushButton("项目管理")
        self.project_btn.setCheckable(True)
        self.project_btn.clicked.connect(self.toggle_project_panel)
        project_layout.addWidget(self.project_btn)
        
        # 项目面板（初始隐藏）
        self.project_panel = QtWidgets.QWidget()
        self.project_panel.setVisible(False)
        project_panel_layout = QtWidgets.QVBoxLayout(self.project_panel)
        
        # 创建5个项目文本框
        self.project_inputs = []
        self.project_combos = []
        
        for i in range(5):
            # 每个项目的水平布局
            project_row_layout = QtWidgets.QHBoxLayout()
            
            # 项目名称输入框
            project_input = QtWidgets.QLineEdit()
            project_input.setPlaceholderText(f"项目{i+1}名称")
            project_input.textChanged.connect(lambda text, idx=i: self.on_project_name_changed(idx, text))
            
            # 操作下拉框
            project_combo = QtWidgets.QComboBox()
            project_combo.addItems(["保存信息", "清除数据", "准备检查"])
            project_combo.currentIndexChanged.connect(lambda index, idx=i: self.on_project_action_selected(idx, index))
            project_combo.setEnabled(False)  # 初始禁用，直到输入项目名
            
            project_row_layout.addWidget(project_input, 1)
            project_row_layout.addWidget(project_combo)
            
            project_panel_layout.addLayout(project_row_layout)
            
            self.project_inputs.append(project_input)
            self.project_combos.append(project_combo)
        
        project_layout.addWidget(self.project_panel)

        left_layout.addWidget(project_group)

        # === 新增：文档保存地址UI ===
        doc_save_group = QtWidgets.QGroupBox("文档保存")
        doc_save_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        doc_save_layout = QtWidgets.QHBoxLayout(doc_save_group)
        
        # 文档地址标签
        doc_label = QtWidgets.QLabel("文档保存地址:")
        doc_save_layout.addWidget(doc_label)
        
        # 文档地址输入框
        self.doc_path_input = QtWidgets.QLineEdit()
        self.doc_path_input.setPlaceholderText("请输入或选择保存路径...")
        doc_save_layout.addWidget(self.doc_path_input, 1)  # 添加拉伸因子1，使其可以拉伸
        
        # 浏览按钮
        self.browse_btn = QtWidgets.QPushButton("浏览")
        self.browse_btn.setFixedSize(60, 25)  # 固定按钮大小
        self.browse_btn.clicked.connect(self.browse_save_path)
        doc_save_layout.addWidget(self.browse_btn)
        
        # 保存按钮
        self.save_btn = QtWidgets.QPushButton("保存")
        self.save_btn.setFixedSize(60, 25)  # 固定按钮大小
        self.save_btn.clicked.connect(self.save_to_markdown)
        doc_save_layout.addWidget(self.save_btn)
        
        left_layout.addWidget(doc_save_group)

        # 选择范围 - 修改这里，将置顶按钮添加到右侧
        scope_group = QtWidgets.QGroupBox("检查范围")
        # 设置大小策略，使组框在垂直方向保持固定大小，水平方向可以拉伸
        scope_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        scope_layout = QtWidgets.QHBoxLayout(scope_group)  # 改为水平布局

        # 左侧的检查范围选项
        scope_left_layout = QtWidgets.QVBoxLayout()
        self.scope_selection = QtWidgets.QRadioButton("选择对象")
        self.scope_all = QtWidgets.QRadioButton("全部对象")
        self.scope_all.setChecked(True)
        scope_left_layout.addWidget(self.scope_selection)
        scope_left_layout.addWidget(self.scope_all)

        # 右侧的置顶按钮
        scope_right_layout = QtWidgets.QVBoxLayout()
        scope_right_layout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)

        # 置顶按钮
        self.pin_btn = QtWidgets.QPushButton("置顶")
        self.pin_btn.setFixedSize(60, 25)
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self.toggle_always_on_top)

        scope_right_layout.addWidget(self.pin_btn)
        scope_right_layout.addStretch()

        # 将左右两侧布局添加到主布局
        scope_layout.addLayout(scope_left_layout)
        scope_layout.addLayout(scope_right_layout)

        left_layout.addWidget(scope_group)

        # 检查选项 - 使用滚动区域
        options_scroll = QtWidgets.QScrollArea()
        options_scroll.setWidgetResizable(True)
        # 移除最大宽度限制，让滚动区域可以随父容器拉伸
        # options_scroll.setMaximumWidth(550)  # 注释掉这行
        options_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        options_widget = QtWidgets.QWidget()
        # 设置选项widget的大小策略，使其在水平方向可以拉伸
        options_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        options_layout = QtWidgets.QVBoxLayout(options_widget)
        
        # 全选/全不选按钮
        select_buttons_layout = QtWidgets.QHBoxLayout()
        self.select_all_btn = QtWidgets.QPushButton("全选")
        self.select_blue_btn = QtWidgets.QPushButton("全选处理")  # 新增按钮
        self.select_none_btn = QtWidgets.QPushButton("全不选")
        select_buttons_layout.addWidget(self.select_all_btn)
        select_buttons_layout.addWidget(self.select_blue_btn)    # 新增按钮
        select_buttons_layout.addWidget(self.select_none_btn)
        left_layout.addLayout(select_buttons_layout)

        # 初始化检查框字典
        self.check_boxes = {}
        
        # 定义颜色分类
        blue_checks = {
            "空层", "着色器", "构造历史", "未冻结变换", "未居中轴点", "空组", "父级几何体", 
            "尾部数字", "重复名称", "命名空间", "形状名称", "多余灯光", "多余摄像机", "多余关键帧",
            "三角形面", "多边面", "硬边", "重叠面", "零面积面", "零长度边", "非流形边", 
            "非星形面", "重叠顶点", "分离模型", "模型高/低于地面", "非map1 UV集", "材质丢失", "未使用材质",
            "未创建HDRI" , "骨骼未冻结变换", "未绑定骨骼", "重叠骨骼", "骨骼命名", "骨骼旋转方向",
            "帧率设置", "时间轴设置", "父骨未朝子", "末端骨骼轴向不一致"
        }
        
        yellow_checks = {"开放边", "极点"}
        
        # 添加分组标题和检查选项
        # 场景大纲组
        scene_label = QtWidgets.QLabel("场景大纲")
        scene_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(scene_label)
        for check_name in ["显示层", "空层", "着色器", "构造历史", "未冻结变换", "未居中轴点", "空组", "父级几何体", 
                          "尾部数字", "重复名称", "命名空间", "形状名称", "多余灯光", "多余摄像机", "多余关键帧"]:
            if check_name in self.check_functions:
                check_box = QtWidgets.QCheckBox(check_name)
                check_box.setChecked(True)
                
                # 设置背景颜色
                if check_name in blue_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                elif check_name in yellow_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                else:
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                
                self.check_boxes[check_name] = check_box
                options_layout.addWidget(check_box)
        
        # 模型拓补组
        topology_label = QtWidgets.QLabel("模型拓补")
        topology_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(topology_label)
        for check_name in ["三角形面", "多边面", "硬边", "重叠面", "零面积面", "零长度边", 
                          "非流形边", "开放边", "极点", "非星形面", "重叠顶点", "分离模型", 
                          "模型对称", "模型高/低于地面", "模型面数", "模型命名"]:
            if check_name in self.check_functions:
                # 特殊处理需要添加额外控件的检查项
                if check_name == "重叠顶点":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加容差标签和输入框
                    tolerance_label = QtWidgets.QLabel("容差：")
                    tolerance_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.overlap_vertex_tolerance = QtWidgets.QLineEdit("0.001")
                    self.overlap_vertex_tolerance.setValidator(QtGui.QDoubleValidator())
                    self.overlap_vertex_tolerance.setFixedWidth(70)  # 增加宽度
                    self.overlap_vertex_tolerance.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.overlap_vertex_tolerance.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(tolerance_label)
                    row_layout.addWidget(self.overlap_vertex_tolerance)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                elif check_name == "模型高/低于地面":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加容差标签和输入框
                    tolerance_label = QtWidgets.QLabel("容差：")
                    tolerance_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.ground_tolerance = QtWidgets.QLineEdit("0.001")
                    self.ground_tolerance.setValidator(QtGui.QDoubleValidator())
                    self.ground_tolerance.setFixedWidth(70)  # 增加宽度
                    self.ground_tolerance.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.ground_tolerance.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(tolerance_label)
                    row_layout.addWidget(self.ground_tolerance)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                elif check_name == "模型面数":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #e74c3c; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加上限标签和输入框
                    limit_label = QtWidgets.QLabel("上限：")
                    limit_label.setStyleSheet("QLabel { background-color: #e74c3c; color: white; margin-left: 5px; }")
                    
                    self.face_limit_input = QtWidgets.QLineEdit("10000")
                    self.face_limit_input.setValidator(QtGui.QIntValidator())
                    self.face_limit_input.setFixedWidth(70)  # 增加宽度
                    self.face_limit_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.face_limit_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(limit_label)
                    row_layout.addWidget(self.face_limit_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                elif check_name == "模型命名":  # 新增的模型命名检查项
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色为蓝色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加后缀标签和输入框
                    suffix_label = QtWidgets.QLabel("后缀：")
                    suffix_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.geometry_suffix_input = QtWidgets.QLineEdit("_Geo")
                    self.geometry_suffix_input.setFixedWidth(70)  # 增加宽度
                    self.geometry_suffix_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.geometry_suffix_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(suffix_label)
                    row_layout.addWidget(self.geometry_suffix_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                else:
                    # 其他复选框的常规处理
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    
                    # 设置背景颜色
                    if check_name in blue_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    elif check_name in yellow_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                    else:
                        check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    options_layout.addWidget(check_box)
        
        # 模型UV组
        uv_label = QtWidgets.QLabel("模型UV")
        uv_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(uv_label)
        for check_name in ["缺少UV", "UV范围", "UV边界", "跨界UV", "非map1 UV集", "自重叠UV"]:
            if check_name in self.check_functions:
                check_box = QtWidgets.QCheckBox(check_name)
                check_box.setChecked(True)
                
                # 设置背景颜色
                if check_name in blue_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                elif check_name in yellow_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                else:
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                
                self.check_boxes[check_name] = check_box
                options_layout.addWidget(check_box)
        
        # 材质组
        material_label = QtWidgets.QLabel("材质组")
        material_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(material_label)
        for check_name in ["材质丢失", "未使用材质", "贴图路径丢失"]:
            if check_name in self.check_functions:
                check_box = QtWidgets.QCheckBox(check_name)
                check_box.setChecked(True)
                
                # 设置背景颜色
                if check_name in blue_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                elif check_name in yellow_checks:
                    check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                else:
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                
                self.check_boxes[check_name] = check_box
                options_layout.addWidget(check_box)
        
        # 灯光渲染
        lighting_label = QtWidgets.QLabel("灯光渲染")
        lighting_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(lighting_label)
        for check_name in ["未创建HDRI", "渲染层masterLayer", "AOV分层", "渲染硬件", "渲染软件"]:
            if check_name in self.check_functions:
                # 特殊处理需要添加额外控件的检查项
                if check_name == "渲染硬件":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加设备标签和下拉选框
                    device_label = QtWidgets.QLabel("设备：")
                    device_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.gpu_device_combo = QtWidgets.QComboBox()
                    self.gpu_device_combo.addItems(["CPU渲染", "GPU渲染"])
                    self.gpu_device_combo.setCurrentText("CPU渲染")
                    self.gpu_device_combo.setFixedWidth(100)  # 增加宽度
                    self.gpu_device_combo.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(device_label)
                    row_layout.addWidget(self.gpu_device_combo)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                elif check_name == "渲染软件":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加渲染器标签和下拉选框
                    renderer_label = QtWidgets.QLabel("渲染器：")
                    renderer_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.arnold_renderer_combo = QtWidgets.QComboBox()
                    self.arnold_renderer_combo.addItems(["Arnold", "Vray", "Redshift"])
                    self.arnold_renderer_combo.setCurrentText("Arnold")
                    self.arnold_renderer_combo.setFixedWidth(100)  # 增加宽度
                    self.arnold_renderer_combo.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(renderer_label)
                    row_layout.addWidget(self.arnold_renderer_combo)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                else:
                    # 其他复选框的常规处理
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    
                    # 设置背景颜色
                    if check_name in blue_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    elif check_name in yellow_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                    else:
                        check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    options_layout.addWidget(check_box)
        
        # 骨骼绑定
        skeleton_label = QtWidgets.QLabel("骨骼绑定")
        skeleton_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(skeleton_label)
        for check_name in ["历史记录检查", "blendshape", "骨骼未冻结变换", "未绑定骨骼", "重叠骨骼", "骨骼命名", "骨骼旋转方向", "父骨未朝子", "末端骨骼轴向不一致", "镜像骨骼",
                        "骨骼数量", "权重丢失", "镜像权重"]:
            if check_name in self.check_functions:
                # 特殊处理需要添加额外控件的检查项
                if check_name == "骨骼旋转方向":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加轴向选择下拉框
                    axis_label = QtWidgets.QLabel("：")
                    axis_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.orient_axis_combo = QtWidgets.QComboBox()
                    self.orient_axis_combo.addItems(["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"])
                    self.orient_axis_combo.setCurrentIndex(0)  # 默认选中XYZ
                    self.orient_axis_combo.setFixedWidth(60)  # 增加宽度
                    self.orient_axis_combo.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(axis_label)
                    row_layout.addWidget(self.orient_axis_combo)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                # 在骨骼绑定分组中找到"骨骼命名"的代码段，修改如下：
                elif check_name == "骨骼命名":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加后缀标签和输入框
                    suffix_label = QtWidgets.QLabel("后缀：")
                    suffix_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.joint_suffix_input = QtWidgets.QLineEdit("_Jnt")
                    self.joint_suffix_input.setFixedWidth(70)  # 增加宽度
                    self.joint_suffix_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.joint_suffix_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(suffix_label)
                    row_layout.addWidget(self.joint_suffix_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                # 在骨骼绑定分组中找到"镜像骨骼"的代码段，修改如下：
                elif check_name == "镜像骨骼":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #e74c3c; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加左侧骨骼后缀标签和输入框
                    left_label = QtWidgets.QLabel("左：")
                    left_label.setStyleSheet("QLabel { background-color: #e74c3c; color: white; margin-left: 5px; }")
                    
                    self.left_suffix_input = QtWidgets.QLineEdit("_L_Jnt")
                    self.left_suffix_input.setFixedWidth(70)
                    self.left_suffix_input.setAlignment(QtCore.Qt.AlignLeft)
                    self.left_suffix_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    # 添加右侧骨骼后缀标签和输入框
                    right_label = QtWidgets.QLabel("右：")
                    right_label.setStyleSheet("QLabel { background-color: #e74c3c; color: white; margin-left: 5px; }")
                    
                    self.right_suffix_input = QtWidgets.QLineEdit("_R_Jnt")
                    self.right_suffix_input.setFixedWidth(70)
                    self.right_suffix_input.setAlignment(QtCore.Qt.AlignLeft)
                    self.right_suffix_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(left_label)
                    row_layout.addWidget(self.left_suffix_input)
                    row_layout.addWidget(right_label)
                    row_layout.addWidget(self.right_suffix_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)

                elif check_name == "父骨未朝子":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加第一个轴向选择下拉框 (orientJoint)
                    axis_label1 = QtWidgets.QLabel("：")
                    axis_label1.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 1px; }")
                    
                    self.orient_axis_combo1 = QtWidgets.QComboBox()
                    self.orient_axis_combo1.addItems(["xyz", "yzx", "zxy", "zyx", "yxz", "xzy", "none"])
                    self.orient_axis_combo1.setCurrentIndex(0)  # 默认选中xyz
                    self.orient_axis_combo1.setFixedWidth(60)  # 增加宽度
                    self.orient_axis_combo1.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(axis_label1)
                    row_layout.addWidget(self.orient_axis_combo1)
                    
                    # 添加第二个轴向选择下拉框 (secondaryAxisOrient)
                    axis_label2 = QtWidgets.QLabel("：")
                    axis_label2.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 1px; }")
                    
                    self.orient_axis_combo2 = QtWidgets.QComboBox()
                    self.orient_axis_combo2.addItems(["xup", "xdown", "yup", "ydown", "zup", "zdown", "none"])
                    self.orient_axis_combo2.setCurrentIndex(2)  # 默认选中yup
                    self.orient_axis_combo2.setFixedWidth(80)  # 增加宽度
                    self.orient_axis_combo2.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(axis_label2)
                    row_layout.addWidget(self.orient_axis_combo2)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                elif check_name == "骨骼数量":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色 - 修改为红色
                    row_widget.setStyleSheet("QWidget { background-color: #e74c3c; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加上限标签和输入框
                    limit_label = QtWidgets.QLabel("上限：")
                    limit_label.setStyleSheet("QLabel { background-color: #e74c3c; color: white; margin-left: 5px; }")
                    
                    self.joint_limit_input = QtWidgets.QLineEdit("35")
                    self.joint_limit_input.setValidator(QtGui.QIntValidator())
                    self.joint_limit_input.setFixedWidth(70)  # 增加宽度
                    self.joint_limit_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.joint_limit_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(limit_label)
                    row_layout.addWidget(self.joint_limit_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                else:
                    # 其他复选框的常规处理
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    
                    # 设置背景颜色
                    if check_name in blue_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    elif check_name in yellow_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                    else:
                        check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    options_layout.addWidget(check_box)

        # 动画
        animation_label = QtWidgets.QLabel("动画")
        animation_label.setStyleSheet("QLabel { background-color: #181818; padding: 10px; font-weight: bold; font-size: 20px; }")
        options_layout.addWidget(animation_label)
        for check_name in ["帧率设置", "时间轴设置", "关键帧动画范围", "文件引用丢失", "关键帧不在整数帧上"]:
            if check_name in self.check_functions:
                # 特殊处理需要添加额外控件的检查项
                if check_name == "帧率设置":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加帧率标签和下拉框
                    frame_rate_label = QtWidgets.QLabel("帧率：")
                    frame_rate_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.frame_rate_combo = QtWidgets.QComboBox()
                    # 添加帧率选项
                    frame_rate_options = [
                        ('game', 15),
                        ('film', 24), 
                        ('pal', 25),
                        ('ntsc', 30),
                        ('show', 48),
                        ('palf', 50),
                        ('ntscf', 60),
                        ('millisecond', 1000)
                    ]
                    for name, fps in frame_rate_options:
                        self.frame_rate_combo.addItem(f"{name} ({fps} FPS)", fps)
                    
                    # 设置默认选中ntsc (30 FPS)
                    self.frame_rate_combo.setCurrentIndex(3)  # ntsc在索引3
                    self.frame_rate_combo.setFixedWidth(150)  # 增加宽度以显示完整文本
                    self.frame_rate_combo.setStyleSheet("""
                        QComboBox {
                            background-color: white;
                            color: black;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            margin-right: 2px;
                        }
                        QComboBox QAbstractItemView {
                            background-color: white;
                            color: black;
                            border: 1px solid #2c3e50;
                        }
                    """)
                    
                    row_layout.addWidget(frame_rate_label)
                    row_layout.addWidget(self.frame_rate_combo)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                elif check_name == "时间轴设置":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加范围标签和输入框
                    range_label = QtWidgets.QLabel("范围：")
                    range_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.timeline_start_input = QtWidgets.QLineEdit("0")
                    self.timeline_start_input.setValidator(QtGui.QIntValidator())
                    self.timeline_start_input.setFixedWidth(50)  # 增加宽度
                    self.timeline_start_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.timeline_start_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    self.timeline_end_input = QtWidgets.QLineEdit("120")
                    self.timeline_end_input.setValidator(QtGui.QIntValidator())
                    self.timeline_end_input.setFixedWidth(50)  # 增加宽度
                    self.timeline_end_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.timeline_end_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(range_label)
                    row_layout.addWidget(self.timeline_start_input)
                    row_layout.addWidget(QtWidgets.QLabel("-"))  # 分隔符
                    row_layout.addWidget(self.timeline_end_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                elif check_name == "关键帧动画范围":
                    # 创建容器widget，设置整个行的背景色
                    row_widget = QtWidgets.QWidget()
                    row_layout = QtWidgets.QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 5, 0)  # 右侧添加5px边距
                    
                    # 设置整个行的背景颜色
                    row_widget.setStyleSheet("QWidget { background-color: #3498db; }")
                    
                    # 复选框部分
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(False)
                    check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    row_layout.addWidget(check_box)
                    
                    # 添加拉伸因子，将右侧控件推到最右
                    row_layout.addStretch()
                    
                    # 添加范围标签和输入框
                    range_label = QtWidgets.QLabel("范围：")
                    range_label.setStyleSheet("QLabel { background-color: #3498db; color: white; margin-left: 5px; }")
                    
                    self.anim_range_start_input = QtWidgets.QLineEdit("0")
                    self.anim_range_start_input.setValidator(QtGui.QIntValidator())
                    self.anim_range_start_input.setFixedWidth(50)  # 增加宽度
                    self.anim_range_start_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.anim_range_start_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    self.anim_range_end_input = QtWidgets.QLineEdit("120")
                    self.anim_range_end_input.setValidator(QtGui.QIntValidator())
                    self.anim_range_end_input.setFixedWidth(50)  # 增加宽度
                    self.anim_range_end_input.setAlignment(QtCore.Qt.AlignLeft)  # 改为左对齐
                    self.anim_range_end_input.setStyleSheet("QLineEdit { background-color: white; color: black; border: 1px solid #2c3e50; margin-right: 2px; }")
                    
                    row_layout.addWidget(range_label)
                    row_layout.addWidget(self.anim_range_start_input)
                    row_layout.addWidget(QtWidgets.QLabel("-"))  # 分隔符
                    row_layout.addWidget(self.anim_range_end_input)
                    
                    # 将容器widget添加到选项布局
                    options_layout.addWidget(row_widget)
                    
                else:
                    # 其他复选框的常规处理
                    check_box = QtWidgets.QCheckBox(check_name)
                    check_box.setChecked(True)
                    
                    # 设置背景颜色
                    if check_name in blue_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #3498db; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    elif check_name in yellow_checks:
                        check_box.setStyleSheet("QCheckBox { background-color: #f1c40f; color: black; padding: 3px; border: 1px solid #2c3e50; }")
                    else:
                        check_box.setStyleSheet("QCheckBox { background-color: #e74c3c; color: white; padding: 3px; border: 1px solid #2c3e50; }")
                    
                    self.check_boxes[check_name] = check_box
                    options_layout.addWidget(check_box)

        options_layout.addStretch()
        options_scroll.setWidget(options_widget)
        left_layout.addWidget(options_scroll)
        
        # 右侧结果显示区域 - 使用分割器分为上下两部分
        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        
        # 上方结果显示区域
        results_group = QtWidgets.QGroupBox("检查结果")
        results_layout = QtWidgets.QVBoxLayout(results_group)
        self.results_text = QtWidgets.QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        right_splitter.addWidget(results_group)
        
        # 下方处理结果显示区域
        fix_results_group = QtWidgets.QGroupBox("处理结果")
        fix_results_layout = QtWidgets.QVBoxLayout(fix_results_group)
        self.fix_results_text = QtWidgets.QTextEdit()
        self.fix_results_text.setReadOnly(True)
        fix_results_layout.addWidget(self.fix_results_text)
        right_splitter.addWidget(fix_results_group)
        
        # 设置分割器比例
        right_splitter.setSizes([400, 200])
        
        # 底部按钮
        button_layout = QtWidgets.QHBoxLayout()
        self.check_btn = QtWidgets.QPushButton("开始检查")
        self.quick_fix_btn = QtWidgets.QPushButton("一键处理")
        self.select_problem_btn = QtWidgets.QPushButton("选择问题对象")
        self.select_problem_btn.setEnabled(False)
        
        button_layout.addWidget(self.select_problem_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.check_btn)
        button_layout.addWidget(self.quick_fix_btn)

        # 右侧主布局
        right_main_layout = QtWidgets.QVBoxLayout()
        right_main_layout.addWidget(right_splitter, 1)
        right_main_layout.addLayout(button_layout)
        
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_main_layout)
        
        # 添加到内容布局
        content_layout.addWidget(left_widget, 1)
        content_layout.addWidget(right_widget, 2)
        
        # 添加到主布局 - 直接添加内容布局，不再添加顶部按钮布局
        main_layout.addLayout(content_layout)
        
        # 连接信号
        self.check_btn.clicked.connect(self.run_checks)
        self.quick_fix_btn.clicked.connect(self.quick_fix)
        self.select_all_btn.clicked.connect(self.select_all_checks)
        self.select_blue_btn.clicked.connect(self.select_blue_checks)  # 新增连接
        self.select_none_btn.clicked.connect(self.select_none_checks)
        self.select_problem_btn.clicked.connect(self.select_problem_objects)

        # 添加互斥逻辑：连接"多余关键帧"和"关键帧动画范围"的信号
        if "多余关键帧" in self.check_boxes and "关键帧动画范围" in self.check_boxes:
            self.check_boxes["多余关键帧"].stateChanged.connect(self.update_mutually_exclusive_checks)
            self.check_boxes["关键帧动画范围"].stateChanged.connect(self.update_mutually_exclusive_checks)
            
            # 确保初始状态正确 - 添加这行代码
            self.update_mutually_exclusive_checks()

    def select_blue_checks(self):
        """选择所有蓝色背景的检查项，并保持互斥逻辑"""
        # 定义蓝色检查项集合
        blue_checks = {
            "空层", "着色器", "构造历史", "未冻结变换", "未居中轴点", "空组", "父级几何体", 
            "尾部数字", "重复名称", "命名空间", "形状名称", "多余灯光", "多余摄像机", "多余关键帧",
            "三角形面", "多边面", "硬边", "重叠面", "零面积面", "零长度边", "非流形边", 
            "非星形面", "重叠顶点", "分离模型", "模型高/低于地面", "非map1 UV集", "材质丢失", "未使用材质",
            "未创建HDRI" , "骨骼未冻结变换", "未绑定骨骼", "重叠骨骼", "骨骼命名", "骨骼旋转方向",
            "帧率设置", "时间轴设置", "父骨未朝子", "末端骨骼轴向不一致", "渲染硬件", "渲染软件"
        }
        
        # 先全部取消选择
        for check_box in self.check_boxes.values():
            check_box.setChecked(False)
        
        # 选择蓝色检查项
        for check_name, check_box in self.check_boxes.items():
            if check_name in blue_checks:
                check_box.setChecked(True)
        
        # 应用互斥逻辑：优先保留"多余关键帧"，取消"关键帧动画范围"
        if "多余关键帧" in self.check_boxes and "关键帧动画范围" in self.check_boxes:
            self.check_boxes["关键帧动画范围"].setChecked(False)
            self.check_boxes["多余关键帧"].setChecked(True)  # 确保多余关键帧被选中

    def toggle_project_panel(self):
        """切换项目面板的显示/隐藏"""
        self.project_panel.setVisible(self.project_btn.isChecked())

    def on_project_name_changed(self, index, text):
        """当项目名称改变时启用/禁用对应的下拉框"""
        combo = self.project_combos[index]
        combo.setEnabled(bool(text.strip()))
        
        # 如果项目名称为空，清除对应的数据
        if not text.strip() and text.strip() in self.project_data:
            del self.project_data[text.strip()]

    def on_project_action_selected(self, index, action_index):
        """处理项目操作选择"""
        project_name = self.project_inputs[index].text().strip()
        if not project_name:
            return
            
        if action_index == 0:  # 保存信息
            self.save_project_config(project_name)
        elif action_index == 1:  # 清除数据
            self.clear_project_data(project_name)
        elif action_index == 2:  # 准备检查
            self.load_project_config(project_name)
            
        # 重置下拉框选择
        self.project_combos[index].setCurrentIndex(-1)

    def save_project_config(self, project_name):
        """保存项目配置"""
        config = {}
        
        # 收集所有检查项的选中状态和参数
        for check_name, check_box in self.check_boxes.items():
            config[check_name] = {
                'checked': check_box.isChecked()
            }
            
            # 收集特殊参数
            if check_name == "重叠顶点":
                config[check_name]['tolerance'] = self.overlap_vertex_tolerance.text()
            elif check_name == "模型高/低于地面":
                config[check_name]['tolerance'] = self.ground_tolerance.text()
            elif check_name == "模型面数":
                config[check_name]['face_limit'] = self.face_limit_input.text()
            elif check_name == "模型命名":
                config[check_name]['suffix'] = self.geometry_suffix_input.text()
            elif check_name == "渲染硬件":
                config[check_name]['device'] = self.gpu_device_combo.currentText()
            elif check_name == "渲染软件":
                config[check_name]['renderer'] = self.arnold_renderer_combo.currentText()
            elif check_name == "骨骼旋转方向":
                config[check_name]['axis'] = self.orient_axis_combo.currentText()
            elif check_name == "骨骼命名":
                config[check_name]['suffix'] = self.joint_suffix_input.text()
            elif check_name == "镜像骨骼":
                config[check_name]['left_suffix'] = self.left_suffix_input.text()
                config[check_name]['right_suffix'] = self.right_suffix_input.text()
            elif check_name == "父骨未朝子":
                config[check_name]['axis1'] = self.orient_axis_combo1.currentText()
                config[check_name]['axis2'] = self.orient_axis_combo2.currentText()
            elif check_name == "骨骼数量":
                config[check_name]['joint_limit'] = self.joint_limit_input.text()
            elif check_name == "帧率设置":
                config[check_name]['frame_rate'] = self.frame_rate_combo.currentText()
            elif check_name == "时间轴设置":
                config[check_name]['start_frame'] = self.timeline_start_input.text()
                config[check_name]['end_frame'] = self.timeline_end_input.text()
            elif check_name == "关键帧动画范围":
                config[check_name]['start_frame'] = self.anim_range_start_input.text()
                config[check_name]['end_frame'] = self.anim_range_end_input.text()
        
        # 保存到项目数据
        self.project_data[project_name] = config
        
        # 显示保存成功消息
        self.results_text.append(f"项目 '{project_name}' 配置已保存")

    def clear_project_data(self, project_name):
        """清除项目数据"""
        if project_name in self.project_data:
            del self.project_data[project_name]
            # 清空对应的输入框
            for input_field in self.project_inputs:
                if input_field.text().strip() == project_name:
                    input_field.clear()
                    break
            self.results_text.append(f"项目 '{project_name}' 数据已清除")

    def load_project_config(self, project_name):
        """加载项目配置到UI"""
        if project_name not in self.project_data:
            self.results_text.append(f"项目 '{project_name}' 未找到配置数据")
            return
            
        config = self.project_data[project_name]
        
        # 应用配置到UI
        for check_name, settings in config.items():
            if check_name in self.check_boxes:
                # 设置复选框状态
                self.check_boxes[check_name].setChecked(settings.get('checked', False))
                
                # 设置特殊参数
                if check_name == "重叠顶点" and 'tolerance' in settings:
                    self.overlap_vertex_tolerance.setText(settings['tolerance'])
                elif check_name == "模型高/低于地面" and 'tolerance' in settings:
                    self.ground_tolerance.setText(settings['tolerance'])
                elif check_name == "模型面数" and 'face_limit' in settings:
                    self.face_limit_input.setText(settings['face_limit'])
                elif check_name == "模型命名" and 'suffix' in settings:
                    self.geometry_suffix_input.setText(settings['suffix'])
                elif check_name == "渲染硬件" and 'device' in settings:
                    index = self.gpu_device_combo.findText(settings['device'])
                    if index >= 0:
                        self.gpu_device_combo.setCurrentIndex(index)
                elif check_name == "渲染软件" and 'renderer' in settings:
                    index = self.arnold_renderer_combo.findText(settings['renderer'])
                    if index >= 0:
                        self.arnold_renderer_combo.setCurrentIndex(index)
                elif check_name == "骨骼旋转方向" and 'axis' in settings:
                    index = self.orient_axis_combo.findText(settings['axis'])
                    if index >= 0:
                        self.orient_axis_combo.setCurrentIndex(index)
                elif check_name == "骨骼命名" and 'suffix' in settings:
                    self.joint_suffix_input.setText(settings['suffix'])
                elif check_name == "镜像骨骼" and 'left_suffix' in settings and 'right_suffix' in settings:
                    self.left_suffix_input.setText(settings['left_suffix'])
                    self.right_suffix_input.setText(settings['right_suffix'])
                elif check_name == "父骨未朝子" and 'axis1' in settings and 'axis2' in settings:
                    index1 = self.orient_axis_combo1.findText(settings['axis1'])
                    index2 = self.orient_axis_combo2.findText(settings['axis2'])
                    if index1 >= 0:
                        self.orient_axis_combo1.setCurrentIndex(index1)
                    if index2 >= 0:
                        self.orient_axis_combo2.setCurrentIndex(index2)
                elif check_name == "骨骼数量" and 'joint_limit' in settings:
                    self.joint_limit_input.setText(settings['joint_limit'])
                elif check_name == "帧率设置" and 'frame_rate' in settings:
                    index = self.frame_rate_combo.findText(settings['frame_rate'])
                    if index >= 0:
                        self.frame_rate_combo.setCurrentIndex(index)
                elif check_name == "时间轴设置" and 'start_frame' in settings and 'end_frame' in settings:
                    self.timeline_start_input.setText(settings['start_frame'])
                    self.timeline_end_input.setText(settings['end_frame'])
                elif check_name == "关键帧动画范围" and 'start_frame' in settings and 'end_frame' in settings:
                    self.anim_range_start_input.setText(settings['start_frame'])
                    self.anim_range_end_input.setText(settings['end_frame'])
        
        self.results_text.append(f"项目 '{project_name}' 配置已加载")

    def update_mutually_exclusive_checks(self):
        """更新互斥检查项的逻辑：多余关键帧和关键帧动画范围不能同时勾选"""
        if not hasattr(self, 'check_boxes'):
            return
            
        extra_keyframes_check = self.check_boxes.get("多余关键帧")
        keyframe_range_check = self.check_boxes.get("关键帧动画范围")
        
        if not extra_keyframes_check or not keyframe_range_check:
            return
            
        # 如果两个都勾选了，根据发送者来决定取消哪一个
        if extra_keyframes_check.isChecked() and keyframe_range_check.isChecked():
            sender = self.sender()
            if sender == extra_keyframes_check:
                # 如果勾选的是"多余关键帧"，则取消"关键帧动画范围"
                keyframe_range_check.setChecked(False)
            elif sender == keyframe_range_check:
                # 如果勾选的是"关键帧动画范围"，则取消"多余关键帧"
                extra_keyframes_check.setChecked(False)

    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.always_on_top = not self.always_on_top
        if self.always_on_top:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.pin_btn.setStyleSheet("QPushButton { background-color: #90EE90; }")
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.pin_btn.setStyleSheet("")
        self.show()

    def collect_all_buttons(self):
        """收集所有需要应用呼吸灯效果的按钮"""
        buttons = []
        
        # 递归收集所有按钮
        def collect_buttons(widget):
            if isinstance(widget, (QtWidgets.QPushButton, QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
                buttons.append(widget)
            elif hasattr(widget, 'children'):
                for child in widget.children():
                    collect_buttons(child)
        
        collect_buttons(self)
        return buttons

    def toggle_breathing_effect(self):
        """切换呼吸灯效果"""
        if self.breathing_active:
            # 停止效果
            self.breathing_timer.stop()
            self.breathing_active = False
            self.restore_original_styles()
            print("呼吸灯效果已停止")
        else:
            # 启动效果
            if not self.breathing_buttons:
                self.breathing_buttons = self.collect_all_buttons()
                self.save_original_styles()
                
            self.breathing_active = True
            self.breathing_phase = 0
            self.breathing_timer.timeout.connect(self.animate_breathing)
            self.breathing_timer.start(100)  # 每50毫秒更新一次
            print("呼吸灯效果已启动")

    def animate_breathing(self):
        """执行呼吸灯动画效果"""
        if not self.breathing_active or not self.breathing_buttons:
            return
            
        # 计算呼吸效果的alpha值（0.3到1.0之间循环）
        alpha = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self.breathing_phase))
        
        # 应用呼吸效果到所有按钮
        for i, button in enumerate(self.breathing_buttons):
            try:
                # 为每个按钮计算不同的色相偏移，实现彩虹色轮转
                hue_offset = (i / len(self.breathing_buttons)) * 360  # 每个按钮有不同的起始色相
                hue = (self.breathing_phase * 180 / math.pi + hue_offset) % 360  # 色相从0到360度循环
                rgb_color = self.hsv_to_rgb(hue / 360, 1.0, alpha)  # 饱和度和亮度固定，使用呼吸alpha值
                
                r, g, b = rgb_color
                hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                
                # 根据按钮类型设置样式
                if isinstance(button, QtWidgets.QPushButton):
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {hex_color};
                            color: white;
                            border: 1px solid #2c3e50;
                            border-radius: 3px;
                            padding: 5px;
                        }}
                        QPushButton:hover {{
                            background-color: #{min(255, int(r*1.2)):02x}{min(255, int(g*1.2)):02x}{min(255, int(b*1.2)):02x};
                        }}
                        QPushButton:pressed {{
                            background-color: #{max(0, int(r*0.8)):02x}{max(0, int(g*0.8)):02x}{max(0, int(b*0.8)):02x};
                        }}
                    """)
                elif isinstance(button, QtWidgets.QCheckBox):
                    button.setStyleSheet(f"""
                        QCheckBox {{
                            background-color: {hex_color};
                            color: white;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            border-radius: 2px;
                        }}
                        QCheckBox::indicator {{
                            width: 13px;
                            height: 13px;
                        }}
                        QCheckBox::indicator:unchecked {{
                            border: 1px solid #34495e;
                            background-color: white;
                        }}
                        QCheckBox::indicator:checked {{
                            border: 1px solid #34495e;
                            background-color: #2c3e50;
                        }}
                    """)
                elif isinstance(button, QtWidgets.QRadioButton):
                    button.setStyleSheet(f"""
                        QRadioButton {{
                            background-color: {hex_color};
                            color: white;
                            padding: 3px;
                            border: 1px solid #2c3e50;
                            border-radius: 2px;
                        }}
                        QRadioButton::indicator {{
                            width: 13px;
                            height: 13px;
                            border-radius: 7px;
                        }}
                        QRadioButton::indicator:unchecked {{
                            border: 1px solid #34495e;
                            background-color: white;
                        }}
                        QRadioButton::indicator:checked {{
                            border: 1px solid #34495e;
                            background-color: #2c3e50;
                        }}
                    """)
                    
            except Exception as e:
                print(f"设置按钮呼吸效果时出错: {e}")
                continue
        
        # 更新呼吸相位
        self.breathing_phase += self.breathing_speed
        if self.breathing_phase > 2 * math.pi:
            self.breathing_phase -= 2 * math.pi

    def hsv_to_rgb(self, h, s, v):
        """将HSV颜色转换为RGB颜色"""
        if s == 0.0:
            return int(v * 255), int(v * 255), int(v * 255)
        
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        
        i = i % 6
        
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        elif i == 5:
            r, g, b = v, p, q
        
        return int(r * 255), int(g * 255), int(b * 255)

    def save_original_styles(self):
        """保存所有按钮的原始样式"""
        self.original_styles = {}
        for button in self.breathing_buttons:
            self.original_styles[button] = button.styleSheet()

    def restore_original_styles(self):
        """恢复所有按钮的原始样式"""
        for button, style in self.original_styles.items():
            try:
                button.setStyleSheet(style)
            except Exception as e:
                print(f"恢复按钮样式时出错: {e}")

    def show_tool_info(self):
        """显示工具说明信息"""
        tool_info = """
    工具概述
    这是一个全面的Maya场景检查和处理工具，包含7大功能模块：场景大纲、模型拓补、模型UV、材质、灯光渲染、骨骼绑定和动画。工具提供自动化检查和一键处理功能，帮助用户快速发现和修复场景中的问题。

    界面功能说明
    颜色说明
    蓝色：包含详细的一键处理功能
    黄色：包含一键处理功能，但是仅高亮显示有问题的地方
    红色：无一键处理功能

    工具管理
    工具说明：在处理栏显示该工具的详细说明，包括按钮功能、参数说明等具体信息
    项目管理：切换项目窗口，下拉展示五个项目检查预设内容，文本框内支持输入预设名称。勾选检查内容并输入检查参数。再点击将返回之前的按钮状态
    保存信息：点击"保存信息"保存预设的检查信息
    准备检查：点击"准备检查"即可调取之前的保存的预设信息作为检查内容
    清除数据：点击"清除数据"即可删除保存的预设及存储的预设信息

    文档保存
    文档保存地址：输入你要保存的检查文档的地址
    浏览：打开或者选择要保存的检查文档的详细地址
    保存：保存".md"检查文档到对应的地址中

    检查范围
    选择对象：只检查当前选中的对象
    全部对象：检查场景中所有对象

    选择按钮
    全选：选中所有检查项
    全选处理：只选中蓝色背景的检查项（推荐的基础检查项）
    全不选：取消所有检查项

    主功能按钮
    开始检查：运行选中的检查项目
    一键处理：自动修复选中的检查项发现的问题
    选择问题对象：选中检查发现的问题对象

    详细检查功能说明
    1. 场景大纲组
    红色：显示层 (layers)
    检查内容：检查节点是否在显示层中
    一键处理：无专门处理功能

    蓝色：空层 (emptyLayers)
    检查内容：检查空的显示层和动画层
    一键处理：删除所有空的显示层和动画层

    蓝色：着色器 (shaders)
    检查内容：检查模型是否使用了非默认着色器
    一键处理：将所有模型指定为lambert1默认材质

    蓝色：构造历史 (history)
    检查内容：检查网格是否有构造历史记录
    一键处理：删除网格的构造历史记录

    蓝色：未冻结变换 (unfrozenTransforms)
    检查内容：检查变换节点的变换值是否未冻结（非零旋转、非单位缩放）
    一键处理：冻结变换节点的变换值

    蓝色：未居中轴点 (uncenteredPivots)
    检查内容：检查变换节点的轴心点是否不在世界原点
    一键处理：将轴心点移动到世界原点

    蓝色：空组 (emptyGroups)
    检查内容：检查空的组节点（没有子节点、没有连接、没有自定义属性）
    一键处理：删除所有空组

    蓝色：父级几何体 (parentGeometry)
    检查内容：检查几何体是否作为其他几何体的父级
    一键处理：解除几何体的父子关系

    蓝色：尾部数字 (trailingNumbers)
    检查内容：检查节点名称是否以数字结尾
    一键处理：重命名节点，添加"_reNamePls"后缀

    蓝色：重复名称 (duplicatedNames)
    检查内容：检查场景中是否有重复的节点名称
    一键处理：重命名所有重复的节点，添加数字后缀

    蓝色：命名空间 (namespaces)
    检查内容：检查节点是否有命名空间
    一键处理：删除空的命名空间，移除节点上的命名空间

    蓝色：形状名称 (shapeNames)
    检查内容：检查形状节点名称是否符合Maya默认约定
    一键处理：重命名形状节点以符合约定

    蓝色：多余灯光 (checkLights)
    检查内容：检查场景中是否有灯光（排除默认灯光）
    一键处理：删除所有灯光

    蓝色：多余摄像机 (checkCameras)
    检查内容：检查场景中是否有非默认摄像机
    一键处理：删除非默认摄像机

    蓝色：多余关键帧 (checkKeyframes)
    检查内容：检查场景中是否有关键帧
    一键处理：删除所有关键帧

    2. 模型拓补组
    蓝色：三角形面 (triangles)
    检查内容：检查网格是否有三角形面
    一键处理：删除三角形面

    蓝色：多边面 (ngons)
    检查内容：检查网格是否有超过4条边的多边形面
    一键处理：删除多边面

    蓝色：硬边 (hardEdges)
    检查内容：检查网格是否有非边界硬边
    一键处理：软化硬边

    蓝色：重叠面 (lamina)
    检查内容：检查网格是否有重叠面
    一键处理：删除重叠面（每对中随机删除一个）

    蓝色：零面积面 (zeroAreaFaces)
    检查内容：检查网格是否有面积接近零的面
    一键处理：删除零面积面

    蓝色：零长度边 (zeroLengthEdges)
    检查内容：检查网格是否有长度接近零的边
    一键处理：删除零长度边

    蓝色：非流形边 (noneManifoldEdges)
    检查内容：检查网格是否有非流形边（连接超过两个面的边）
    一键处理：删除非流形边

    黄色：开放边 (openEdges)
    检查内容：检查网格是否有开放边（只连接一个面的边）
    一键处理：选择开放边（无自动修复）

    黄色：极点 (poles)
    检查内容：检查网格是否有极点（连接超过5条边的顶点）
    一键处理：选择极点（无自动修复）

    蓝色：非星形面 (starlike)
    检查内容：检查网格是否有非星形面
    一键处理：删除非星形面

    蓝色：重叠顶点 (overlapping_vertices)
    检查内容：检查网格是否有重叠的顶点
    一键处理：合并重叠顶点（使用UI设置的容差值）
    输入参数：合并重叠顶点的容差值，即合并顶点间的最小距离

    蓝色：分离模型 (is_selected_model_separated)
    检查内容：检查模型是否由多个分离的部分组成
    一键处理：分离未分离的模型

    红色：模型对称 (checkModelSymmetry)
    检查内容：检查模型是否沿世界X轴对称
    一键处理：无自动修复功能

    蓝色：模型高/低于地面 (checkGroundAlignment)
    检查内容：检查模型最低顶点位置是否不等于地面
    一键处理：将模型移动到地面上并冻结变换
    输入参数：模型顶点和世界平面的容差值，即模型最低或者最高顶点距离世界平面的最小距离

    红色：模型面数 (checkModelFacesNum)
    检查内容：检查模型面数是否超过限定数值
    一键处理：无自动修复功能（需要手动优化）
    输入参数：模型三角面总数（上限）

    蓝色：模型命名 (checkGeometrySuffix)
    检查内容：检查模型后缀命名是否符合规范
    一键处理：给模型添加后缀名
    输入参数：模型的后缀名

    3. 模型UV组
    红色：缺少UV (missingUVs)
    检查内容：检查网格是否有面没有UV
    一键处理：无自动修复功能

    红色：UV范围 (uvRange)
    检查内容：检查UV是否在0-1范围之外
    一键处理：无自动修复功能

    红色：UV边界 (onBorder)
    检查内容：检查UV是否在UV边界上
    一键处理：无自动修复功能

    红色：跨界UV (crossBorder)
    检查内容：检查面的UV是否跨越多个UV瓦片
    一键处理：无自动修复功能

    蓝色：非map1 UV集 (nonMap1UVSets)
    检查内容：检查网格是否有非map1的UV集
    一键处理：重命名UV集为map1

    红色：自重叠UV (selfPenetratingUVs)
    检查内容：检查UV是否有自重叠
    一键处理：无自动修复功能

    4. 材质组
    蓝色：材质丢失 (checkMissingMaterials)
    检查内容：检查模型是否没有材质
    一键处理：为模型赋予lambert1默认材质

    蓝色：未使用材质 (check_material_info)
    检查内容：检查场景中未使用的材质和着色组
    一键处理：删除未使用的材质和着色组

    红色：贴图路径丢失 (texturePathLost)
    检查内容：检查材质贴图的文件路径是否丢失
    一键处理：无自动修复功能

    5. 灯光渲染组
    蓝色：未创建HDRI (checkSkyDomeLight)
    检查内容：检查场景中是否有SkyDomeLight
    一键处理：创建SkyDomeLight

    红色：渲染层masterLayer (checkRenderLayer)
    检查内容：检查当前渲染层是否是masterLayer
    一键处理：无自动修复功能

    红色：AOV分层 (checkAOVs)
    检查内容：检查渲染设置中是否有AOV分层
    一键处理：无自动修复功能

    蓝色：渲染硬件 (checkCPURendering)
    检查内容：检查渲染设置中是否是CPU/GPU渲染
    一键处理：根据用户选择设置渲染设备
    输入参数：CPU渲染/GPU渲染

    蓝色：渲染软件 (checkArnoldRenderer)
    检查内容：检查渲染设置中是否使用指定的渲染器
    一键处理：设置当前渲染器为用户选择的渲染器
    输入参数：Arnold等常用渲染器

    6. 骨骼绑定组
    红色：历史记录检查 (checkBoundModelIssues)
    检查内容：检查已绑定模型的建模历史、未冻结变换和未居中轴心
    一键处理：无自动修复功能

    红色：blendshape (checkBlendShape)
    检查内容：检查模型上是否有blendshape
    一键处理：无自动修复功能

    蓝色：骨骼未冻结变换 (checkUnboundJointsTransforms)
    检查内容：检查未绑定的骨骼上变换节点是否已冻结
    一键处理：冻结未绑定骨骼的变换

    蓝色：未绑定骨骼 (find_redundant_joints)
    检查内容：检查场景中是否有多余的骨骼（没有和模型绑定的骨骼）
    一键处理：删除未绑定的骨骼

    蓝色：重叠骨骼 (checkOverlappingJoints)
    检查内容：检查场景中是否有重叠的骨骼
    一键处理：删除重叠的骨骼

    蓝色：骨骼命名 (checkJointSuffix)
    检查内容：检查骨骼的后缀名是否和参数中的一致
    一键处理：为骨骼添加和参数中一致的后缀名
    输入参数：骨骼后缀名称

    蓝色：骨骼旋转方向 (check_joint_alignment_XYZ)
    检查内容：检查骨骼的旋转顺序是否符合目标旋转顺序
    一键处理：设置骨骼的旋转顺序为目标旋转顺序
    输入参数：骨骼的旋转方向

    蓝色：父骨未朝子 (check_joint_parent_child)
    检查内容：检查所有骨骼的父级骨骼是否朝向子骨骼。另外会检查第一个参数输入的内容，如果选择参数"yzx"将检查父级骨骼的y轴（选择参数的第一个字母所在的轴向）方向是否朝向子级，但不会检查第二个参数的内容
    一键处理：根据两个参数的选择重新定向非末端骨骼的朝向
    输入参数：
    第一个参数可以是以下字符串之一"xyz、yzx、zxy、zyx、yxz、xzy、none"。该命令会修改关节的方向和缩放方向，使参数中第一个字母指示的轴与从该关节到其第一个子关节的向量对齐。例如，如果参数是"yzx"，则y轴将指向子关节。在用户未指定次要轴方向的情况下，由参数中最后一个字母指示的旋转轴将与垂直于第一个轴和从此关节到其父关节的向量的向量对齐。剩余轴根据右手规则对齐。如果参数是"none"，则关节方向将被设置为零，并且其对下方层次结构的影响将通过修改缩放方向来抵消。
    第二个参数可以是以下字符串之一"xup、xdown、yup、ydown、zup、zdown、none"。此标志与第一个参数结合使用。它指定第二个轴应与场景中的哪个轴对齐。例如，标志组合"-oj yzx -sao yup"将导致y轴指向骨骼下方，z轴与场景的正y轴方向一致，而x轴则根据右手规则定向。

    蓝色：末端骨骼轴向不一致 (check_end_joint_alignment)
    检查内容：检查末端骨骼与父级轴向一致性
    一键处理：修复末端骨骼的轴向，使其与父级骨骼保持一致

    红色：镜像骨骼 (check_joint_symmetry_x_axis)
    检查内容：检查遵循左侧骨骼后缀名和右侧骨骼后缀名命名约定的骨骼是否沿X轴对称
    一键处理：无自动修复功能
    输入参数：左侧骨骼后缀命名和右侧骨骼后缀命名

    红色：骨骼数量 (check_joint_limit)
    检查内容：检查场景中骨骼的数量是否超过限制
    一键处理：无自动修复功能
    输入参数：最大骨骼数量的具体数值

    红色：权重丢失 (check_missing_weights)
    检查内容：检查已有绑定信息的模型和骨骼上的权重是否丢失
    一键处理：无自动修复功能

    红色：镜像权重 (check_weight_symmetry)
    检查内容：检查已有绑定信息的模型和骨骼上的权重是否对称
    一键处理：无自动修复功能

    7. 动画组
    蓝色：帧率设置 (check_frame_rate)	
    检查内容：检查动画帧率设置是否符合目标设置
    一键处理：设置动画帧率为目标帧率
    输入参数：要设置的动画帧率的具体数值

    蓝色：时间轴设置 (check_timeline_range)
    检查内容：检查时间轴范围是否符合规范
    一键处理：设置时间轴范围
    输入参数：第一个参数为起始帧的具体数值，第二个为结束帧的具体数值

    蓝色：关键帧动画范围 (check_joint_keyframes_in_range)
    检查内容：检查所有物体上的关键帧是否在时间轴设置范围内
    一键处理：删除范围外的关键帧，并在边界设置关键帧
    输入参数：第一个参数为起始帧的具体数值，第二个为结束帧的具体数值

    红色：文件引用丢失 (check_missing_references)
    检查内容：检查场景中的动画文件引用路径是否丢失
    一键处理：无自动修复功能

    红色：关键帧不在整数帧上 (check_integer_keyframes)
    检查内容：检查场景中的关键帧是否都在整数帧上
    一键处理：无自动修复功能

    使用建议
    首次使用：建议点击"全选处理"按钮，只选择蓝色背景的基础检查项
    常规检查：使用默认设置进行全场景检查
    针对性检查：根据具体需求选择特定组的检查项
    处理前备份：在进行一键处理前，建议保存场景备份
    参数调整：部分检查项支持参数调整（如容差值、限制值等），可根据需要修改
    """
        
        # 创建富文本格式
        from PySide2.QtCore import Qt
        from PySide2.QtGui import QTextCursor, QColor
        
        # 清空文本框
        self.fix_results_text.clear()
        
        # 设置默认白色
        self.fix_results_text.setTextColor(QColor(255, 255, 255))
        
        lines = tool_info.strip().split('\n')
        
        for line in lines:
            if line.startswith('    '):  # 缩进行
                # 移除前4个空格的缩进
                clean_line = line[4:]
                
                # 检查颜色标记
                if clean_line.startswith('蓝色：'):
                    self.fix_results_text.setTextColor(QColor(0, 150, 255))  # 蓝色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                elif clean_line.startswith('黄色：'):
                    self.fix_results_text.setTextColor(QColor(255, 255, 0))  # 黄色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                elif clean_line.startswith('红色：'):
                    self.fix_results_text.setTextColor(QColor(255, 100, 100))  # 红色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                elif clean_line.startswith('蓝色'):
                    self.fix_results_text.setTextColor(QColor(0, 150, 255))  # 蓝色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                elif clean_line.startswith('黄色'):
                    self.fix_results_text.setTextColor(QColor(255, 255, 0))  # 黄色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                elif clean_line.startswith('红色'):
                    self.fix_results_text.setTextColor(QColor(255, 100, 100))  # 红色
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
                    self.fix_results_text.setTextColor(QColor(255, 255, 255))  # 恢复白色
                else:
                    self.fix_results_text.insertPlainText('    ' + clean_line + '\n')
            else:
                # 非缩进行直接添加
                self.fix_results_text.insertPlainText(line + '\n')

    def quick_fix(self):
        """一键处理功能 - 只处理选中的检查内容"""
        # 清空之前的处理结果
        self.fix_results_text.clear()
        self.fix_results_text.append("开始一键处理...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 获取要处理的节点（根据用户选择的范围）
        nodes_to_process = self.get_nodes_to_check()
        if not nodes_to_process:
            self.fix_results_text.append("没有找到要处理的对象！")
            return
        
        # 检查用户选中了哪些检查项
        selected_checks = [check_name for check_name, check_box in self.check_boxes.items() if check_box.isChecked()]
        
        if not selected_checks:
            self.fix_results_text.append("请先选择要处理的检查项！")
            return
        
        self.fix_results_text.append(f"将处理以下检查项: {', '.join(selected_checks)}")
        
        # 将"模型高/低于地面"检查项移到处理队列的最前面
        ground_check = "模型高/低于地面"
        if ground_check in selected_checks:
            selected_checks.remove(ground_check)
            selected_checks.insert(0, ground_check)  # 插入到列表开头
        
        # 根据选中的检查项执行相应的处理
        processed_items = 0
        
        # 首先处理"模型高/低于地面"检查项
        if "模型高/低于地面" in selected_checks:
            self.fix_results_text.append("正在处理: 模型高/低于地面...")
            # 从UI获取容差值
            try:
                tolerance_value = float(self.ground_tolerance.text())
            except ValueError:
                tolerance_value = 0.001
            moved_count = self.moveModelsToGroundAndFreeze(nodes_to_process, tolerance_value)
            if moved_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 移动了 {moved_count} 个高/低于地面的模型"))
                processed_items += moved_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到高/低于地面的模型"))
            
        
        # 处理空层
        if "空层" in selected_checks:
            self.fix_results_text.append("正在处理: 空层...")
            deleted_layers = self.delete_empty_layers(nodes_to_process)
            if deleted_layers:
                # 显示处理结果
                display_layers = deleted_layers[:5]
                layer_list = ", ".join(display_layers)
                if len(deleted_layers) > 5:
                    layer_list += f" 等 {len(deleted_layers)} 个空层"
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: {len(deleted_layers)} 个 - {layer_list}"))
                processed_items += len(deleted_layers)
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到空层"))
        
        # 处理材质
        if "着色器" in selected_checks:
            self.fix_results_text.append("正在处理: 材质...")
            assigned_count = self.checkAndAssignLambert(nodes_to_process)
            if assigned_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 为 {assigned_count} 个模型指定了lambert1材质"))
                processed_items += assigned_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有模型都已使用lambert1材质"))
        
        # 处理构造历史
        if "构造历史" in selected_checks:
            self.fix_results_text.append("正在处理: 构造历史...")
            deleted_count = self.checkAndDeleteMeshHistory(nodes_to_process)
            if deleted_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_count} 个网格的历史记录"))
                processed_items += deleted_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有网格都没有历史记录"))
        
        # 处理未冻结变换
        if "未冻结变换" in selected_checks:
            self.fix_results_text.append("正在处理: 未冻结变换...")
            frozen_count = self.checkAndFreezeTransforms(nodes_to_process)
            if frozen_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 冻结了 {frozen_count} 个变换节点"))
                processed_items += frozen_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有变换节点都已冻结"))
        
        # 处理未居中轴点
        if "未居中轴点" in selected_checks:
            self.fix_results_text.append("正在处理: 未居中轴点...")
            centered_count = self.checkAndCenterPivots(nodes_to_process)
            if centered_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 将 {centered_count} 个节点的轴心点移动到世界原点"))
                processed_items += centered_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有节点的轴心点都已位于世界原点"))
        
        # 处理空组
        if "空组" in selected_checks:
            self.fix_results_text.append("正在处理: 空组...")
            deleted_groups = self.delete_empty_groups(nodes_to_process)
            if deleted_groups:
                # 显示处理结果
                display_groups = deleted_groups[:5]
                group_list = ", ".join(display_groups)
                if len(deleted_groups) > 5:
                    group_list += f" 等 {len(deleted_groups)} 个空组"
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: {len(deleted_groups)} 个 - {group_list}"))
                processed_items += len(deleted_groups)
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到可删除的空组"))
        
        # 处理父级几何体
        if "父级几何体" in selected_checks:
            self.fix_results_text.append("正在处理: 父级几何体...")
            unparented_count = self.checkAndUnparentGeometry(nodes_to_process)
            if unparented_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 解除了 {unparented_count} 个几何体的父子关系"))
                processed_items += unparented_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有发现几何体父子关系问题"))
        
        # 处理尾部数字
        if "尾部数字" in selected_checks:
            self.fix_results_text.append("正在处理: 尾部数字...")
            renamed_count = self.renameNodesWithTrailingNumbers(nodes_to_process)
            if renamed_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 重命名了 {renamed_count} 个以数字结尾的节点"))
                processed_items += renamed_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到以数字结尾的节点"))

        # 处理重复命名
        if "重复名称" in selected_checks:
            self.fix_results_text.append("正在处理: 重复名称...")
            renamed_dupted_count = self.renameAllDuplicatedNodes(nodes_to_process)
            if renamed_dupted_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 重命名了 {renamed_dupted_count} 个重复名称"))
                processed_items += renamed_dupted_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到重复名称"))

        # 处理空命名空间
        if "命名空间" in selected_checks:
            self.fix_results_text.append("正在处理: 命名空间...")
            deleted_namespace_count = self.deleteAllEmptyNamespaces(nodes_to_process)
            if deleted_namespace_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_namespace_count} 个命名空间"))
                processed_items += len(deleted_namespace_count)
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到命名空间"))

        # 处理形状名称
        if "形状名称" in selected_checks:
            self.fix_results_text.append("正在处理: 形状名称...")
            renamed_shape_count = self.checkAndRenameShapeNodes(nodes_to_process)
            if renamed_shape_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 重命名了 {renamed_shape_count} 个形状节点"))
                processed_items += renamed_shape_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有形状节点都符合命名约定"))

        # 处理删除灯光
        if "多余灯光" in selected_checks:
            self.fix_results_text.append("正在处理: 多余灯光...")
            QtCore.QCoreApplication.processEvents()  # 更新UI
            deleted_lights_count = self.delete_all_lights(nodes_to_process)
            if deleted_lights_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_lights_count} 个灯光"))
                processed_items += deleted_lights_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中没有找到需要删除的灯光"))

        # 处理多余摄像机
        if "多余摄像机" in selected_checks:
            self.fix_results_text.append("正在处理: 多余摄像机...")
            deleted_camera_count = self.delete_extra_cameras(nodes_to_process)
            if deleted_camera_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_camera_count} 个多余摄像机"))
                processed_items += deleted_camera_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到多余摄像机"))

        # 处理多余关键帧
        if "多余关键帧" in selected_checks:
            self.fix_results_text.append("正在处理: 多余关键帧...")
            deleted_keyframe_count = self.deleteKeyframes(nodes_to_process)
            if deleted_keyframe_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_keyframe_count} 个关键帧"))
                processed_items += deleted_keyframe_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到关键帧"))

        # 处理三角形面
        if "三角形面" in selected_checks:
            self.fix_results_text.append("正在处理: 三角形面...")
            deleted_triangles_count = self.checkAndDeleteTriangles(nodes_to_process)
            if deleted_triangles_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_triangles_count} 个三角形面"))
                processed_items += deleted_triangles_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到三角形面"))

        # 处理多边面
        if "多边面" in selected_checks:
            self.fix_results_text.append("正在处理: 多边面...")
            deleted_ngons_count = self.checkAndDeleteNgons(nodes_to_process)
            if deleted_ngons_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_ngons_count} 个多边面"))
                processed_items += deleted_ngons_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到多边面"))

        # 处理硬边
        if "硬边" in selected_checks:
            self.fix_results_text.append("正在处理: 硬边...")
            softened_hard_edges_count = self.checkAndSoftenHardEdges(nodes_to_process)
            if softened_hard_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 软化了 {softened_hard_edges_count} 个硬边"))
                processed_items += softened_hard_edges_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到硬边"))

        # 处理重叠面
        if "重叠面" in selected_checks:
            self.fix_results_text.append("正在处理: 重叠面...")
            deleted_lumina_count = self.checkAndDeleteHalfLaminaFaces_main(nodes_to_process)
            if deleted_lumina_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_lumina_count} 个重叠面"))
                processed_items += deleted_lumina_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到重叠面"))

        # 处理零面积面
        if "零面积面" in selected_checks:
            self.fix_results_text.append("正在处理: 零面积面...")
            deleted_ZeroAreaFaces_count = self.checkAndDeleteZeroAreaFaces(nodes_to_process)
            if deleted_ZeroAreaFaces_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_ZeroAreaFaces_count} 个零面积面"))
                processed_items += deleted_ZeroAreaFaces_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到零面积面"))

        # 处理零长度边
        if "零长度边" in selected_checks:
            self.fix_results_text.append("正在处理: 零长度边...")
            deleted_zero_length_edges_count = self.checkAndDeleteZeroLengthEdges(nodes_to_process)
            if deleted_zero_length_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {deleted_zero_length_edges_count} 个零长度边"))
                processed_items += deleted_zero_length_edges_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到零长度边"))

        # 处理非流形边
        if "非流形边" in selected_checks:
            self.fix_results_text.append("正在处理:非流形边...")
            actual_deleted = self.checkAndDeleteNonManifoldEdges(nodes_to_process)
            if actual_deleted > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 删除了 {actual_deleted} 个非流形边"))
                processed_items += actual_deleted
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到非流形边"))

        # 选择开放边
        if "开放边" in selected_checks:
            self.fix_results_text.append("正在计算:开放边...")
            selected_edges_count = self.checkAndSelectOpenEdges(nodes_to_process)
            if selected_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 选择了 {selected_edges_count} 个开放边"))
                processed_items += selected_edges_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到开放边"))

        # 选择极点
        if "极点" in selected_checks:
            self.fix_results_text.append("正在计算:极点...")
            selected_poles_count = self.checkAndSelectPoleVertices(nodes_to_process)
            if selected_poles_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 选择了 {selected_poles_count} 个极点"))
                processed_items += selected_poles_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到极点"))

        # 删除非星形面
        if "非星形面" in selected_checks:
            self.fix_results_text.append("正在删除:非星形面...")
            deleted_non_starlike_count = self.checkAndDeleteNonStarlikeFaces(nodes_to_process)
            if deleted_non_starlike_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 删除了 {deleted_non_starlike_count} 个非星形面"))
                processed_items += deleted_non_starlike_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到非星形面"))

        # 合并重叠顶点
        if "重叠顶点" in selected_checks:
            self.fix_results_text.append("正在合并:重叠顶点...")
            merged_count = self.checkAndMergeOverlappingVertices(nodes_to_process)
            if merged_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 合并了 {merged_count} 个重叠顶点"))
                processed_items += merged_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到重叠顶点"))

        # 分离未分离的模型
        if "分离模型" in selected_checks:
            self.fix_results_text.append("正在分离:未分离的模型...")
            split_count = self.split_separated_model(nodes_to_process)
            if split_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 分离了 {split_count} 个未分离的模型"))
                processed_items += split_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到未分离的模型"))

        # 处理模型命名
        if "模型命名" in selected_checks:
            self.fix_results_text.append("正在修改: 模型命名...")
            # 从UI获取后缀
            suffix_text = self.geometry_suffix_input.text()
            renamed_geometry_count = self.addGeometrySuffix(nodes_to_process, suffix_text)
            if renamed_geometry_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了 {renamed_geometry_count} 个模型命名"))
                processed_items += renamed_geometry_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有模型都符合命名规范"))

        # 非map1 UV集
        if "非map1 UV集" in selected_checks:
            self.fix_results_text.append("正在处理: 非map1 UV集...")
            renamed_uv_count = self.renameUVSetsToMap1(nodes_to_process)
            if renamed_uv_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已处理完成: 重命名了 {renamed_uv_count} 个UV集为map1"))
                processed_items += renamed_uv_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有UV集都已命名为map1"))

        # 材质丢失
        if "材质丢失" in selected_checks:
            self.fix_results_text.append("正在赋予:材质丢失的模型...")
            fixed_count = self.checkAndFixMissingMaterials(nodes_to_process)
            if fixed_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 赋予了 {fixed_count} 个材质丢失的模型"))
                processed_items += fixed_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到材质丢失的模型"))

        # 未使用材质
        if "未使用材质" in selected_checks:
            self.fix_results_text.append("正在删除:未使用材质...")
            total_deleted = self.delete_unused_materials_and_shading_groups(nodes_to_process)
            if total_deleted > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 删除了 {total_deleted} 个未使用材质"))
                processed_items += total_deleted
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 没有找到未使用材质"))

        # 处理未创建HDRI
        if "未创建HDRI" in selected_checks:
            self.fix_results_text.append("正在处理: 未创建HDRI...")
            aiSkyDomeLight_count = self.checkAndCreateSkyDomeLight(nodes_to_process)
            if aiSkyDomeLight_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 创建了 {aiSkyDomeLight_count} 个SkyDomeLight"))
                processed_items += aiSkyDomeLight_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中已存在SkyDomeLight"))

        # 骨骼未冻结变换
        if "骨骼未冻结变换" in selected_checks:
            self.fix_results_text.append("正在处理: 骨骼未冻结变换...")
            frozen_count = self.freezeUnboundJointsTransforms(nodes_to_process)
            if frozen_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 处理了 {frozen_count} 个未冻结变换的骨骼"))
                processed_items += frozen_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中骨骼都已完成冻结变换操作"))

        # 未绑定骨骼
        if "未绑定骨骼" in selected_checks:
            self.fix_results_text.append("正在删除: 未绑定的骨骼...")
            redundant_joints_count = self.remove_redundant_joints(nodes_to_process)
            if redundant_joints_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 删除了 {redundant_joints_count} 个未绑定的骨骼"))
                processed_items += redundant_joints_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有骨骼都有绑定信息"))

        # 重叠骨骼
        if "重叠骨骼" in selected_checks:
            self.fix_results_text.append("正在删除: 重叠骨骼...")
            deleted_overlapping_joints_count = self.deleteOverlappingJoints(nodes_to_process)
            if deleted_overlapping_joints_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 删除了 {deleted_overlapping_joints_count} 个重叠骨骼"))
                processed_items += deleted_overlapping_joints_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有骨骼没有重叠"))

        # 骨骼命名
        if "骨骼命名" in selected_checks:
            self.fix_results_text.append("正在修改: 骨骼命名...")
            # 从UI获取后缀
            suffix_text = self.joint_suffix_input.text()
            renamed_joints_count = self.addJointSuffix(nodes_to_process, suffix_text)
            if renamed_joints_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了 {renamed_joints_count} 个骨骼命名"))
                processed_items += renamed_joints_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有骨骼都符合命名规范"))

        # 骨骼旋转方向
        if "骨骼旋转方向" in selected_checks:
            self.fix_results_text.append("正在修改: 骨骼旋转方向...")
            # 获取选中的旋转顺序索引
            target_rotate_order = self.orient_axis_combo.currentIndex()
            joint_alignment_xyz_count = self.joint_alignment_XYZ(nodes_to_process, target_rotate_order)
            if joint_alignment_xyz_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了 {joint_alignment_xyz_count} 个骨骼旋转方向"))
                processed_items += joint_alignment_xyz_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有骨骼旋转方向都符合规范"))

        # 父级骨骼未朝向子级
        if "父骨未朝子" in selected_checks:
            self.fix_results_text.append("正在修改: 非末端父级骨骼朝向...")
            # 获取两个下拉框的当前值
            orient_joint = self.orient_axis_combo1.currentText()
            secondary_axis_orient = self.orient_axis_combo2.currentText()
            
            # 创建参数字典
            params = {
                'orientJoint': orient_joint,
                'secondaryAxisOrient': secondary_axis_orient
            }
            
            orient_joints_excluding_end_joints_count = self.orient_joints_excluding_end_joints_main(nodes_to_process, params)
            if orient_joints_excluding_end_joints_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了 {orient_joints_excluding_end_joints_count} 个非末端父级骨骼朝向"))
                processed_items += orient_joints_excluding_end_joints_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有非末端父级骨骼朝向都符合规范"))

        # 末端骨骼轴向不一致
        if "末端骨骼轴向不一致" in selected_checks:
            self.fix_results_text.append("正在修改: 末端骨骼轴向...")
            fix_end_joint_alignment_count = self.check_and_fix_end_joint_axis_alignment(nodes_to_process)
            if fix_end_joint_alignment_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了 {fix_end_joint_alignment_count} 个末端骨骼的轴向"))
                processed_items += fix_end_joint_alignment_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 场景中所有的末端骨骼轴向都符合规范"))

        # 处理渲染硬件
        if "渲染硬件" in selected_checks:
            self.fix_results_text.append("正在处理: 渲染硬件...")
            fix_cpu_gpu_count = self.check_and_fix_cpu_gpu(nodes_to_process)
            if fix_cpu_gpu_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了渲染硬件设置"))
                processed_items += fix_cpu_gpu_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 渲染硬件设置正确"))

        # 处理渲染软件
        if "渲染软件" in selected_checks:
            self.fix_results_text.append("正在处理: 渲染软件...")
            fix_render_software_count = self.check_and_fix_render_software(nodes_to_process)
            if fix_render_software_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修改了渲染软件设置"))
                processed_items += fix_render_software_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 渲染软件设置正确"))

        # 处理帧率设置
        if "帧率设置" in selected_checks:
            self.fix_results_text.append("正在设置: 帧率...")
            fix_ani_rate_count = self.check_and_fix_ani_rate(nodes_to_process)
            if fix_ani_rate_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 设置了动画帧率"))
                processed_items += fix_ani_rate_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 帧率设置正确，无需修改"))

        # 处理时间轴设置
        if "时间轴设置" in selected_checks:
            self.fix_results_text.append("正在设置: 时间轴范围...")
            fixed_timeline_count = self.check_and_fix_timeline_range(nodes_to_process)
            if fixed_timeline_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 设置了时间轴范围"))
                processed_items += fixed_timeline_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 时间轴范围设置正确，无需修改"))

        # 处理关键帧动画范围
        if "关键帧动画范围" in selected_checks:
            self.fix_results_text.append("正在修复: 关键帧动画范围...")
            # 从UI获取开始帧和结束帧
            try:
                target_start_frame = int(self.anim_range_start_input.text())
            except ValueError:
                target_start_frame = 0
            try:
                target_end_frame = int(self.anim_range_end_input.text())
            except ValueError:
                target_end_frame = 150
            
            params = {
                'start_frame': target_start_frame,
                'end_frame': target_end_frame
            }
            
            fixed_anim_range_count = self.check_and_fix_animation_range(nodes_to_process, params)
            if fixed_anim_range_count > 0:
                self.fix_results_text.append(self.format_status(f"  [OK] 已完成: 修复了 {fixed_anim_range_count} 个关键帧动画范围"))
                processed_items += fixed_anim_range_count
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 所有关键帧都在指定范围内"))

        if processed_items > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 一键处理完成！共处理了 {processed_items} 个项目"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 一键处理完成！没有需要处理的项目"))

    def getAllTransformNodesUUIDs(self):
        """获取场景中所有变换节点的UUID"""
        transform_uuids = []
        
        # 获取所有变换节点
        try:
            transforms = cmds.ls(type='transform')
            for transform in transforms:
                try:
                    uuid = cmds.ls(transform, uuid=True)[0]
                    transform_uuids.append(uuid)
                except:
                    continue
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 获取变换节点UUID时出错: {str(e)}"))
        
        return transform_uuids

    def get_non_manifold_edges(self, mesh):
        """获取非流形边（仅包含连接3个及以上面的边，排除开放边）"""
        if not cmds.objExists(mesh):
            raise ValueError(f"对象 '{mesh}' 不存在")
        
        # 确保处理的是形状节点
        shape = mesh
        if cmds.objectType(mesh) == 'transform':
            shapes = cmds.listRelatives(mesh, shapes=True, type='mesh')
            if not shapes:
                raise ValueError(f"对象 '{mesh}' 不包含网格形状")
            shape = shapes[0]

        non_manifold_edges = []
        all_edges = cmds.ls(f"{shape}.e[:]", flatten=True)
        
        for edge in all_edges:
            # 获取边连接的面
            faces = cmds.polyListComponentConversion(edge, toFace=True)
            faces = cmds.ls(faces, flatten=True) if faces else []
            face_count = len(faces)
            
            # 非流形边定义：连接3个或更多面的边
            # 排除开放边（只连接1个面）和正常流形边（连接2个面）
            if face_count >= 3:
                # 提取边ID
                edge_id = int(edge.split('[')[-1].split(']')[0])
                non_manifold_edges.append(edge_id)
        
        return non_manifold_edges

    def delete_empty_layers(self, nodes_to_process=None):
        """删除场景中所有空的显示层和动画层"""
        deleted_layers = []
        
        # 获取所有显示层
        display_layers = cmds.ls(type="displayLayer")
        
        # 检查并删除空的显示层
        for layer in display_layers:
            # 跳过默认显示层
            if layer == "defaultLayer":
                continue
                
            # 获取层中的成员
            try:
                members = cmds.editDisplayLayerMembers(layer, query=True, fullNames=True)
            except:
                members = []
                
            # 如果层中没有成员，则删除
            if not members or len(members) == 0:
                try:
                    cmds.delete(layer)
                    deleted_layers.append(layer)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 无法删除显示层 {layer}: {str(e)}"))
        
        # 获取所有动画层
        anim_layers = cmds.ls(type="animLayer")
        
        # 检查并删除空的动画层
        for layer in anim_layers:
            # 获取层中的动画曲线
            try:
                anim_curves = cmds.animLayer(layer, query=True, attribute=True)
            except:
                anim_curves = []
                
            # 如果层中没有动画曲线，则删除
            if not anim_curves or len(anim_curves) == 0:
                try:
                    cmds.delete(layer)
                    deleted_layers.append(layer)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 无法删除动画层 {layer}: {str(e)}"))
        
        return deleted_layers

    def checkAndAssignLambert(self, nodes_to_process=None):
        """检查并指定lambert1材质的主函数"""
        self.fix_results_text.append("开始检查模型着色器...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 获取所有变换节点的UUID
        if nodes_to_process is None:
            all_transform_uuids = self.getAllTransformNodesUUIDs()
        else:
            all_transform_uuids = nodes_to_process
        
        # 检查非默认着色器
        non_default_shaders = []
        
        for node in all_transform_uuids:
            node_name = getNodeNameFromUUID(node)
            if node_name and cmds.objExists(node_name):
                try:
                    # 获取形状节点
                    shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True)
                    if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                        shape_node = shapes[0]
                        
                        # 获取着色组
                        shading_engines = cmds.listConnections(shape_node, type='shadingEngine') or []
                        
                        # 检查是否使用了非默认着色器
                        if shading_engines and shading_engines[0] != 'initialShadingGroup':
                            # 获取材质信息
                            materials = cmds.listConnections(shading_engines[0], type='lambert') or []
                            material_name = materials[0] if materials else "未知材质"
                            
                            non_default_shaders.append({
                                "node": node,
                                "node_name": node_name,
                                "shading_engine": shading_engines[0],
                                "material": material_name
                            })
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 检查节点 '{node_name}' 的着色器时出错: {str(e)}"))
        
        assigned_count = 0
        
        if non_default_shaders:
            self.fix_results_text.append(f"发现 {len(non_default_shaders)} 个模型使用了非默认着色器:")
            for info in non_default_shaders:
                self.fix_results_text.append(f"  - '{info['node_name']}' 使用了 '{info['material']}' 材质")
            
            # 确保lambert1材质存在
            if not cmds.objExists('lambert1'):
                try:
                    cmds.shadingNode('lambert', asShader=True, name='lambert1')
                    self.fix_results_text.append("创建了lambert1材质")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 创建lambert1材质时出错: {str(e)}"))
            
            # 确保initialShadingGroup存在
            if not cmds.objExists('initialShadingGroup'):
                try:
                    cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='initialShadingGroup')
                    cmds.connectAttr('lambert1.outColor', 'initialShadingGroup.surfaceShader', force=True)
                    self.fix_results_text.append("创建了initialShadingGroup着色组")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 创建initialShadingGroup着色组时出错: {str(e)}"))
            
            # 为所有使用非默认着色器的模型指定lambert1材质
            for info in non_default_shaders:
                node_name = info["node_name"]
                
                try:
                    # 获取形状节点
                    shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True)
                    if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                        # 将模型指定到initialShadingGroup
                        cmds.sets(shapes[0], edit=True, forceElement='initialShadingGroup')
                        self.fix_results_text.append(f"已将 '{node_name}' 的材质设置为lambert1")
                        assigned_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 为 '{node_name}' 指定lambert1材质时出错: {str(e)}"))
            
            if assigned_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功为 {assigned_count} 个模型指定lambert1材质"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 没有模型需要指定lambert1材质"))
        else:
            self.fix_results_text.append("所有模型都已使用默认着色器(lambert1)")
            
            # 即使所有模型都使用默认着色器，也确保所有模型都使用lambert1
            # 获取所有网格
            if nodes_to_process is None:
                all_meshes = cmds.ls(type='mesh')
            else:
                # 从传入的节点列表中提取网格
                all_meshes = []
                for node_uuid in nodes_to_process:
                    node_name = getNodeNameFromUUID(node_uuid)
                    if node_name and cmds.objExists(node_name):
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True) or []
                        for shape in shapes:
                            if cmds.nodeType(shape) == 'mesh':
                                all_meshes.append(shape)
            
            assigned_count = 0
            
            for mesh in all_meshes:
                try:
                    # 将模型指定到initialShadingGroup
                    cmds.sets(mesh, edit=True, forceElement='initialShadingGroup')
                    assigned_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 为 '{mesh}' 指定lambert1材质时出错: {str(e)}"))
            
            if assigned_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已确认 {assigned_count} 个模型使用lambert1材质"))
        
        return assigned_count

    def checkAndDeleteMeshHistory(self, nodes_to_process=None):
        """检查并删除网格的历史记录"""
        self.fix_results_text.append("开始检查网格历史记录...")
        
        # 如果没有传入节点列表，则获取所有网格节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 使用history函数检查有历史记录的网格节点
        _, history_mesh_uuids = history(nodes_to_process, None)
        
        deleted_count = 0
        if history_mesh_uuids:
            # 转换为节点名称
            mesh_names = []
            for uuid in history_mesh_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    mesh_names.append(node_name)
            
            # 删除所有有历史记录的网格的历史
            for mesh_transform in mesh_names:
                try:
                    # 获取网格形状节点
                    shapes = cmds.listRelatives(mesh_transform, shapes=True, fullPath=True)
                    if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                        mesh_shape = shapes[0]
                        
                        # 获取历史记录
                        history_nodes = cmds.listHistory(mesh_shape)
                        history_count = len(history_nodes)
                        
                        self.fix_results_text.append(f"发现网格 '{mesh_transform}' 有 {history_count-1} 个历史记录节点")
                        
                        # 删除历史记录（保留创建历史）
                        cmds.delete(mesh_shape, constructionHistory=True)
                        self.fix_results_text.append(f"  - 已删除 '{mesh_transform}' 的历史记录")
                        deleted_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 删除网格历史记录 '{mesh_transform}' 时出错: {str(e)}"))
            
            if deleted_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_count} 个网格的历史记录"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 所有网格都没有历史记录"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 所有网格都没有历史记录"))
        
        return deleted_count

    def checkAndFreezeTransforms(self, nodes_to_process=None):
        """检查并冻结未冻结的变换节点"""
        self.fix_results_text.append("开始检查变换节点冻结状态...")
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 使用unfrozenTransforms函数检查未冻结的变换节点
        _, unfrozen_transform_uuids = unfrozenTransforms(nodes_to_process, None)
        
        frozen_count = 0
        if unfrozen_transform_uuids:
            # 转换为节点名称
            transform_names = []
            for uuid in unfrozen_transform_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    transform_names.append(node_name)
            
            # 冻结所有未冻结的变换节点
            for transform in transform_names:
                try:
                    # 检查节点是否为骨骼节点（骨骼节点通常不需要冻结变换）
                    if cmds.objectType(transform) == 'joint':
                        self.fix_results_text.append(f"跳过骨骼节点: {transform}")
                        continue
                    
                    # 获取当前变换值
                    translation = cmds.xform(transform, q=True, worldSpace=True, translation=True)
                    rotation = cmds.xform(transform, q=True, worldSpace=True, rotation=True)
                    scale = cmds.xform(transform, q=True, worldSpace=True, scale=True)
                    
                    self.fix_results_text.append(f"发现未冻结的变换节点: '{transform}'")
                    self.fix_results_text.append(f"  位置: {translation}")
                    self.fix_results_text.append(f"  旋转: {rotation}")
                    self.fix_results_text.append(f"  缩放: {scale}")
                    
                    # 执行冻结变换
                    cmds.makeIdentity(transform, apply=True, translate=True, rotate=True, scale=True)
                    self.fix_results_text.append(f"  - 已冻结 '{transform}' 的变换")
                    frozen_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 冻结变换节点 '{transform}' 时出错: {str(e)}"))
            
            if frozen_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功冻结 {frozen_count} 个变换节点"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 所有变换节点都已冻结"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 所有变换节点都已冻结"))
        
        return frozen_count

    def checkAndCenterPivots(self, nodes_to_process=None):
        """检查并将轴心点移动到世界原点"""
        self.fix_results_text.append("开始检查变换节点轴心点...")
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 使用uncenteredPivots函数检查轴心点不在世界原点的节点
        _, uncentered_pivot_uuids = uncenteredPivots(nodes_to_process, None)
        
        centered_count = 0
        if uncentered_pivot_uuids:
            # 转换为节点名称
            transform_names = []
            for uuid in uncentered_pivot_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    transform_names.append(node_name)
            
            # 将所有轴心点不在世界原点的节点移动到世界原点
            for transform in transform_names:
                try:
                    # 检查节点是否为骨骼节点（骨骼节点通常不需要移动轴心点）
                    if cmds.objectType(transform) == 'joint':
                        self.fix_results_text.append(f"跳过骨骼节点: {transform}")
                        continue
                    
                    # 获取当前轴心点位置
                    pivot_position = cmds.xform(transform, q=True, ws=True, rp=True)
                    
                    self.fix_results_text.append(f"发现轴心点不在世界原点的节点: '{transform}'")
                    self.fix_results_text.append(f"  当前轴心点位置: {pivot_position}")
                    
                    # 将轴心点移动到世界原点
                    cmds.xform(transform, pivots=(0, 0, 0), worldSpace=True)
                    self.fix_results_text.append(f"  - 已将 '{transform}' 的轴心点移动到世界原点")
                    centered_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 移动轴心点 '{transform}' 时出错: {str(e)}"))
            
            if centered_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功将 {centered_count} 个节点的轴心点移动到世界原点"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 所有变换节点的轴心点都已位于世界原点"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 所有变换节点的轴心点都已位于世界原点"))
        
        return centered_count

    def delete_empty_groups(self, nodes_to_process=None):
        """删除场景中所有空的组节点"""
        deleted_groups = []
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            nodes_to_process = cmds.ls(type='transform', uuid=True)
        
        # 使用emptyGroups函数筛选空组
        _, empty_group_uuids = emptyGroups(nodes_to_process, None)
        
        # 将UUID转换为节点名并进一步筛选
        if empty_group_uuids:
            empty_group_names = []
            for uuid in empty_group_uuids:
                node_name = _getNodeName(uuid)
                if node_name:
                    # 排除骨骼节点
                    if cmds.objectType(node_name) == 'joint':
                        self.fix_results_text.append(f"跳过骨骼节点: {node_name}")
                        continue
                        
                    # 排除有特殊属性的节点(如约束、表达式等)
                    if cmds.listConnections(node_name, connections=True, source=True, destination=False):
                        self.fix_results_text.append(f"跳过有连接的节点: {node_name}")
                        continue
                        
                    # 排除有自定义属性的节点
                    if cmds.listAttr(node_name, userDefined=True):
                        self.fix_results_text.append(f"跳过有自定义属性的节点: {node_name}")
                        continue
                        
                    # 确认这是真正的空组(没有子节点)
                    children = cmds.listRelatives(node_name, children=True, fullPath=True)
                    if not children:
                        empty_group_names.append(node_name)
            
            if empty_group_names:
                self.fix_results_text.append("即将删除以下空组：")
                for name in empty_group_names:
                    self.fix_results_text.append(f" - {name}")
                
                # 删除空组
                try:
                    cmds.delete(empty_group_names)
                    deleted_groups = empty_group_names
                    self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {len(empty_group_names)} 个空组"))
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 删除过程中出现错误: {str(e)}"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 没有找到可删除的空组"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有空组"))
        
        return deleted_groups

    def checkAndUnparentGeometry(self, nodes_to_process=None):
        """检查并解除几何体作为其他几何体父级的关系"""
        self.fix_results_text.append("开始检查几何体父子关系...")
        
        def has_mesh_shape(node):
            """检查节点是否有网格形状"""
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            for shape in shapes:
                if cmds.nodeType(shape) == 'mesh':
                    return True
            return False
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            all_transforms = cmds.ls(type='transform')
        else:
            # 将UUID转换为节点名称
            all_transforms = []
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    all_transforms.append(node_name)
        
        parents_with_geo_children = []
        
        for transform in all_transforms:
            # 检查当前变换节点是否有网格
            if not has_mesh_shape(transform):
                continue
            
            # 获取其直接子代（变换节点）
            child_transforms = cmds.listRelatives(transform, children=True, type='transform', fullPath=True) or []
            
            geo_children = []
            for child in child_transforms:
                # 检查子节点是否有网格
                if has_mesh_shape(child):
                    geo_children.append(child)
            
            # 如果存在包含网格的子节点，则记录此父节点及其几何体子节点
            if geo_children:
                parents_with_geo_children.append((transform, geo_children))
        
        # 处理找到的节点
        unparented_count = 0
        if parents_with_geo_children:
            for parent, geo_children in parents_with_geo_children:
                self.fix_results_text.append(f"发现变换节点 '{parent}' 作为以下几何体的父级:")
                for child in geo_children:
                    self.fix_results_text.append(f"  - {child}")
                
                try:
                    # 获取父节点的父节点（祖父节点）
                    grandparent = cmds.listRelatives(parent, parent=True, fullPath=True)
                    
                    if grandparent:
                        # 如果父节点有父节点（在组中），则将子节点移动到祖父节点下
                        cmds.parent(geo_children, grandparent[0])
                        self.fix_results_text.append(f"  已将 {len(geo_children)} 个子级移动到 '{grandparent[0]}' 下")
                    else:
                        # 如果父节点没有父节点（在世界中），则将子节点移动到世界
                        cmds.parent(geo_children, world=True)
                        self.fix_results_text.append(f"  已将 {len(geo_children)} 个子级移动到世界")
                    
                    unparented_count += len(geo_children)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{parent}' 的父子关系时出错: {str(e)}"))
            
            self.fix_results_text.append(self.format_status(f"[OK] 已成功处理 {unparented_count} 个几何体的父子关系"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 没有发现变换节点同时作为其他几何体父级的情况"))
        
        return unparented_count

    def renameNodesWithTrailingNumbers(self, nodes_to_process=None):
        """重命名名称以数字结尾的节点"""
        self.fix_results_text.append("开始检查以数字结尾的节点名称...")
        
        # 如果没有传入节点列表，则获取所有节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 使用trailingNumbers函数检查以数字结尾的节点
        _, trailing_number_uuids = trailingNumbers(nodes_to_process, None)
        
        renamed_count = 0
        if trailing_number_uuids:
            # 转换为节点名称
            node_names = []
            for uuid in trailing_number_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    node_names.append(node_name)
            
            self.fix_results_text.append(f"找到 {len(node_names)} 个以数字结尾的节点:")
            
            # 为所有以数字结尾的节点添加后缀
            for node in node_names:
                try:
                    # 生成新的名称：原名称 + "_reNamePls"
                    new_name = f"{node}_reNamePls"
                    
                    # 确保新名称在场景中是唯一的
                    if cmds.objExists(new_name):
                        # 如果已存在，添加数字后缀
                        counter = 1
                        while cmds.objExists(f"{new_name}_{counter:02d}"):
                            counter += 1
                        new_name = f"{new_name}_{counter:02d}"
                    
                    # 重命名节点
                    cmds.rename(node, new_name)
                    self.fix_results_text.append(f"  - 已将 '{node}' 重命名为 '{new_name}'")
                    renamed_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 重命名节点 '{node}' 时出错: {str(e)}"))
            
            if renamed_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功重命名 {renamed_count} 个以数字结尾的节点"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有找到以数字结尾的节点"))
        
        return renamed_count

    def renameAllDuplicatedNodes(self, nodes_to_process=None):
        """重命名场景中所有名称重复的节点"""
        self.fix_results_text.append("开始检查重复节点名称...")
        
        # 如果没有传入节点列表，则获取所有节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllNodesUUIDs()
        
        # 使用duplicatedNames函数检查重复名称的节点
        _, duplicated_node_uuids = duplicatedNames(nodes_to_process, None)
        
        renamed_dupted_count = 0
        if duplicated_node_uuids:
            # 将重复节点的UUID转换为节点名称并按名称分组
            duplicated_nodes_by_name = {}
            for uuid in duplicated_node_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    short_name = node_name.rsplit('|', 1)[-1]
                    if short_name not in duplicated_nodes_by_name:
                        duplicated_nodes_by_name[short_name] = []
                    duplicated_nodes_by_name[short_name].append(node_name)
            
            # 为每个重复名称的所有节点添加后缀
            for short_name, nodes in duplicated_nodes_by_name.items():
                if len(nodes) > 1:
                    self.fix_results_text.append(f"发现重复名称 '{short_name}'，共有 {len(nodes)} 个节点:")
                    
                    # 为所有重复节点重命名（包括第一个）
                    for i, node in enumerate(nodes):
                        try:
                            # 生成新的名称：原名称 + "_" + 数字（从00到99） + "_reNamePls"
                            new_name = f"{short_name}_{i:02d}_reNamePls"
                            
                            # 确保新名称在场景中是唯一的
                            if cmds.objExists(new_name):
                                # 如果已存在，添加更多后缀
                                counter = 1
                                while cmds.objExists(f"{new_name}_{counter:02d}"):
                                    counter += 1
                                new_name = f"{new_name}_{counter:02d}"
                            
                            # 重命名节点
                            cmds.rename(node, new_name)
                            self.fix_results_text.append(f"  - 已将 '{node}' 重命名为 '{new_name}'")
                            renamed_dupted_count += 1
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"[ERR] 重命名节点 '{node}' 时出错: {e}"))
            
            if renamed_dupted_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功重命名 {renamed_dupted_count} 个重复节点"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有找到名称重复的节点"))
        
        return renamed_dupted_count

    def deleteAllEmptyNamespaces(self, nodes_to_process=None):
        """删除所有空的命名空间，但跳过UI和shared命名空间"""
        
        # 获取所有命名空间
        def getAllNamespaces():
            """获取场景中的所有命名空间"""
            try:
                # 获取所有命名空间（包括递归子命名空间）
                namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
                # 添加根命名空间
                namespaces.insert(0, ":")
                return namespaces
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 获取命名空间时出错: {e}"))
                return []

        # 删除命名空间
        def removeNamespace(namespace):
            """安全地删除命名空间"""
            try:
                # 确保不是根命名空间和默认命名空间
                if namespace == ":" or namespace == "" or namespace in ["UI", "shared"]:
                    self.fix_results_text.append(f"跳过默认命名空间: {namespace}")
                    return False
                    
                # 检查命名空间是否存在
                if not cmds.namespace(exists=namespace):
                    self.fix_results_text.append(f"命名空间 '{namespace}' 不存在，跳过删除")
                    return False
                    
                # 检查命名空间是否为空
                try:
                    nodes_in_ns = cmds.namespaceInfo(namespace, listNamespace=True)
                    # 修复: 处理返回None的情况
                    if nodes_in_ns is None:
                        nodes_in_ns = []
                        
                    if nodes_in_ns:
                        self.fix_results_text.append(f"命名空间 '{namespace}' 不为空，包含 {len(nodes_in_ns)} 个节点，跳过删除")
                        return False
                except Exception as e:
                    # 如果无法列出节点，假设命名空间不为空
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法获取命名空间 '{namespace}' 的节点信息，可能不为空，跳过删除: {str(e)}"))
                    return False
                    
                # 删除命名空间
                cmds.namespace(removeNamespace=namespace)
                self.fix_results_text.append(f"已删除命名空间: {namespace}")
                return True
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 删除命名空间 '{namespace}' 时出错: {str(e)}"))
                return False

        # 重命名节点以移除命名空间
        def removeNamespaceFromNodes():
            """移除所有节点上的命名空间"""
            # 获取所有包含命名空间的节点
            if nodes_to_process:
                # 如果有指定的节点列表，只处理这些节点
                all_nodes = [getNodeNameFromUUID(uuid) for uuid in nodes_to_process if cmds.objExists(getNodeNameFromUUID(uuid))]
            else:
                # 如果没有指定节点列表，处理所有节点
                all_nodes = cmds.ls()
                
            renamed_count = 0
            
            for node in all_nodes:
                if ':' in node:
                    try:
                        # 获取不带命名空间的名称
                        new_name = node.split(':')[-1]
                        
                        # 确保新名称在场景中是唯一的
                        if cmds.objExists(new_name):
                            # 如果已存在，添加后缀
                            counter = 1
                            while cmds.objExists(f"{new_name}_{counter}"):
                                counter += 1
                            new_name = f"{new_name}_{counter}"
                        
                        # 重命名节点
                        cmds.rename(node, new_name)
                        renamed_count += 1
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[ERR] 重命名节点 {node} 时出错: {e}"))
            
            return renamed_count

        # 开始执行删除操作
        self.fix_results_text.append("开始删除空命名空间...")
        
        # 首先移除节点上的命名空间
        self.fix_results_text.append("正在移除节点上的命名空间...")
        renamed_count = removeNamespaceFromNodes()
        self.fix_results_text.append(self.format_status(f"[OK] 已移除 {renamed_count} 个节点上的命名空间"))
        
        # 获取所有命名空间
        all_namespaces = getAllNamespaces()
        
        # 过滤出非根命名空间
        non_root_namespaces = [ns for ns in all_namespaces if ns != ":"]
        
        # 删除空的命名空间
        deleted_namespace_count = 0
        if non_root_namespaces:
            self.fix_results_text.append("\n找到以下命名空间:")
            for ns in non_root_namespaces:
                # 检查命名空间是否为空
                try:
                    # 首先检查命名空间是否存在
                    if not cmds.namespace(exists=ns):
                        self.fix_results_text.append(f" - {ns} (命名空间不存在，跳过)")
                        continue
                        
                    # 尝试获取命名空间中的节点
                    nodes_in_ns = cmds.namespaceInfo(ns, listNamespace=True) if cmds.namespace(exists=ns) else []
                    
                    # 修复: 处理返回None的情况
                    if nodes_in_ns is None:
                        nodes_in_ns = []
                        
                    self.fix_results_text.append(f" - {ns} (包含 {len(nodes_in_ns)} 个节点)")
                    
                    # 直接删除空的命名空间
                    if not nodes_in_ns:
                        if removeNamespace(ns):
                            deleted_namespace_count += 1
                except Exception as e:
                    self.fix_results_text.append(f" - {ns} (检查命名空间时出错: {str(e)})")
            
            self.fix_results_text.append(self.format_status(f"\n[OK] 已成功删除 {deleted_namespace_count} 个命名空间"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有找到任何非根命名空间"))
        
        return deleted_namespace_count

    def checkAndRenameShapeNodes(self, nodes_to_process=None):
        """检查并重命名形状节点以符合Maya默认约定"""
        self.fix_results_text.append("开始检查形状节点命名...")
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 使用shapeNames函数检查不符合约定的形状节点
        _, non_conforming_shape_uuids = shapeNames(nodes_to_process, None)
        
        renamed_shape_count = 0
        if non_conforming_shape_uuids:
            # 转换为节点名称
            transform_names = []
            for uuid in non_conforming_shape_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    transform_names.append(node_name)
            
            # 检查每个变换节点的形状节点命名
            for transform in transform_names:
                try:
                    # 获取变换节点的非中间体形状节点
                    shapes = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True)
                    if shapes:
                        # 获取变换节点的短名称（不含路径）
                        transform_short_name = transform.split('|')[-1]
                        
                        for shape in shapes:
                            # 获取形状节点的短名称
                            shape_short_name = shape.split('|')[-1]
                            
                            # 检查形状节点名称是否符合约定
                            expected_shape_name = f"{transform_short_name}Shape"
                            if shape_short_name != expected_shape_name:
                                self.fix_results_text.append(f"发现不符合约定的形状节点: '{shape_short_name}' (应为 '{expected_shape_name}')")
                                
                                # 确保新名称在场景中是唯一的
                                new_name = expected_shape_name
                                if cmds.objExists(new_name):
                                    # 如果已存在，添加数字后缀
                                    counter = 1
                                    while cmds.objExists(f"{new_name}{counter}"):
                                        counter += 1
                                    new_name = f"{new_name}{counter}"
                                
                                # 重命名形状节点
                                cmds.rename(shape, new_name)
                                self.fix_results_text.append(f"  - 已将 '{shape_short_name}' 重命名为 '{new_name}'")
                                renamed_shape_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理变换节点 '{transform}' 时出错: {e}"))
            
            if renamed_shape_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功重命名 {renamed_shape_count} 个形状节点"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 所有形状节点都符合Maya的默认命名约定"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 所有形状节点都符合Maya的默认命名约定"))
        
        return renamed_shape_count

    def delete_all_lights(self, nodes_to_process=None):
        """
        删除Maya场景中的所有灯光对象
        """
        # 清空之前的处理结果
        self.fix_results_text.clear()
        self.fix_results_text.append("开始删除所有灯光...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 如果没有传入节点列表，则获取场景中所有灯光
        if nodes_to_process is None:
            # 获取所有灯光形状节点
            all_lights_shapes = cmds.ls(type='light')
        else:
            # 从传入的节点列表中筛选出灯光
            all_lights_shapes = []
            for node_uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(node_uuid)
                if node_name and cmds.objExists(node_name):
                    # 检查节点是否为灯光类型
                    if cmds.objectType(node_name, isa='light'):
                        all_lights_shapes.append(node_name)
                    else:
                        # 检查节点是否有灯光形状子节点
                        shapes = cmds.listRelatives(node_name, shapes=True, type='light') or []
                        all_lights_shapes.extend(shapes)
        
        if not all_lights_shapes:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有找到灯光。"))
            return 0
        
        # 获取每个灯光形状节点的变换节点（父节点）
        # 因为通常我们操作和删除的是变换节点
        all_lights_transforms = []
        for light_shape in all_lights_shapes:
            light_transform = cmds.listRelatives(light_shape, parent=True, fullPath=True)
            if light_transform:
                all_lights_transforms.extend(light_transform)
        
        # 使用集合去重（防止某些特殊情况下的重复）
        all_lights_transforms = list(set(all_lights_transforms))
        
        if not all_lights_transforms:
            self.fix_results_text.append(self.format_status(f"[WARN] 未找到要删除的灯光变换节点。"))
            return 0
            
        self.fix_results_text.append(f"找到 {len(all_lights_transforms)} 个灯光:")
        
        # 列出所有要删除的灯光名称
        for light in all_lights_transforms:
            self.fix_results_text.append(f"  - {light}")
        
        self.fix_results_text.append("正在删除...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 逐个删除灯光变换节点（这会同时删除形状节点）
        try:
            cmds.delete(all_lights_transforms)
            self.fix_results_text.append(self.format_status(f"[OK] 成功删除 {len(all_lights_transforms)} 个灯光。"))
            return len(all_lights_transforms)  # 返回删除的灯光数量
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 删除灯光时发生错误: {e}"))
            return 0  # 发生错误时返回0

    def delete_extra_cameras(self, nodes_to_process=None):
        """
        删除场景中所有非默认摄像机（默认摄像机包括: persp, top, front, side）
        """
        # 定义要保留的默认摄像机名称
        default_cams = ['persp', 'top', 'front', 'side']
        
        # 如果没有传入节点列表，则获取场景中所有摄像机
        if nodes_to_process is None:
            # 获取所有摄像机形状节点
            all_cameras = cmds.ls(type='camera')
        else:
            # 从传入的节点列表中筛选出摄像机
            all_cameras = []
            for node_uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(node_uuid)
                if node_name and cmds.objExists(node_name):
                    # 检查节点是否为摄像机类型
                    if cmds.objectType(node_name, isa='camera'):
                        all_cameras.append(node_name)
                    else:
                        # 检查节点是否有摄像机形状子节点
                        shapes = cmds.listRelatives(node_name, shapes=True, type='camera') or []
                        all_cameras.extend(shapes)
        
        if not all_cameras:
            self.fix_results_text.append(self.format_status(f"[OK] 场景中没有找到摄像机。"))
            return 0
        
        # 提取摄像机变换节点（通常我们需要操作的是变换节点）
        camera_transforms = []
        for cam in all_cameras:
            # 获取摄像机的变换节点
            transform = cmds.listRelatives(cam, parent=True, fullPath=True)
            if transform:
                camera_transforms.append(transform[0])
        
        # 使用集合去重（防止某些特殊情况下的重复）
        camera_transforms = list(set(camera_transforms))
        
        # 找出需要删除的非默认摄像机
        cameras_to_delete = []
        for cam_transform in camera_transforms:
            # 获取短名称（不包含路径）
            short_name = cam_transform.split('|')[-1]
            
            # 检查是否为默认摄像机
            if short_name not in default_cams:
                cameras_to_delete.append(cam_transform)
        
        # 如果没有需要删除的摄像机，则退出
        if not cameras_to_delete:
            self.fix_results_text.append(self.format_status(f"[OK] 没有找到需要删除的非默认摄像机。"))
            return 0
            
        self.fix_results_text.append(f"找到 {len(cameras_to_delete)} 个非默认摄像机:")
        
        # 列出所有要删除的摄像机名称
        for cam in cameras_to_delete:
            self.fix_results_text.append(f"  - {cam}")
        
        self.fix_results_text.append("正在删除...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 尝试删除非默认摄像机
        deleted_camera_count = 0
        for cam in cameras_to_delete:
            try:
                # 特殊处理：如果摄像机被设置为启动摄像机，需要先取消该设置
                try:
                    if cmds.camera(cam, query=True, startupCamera=True):
                        cmds.camera(cam, edit=True, startupCamera=False)
                        self.fix_results_text.append(f"已移除摄像机 {cam} 的启动摄像机属性")
                except:
                    pass  # 如果查询失败，继续尝试删除
                
                # 删除摄像机
                cmds.delete(cam)
                self.fix_results_text.append(f"已成功删除摄像机: {cam}")
                deleted_camera_count += 1
                
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 删除摄像机 {cam} 时出错: {str(e)}"))
        
        self.fix_results_text.append(self.format_status(f"[OK] 成功删除了 {deleted_camera_count} 个非默认摄像机。"))
        return deleted_camera_count

    def deleteKeyframes(self, nodes_to_process=None):
        """删除场景中的关键帧"""
        self.fix_results_text.append("开始检查场景内的关键帧...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 如果没有传入节点列表，则获取所有变换节点
        if nodes_to_process is None:
            nodes_to_process = self.getAllTransformNodesUUIDs()
        
        # 检查关键帧
        _, keyframe_uuids = checkKeyframes(nodes_to_process, None)
        
        deleted_keyframe_count = 0
        if keyframe_uuids:
            # 转换为节点名称
            node_names = []
            for uuid in keyframe_uuids:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    node_names.append(node_name)
            
            self.fix_results_text.append(f"找到 {len(node_names)} 个有关键帧的节点:")
            
            # 列出所有要处理的节点名称
            for node in node_names:
                self.fix_results_text.append(f"  - {node}")
            
            self.fix_results_text.append("正在删除关键帧...")
            QtCore.QCoreApplication.processEvents()  # 更新UI
            
            # 尝试删除关键帧
            for node in node_names:
                try:
                    # 获取节点的动画曲线
                    anim_curves = cmds.listConnections(node, 
                                                    type='animCurve', 
                                                    source=True, 
                                                    destination=False) or []
                    
                    if anim_curves:
                        # 获取关键帧数量
                        keyframe_count = 0
                        for curve in anim_curves:
                            keytimes = cmds.keyframe(curve, query=True, timeChange=True) or []
                            keyframe_count += len(keytimes)
                        
                        self.fix_results_text.append(f"发现节点 '{node}' 有 {keyframe_count} 个关键帧")
                        
                        # 删除所有动画曲线
                        cmds.delete(anim_curves)
                        self.fix_results_text.append(f"  - 已删除 '{node}' 的所有关键帧")
                        deleted_keyframe_count += keyframe_count
                    else:
                        self.fix_results_text.append(f"节点 '{node}' 没有找到动画曲线")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 删除 '{node}' 的关键帧时出错: {str(e)}"))
            
            if deleted_keyframe_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_keyframe_count} 个关键帧"))
            else:
                self.fix_results_text.append(self.format_status(f"[WARN] 没有关键帧需要删除"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 场景内没有关键帧"))
        
        return deleted_keyframe_count

    def checkAndDeleteTriangles(self, nodes_to_process=None):
        """检查并删除三角形面，支持处理选中的模型"""
        self.fix_results_text.append("开始检查三角形面...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                except:
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    # 直接检查节点是否为网格
                    if cmds.nodeType(node_name) == 'mesh':
                        try:
                            mesh_selection.add(node_name)
                        except:
                            continue
                    else:
                        # 如果是变换节点，获取其网格形状
                        shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                        for shape in shapes:
                            if cmds.objExists(shape):
                                try:
                                    mesh_selection.add(shape)
                                except:
                                    continue
        
        # 使用triangles函数检查三角形面
        result_type, triangles_info = triangles(None, mesh_selection)
        
        deleted_triangles_count = 0
        
        if triangles_info:            
            # 遍历所有有三角形面的网格
            for uuid, face_indices in triangles_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(face_indices)} 个三角形面")
                    
                    try:
                        # 获取形状节点（处理可能的层级路径）
                        if cmds.nodeType(node_name) == 'transform':
                            # 如果是变换节点，获取其形状节点
                            shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                            if not shapes or len(shapes) == 0:
                                self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                                continue
                            shape_node = shapes[0]
                        else:
                            # 已经是形状节点
                            shape_node = node_name
                            
                        # 清除历史记录，确保面索引正确
                        cmds.select(node_name)
                        cmds.delete(ch=True)  # 只删除构造历史，保留对象
                        
                        # 构建面选择列表并确保面存在
                        faces_to_delete = []
                        for face_index in face_indices:
                            face_name = f"{shape_node}.f[{face_index}]"
                            if cmds.objExists(face_name):
                                faces_to_delete.append(face_name)
                            else:
                                self.fix_results_text.append(self.format_status(f"[WARN] 面 {face_name} 不存在"))
                        
                        # 删除三角形面
                        if faces_to_delete:
                            # 先取消所有选择
                            cmds.select(clear=True)
                            
                            # 选择要删除的面
                            cmds.select(faces_to_delete, add=True)
                            
                            # 执行删除操作
                            cmds.delete()
                            deleted_triangles_count += len(faces_to_delete)
                            self.fix_results_text.append(f"  - 已删除 {len(faces_to_delete)} 个三角形面")
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的三角形面"))
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[ERR] 删除 '{node_name}' 的三角形面时出错: {e}"))
            
            if deleted_triangles_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_triangles_count} 个三角形面"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有三角形面需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现三角形面"))
        
        return deleted_triangles_count  # 返回删除的三角形面数量

    def checkAndDeleteNgons(self, nodes_to_process=None):
        """检查并删除边数大于4的多边形面（N边形），支持处理选中的模型"""
        self.fix_results_text.append("开始检查N边形面...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 失败: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    continue
                    
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 失败: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(
                        node_name, 
                        shapes=True, 
                        type='mesh', 
                        fullPath=True
                    ) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 失败: {str(e)}"))
                                continue
        
        # 使用ngons函数检查N边形面
        result_type, ngons_info = ngons(None, mesh_selection)
        
        deleted_ngons_count = 0
        
        if ngons_info:            
            # 遍历所有有N边形面的网格
            for uuid, face_indices in ngons_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    continue
                    
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(face_indices)} 个N边形面")
                
                try:
                    # 获取形状节点（处理可能的层级路径）
                    if cmds.nodeType(node_name) == 'transform':
                        # 如果是变换节点，获取其形状节点
                        shapes = cmds.listRelatives(
                            node_name, 
                            shapes=True, 
                            fullPath=True, 
                            type='mesh'
                        )
                        if not shapes:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    else:
                        # 已经是形状节点
                        shape_node = node_name
                        
                    # 清除历史记录，确保面索引正确
                    cmds.delete(node_name, ch=True)  # 直接删除构造历史，无需先选择
                    
                    # 构建面选择列表并确保面存在
                    faces_to_delete = [
                        f"{shape_node}.f[{idx}]" 
                        for idx in face_indices 
                        if cmds.objExists(f"{shape_node}.f[{idx}]")
                    ]
                    
                    # 记录不存在的面
                    missing_faces = len(face_indices) - len(faces_to_delete)
                    if missing_faces > 0:
                        self.fix_results_text.append(self.format_status(f"[WARN] 有 {missing_faces} 个面不存在"))
                    
                    # 删除N边形面
                    if faces_to_delete:
                        # 直接删除面，无需显式选择
                        cmds.delete(faces_to_delete)
                        deleted_ngons_count += len(faces_to_delete)
                        self.fix_results_text.append(f"  - 已删除 {len(faces_to_delete)} 个N边形面")
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的N边形面"))
                        
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 删除 '{node_name}' 的N边形面时出错: {str(e)}"))
            
            if deleted_ngons_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_ngons_count} 个N边形面"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有N边形面需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现N边形面"))
        
        return deleted_ngons_count  # 返回删除的N边形面数量

    def checkAndSoftenHardEdges(self, nodes_to_process=None):
        """检查并软化非边界硬边，支持处理选中的模型"""
        self.fix_results_text.append("开始检查非边界硬边...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 失败: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    continue
                    
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 失败: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(
                        node_name, 
                        shapes=True, 
                        type='mesh', 
                        fullPath=True
                    ) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 失败: {str(e)}"))
                                continue
        
        # 使用hardEdges函数检查非边界硬边
        result_type, hard_edges_info = hardEdges(None, mesh_selection)
        
        softened_hard_edges_count = 0
        
        if hard_edges_info:            
            # 遍历所有有非边界硬边的网格
            for uuid, edge_indices in hard_edges_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    continue
                    
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(edge_indices)} 条非边界硬边")
                
                try:
                    # 获取形状节点（处理可能的层级路径）
                    if cmds.nodeType(node_name) == 'transform':
                        # 如果是变换节点，获取其形状节点
                        shapes = cmds.listRelatives(
                            node_name, 
                            shapes=True, 
                            fullPath=True, 
                            type='mesh'
                        )
                        if not shapes:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    else:
                        # 已经是形状节点
                        shape_node = node_name
                        
                    # 清除历史记录，确保边索引正确
                    cmds.delete(node_name, ch=True)  # 直接删除构造历史，无需先选择
                    
                    # 构建边选择列表并确保边存在
                    edges_to_soften = [
                        f"{shape_node}.e[{idx}]" 
                        for idx in edge_indices 
                        if cmds.objExists(f"{shape_node}.e[{idx}]")
                    ]
                    
                    # 记录不存在的边
                    missing_edges = len(edge_indices) - len(edges_to_soften)
                    if missing_edges > 0:
                        self.fix_results_text.append(self.format_status(f"[WARN] 有 {missing_edges} 条边不存在"))
                    
                    # 软化非边界硬边（而不是删除）
                    if edges_to_soften:
                        # 先选择要软化的边
                        cmds.select(edges_to_soften, replace=True)
                        
                        # 使用Maya的软化边命令，设置角度为180度以完全软化
                        cmds.polySoftEdge(edges_to_soften, angle=180, constructionHistory=False)
                        
                        softened_hard_edges_count += len(edges_to_soften)
                        self.fix_results_text.append(f"  - 已软化 {len(edges_to_soften)} 条非边界硬边")
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的非边界硬边"))
                        
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 软化 '{node_name}' 的非边界硬边时出错: {str(e)}"))
            
            if softened_hard_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功软化 {softened_hard_edges_count} 条非边界硬边"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有非边界硬边需要软化"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现非边界硬边"))
        
        return softened_hard_edges_count  # 返回软化的非边界硬边数量

    def checkAndDeleteHalfLaminaFaces_main(self, nodes_to_process=None):
        """检查并删除重叠面（lamina faces）主方法，支持处理选中的模型"""
        self.fix_results_text.append("开始检查重叠面...")
        
        # 创建网格选择列表的内部函数
        def createMeshSelectionList():
            mesh_selection = om.MSelectionList()
            
            if nodes_to_process is None:
                # 如果没有传入节点列表，则获取所有网格
                all_meshes = cmds.ls(type='mesh')
                for mesh in all_meshes:
                    try:
                        mesh_selection.add(mesh)
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 失败: {str(e)}"))
                        continue
            else:
                # 处理传入的节点列表，只添加其中的网格
                for uuid in nodes_to_process:
                    node_name = getNodeNameFromUUID(uuid)
                    if not node_name or not cmds.objExists(node_name):
                        continue
                        
                    # 检查节点是否为网格
                    if cmds.nodeType(node_name) == 'mesh':
                        try:
                            mesh_selection.add(node_name)
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 失败: {str(e)}"))
                            continue
                    else:
                        # 如果是变换节点，获取其网格形状
                        shapes = cmds.listRelatives(
                            node_name, 
                            shapes=True, 
                            type='mesh', 
                            fullPath=True
                        ) or []
                        for shape in shapes:
                            if cmds.objExists(shape):
                                try:
                                    mesh_selection.add(shape)
                                except Exception as e:
                                    self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 失败: {str(e)}"))
                                    continue
            return mesh_selection
        
        # 查找成对的重叠面的内部函数
        def findLaminaPairs(mesh_name, lamina_face_indices):
            """查找成对的重叠面"""
            # 获取所有面的顶点信息
            face_vertices = {}
            for face_idx in lamina_face_indices:
                face_name = f"{mesh_name}.f[{face_idx}]"
                if not cmds.objExists(face_name):
                    self.fix_results_text.append(self.format_status(f"[WARN] 面 {face_name} 不存在"))
                    continue
                try:
                    vertices = cmds.polyListComponentConversion(face_name, fromFace=True, toVertex=True)
                    vertices = cmds.filterExpand(vertices, selectionMask=31)
                    face_vertices[face_idx] = set(vertices)
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 获取面 {face_idx} 的顶点信息失败: {str(e)}"))
            
            # 查找共享相同顶点的面对
            pairs = []
            processed = set()
            
            for i, face_idx1 in enumerate(lamina_face_indices):
                if face_idx1 in processed or face_idx1 not in face_vertices:
                    continue
                    
                for j, face_idx2 in enumerate(lamina_face_indices[i+1:], i+1):
                    if face_idx2 in processed or face_idx2 not in face_vertices:
                        continue
                        
                    # 检查两个面是否共享所有顶点
                    if face_vertices[face_idx1] == face_vertices[face_idx2]:
                        pairs.append((face_idx1, face_idx2))
                        processed.add(face_idx1)
                        processed.add(face_idx2)
                        break
            
            # 添加未配对的面（如果有）
            for face_idx in lamina_face_indices:
                if face_idx not in processed and face_idx in face_vertices:
                    self.fix_results_text.append(self.format_status(f"[WARN] 面 {face_idx} 没有找到配对的重叠面"))
            
            return pairs
        
        # 删除指定面的内部辅助函数
        def deleteFacesWithCommands(shape_node, face_indices):
            """使用Maya命令删除指定的面"""
            try:
                # 构建面选择列表
                faces_to_delete = [f"{shape_node}.f[{idx}]" for idx in face_indices if cmds.objExists(f"{shape_node}.f[{idx}]")]
                
                if not faces_to_delete:
                    self.fix_results_text.append(self.format_status("[WARN] 没有找到有效的面进行删除"))
                    return False
                    
                # 清除历史记录，确保面索引正确
                cmds.delete(shape_node, ch=True)
                
                # 执行删除操作
                cmds.select(faces_to_delete, replace=True)
                cmds.delete()
                return True
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 删除面时出错: {str(e)}"))
                return False
        
        # 创建网格选择列表
        mesh_selection = createMeshSelectionList()
        
        # 使用lamina函数检查重叠面
        result_type, lamina_info = lamina(None, mesh_selection)
        
        deleted_lumina_count = 0
        
        if lamina_info:
            # 遍历所有有重叠面的网格
            for uuid, face_indices in lamina_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    continue
                    
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(face_indices)} 个重叠面")
                
                try:
                    # 获取形状节点（处理可能的层级路径）
                    if cmds.nodeType(node_name) == 'transform':
                        # 如果是变换节点，获取其形状节点
                        shapes = cmds.listRelatives(
                            node_name, 
                            shapes=True, 
                            fullPath=True, 
                            type='mesh'
                        )
                        if not shapes:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    else:
                        # 已经是形状节点
                        shape_node = node_name
                        
                    # 清除历史记录，确保面索引正确
                    cmds.delete(node_name, ch=True)
                    
                    # 查找成对的重叠面
                    lamina_pairs = findLaminaPairs(shape_node, face_indices)
                    self.fix_results_text.append(f"  找到 {len(lamina_pairs)} 对重叠面")
                    
                    # 从每对中随机选择一个面删除
                    faces_to_delete = []
                    for pair in lamina_pairs:
                        # 随机选择一对中的一个面删除
                        face_to_delete = random.choice(pair)
                        faces_to_delete.append(face_to_delete)
                    
                    # 删除选择的面
                    if faces_to_delete:
                        if deleteFacesWithCommands(shape_node, faces_to_delete):
                            deleted_lumina_count += len(faces_to_delete)
                            self.fix_results_text.append(f"  - 已删除 {len(faces_to_delete)} 个重叠面（每对中随机选择一个）")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{node_name}' 的重叠面时出错: {str(e)}"))
            
            if deleted_lumina_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_lumina_count} 个重叠面（每对重叠面中随机删除一个）"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有重叠面需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现重叠面"))
        
        return deleted_lumina_count  # 返回删除的重叠面数量

    def checkAndDeleteZeroAreaFaces(self, nodes_to_process=None):
        """检查并删除面积接近零的面，支持处理选中的模型"""
        self.fix_results_text.append("开始检查面积接近零的面...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                    self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法添加网格 {mesh} 到检查列表: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 直接检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                        self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 无法添加网格 {node_name} 到检查列表: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                                self.fix_results_text.append(f"添加形状到检查列表: {shape}")
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 无法添加形状 {shape} 到检查列表: {str(e)}"))
                                continue
        
        # 验证选择列表是否有内容
        if mesh_selection.length() == 0:
            self.fix_results_text.append(self.format_status("[WARN] 检查列表中没有任何网格或形状节点"))
            return 0
        
        # 使用zeroAreaFaces函数检查面积接近零的面
        try:
            result_type, zero_area_info = zeroAreaFaces(None, mesh_selection)
            self.fix_results_text.append(f"零面积面检查完成，发现 {len(zero_area_info)} 个有问题的网格")
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 执行零面积面检查时出错: {str(e)}"))
            return 0
        
        deleted_ZeroAreaFaces_count = 0
        total_attempted = 0
        
        if zero_area_info:
            # 遍历所有有面积接近零的面的网格
            for uuid, face_indices in zero_area_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 无法解析 UUID {uuid} 对应的节点名称"))
                    continue
                    
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(face_indices)} 个面积接近零的面")
                total_attempted += len(face_indices)
                
                try:
                    # 获取形状节点（处理可能的层级路径）
                    if cmds.nodeType(node_name) == 'transform':
                        # 如果是变换节点，获取其形状节点
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                        if not shapes or len(shapes) == 0:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    else:
                        # 已经是形状节点
                        shape_node = node_name
                        
                    # 清除历史记录前先记录原始面索引
                    original_face_indices = face_indices.copy()
                    
                    # 清除历史记录，确保面索引正确
                    self.fix_results_text.append(f"  - 清除 '{node_name}' 的构造历史")
                    cmds.delete(node_name, ch=True)  # 直接删除构造历史，无需先选择
                    
                    # 重新获取零面积面，因为清除历史可能改变面索引
                    try:
                        temp_selection = om.MSelectionList()
                        temp_selection.add(shape_node)
                        _, updated_zero_area = zeroAreaFaces(None, temp_selection)
                        if updated_zero_area and uuid in updated_zero_area:
                            face_indices = updated_zero_area[uuid]
                            self.fix_results_text.append(f"  - 清除历史后更新面索引，现在有 {len(face_indices)} 个面积接近零的面")
                        else:
                            self.fix_results_text.append(f"  - 清除历史后面索引未更新，使用原始索引")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 更新面索引时出错: {str(e)}，将使用原始索引"))
                    
                    # 保存原始面数量用于后续验证
                    original_face_count = cmds.polyEvaluate(shape_node, face=True)
                    
                    # 构建面选择列表并确保面存在
                    faces_to_delete = []
                    for face_index in face_indices:
                        face_name = f"{shape_node}.f[{face_index}]"
                        if cmds.objExists(face_name):
                            faces_to_delete.append(face_name)
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 面 {face_name} 不存在，跳过删除"))
                    
                    # 删除面积接近零的面
                    if faces_to_delete:
                        # 执行删除操作，不依赖显式选择
                        self.fix_results_text.append(f"  - 准备删除 {len(faces_to_delete)} 个面积接近零的面")
                        
                        # 方法1: 直接删除
                        cmds.delete(faces_to_delete)
                        
                        # 验证删除结果 - 比较删除前后的面数量
                        new_face_count = cmds.polyEvaluate(shape_node, face=True)
                        deleted_by_count = original_face_count - new_face_count
                        
                        if deleted_by_count > 0:
                            self.fix_results_text.append(f"  - 通过面数量变化确认: 成功删除 {deleted_by_count} 个面")
                            deleted_ZeroAreaFaces_count += deleted_by_count
                            continue
                        else:
                            self.fix_results_text.append(f"  - 面数量未发生变化，删除可能未成功")
                        
                        # 方法2: 尝试先解除可能的约束
                        self.fix_results_text.append(f"  - 尝试解除约束和连接...")
                        for face in faces_to_delete:
                            # 查找并删除相关约束
                            constraints = cmds.listConnections(face, type='constraint') or []
                            for constraint in constraints:
                                self.fix_results_text.append(f"  - 移除约束: {constraint}")
                                cmds.delete(constraint)
                            
                            # 断开输入连接
                            inputs = cmds.listConnections(face, destination=False, source=True) or []
                            for input_node in inputs:
                                if cmds.nodeType(input_node) not in ['transform', 'mesh']:
                                    self.fix_results_text.append(f"  - 断开连接: {input_node}")
                                    cmds.disconnectAttr(f"{input_node}.output", f"{face}.inMesh")
                        
                        # 再次尝试删除
                        cmds.delete(faces_to_delete)
                        
                        # 再次验证删除结果
                        new_face_count = cmds.polyEvaluate(shape_node, face=True)
                        deleted_by_count = original_face_count - new_face_count
                        
                        if deleted_by_count > 0:
                            self.fix_results_text.append(f"  - 解除约束后: 成功删除 {deleted_by_count} 个面")
                            deleted_ZeroAreaFaces_count += deleted_by_count
                            continue
                        else:
                            self.fix_results_text.append(f"  - 解除约束后面数量仍未变化")
                        
                        # 方法3: 使用替代选择方式删除
                        self.fix_results_text.append(f"  - 尝试使用替代方法删除剩余面...")
                        try:
                            # 切换选择模式为面模式
                            cmds.selectMode(component=True)
                            cmds.selectType(facet=True)
                            
                            # 选择面并删除
                            cmds.select(faces_to_delete, replace=True)
                            cmds.delete()
                            
                            # 最后验证删除结果
                            new_face_count = cmds.polyEvaluate(shape_node, face=True)
                            deleted_by_count = original_face_count - new_face_count
                            
                            if deleted_by_count > 0:
                                self.fix_results_text.append(f"  - 替代方法成功删除 {deleted_by_count} 个面")
                                deleted_ZeroAreaFaces_count += deleted_by_count
                            else:
                                self.fix_results_text.append(self.format_status(f"[WARN] 所有方法均无法删除面"))
                                # 最后的验证：检查是否还有零面积面
                                _, final_zero_area = zeroAreaFaces(None, temp_selection)
                                if final_zero_area and uuid in final_zero_area and len(final_zero_area[uuid]) > 0:
                                    self.fix_results_text.append(f"  - 确认仍有 {len(final_zero_area[uuid])} 个零面积面")
                                else:
                                    self.fix_results_text.append(f"  - 零面积面已被删除，但面索引已改变")
                                    deleted_ZeroAreaFaces_count += len(faces_to_delete)
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"[ERR] 替代删除方法失败: {str(e)}"))
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的面积接近零的面进行删除"))
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{node_name}' 的面积接近零的面时出错: {str(e)}"))
            
            # 智能结果报告
            if deleted_ZeroAreaFaces_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_ZeroAreaFaces_count} 个面积接近零的面"))
                if deleted_ZeroAreaFaces_count < total_attempted:
                    self.fix_results_text.append(self.format_status(f"[WARN] 注意: 共有 {total_attempted - deleted_ZeroAreaFaces_count} 个面未能删除"))
            else:
                if total_attempted > 0:
                    self.fix_results_text.append(self.format_status(f"[WARN] 所有 {total_attempted} 个面积接近零的面均未能删除"))
                else:
                    self.fix_results_text.append(self.format_status("[OK] 没有面积接近零的面需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现面积接近零的面"))
        
        return deleted_ZeroAreaFaces_count  # 返回删除的面积接近零的面数量

    # 检查并删除长度接近零的边
    def checkAndDeleteZeroLengthEdges(self, nodes_to_process=None):
        """检查并删除长度接近零的边，支持处理选中的模型"""
        self.fix_results_text.append("开始检查长度接近零的边...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                    self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法添加网格 {mesh} 到检查列表: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 直接检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                        self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 无法添加网格 {node_name} 到检查列表: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                                self.fix_results_text.append(f"添加形状到检查列表: {shape}")
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 无法添加形状 {shape} 到检查列表: {str(e)}"))
                                continue
        
        # 验证选择列表是否有内容
        if mesh_selection.length() == 0:
            self.fix_results_text.append(self.format_status("[WARN] 检查列表中没有任何网格或形状节点"))
            return 0
        
        # 使用zeroLengthEdges函数检查长度接近零的边
        try:
            result_type, zero_length_info = zeroLengthEdges(None, mesh_selection)
            self.fix_results_text.append(f"零长度边检查完成，发现 {len(zero_length_info)} 个有问题的网格")
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 执行零长度边检查时出错: {str(e)}"))
            return 0
        
        deleted_zero_length_edges_count = 0
        total_attempted = 0
        
        if zero_length_info:
            # 遍历所有有长度接近零的边的网格
            for uuid, edge_indices in zero_length_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 无法解析 UUID {uuid} 对应的节点名称"))
                    continue
                    
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {len(edge_indices)} 条长度接近零的边")
                total_attempted += len(edge_indices)
                
                try:
                    # 获取形状节点（处理可能的层级路径）
                    if cmds.nodeType(node_name) == 'transform':
                        # 如果是变换节点，获取其形状节点
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                        if not shapes or len(shapes) == 0:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    else:
                        # 已经是形状节点
                        shape_node = node_name
                        
                    # 清除历史记录前先记录原始边索引
                    original_edge_indices = edge_indices.copy()
                    
                    # 清除历史记录，确保边索引正确
                    self.fix_results_text.append(f"  - 清除 '{node_name}' 的构造历史")
                    cmds.delete(node_name, ch=True)  # 直接删除构造历史，无需先选择
                    
                    # 重新获取零长度边，因为清除历史可能改变边索引
                    try:
                        temp_selection = om.MSelectionList()
                        temp_selection.add(shape_node)
                        _, updated_zero_length = zeroLengthEdges(None, temp_selection)
                        if updated_zero_length and uuid in updated_zero_length:
                            edge_indices = updated_zero_length[uuid]
                            self.fix_results_text.append(f"  - 清除历史后更新边索引，现在有 {len(edge_indices)} 条长度接近零的边")
                        else:
                            self.fix_results_text.append(f"  - 清除历史后边索引未更新，使用原始索引")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 更新边索引时出错: {str(e)}，将使用原始索引"))
                    
                    # 保存原始边数量用于后续验证
                    original_edge_count = cmds.polyEvaluate(shape_node, edge=True)
                    
                    # 构建边选择列表并确保边存在
                    edges_to_delete = []
                    for edge_index in edge_indices:
                        edge_name = f"{shape_node}.e[{edge_index}]"
                        if cmds.objExists(edge_name):
                            edges_to_delete.append(edge_name)
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 边 {edge_name} 不存在，跳过删除"))
                    
                    # 删除长度接近零的边
                    if edges_to_delete:
                        # 执行删除操作，不依赖显式选择
                        self.fix_results_text.append(f"  - 准备删除 {len(edges_to_delete)} 条长度接近零的边")
                        
                        # 方法1: 直接删除
                        cmds.delete(edges_to_delete)
                        
                        # 验证删除结果 - 比较删除前后的边数量
                        new_edge_count = cmds.polyEvaluate(shape_node, edge=True)
                        deleted_by_count = original_edge_count - new_edge_count
                        
                        if deleted_by_count > 0:
                            self.fix_results_text.append(f"  - 通过边数量变化确认: 成功删除 {deleted_by_count} 条边")
                            deleted_zero_length_edges_count += deleted_by_count
                            continue
                        else:
                            self.fix_results_text.append(f"  - 边数量未发生变化，删除可能未成功")
                        
                        # 方法2: 尝试先解除可能的约束
                        self.fix_results_text.append(f"  - 尝试解除约束和连接...")
                        for edge in edges_to_delete:
                            # 查找并删除相关约束
                            constraints = cmds.listConnections(edge, type='constraint') or []
                            for constraint in constraints:
                                self.fix_results_text.append(f"  - 移除约束: {constraint}")
                                cmds.delete(constraint)
                            
                            # 断开输入连接
                            inputs = cmds.listConnections(edge, destination=False, source=True) or []
                            for input_node in inputs:
                                if cmds.nodeType(input_node) not in ['transform', 'mesh']:
                                    self.fix_results_text.append(f"  - 断开连接: {input_node}")
                                    cmds.disconnectAttr(f"{input_node}.output", f"{edge}.inMesh")
                        
                        # 再次尝试删除
                        cmds.delete(edges_to_delete)
                        
                        # 再次验证删除结果
                        new_edge_count = cmds.polyEvaluate(shape_node, edge=True)
                        deleted_by_count = original_edge_count - new_edge_count
                        
                        if deleted_by_count > 0:
                            self.fix_results_text.append(f"  - 解除约束后: 成功删除 {deleted_by_count} 条边")
                            deleted_zero_length_edges_count += deleted_by_count
                            continue
                        else:
                            self.fix_results_text.append(f"  - 解除约束后边数量仍未变化")
                        
                        # 方法3: 使用替代选择方式删除
                        self.fix_results_text.append(f"  - 尝试使用替代方法删除剩余边...")
                        try:
                            # 切换选择模式为边模式
                            cmds.selectMode(component=True)
                            cmds.selectType(edge=True)
                            
                            # 选择边并删除
                            cmds.select(edges_to_delete, replace=True)
                            cmds.delete()
                            
                            # 最后验证删除结果
                            new_edge_count = cmds.polyEvaluate(shape_node, edge=True)
                            deleted_by_count = original_edge_count - new_edge_count
                            
                            if deleted_by_count > 0:
                                self.fix_results_text.append(f"  - 替代方法成功删除 {deleted_by_count} 条边")
                                deleted_zero_length_edges_count += deleted_by_count
                            else:
                                self.fix_results_text.append(self.format_status(f"[WARN] 所有方法均无法删除边"))
                                # 最后的验证：检查是否还有零长度边
                                _, final_zero_length = zeroLengthEdges(None, temp_selection)
                                if final_zero_length and uuid in final_zero_length and len(final_zero_length[uuid]) > 0:
                                    self.fix_results_text.append(f"  - 确认仍有 {len(final_zero_length[uuid])} 条零长度边")
                                else:
                                    self.fix_results_text.append(f"  - 零长度边已被删除，但边索引已改变")
                                    deleted_zero_length_edges_count += len(edges_to_delete)
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"[ERR] 替代删除方法失败: {str(e)}"))
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的长度接近零的边进行删除"))
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{node_name}' 的长度接近零的边时出错: {str(e)}"))
            
            # 智能结果报告
            if deleted_zero_length_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_zero_length_edges_count} 条长度接近零的边"))
                if deleted_zero_length_edges_count < total_attempted:
                    self.fix_results_text.append(self.format_status(f"[WARN] 注意: 共有 {total_attempted - deleted_zero_length_edges_count} 条边未能删除"))
            else:
                if total_attempted > 0:
                    self.fix_results_text.append(self.format_status(f"[WARN] 所有 {total_attempted} 条长度接近零的边均未能删除"))
                else:
                    self.fix_results_text.append(self.format_status("[OK] 没有长度接近零的边需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现长度接近零的边"))
        
        return deleted_zero_length_edges_count  # 返回删除的长度接近零的边数量

    def checkAndDeleteNonManifoldEdges(self, nodes_to_process=None):
        """检查并删除非流形边（连接超过两个面的边），支持处理选中的模型"""
        self.fix_results_text.append("开始检查非流形边...")
        
        # 收集需要处理的网格形状节点
        meshes_to_process = []
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                meshes_to_process.append(mesh)
                self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    meshes_to_process.append(node_name)
                    self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            meshes_to_process.append(shape)
                            self.fix_results_text.append(f"添加形状到检查列表: {shape}")
        
        # 验证是否有需要处理的网格
        if not meshes_to_process:
            self.fix_results_text.append(self.format_status("[WARN] 检查列表中没有任何网格或形状节点"))
            return 0
        
        deleted_non_manifold_edges_count = 0  # 初始化总计数
        total_attempted = 0
        
        # 遍历所有需要处理的网格
        for shape_node in meshes_to_process:
            # 获取变换节点（用于用户显示）
            transform_node = cmds.listRelatives(shape_node, parent=True, fullPath=True)[0]
            node_name = cmds.ls(transform_node, shortNames=True)[0]
            
            try:
                # 1. 首次检查非流形边
                non_manifold_edges = self.get_non_manifold_edges(shape_node)
                initial_edge_count = len(non_manifold_edges)  # 初始非流形边数
                
                if initial_edge_count == 0:
                    self.fix_results_text.append(f"网格 '{node_name}' 没有发现非流形边")
                    continue
                
                self.fix_results_text.append(f"发现网格 '{node_name}' 有 {initial_edge_count} 条非流形边")
                total_attempted += initial_edge_count
                
                # 2. 清除构造历史（避免边索引混乱）
                self.fix_results_text.append(f"  - 清除 '{node_name}' 的构造历史")
                cmds.delete(transform_node, ch=True)
                
                # 3. 清除历史后重新获取非流形边（索引可能变化）
                updated_non_manifold_edges = self.get_non_manifold_edges(shape_node)
                updated_edge_count = len(updated_non_manifold_edges)
                
                if updated_edge_count != initial_edge_count:
                    self.fix_results_text.append(f"  - 清除历史后更新边索引，现在有 {updated_edge_count} 条非流形边")
                else:
                    self.fix_results_text.append(f"  - 清除历史后非流形边数量保持不变: {updated_edge_count} 条")
                
                # 4. 构建有效边列表（过滤不存在的边）
                edges_to_delete = []
                for edge_index in updated_non_manifold_edges:
                    edge_name = f"{shape_node}.e[{edge_index}]"
                    if cmds.objExists(edge_name):
                        edges_to_delete.append(edge_name)
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 边 {edge_name} 不存在，跳过删除"))
                
                if not edges_to_delete:
                    self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的非流形边进行删除"))
                    continue
                
                self.fix_results_text.append(f"  - 准备删除 {len(edges_to_delete)} 条非流形边")
                
                # 5. 执行删除逻辑（删除边关联的多余面）
                for edge in edges_to_delete:
                    # 获取边连接的所有面
                    faces = cmds.polyListComponentConversion(edge, toFace=True)
                    faces = cmds.ls(faces, flatten=True) if faces else []
                    
                    if len(faces) >= 3:
                        # 删除最后一个关联的面（解除非流形状态）
                        cmds.delete(faces[-1])
                        self.fix_results_text.append(f"  - 已删除边 {edge} 关联的面 {faces[-1]}")
                
                # 6. 校验删除结果（核心修复点：通过删除前后的非流形边数差计算实际删除量）
                final_non_manifold_edges = self.get_non_manifold_edges(shape_node)
                final_edge_count = len(final_non_manifold_edges)
                actual_deleted = updated_edge_count - final_edge_count  # 实际删除数 = 处理前 - 处理后
                
                # 确保实际删除数不为负（避免异常情况）
                actual_deleted = max(actual_deleted, 0)
                
                # 打印当前模型的删除结果
                if actual_deleted > 0:
                    self.fix_results_text.append(self.format_status(f" [OK] 成功删除 {actual_deleted} 条非流形边"))
                else:
                    self.fix_results_text.append(self.format_status(f"[WARN] 未删除任何非流形边（可能删除逻辑未生效）"))
                
                # 补充最终状态说明
                if final_edge_count == 0:
                    self.fix_results_text.append(f"  - 网格 '{node_name}' 非流形边已全部清除")
                else:
                    self.fix_results_text.append(f"  - 网格 '{node_name}' 剩余 {final_edge_count} 条非流形边")
            
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{node_name}' 的非流形边时出错: {str(e)}"))

        return actual_deleted  # 返回删除的非流形边数量

    def checkAndSelectOpenEdges(self, nodes_to_process=None):
        """检查并选择开放边（只连接一个面的边），支持处理选中的模型"""
        self.fix_results_text.append("开始检查开放边...")
        
        # 清空当前选择
        cmds.select(clear=True)
        
        # 创建网格选择列表（使用Maya API的MSelectionList）
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取场景中所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    # 将网格添加到选择列表
                    mesh_selection.add(mesh)
                    self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 到选择列表失败: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表（支持UUID），只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                
                # 检查节点类型：直接是网格形状节点
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                        self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 到选择列表失败: {str(e)}"))
                        continue
                else:
                    # 是变换节点，获取其关联的网格形状节点
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                                self.fix_results_text.append(f"添加形状到检查列表: {shape}")
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 到选择列表失败: {str(e)}"))
                                continue
        
        # 使用openEdges函数检查开放边（需确保该函数已正确定义，返回(result_type, {uuid: edge_indices_list})）
        result_type, open_edges_info = openEdges(None, mesh_selection)
        
        selected_edges_count = 0  # 记录选中的开放边总数
        
        if open_edges_info:
            # 遍历所有有开放边的网格
            for uuid, edge_indices in open_edges_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法解析UUID {uuid} 对应的节点，跳过处理"))
                    continue
                
                # 获取变换节点（用于用户友好显示，优先取短名）
                if cmds.nodeType(node_name) == 'transform':
                    transform_node = node_name
                else:
                    # 是形状节点，获取其父变换节点
                    transform_node = cmds.listRelatives(node_name, parent=True, fullPath=True)[0] if cmds.listRelatives(node_name, parent=True) else node_name
                display_name = cmds.ls(transform_node, shortNames=True)[0]
                
                self.fix_results_text.append(f"发现网格 '{display_name}' 有 {len(edge_indices)} 条开放边")
                
                try:
                    # 明确获取网格形状节点（确保边索引对应正确）
                    if cmds.nodeType(node_name) == 'mesh':
                        shape_node = node_name
                    else:
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                        if not shapes or len(shapes) == 0:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格 '{display_name}' 的形状节点，跳过选择"))
                            continue
                        shape_node = shapes[0]
                    
                    # 构建有效的开放边列表（过滤不存在的边）
                    edges_to_select = []
                    for edge_index in edge_indices:
                        edge_name = f"{shape_node}.e[{edge_index}]"
                        if cmds.objExists(edge_name):
                            edges_to_select.append(edge_name)
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 边 {edge_name} 不存在，跳过选择"))
                    
                    # 选择有效的开放边
                    if edges_to_select:
                        # 以添加模式选择边（保留之前的选择）
                        cmds.select(edges_to_select, add=True)
                        selected_count = len(edges_to_select)
                        selected_edges_count += selected_count
                        self.fix_results_text.append(f"  - 已选择 {selected_count} 条开放边")
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 网格 '{display_name}' 没有找到有效的开放边"))
                
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{display_name}' 的开放边时出错: {str(e)}"))
        
            # 输出整体选择结果
            if selected_edges_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功选择 {selected_edges_count} 条开放边"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有开放边需要选择"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现开放边"))
        
        return selected_edges_count  # 返回选中的开放边总数

    def checkAndSelectPoleVertices(self, nodes_to_process=None):
        """检查并选择连接超过5条边的顶点（极点），支持处理选中的模型"""
        self.fix_results_text.append("开始检查极点...")
        
        # 清空当前选择
        cmds.select(clear=True)
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                    self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 失败: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                        self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 失败: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                                self.fix_results_text.append(f"添加形状到检查列表: {shape}")
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 失败: {str(e)}"))
                                continue
        
        # 使用poles函数检查极点
        result_type, poles_info = poles(None, mesh_selection)
        
        selected_poles_count = 0
        all_pole_vertices = []
        
        if poles_info:
            # 遍历所有有极点的网格
            for uuid, vertex_indices in poles_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法解析UUID {uuid} 对应的节点"))
                    continue
                
                # 获取变换节点用于显示
                if cmds.nodeType(node_name) == 'transform':
                    transform_node = node_name
                else:
                    transform_node = cmds.listRelatives(node_name, parent=True, fullPath=True)[0] if cmds.listRelatives(node_name, parent=True) else node_name
                display_name = cmds.ls(transform_node, shortNames=True)[0]
                
                self.fix_results_text.append(f"发现网格 '{display_name}' 有 {len(vertex_indices)} 个极点")
                
                try:
                    # 获取形状节点
                    if cmds.nodeType(node_name) == 'mesh':
                        shape_node = node_name
                    else:
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                        if not shapes or len(shapes) == 0:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    
                    # 构建顶点选择列表并确保顶点存在
                    pole_vertices = []
                    for vtx_index in vertex_indices:
                        vtx_name = f"{shape_node}.vtx[{vtx_index}]"
                        if cmds.objExists(vtx_name):
                            pole_vertices.append(vtx_name)
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 顶点 {vtx_name} 不存在"))
                    
                    if pole_vertices:
                        all_pole_vertices.extend(pole_vertices)
                        selected_count = len(pole_vertices)
                        selected_poles_count += selected_count
                        self.fix_results_text.append(f"  - 已识别 {selected_count} 个有效极点")
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的极点"))
                
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{display_name}' 的极点时出错: {str(e)}"))
            
            # 选择所有极点
            if all_pole_vertices:
                cmds.select(all_pole_vertices, replace=True)
                self.fix_results_text.append(self.format_status(f"[OK] 已成功选择 {selected_poles_count} 个极点"))
            else:
                cmds.select(clear=True)
                self.fix_results_text.append(self.format_status("[OK] 没有发现可选择的极点"))
        else:
            cmds.select(clear=True)
            self.fix_results_text.append(self.format_status("[OK] 没有发现极点"))
        
        return selected_poles_count  # 返回选中的极点数量

    def checkAndDeleteNonStarlikeFaces(self, nodes_to_process=None):
        """检查并删除非星形面，支持处理选中的模型"""
        self.fix_results_text.append("开始检查非星形面...")
        
        # 创建网格选择列表
        mesh_selection = om.MSelectionList()
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                try:
                    mesh_selection.add(mesh)
                    self.fix_results_text.append(f"添加网格到检查列表: {mesh}")
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {mesh} 失败: {str(e)}"))
                    continue
        else:
            # 处理传入的节点列表，只添加其中的网格
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 检查节点是否为网格
                if cmds.nodeType(node_name) == 'mesh':
                    try:
                        mesh_selection.add(node_name)
                        self.fix_results_text.append(f"添加网格到检查列表: {node_name}")
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[WARN] 添加网格 {node_name} 失败: {str(e)}"))
                        continue
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            try:
                                mesh_selection.add(shape)
                                self.fix_results_text.append(f"添加形状到检查列表: {shape}")
                            except Exception as e:
                                self.fix_results_text.append(self.format_status(f"[WARN] 添加形状 {shape} 失败: {str(e)}"))
                                continue
        
        # 使用starlike函数检查非星形面
        result_type, non_starlike_info = starlike(None, mesh_selection)
        
        deleted_non_starlike_count = 0
        
        if non_starlike_info:
            # 遍历所有有非星形面的网格
            for uuid, face_indices in non_starlike_info.items():
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[WARN] 无法解析UUID {uuid} 对应的节点"))
                    continue
                
                # 获取变换节点用于显示
                if cmds.nodeType(node_name) == 'transform':
                    transform_node = node_name
                else:
                    transform_node = cmds.listRelatives(node_name, parent=True, fullPath=True)[0] if cmds.listRelatives(node_name, parent=True) else node_name
                display_name = cmds.ls(transform_node, shortNames=True)[0]
                
                self.fix_results_text.append(f"发现网格 '{display_name}' 有 {len(face_indices)} 个非星形面")
                
                try:
                    # 获取形状节点
                    if cmds.nodeType(node_name) == 'mesh':
                        shape_node = node_name
                    else:
                        shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True, type='mesh')
                        if not shapes or len(shapes) == 0:
                            self.fix_results_text.append(self.format_status(f"[WARN] 未找到网格形状节点"))
                            continue
                        shape_node = shapes[0]
                    
                    # 清除历史记录，确保面索引正确
                    cmds.select(transform_node)
                    cmds.delete(ch=True)  # 只删除构造历史，保留对象
                    
                    # 构建面选择列表并确保面存在
                    faces_to_delete = []
                    for face_index in face_indices:
                        face_name = f"{shape_node}.f[{face_index}]"
                        if cmds.objExists(face_name):
                            faces_to_delete.append(face_name)
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 面 {face_name} 不存在，跳过删除"))
                    
                    # 删除非星形面
                    if faces_to_delete:
                        # 先取消所有选择
                        cmds.select(clear=True)
                        
                        # 选择要删除的面
                        cmds.select(faces_to_delete, add=True)
                        
                        # 执行删除操作
                        cmds.delete()
                        deleted_count = len(faces_to_delete)
                        deleted_non_starlike_count += deleted_count
                        self.fix_results_text.append(f"  - 已删除 {deleted_count} 个非星形面")
                    else:
                        self.fix_results_text.append(self.format_status(f"[WARN] 没有找到有效的非星形面"))
                
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{display_name}' 的非星形面时出错: {str(e)}"))
            
            if deleted_non_starlike_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功删除 {deleted_non_starlike_count} 个非星形面"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有非星形面需要删除"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现非星形面"))
        
        return deleted_non_starlike_count  # 返回删除的非星形面数量

    def checkAndMergeOverlappingVertices(self, nodes_to_process=None):
        """
        检查并自动合并重叠顶点，使用UI中设置的容差值
        支持处理选中的模型或指定节点列表
        
        参数:
            nodes_to_process: 可选，UUID列表，指定要处理的模型
            
        返回:
            合并的顶点数量
        """
        self.fix_results_text.append("开始检查并合并重叠顶点...")
        
        # 从UI获取容差值
        try:
            tolerance = float(self.overlap_vertex_tolerance.text())
            self.fix_results_text.append(f"使用容差值: {tolerance}")
        except ValueError:
            tolerance = 0.001
            self.fix_results_text.append(f"使用默认容差值: {tolerance}")
        
        # 收集需要处理的网格
        meshes_to_process = []
        
        if nodes_to_process is None:
            # 如果没有传入节点列表，则获取场景中所有网格
            all_meshes = cmds.ls(type='mesh')
            for mesh in all_meshes:
                meshes_to_process.append(mesh)
                self.fix_results_text.append(f"添加网格到处理列表: {mesh}")
        else:
            # 处理传入的节点列表（UUID）
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                    
                # 检查节点类型
                if cmds.nodeType(node_name) == 'mesh':
                    meshes_to_process.append(node_name)
                    self.fix_results_text.append(f"添加网格到处理列表: {node_name}")
                else:
                    # 如果是变换节点，获取其网格形状
                    shapes = cmds.listRelatives(node_name, shapes=True, type='mesh', fullPath=True) or []
                    for shape in shapes:
                        if cmds.objExists(shape):
                            meshes_to_process.append(shape)
                            self.fix_results_text.append(f"添加形状到处理列表: {shape}")
        
        # 验证是否有需要处理的网格
        if not meshes_to_process:
            self.fix_results_text.append(self.format_status("[WARN] 处理列表中没有任何网格或形状节点"))
            return 0
        
        # 存储所有重叠顶点组
        overlapping_groups = []
        
        # 第一步：检测重叠顶点
        for shape_node in meshes_to_process:
            # 获取变换节点用于显示
            transform_node = cmds.listRelatives(shape_node, parent=True, fullPath=True)[0] if cmds.listRelatives(shape_node, parent=True) else shape_node
            display_name = cmds.ls(transform_node, shortNames=True)[0]
            
            try:
                # 获取所有顶点
                vertices = cmds.ls(f"{shape_node}.vtx[:]", flatten=True)
                if not vertices:
                    self.fix_results_text.append(self.format_status(f"[WARN] 网格 '{display_name}' 没有顶点，跳过处理"))
                    continue
                
                # 存储顶点位置和字符串表示
                vertex_positions = []
                for vtx in vertices:
                    pos = cmds.xform(vtx, query=True, translation=True, worldSpace=True)
                    vertex_positions.append((vtx, pos))
                
                # 检查重叠顶点
                checked = set()
                for i in range(len(vertex_positions)):
                    if i in checked:
                        continue
                        
                    vtx1, pos1 = vertex_positions[i]
                    group = [vtx1]
                    
                    for j in range(i + 1, len(vertex_positions)):
                        if j in checked:
                            continue
                            
                        vtx2, pos2 = vertex_positions[j]
                        
                        # 计算欧氏距离
                        dx = pos1[0] - pos2[0]
                        dy = pos1[1] - pos2[1]
                        dz = pos1[2] - pos2[2]
                        distance = (dx**2 + dy**2 + dz**2)** 0.5
                        
                        if distance < tolerance:
                            group.append(vtx2)
                            checked.add(j)
                    
                    # 如果有重叠顶点（组内超过1个顶点）
                    if len(group) > 1:
                        overlapping_groups.append(group)
                        checked.add(i)
                        
                        # 提取顶点ID用于显示
                        vtx_ids = [v.split('[')[-1].split(']')[0] for v in group]
                        self.fix_results_text.append(f"模型 '{display_name}' 发现 {len(group)} 个重叠顶点: {', '.join(vtx_ids)}")
            
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 处理 '{display_name}' 的顶点时出错: {str(e)}"))
                continue
        
        # 汇总所有重叠顶点
        all_overlapping = [vtx for group in overlapping_groups for vtx in group]
        if not all_overlapping:
            self.fix_results_text.append(self.format_status("[OK] 未发现重叠顶点"))
            return 0
        
        self.fix_results_text.append(f"共发现 {len(all_overlapping)} 个重叠顶点，准备合并")
        
        # 第二步：合并重叠顶点
        merged_count = 0
        
        try:
            # 按模型分组处理
            model_groups = {}
            for group in overlapping_groups:
                if group:
                    # 从顶点名提取模型名
                    model_name = group[0].split('.')[0]
                    if model_name not in model_groups:
                        model_groups[model_name] = []
                    model_groups[model_name].extend(group)
            
            # 对每个模型执行合并操作
            for model, vertices in model_groups.items():
                # 去重并选择顶点
                unique_vertices = list(set(vertices))
                cmds.select(unique_vertices, replace=True)
                
                # 获取模型显示名
                display_name = cmds.ls(model, shortNames=True)[0]
                
                # 执行合并命令（使用UI设置的容差值）
                cmds.polyMergeVertex(distance=tolerance, constructionHistory=False)
                current_merged = len(unique_vertices)  # 合并n个顶点
                merged_count += current_merged
                
                self.fix_results_text.append(f"  - 模型 '{display_name}' 合并了 {current_merged} 个顶点")
            
            if merged_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 合并完成，共合并 {merged_count} 个顶点"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 未实际合并任何顶点"))
                
            return merged_count
            
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 合并顶点时出错: {str(e)}"))
            return 0

    def split_separated_model(self, nodes_to_process=None):
        """
        检查并分离由多个部分组成的模型，支持处理选中的模型或传入的节点列表
        
        参数:
            nodes_to_process: 可选的节点UUID列表，如果未提供则处理当前选择
            
        返回:
            int: 成功分离的模型数量
        """
        self.fix_results_text.append("开始检查并分离模型...")
        split_count = 0
        
        # 准备要处理的节点列表
        nodes_list = []
        
        if nodes_to_process is None:
            # 获取当前选择的节点
            selected = cmds.ls(selection=True, long=True)
            if not selected:
                self.fix_results_text.append(self.format_status("[WARN] 没有选择任何模型"))
                return 0
            nodes_list = selected
        else:
            # 处理传入的UUID列表
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                nodes_list.append(node_name)
        
        # 处理每个节点
        for node in nodes_list:
            try:
                # 确保处理的是变换节点
                if cmds.nodeType(node) != 'transform':
                    # 如果是形状节点，获取其父变换节点
                    parent = cmds.listRelatives(node, parent=True, fullPath=True)
                    if parent:
                        original_model = parent[0]
                    else:
                        self.fix_results_text.append(self.format_status(f"[ERR] 无法获取节点 {node} 的变换节点，跳过处理"))
                        continue
                else:
                    original_model = node
                
                model_name = cmds.ls(original_model, shortNames=True)[0]  # 获取短名称
                self.fix_results_text.append(f"开始处理模型: {model_name}")
                
                # 检查模型是否存在
                if not cmds.objExists(original_model):
                    self.fix_results_text.append(self.format_status(f"[WARN] 模型 {original_model} 不存在，跳过处理"))
                    continue
                
                # 获取变换节点下的网格形状
                shapes = cmds.listRelatives(original_model, shapes=True, type='mesh', fullPath=True)
                if not shapes:
                    self.fix_results_text.append(self.format_status(f"[WARN] 模型 {model_name} 不包含网格形状，跳过处理"))
                    continue
                shape_node = shapes[0]
                
                # 计算模型的壳数量
                shell_count = cmds.polyEvaluate(shape_node, shell=True)
                self.fix_results_text.append(f"模型 {model_name} 包含 {shell_count} 个壳")
                
                # 壳数量大于1表示是分离模型
                if shell_count > 1:
                    # 复制原始模型以便操作
                    duplicated_model = original_model
                    
                    # 分离壳并禁用历史记录
                    cmds.polySeparate(duplicated_model, constructionHistory=False)
                    
                    # 关键修复：直接获取复制模型的子物体作为分离结果
                    # 确保只获取变换节点类型的子物体
                    separated_models = cmds.listRelatives(duplicated_model, 
                                                    children=True, 
                                                    type='transform',
                                                    fullPath=True) or []
                    
                    # 如果分离后没有子物体，说明分离后的物体就是复制模型本身
                    if not separated_models:
                        separated_models = [duplicated_model]
                    else:
                        # 将分离后的模型移动到场景根层级，避免删除复制模型时被连带删除
                        for model in separated_models:
                            continue
                    
                    # 重命名每个分离后的模型并删除历史记录
                    new_models = []
                    for i, model in enumerate(separated_models, 1):
                        # 删除构造历史
                        cmds.delete(model, constructionHistory=True)
                        
                        # 重命名模型
                        new_name = f"{model_name}_part_{i}"
                        new_model = cmds.rename(model, new_name)
                        new_models.append(new_model)
                        self.fix_results_text.append(f"创建独立模型: {new_model}")

                    # 选择新创建的模型
                    cmds.select(new_models)
                    
                    split_count += 1
                    self.fix_results_text.append(self.format_status(f"[OK] 模型 {model_name} 已成功分离为 {len(new_models)} 个部分"))
                else:
                    self.fix_results_text.append(self.format_status(f"[OK] 模型 {model_name} 是完整模型，无需分离"))
            
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 处理模型 {node} 时出错: {str(e)}"))
                continue
        
        return split_count

    def moveModelsToGroundAndFreeze(self, nodes_to_process=None, tolerance=0.001):
        """
        将模型移动到地面上并冻结变换
        
        参数:
            nodes_to_process: 可选的节点UUID列表，如果未提供则处理当前选择
            tolerance: 容差值，默认0.001
                
        返回:
            int: 成功处理的模型数量
        """
        moved_count = 0
        
        # 准备要处理的节点列表
        nodes_list = []
        
        if nodes_to_process is None:
            # 获取当前选择的节点
            selected = cmds.ls(selection=True, long=True)
            if not selected:
                self.fix_results_text.append(self.format_status("[WARN] 没有选择任何模型"))
                return 0
            nodes_list = selected
        else:
            # 处理传入的UUID列表
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if not node_name or not cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 节点 UUID {uuid} 不存在或无法解析"))
                    continue
                nodes_list.append(node_name)
        
        self.fix_results_text.append(f"开始检查模型是否对齐地面(容差: {tolerance})...")
        
        # 检查每个模型的地面对齐情况
        misaligned_info = []
        
        for node in nodes_list:
            try:
                # 确保处理的是变换节点
                if cmds.nodeType(node) != 'transform':
                    # 如果是形状节点，获取其父变换节点
                    parent = cmds.listRelatives(node, parent=True, fullPath=True)
                    if parent:
                        transform_node = parent[0]
                    else:
                        self.fix_results_text.append(self.format_status(f"[ERR] 无法获取节点 {node} 的变换节点，跳过处理"))
                        continue
                else:
                    transform_node = node
                
                # 获取变换节点下的网格形状
                shapes = cmds.listRelatives(transform_node, shapes=True, type='mesh', fullPath=True)
                if not shapes:
                    self.fix_results_text.append(self.format_status(f"[WARN] 模型 {transform_node} 不包含网格形状，跳过处理"))
                    continue
                
                shape_node = shapes[0]
                
                # 获取所有顶点在世界空间中的位置
                vertices = cmds.ls(f"{shape_node}.vtx[*]", flatten=True)
                min_y = float('inf')
                
                for vtx in vertices:
                    pos = cmds.xform(vtx, query=True, translation=True, worldSpace=True)
                    if pos[1] < min_y:
                        min_y = pos[1]
                
                # 使用参数传递的容差值
                if abs(min_y) > tolerance:
                    misaligned_info.append({
                        "node_name": transform_node,
                        "min_y": min_y
                    })
                    
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 检查模型 {node} 时出错: {str(e)}"))
                continue
        
        # 处理不对齐地面的模型
        if misaligned_info:
            for info in misaligned_info:
                node_name = info["node_name"]
                min_y = info["min_y"]
                
                status = "低于" if min_y < 0 else "高于"
                self.fix_results_text.append(self.format_status(f"[ERR] 发现模型 '{node_name}' 的最低顶点Y值为 {min_y:.3f}，{status}地面"))
                
                try:
                    # 获取当前位置
                    current_position = cmds.xform(node_name, query=True, translation=True, worldSpace=True)
                    
                    # 计算需要移动的距离（将最低点移动到Y=0）
                    move_distance = -min_y
                    
                    # 移动模型
                    new_position = [
                        current_position[0],
                        current_position[1] + move_distance,
                        current_position[2]
                    ]
                    
                    cmds.xform(node_name, translation=new_position, worldSpace=True)
                    self.fix_results_text.append(f"  - 已将 '{node_name}' 移动 {move_distance:.3f} 单位到地面上")
                    
                    # 冻结变换
                    cmds.makeIdentity(node_name, apply=True, translate=True, rotate=True, scale=True)
                    self.fix_results_text.append(f"  - 已冻结 '{node_name}' 的变换")
                    
                    moved_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理模型 '{node_name}' 时出错: {e}"))
            
            if moved_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功将 {moved_count} 个模型移动到地面上并冻结变换"))
            else:
                self.fix_results_text.append(self.format_status("[WARN] 没有模型需要移动到地面上"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 所有模型都已正确对齐地面"))
        
        return moved_count

    def renameUVSetsToMap1(self, nodes_to_process=None):
        """检查并重命名所有UV集为map1"""
        self.fix_results_text.append("开始检查UV集命名...")
        QtCore.QCoreApplication.processEvents()  # 更新UI
        
        # 如果没有传入节点列表，则获取所有网格节点
        if nodes_to_process is None:
            # 获取所有网格节点
            all_meshes = cmds.ls(type='mesh')
        else:
            # 从传入的节点列表中筛选出网格节点
            all_meshes = []
            for node_uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(node_uuid)
                if node_name and cmds.objExists(node_name):
                    # 检查节点是否为网格类型
                    if cmds.objectType(node_name, isa='mesh'):
                        all_meshes.append(node_name)
                    else:
                        # 检查节点是否有网格形状子节点
                        shapes = cmds.listRelatives(node_name, shapes=True, type='mesh') or []
                        all_meshes.extend(shapes)
        
        if not all_meshes:
            self.fix_results_text.append(self.format_status("[OK] 场景中没有找到网格"))
            return 0
        
        # 使用集合去重（防止某些特殊情况下的重复）
        all_meshes = list(set(all_meshes))
        
        # 检查UV集命名
        renamed_count = 0
        meshes_with_non_map1 = []
        
        for mesh in all_meshes:
            try:
                # 获取所有UV集
                uv_sets = cmds.polyUVSet(mesh, query=True, allUVSets=True) or []
                
                # 检查是否有非map1的UV集
                non_map1_sets = [uv_set for uv_set in uv_sets if uv_set != "map1"]
                
                if non_map1_sets:
                    meshes_with_non_map1.append({
                        "mesh_name": mesh,
                        "non_map1_sets": non_map1_sets
                    })
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 检查网格 '{mesh}' 的UV集时出错: {str(e)}"))
        
        if meshes_with_non_map1:
            self.fix_results_text.append(f"找到 {len(meshes_with_non_map1)} 个有非map1 UV集的网格:")
            
            # 列出所有要处理的网格名称
            for mesh_info in meshes_with_non_map1:
                mesh_name = mesh_info["mesh_name"]
                non_map1_sets = mesh_info["non_map1_sets"]
                self.fix_results_text.append(f"  - {mesh_name}: {non_map1_sets}")
            
            self.fix_results_text.append("正在处理UV集...")
            QtCore.QCoreApplication.processEvents()  # 更新UI
            
            # 尝试重命名或删除非map1的UV集
            for mesh_info in meshes_with_non_map1:
                mesh_name = mesh_info["mesh_name"]
                non_map1_sets = mesh_info["non_map1_sets"]
                
                self.fix_results_text.append(f"处理网格 '{mesh_name}' 的UV集: {non_map1_sets}")
                
                for uv_set in non_map1_sets:
                    try:
                        # 获取当前所有UV集（可能已经改变）
                        current_uv_sets = cmds.polyUVSet(mesh_name, allUVSets=True, query=True) or []
                        
                        # 如果已经存在map1，先删除非map1的UV集
                        if "map1" in current_uv_sets:
                            cmds.polyUVSet(mesh_name, delete=True, uvSet=uv_set)
                            self.fix_results_text.append(f"  - 已删除UV集 '{uv_set}' (已存在map1)")
                        else:
                            # 重命名非map1的UV集为map1
                            cmds.polyUVSet(mesh_name, rename=True, uvSet=uv_set, newUVSet="map1")
                            self.fix_results_text.append(f"  - 已将UV集 '{uv_set}' 重命名为 'map1'")
                            renamed_count += 1
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[ERR] 处理UV集 '{uv_set}' 时出错: {str(e)}"))
            
            if renamed_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 已成功重命名 {renamed_count} 个UV集为map1"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 所有非map1的UV集已被处理（重命名或删除）"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 所有UV集都已命名为map1"))
        
        return renamed_count

    def checkAndFixMissingMaterials(self, nodes_to_process=None):
        """
        检查并修复丢失的材质，返回赋予lambert材质的模型数量
        """
        self.fix_results_text.append("开始检查材质丢失...")
        
        # 确保lambert1材质存在
        def ensureLambert1Material():
            if not cmds.objExists('lambert1'):
                lambert = cmds.shadingNode('lambert', asShader=True, name='lambert1')
                shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='lambert1SG')
                cmds.connectAttr(lambert + '.outColor', shading_group + '.surfaceShader', force=True)
                return lambert, shading_group
            return 'lambert1', 'initialShadingGroup'

        # 给指定网格赋予lambert1材质
        def assignLambert1Material(mesh_name):
            try:
                lambert, shading_group = ensureLambert1Material()
                cmds.select(mesh_name)
                cmds.hyperShade(assign=lambert)
                return True
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 赋予材质时出错: {e}"))
                return False

        # 获取所有网格变换节点的UUID列表
        def getMeshTransformUUIDs():
            all_meshes = cmds.ls(type='mesh')
            transform_uuids = []
            for mesh in all_meshes:
                parents = cmds.listRelatives(mesh, parent=True, fullPath=True)
                if parents:
                    uuid = cmds.ls(parents[0], uuid=True)
                    if uuid:
                        transform_uuids.append(uuid[0])
            return transform_uuids

        # 检查材质丢失
        def checkMissingMaterials(nodes, _):
            missing_materials = {}
            for uuid in nodes:
                node_name = cmds.ls(uuid, long=True)[0] if cmds.ls(uuid) else None
                if node_name and cmds.objExists(node_name):
                    shapes = cmds.listRelatives(node_name, shapes=True, fullPath=True)
                    if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                        mesh = shapes[0]
                        shading_groups = cmds.listConnections(mesh, type='shadingEngine') or []
                        has_valid_material = any(cmds.listConnections(sg + '.surfaceShader', source=True, destination=False) 
                                            for sg in shading_groups)
                        if not shading_groups or not has_valid_material:
                            missing_materials[uuid] = "材质丢失或无效"
            return "nodes", missing_materials

        # 如果没有指定节点，则获取所有网格变换节点的UUID列表
        if nodes_to_process is None:
            nodes_to_process = getMeshTransformUUIDs()
        
        # 检查材质丢失
        result_type, missing_materials_info = checkMissingMaterials(nodes_to_process, None)
        fixed_count = 0
        
        if missing_materials_info:
            # 遍历所有有材质丢失的网格
            for uuid, _ in missing_materials_info.items():
                node_name = cmds.ls(uuid, long=True)[0] if cmds.ls(uuid) else None
                if node_name and cmds.objExists(node_name):
                    self.fix_results_text.append(self.format_status(f"[ERR] 发现网格 '{node_name}' 材质丢失"))
                    if assignLambert1Material(node_name):
                        fixed_count += 1
                        self.fix_results_text.append(self.format_status(f"  [OK] 已赋予 lambert1 材质"))
        
        if fixed_count > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 已成功为 {fixed_count} 个网格赋予 lambert1 材质"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现材质丢失的网格"))
        
        # 返回赋予lambert材质的模型数量
        return fixed_count

    def delete_unused_materials_and_shading_groups(self, nodes_to_process=None):
        """
        删除场景中所有未使用的材质和着色组
        返回: 删除的节点总数
        """
        
        # 定义不可删除的默认节点
        PROTECTED_NODES = [
            "lambert1", 
            "standardSurface1", 
            "particleCloud1", 
            "shaderGlow1",
            "initialShadingGroup",
            "initialParticleSE"
        ]
        
        def get_material_info():
            """获取场景中的材质信息"""
            # 获取所有材质节点
            all_materials = cmds.ls(mat=True)
            # 过滤掉受保护的默认材质
            all_materials = [mat for mat in all_materials if mat not in PROTECTED_NODES]
            
            # 获取所有着色组
            all_shading_groups = cmds.ls(type='shadingEngine')
            # 过滤掉受保护的默认着色组
            all_shading_groups = [sg for sg in all_shading_groups if sg not in PROTECTED_NODES]
            
            # 识别已使用和未使用的材质
            used_materials = []
            unused_materials = []
            
            for material in all_materials:
                # 检查材质是否连接到着色组
                shading_groups = cmds.listConnections(
                    material + ".outColor", 
                    type="shadingEngine"
                ) or []
                
                # 检查着色组是否有对象连接
                is_used = False
                for sg in shading_groups:
                    objects = cmds.sets(sg, query=True) or []
                    if objects:
                        is_used = True
                        break
                
                if is_used:
                    used_materials.append(material)
                else:
                    unused_materials.append(material)
            
            # 识别未使用的着色组
            unused_shading_groups = []
            
            for shading_group in all_shading_groups:
                # 检查着色组是否有对象连接
                objects = cmds.sets(shading_group, query=True) or []
                
                # 检查着色组是否有材质连接
                connected_materials = cmds.listConnections(
                    shading_group + ".surfaceShader",
                    source=True,
                    destination=False
                ) or []
                
                # 如果既没有对象连接也没有材质连接，则认为是未使用的着色组
                if not objects and not connected_materials:
                    unused_shading_groups.append(shading_group)
            
            return {
                "unused_materials": unused_materials,
                "unused_shading_groups": unused_shading_groups
            }
        
        # 处理nodes_to_process参数
        if nodes_to_process:
            # 获取指定节点使用的材质
            used_materials_in_selection = set()
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name):
                    # 获取节点连接的材质
                    shading_engines = cmds.listConnections(node_name, type='shadingEngine') or []
                    for sg in shading_engines:
                        materials = cmds.listConnections(sg + '.surfaceShader', source=True) or []
                        used_materials_in_selection.update(materials)
            
            # 过滤掉受保护的材质
            used_materials_in_selection = [mat for mat in used_materials_in_selection if mat not in PROTECTED_NODES]
        
        # 获取材质信息
        material_info = get_material_info()
        unused_materials = material_info["unused_materials"]
        unused_shading_groups = material_info["unused_shading_groups"]
        
        # 如果指定了节点，则只删除这些节点未使用的材质
        if nodes_to_process:
            unused_materials = [mat for mat in unused_materials if mat not in used_materials_in_selection]
            # 对于着色组，需要检查是否连接到指定节点的材质
            unused_shading_groups = [
                sg for sg in unused_shading_groups 
                if not any(mat in used_materials_in_selection for mat in 
                        cmds.listConnections(sg + '.surfaceShader', source=True) or [])
            ]
        
        # 删除未使用的材质和着色组
        deleted_materials = 0
        deleted_shading_groups = 0
        
        # 删除未使用的材质
        for material in unused_materials:
            try:
                if cmds.objExists(material):
                    cmds.delete(material)
                    deleted_materials += 1
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 删除材质 {material} 时出错: {str(e)}"))
        
        # 删除未使用的着色组
        for shading_group in unused_shading_groups:
            try:
                if cmds.objExists(shading_group):
                    cmds.delete(shading_group)
                    deleted_shading_groups += 1
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 删除着色组 {shading_group} 时出错: {str(e)}"))
        
        # 计算删除的节点总数
        total_deleted = deleted_materials + deleted_shading_groups
        
        # 打印结果
        scope = "指定节点" if nodes_to_process else "场景"
        self.fix_results_text.append(f"从{scope}中删除了 {deleted_materials} 个未使用的材质")
        self.fix_results_text.append(f"从{scope}中删除了 {deleted_shading_groups} 个未使用的着色组")
        
        if total_deleted > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 总共删除了 {total_deleted} 个未使用节点"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 没有发现未使用的材质和着色组"))
        
        return total_deleted

    def checkAndCreateSkyDomeLight(self, nodes_to_process=None):
        """检查场景中是否有SkyDomeLight，如果没有则创建，并返回创建的数量"""
        
        # 使用checkSkyDomeLight函数检查SkyDomeLight
        result_type, skydomeLights_info = checkSkyDomeLight(None, None)
        
        aiSkyDomeLight_count = 0
        
        # 检查是否有SkyDomeLight - 修改逻辑
        has_skydome = False
        has_error = False
        
        for uuid, value in skydomeLights_info.items():
            # 如果值不是错误信息，则表示有SkyDomeLight
            if value != ["未创建HDRI环境光"]:
                has_skydome = True
            else:
                has_error = True
        
        # 如果有错误信息且没有找到天空灯，则创建
        if has_error and not has_skydome:
            self.fix_results_text.append("场景中没有找到SkyDomeLight")
            self.fix_results_text.append("正在创建SkyDomeLight...")
            
            # 创建SkyDomeLight
            try:
                # 使用正确的命令创建SkyDomeLight
                skydomeLight = cmds.createNode('aiSkyDomeLight', name='aiSkyDomeLight1')
                
                # 设置一些默认属性
                cmds.setAttr(skydomeLight + '.intensity', 1.0)
                cmds.setAttr(skydomeLight + '.resolution', 1024)
                
                # 确保灯光被正确连接到渲染
                # 获取默认的Arnold渲染选项
                if cmds.objExists('defaultArnoldRenderOptions'):
                    # 连接天空灯到Arnold渲染选项的环境光
                    try:
                        cmds.connectAttr(skydomeLight + '.message', 'defaultArnoldRenderOptions.environmentLight', force=True)
                    except:
                        # 如果连接失败，可能是已经连接了其他灯光
                        pass
                
                self.fix_results_text.append(self.format_status(f"[OK] 已创建SkyDomeLight: {skydomeLight}"))
                aiSkyDomeLight_count = 1
                self.fix_results_text.append(self.format_status("[OK] SkyDomeLight创建成功"))
                
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 创建SkyDomeLight时出错: {str(e)}"))
        else:
            self.fix_results_text.append(f"场景中已找到 {len(skydomeLights_info)} 个SkyDomeLight:")
            for uuid, _ in skydomeLights_info.items():
                # 跳过错误信息条目
                if skydomeLights_info[uuid] == ["未创建HDRI环境光"]:
                    continue
                    
                node_name = getNodeNameFromUUID(uuid)
                if node_name:
                    self.fix_results_text.append(f"  - {node_name}")
                else:
                    self.fix_results_text.append(f"  - {uuid}")
            
            self.fix_results_text.append(self.format_status("[OK] 无需创建新的SkyDomeLight"))
        
        return aiSkyDomeLight_count

    def freezeUnboundJointsTransforms(self, nodes_to_process=None):
        """
        冻结未绑定骨骼的变换
        """
        # 初始化结果文本列表
        self.fix_results_text.append("开始检查未绑定骨骼的变换...")
        
        # 检查骨骼是否已绑定的辅助函数
        def is_joint_bound(joint):
            """检查骨骼是否已绑定"""
            try:
                history = cmds.listHistory(joint)
                if history:
                    skin_clusters = cmds.ls(history, type='skinCluster')
                    if skin_clusters:
                        # 检查这个skinCluster是否连接到当前骨骼
                        for skin_cluster in skin_clusters:
                            influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []
                            if joint in influences:
                                return True
                return False
            except:
                return False
        
        # 获取未绑定骨骼的辅助函数
        def get_unbound_joints(nodes_to_process):
            """获取未绑定骨骼列表"""
            unbound_joints = []
            
            if nodes_to_process is None:
                # 如果没有传入节点列表，则获取所有骨骼
                all_joints = cmds.ls(type='joint')
                for joint in all_joints:
                    if not is_joint_bound(joint):
                        unbound_joints.append(joint)
            else:
                # 处理传入的节点列表
                for uuid in nodes_to_process:
                    joint_name = getNodeNameFromUUID(uuid)
                    if joint_name and cmds.objExists(joint_name) and cmds.objectType(joint_name) == 'joint':
                        if not is_joint_bound(joint_name):
                            unbound_joints.append(joint_name)
            
            return unbound_joints
        
        # 检查骨骼变换是否需要冻结的辅助函数
        def needs_freeze(joint):
            """检查骨骼是否需要冻结变换"""
            try:
                # 检查旋转是否不为0
                rotate = cmds.getAttr(joint + '.rotate')[0]
                rotation_non_zero = (abs(rotate[0]) > 0.001 or abs(rotate[1]) > 0.001 or abs(rotate[2]) > 0.001)
                
                # 检查缩放是否不为1
                scale = cmds.getAttr(joint + '.scale')[0]
                scale_non_one = (abs(scale[0] - 1.0) > 0.001 or abs(scale[1] - 1.0) > 0.001 or abs(scale[2] - 1.0) > 0.001)
                
                return rotation_non_zero or scale_non_one
            except:
                return False
        
        # 获取未绑定骨骼列表
        unbound_joints = get_unbound_joints(nodes_to_process)
        
        if not unbound_joints:
            self.fix_results_text.append(self.format_status("[OK] 场景中没有找到未绑定骨骼"))
            return 0
        
        self.fix_results_text.append(f"找到 {len(unbound_joints)} 个未绑定骨骼")
        
        # 检查哪些骨骼需要冻结变换
        joints_to_freeze = []
        for joint in unbound_joints:
            if needs_freeze(joint):
                joints_to_freeze.append(joint)
        
        if not joints_to_freeze:
            self.fix_results_text.append(self.format_status("[OK] 所有未绑定骨骼的变换已冻结"))
            return 0
        
        self.fix_results_text.append(f"发现 {len(joints_to_freeze)} 个需要冻结变换的未绑定骨骼:")
        for joint in joints_to_freeze:
            self.fix_results_text.append(f"  - {joint}")
        
        # 冻结变换
        frozen_count = 0
        for joint in joints_to_freeze:
            try:
                # 冻结变换（只冻结旋转和缩放，不冻结平移）
                cmds.makeIdentity(joint, apply=True, translate=False, rotate=True, scale=True)
                
                # 验证变换是否已冻结
                rotate_after = cmds.getAttr(joint + '.rotate')[0]
                scale_after = cmds.getAttr(joint + '.scale')[0]
                
                rotation_frozen = (abs(rotate_after[0]) <= 0.001 and 
                                abs(rotate_after[1]) <= 0.001 and 
                                abs(rotate_after[2]) <= 0.001)
                
                scale_frozen = (abs(scale_after[0] - 1.0) <= 0.001 and 
                            abs(scale_after[1] - 1.0) <= 0.001 and 
                            abs(scale_after[2] - 1.0) <= 0.001)
                
                if rotation_frozen and scale_frozen:
                    self.fix_results_text.append(self.format_status(f"[OK] 已冻结骨骼 '{joint}' 的变换"))
                    frozen_count += 1
                else:
                    self.fix_results_text.append(self.format_status(f"[ERR] 骨骼 '{joint}' 的变换可能未完全冻结"))
                    
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 冻结骨骼 '{joint}' 时出错: {str(e)}"))
        
        if frozen_count > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 冻结操作完成: 成功冻结了 {frozen_count} 个骨骼的变换"))
        else:
            self.fix_results_text.append(self.format_status("[WARN] 冻结操作完成: 未能成功冻结任何骨骼"))
        
        return frozen_count

    def remove_redundant_joints(self, nodes_to_process=None):
        """
        删除场景中多余的骨骼（没有和模型绑定的骨骼）
        """
        try:
            # 获取要处理的关节列表
            if nodes_to_process is None:
                # 处理整个场景
                all_joints = cmds.ls(type='joint', long=True)
            else:
                # 只处理指定的节点（筛选出关节类型）
                all_joints = cmds.ls(nodes_to_process, type='joint', long=True)
            
            if not all_joints:
                self.fix_results_text.append(self.format_status("[OK] 没有找到要处理的骨骼"))
                return 0
            
            # 获取所有皮肤簇
            skin_clusters = cmds.ls(type='skinCluster', long=True)
            
            if not skin_clusters:
                self.fix_results_text.append(self.format_status("[WARN] 场景中没有找到皮肤簇，所有指定骨骼都将被视为未绑定"))
                # 直接删除所有指定骨骼
                deleted = cmds.delete(all_joints)
                redundant_joints_count = len(deleted) if deleted else 0
                self.fix_results_text.append(self.format_status(f"[OK] 成功删除 {redundant_joints_count} 个多余骨骼"))
                # 刷新视图
                cmds.refresh()
                return redundant_joints_count
            
            # 收集所有被皮肤簇使用的关节
            used_joints = set()
            for skin_cluster in skin_clusters:
                # 检查皮肤簇是否有效
                if not cmds.objExists(skin_cluster):
                    continue
                    
                try:
                    # 获取皮肤簇影响关节
                    influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
                    if influences:
                        # 转换为长名称以确保比较准确性
                        influences_long = cmds.ls(influences, long=True)
                        used_joints.update(influences_long)	
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[WARN] 处理皮肤簇 {skin_cluster} 时出错: {str(e)}"))
                    continue
            
            # 找出未使用的关节
            redundant_joints = [joint for joint in all_joints if joint not in used_joints]
            
            if not redundant_joints:
                self.fix_results_text.append(self.format_status("[OK] 没有找到多余的骨骼"))
                return 0
            
            # 显示将要删除的骨骼
            self.fix_results_text.append(f"找到 {len(redundant_joints)} 个多余骨骼，正在删除:")
            for joint in redundant_joints:
                self.fix_results_text.append(f"  - {joint}")
            
            # 直接执行删除，不显示确认对话框
            deleted = cmds.delete(redundant_joints)
            redundant_joints_count = len(deleted) if deleted else 0
            
            if redundant_joints_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 成功删除 {redundant_joints_count} 个多余骨骼"))
                # 刷新视图
                cmds.refresh()
            else:
                self.fix_results_text.append(self.format_status("[WARN] 没有删除任何骨骼"))
                
            return redundant_joints_count
                
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 删除冗余骨骼时出错: {str(e)}"))
            return 0

    def deleteOverlappingJoints(self, nodes_to_process=None):
        """
        删除场景中重叠的骨骼
        """
        try:
            # 创建包含所有骨骼的选择列表
            def createAllJointsSelectionList():
                """创建包含所有骨骼的选择列表"""
                selection_list = om.MSelectionList()
                
                # 获取所有骨骼
                if nodes_to_process is None:
                    joints = cmds.ls(type='joint')
                else:
                    joints = cmds.ls(nodes_to_process, type='joint')
                
                for joint in joints:
                    try:
                        selection_list.add(joint)
                    except:
                        continue
                
                return selection_list

            # 检查重叠骨骼的函数
            def checkOverlappingJoints(_, SLMesh):
                """检查场景中是否有重叠的骨骼"""
                overlappingJointIssues = {}
                
                # 获取所有骨骼
                if nodes_to_process is None:
                    joints = cmds.ls(type='joint')
                else:
                    joints = cmds.ls(nodes_to_process, type='joint')
                
                # 存储骨骼位置信息
                joint_positions = {}
                
                for joint in joints:
                    try:
                        # 获取骨骼的世界空间位置
                        pos = cmds.xform(joint, query=True, worldSpace=True, translation=True)
                        pos_key = f"{pos[0]:.3f}_{pos[1]:.3f}_{pos[2]:.3f}"  # 使用精度为3位小数的字符串作为位置键
                        
                        # 获取骨骼的UUID
                        sel = om.MSelectionList()
                        sel.add(joint)
                        dag = sel.getDagPath(0)
                        fn = om.MFnDependencyNode(dag.node())
                        uuid = fn.uuid().asString()
                        
                        # 记录位置信息
                        if pos_key not in joint_positions:
                            joint_positions[pos_key] = []
                        joint_positions[pos_key].append((uuid, joint, pos))
                                
                    except Exception as e:
                        # 如果处理骨骼时出错，记录错误信息
                        try:
                            sel = om.MSelectionList()
                            sel.add(joint)
                            dag = sel.getDagPath(0)
                            fn = om.MFnDependencyNode(dag.node())
                            uuid = fn.uuid().asString()
                            overlappingJointIssues[uuid] = [f"检查骨骼时出错: {str(e)}"]
                        except:
                            overlappingJointIssues[joint] = [f"检查骨骼时出错: {str(e)}"]
                
                # 检查重叠的骨骼
                tolerance = 0.001  # 位置容差值
                for pos_key, joints_at_position in joint_positions.items():
                    if len(joints_at_position) > 1:
                        # 这个位置有多个骨骼，检查它们是否真的重叠
                        for i, (uuid1, joint1, pos1) in enumerate(joints_at_position):
                            for j, (uuid2, joint2, pos2) in enumerate(joints_at_position[i+1:], i+1):
                                # 计算距离
                                distance = ((pos1[0] - pos2[0])**2 + 
                                        (pos1[1] - pos2[1])**2 + 
                                        (pos1[2] - pos2[2])**2)**0.5
                                
                                if distance < tolerance:
                                    # 骨骼重叠
                                    if uuid1 not in overlappingJointIssues:
                                        overlappingJointIssues[uuid1] = []
                                    overlappingJointIssues[uuid1].append(f"与 '{joint2}' 重叠 (距离: {distance:.4f})")
                                    
                                    if uuid2 not in overlappingJointIssues:
                                        overlappingJointIssues[uuid2] = []
                                    overlappingJointIssues[uuid2].append(f"与 '{joint1}' 重叠 (距离: {distance:.4f})")
                
                return "overlapping_joints", overlappingJointIssues

            self.fix_results_text.append("开始检查重叠的骨骼...")
            
            # 创建包含所有骨骼的选择列表
            joints_selection = createAllJointsSelectionList()
            
            # 使用checkOverlappingJoints函数检查重叠的骨骼
            result_type, overlapping_joints_issues = checkOverlappingJoints(None, joints_selection)
            
            deleted_overlapping_joints_count = 0
            
            if overlapping_joints_issues:
                joints_to_delete = []
                overlapping_groups = {}
                
                # 组织重叠的骨骼组
                for uuid, issues in overlapping_joints_issues.items():
                    node_name = getNodeNameFromUUID(uuid)
                    if not node_name:
                        node_name = uuid  # 如果无法获取节点名称，使用UUID
                    
                    # 检查是否是错误信息
                    if "出错" in str(issues):
                        self.fix_results_text.append(self.format_status(f"[ERR] 骨骼 '{node_name}' - {issues[0]}"))
                    else:
                        # 提取重叠信息
                        for issue in issues:
                            if "与 '" in issue and "' 重叠" in issue:
                                other_joint = issue.split("'")[1]
                                group_key = frozenset([node_name, other_joint])
                                
                                if group_key not in overlapping_groups:
                                    overlapping_groups[group_key] = (node_name, other_joint, issue)
                
                # 处理重叠组
                processed_joints = set()
                for group_key, (joint1, joint2, issue) in overlapping_groups.items():
                    if joint1 in processed_joints or joint2 in processed_joints:
                        continue
                        
                    self.fix_results_text.append(f"发现重叠的骨骼: '{joint1}' 和 '{joint2}'")
                    self.fix_results_text.append(f"  - {issue}")
                    
                    # 决定删除哪个骨骼（保留层级较高的或名称较短的）
                    joint1_parents = cmds.listRelatives(joint1, allParents=True, fullPath=True) or []
                    joint2_parents = cmds.listRelatives(joint2, allParents=True, fullPath=True) or []
                    
                    # 优先删除没有子节点的骨骼
                    joint1_children = cmds.listRelatives(joint1, children=True, fullPath=True) or []
                    joint2_children = cmds.listRelatives(joint2, children=True, fullPath=True) or []
                    
                    if not joint1_children and joint2_children:
                        joints_to_delete.append(joint1)
                        processed_joints.add(joint1)
                        self.fix_results_text.append(f"  将删除 '{joint1}' (没有子节点)")
                    elif not joint2_children and joint1_children:
                        joints_to_delete.append(joint2)
                        processed_joints.add(joint2)
                        self.fix_results_text.append(f"  将删除 '{joint2}' (没有子节点)")
                    elif len(joint1) <= len(joint2):  # 名称较短的优先保留
                        joints_to_delete.append(joint2)
                        processed_joints.add(joint2)
                        self.fix_results_text.append(f"  将删除 '{joint2}' (名称较长)")
                    else:
                        joints_to_delete.append(joint1)
                        processed_joints.add(joint1)
                        self.fix_results_text.append(f"  将删除 '{joint1}' (名称较长)")
                
                if joints_to_delete:
                    self.fix_results_text.append(f"\n找到 {len(joints_to_delete)} 个重叠的骨骼需要删除")
                    
                    # 直接删除重叠的骨骼
                    for joint in joints_to_delete:
                        try:
                            if cmds.objExists(joint):
                                cmds.delete(joint)
                                self.fix_results_text.append(f"已删除骨骼: {joint}")
                                deleted_overlapping_joints_count += 1
                            else:
                                self.fix_results_text.append(self.format_status(f"[WARN] 骨骼 '{joint}' 已不存在"))
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"[ERR] 删除骨骼 '{joint}' 时出错: {str(e)}"))
                    
                    self.fix_results_text.append(self.format_status(f"[OK] 成功删除 {deleted_overlapping_joints_count} 个重叠的骨骼"))
                    # 刷新视图
                    cmds.refresh()
                else:
                    self.fix_results_text.append(self.format_status("[OK] 没有发现需要删除的重叠骨骼"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有发现重叠的骨骼"))
                
            return deleted_overlapping_joints_count
                
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 删除重叠骨骼时出错: {str(e)}"))
            return 0

    def addJointSuffix(self, nodes_to_process=None, suffix="_Jnt"):
        """
        检查并为骨骼添加指定的后缀名
        """
        renamed_joints_count = 0
        jointSuffixIssues = {}
        
        # 获取需要处理的骨骼
        if nodes_to_process is None:
            joints = cmds.ls(type='joint')
        else:
            # 确保只处理存在的骨骼
            joints = [j for j in nodes_to_process if cmds.objExists(j) and cmds.nodeType(j) == 'joint']
        
        # 检查骨骼后缀名
        for joint in joints:
            try:
                # 检查骨骼名称是否以指定后缀结尾
                if not joint.endswith(suffix):
                    # 获取骨骼的UUID
                    sel = om.MSelectionList()
                    sel.add(joint)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    
                    # 记录问题信息
                    jointSuffixIssues[uuid] = [f"骨骼名称 '{joint}' 不以'{suffix}'结尾"]
                        
            except Exception as e:
                # 如果处理骨骼时出错，记录错误信息
                try:
                    sel = om.MSelectionList()
                    sel.add(joint)
                    dag = sel.getDagPath(0)
                    fn = om.MFnDependencyNode(dag.node())
                    uuid = fn.uuid().asString()
                    jointSuffixIssues[uuid] = [f"检查骨骼时出错: {str(e)}"]
                except:
                    jointSuffixIssues[joint] = [f"检查骨骼时出错: {str(e)}"]
        
        # 处理需要重命名的骨骼
        if jointSuffixIssues:
            joints_to_rename = []
            
            # 遍历所有不符合后缀名要求的骨骼
            for uuid, issues in jointSuffixIssues.items():
                # 从UUID获取节点名称
                def getNodeNameFromUUID(uuid):
                    nodes = cmds.ls(uuid)
                    if nodes:
                        return nodes[0]
                    return None
                
                node_name = getNodeNameFromUUID(uuid)
                if not node_name:
                    node_name = uuid  # 如果无法获取节点名称，使用UUID
                
                # 检查是否是错误信息
                if "出错" in str(issues):
                    self.fix_results_text.append(self.format_status(f"[ERR] 骨骼 '{node_name}' - {issues[0]}"))
                else:
                    self.fix_results_text.append(self.format_status(f"[ERR] 骨骼 '{node_name}' - {issues[0]}"))
                    joints_to_rename.append(node_name)
            
            if joints_to_rename:
                self.fix_results_text.append(f"\n找到 {len(joints_to_rename)} 个需要添加后缀名的骨骼")
                
                # 为骨骼添加指定的后缀名
                for joint in joints_to_rename:
                    try:
                        if cmds.objExists(joint):
                            # 生成新的名称（去掉可能存在的其他后缀，然后添加指定后缀）
                            base_name = joint
                            if '_' in joint:
                                base_name = joint.rsplit('_', 1)[0]
                            
                            new_name = base_name + suffix
                            
                            # 重命名骨骼
                            renamed_joint = cmds.rename(joint, new_name)
                            self.fix_results_text.append(f"已重命名骨骼: '{joint}' -> '{renamed_joint}'")
                            renamed_joints_count += 1
                        else:
                            self.fix_results_text.append(self.format_status(f"[WARN] 骨骼 '{joint}' 已不存在"))
                    except Exception as e:
                        self.fix_results_text.append(self.format_status(f"[ERR] 重命名骨骼 '{joint}' 时出错: {str(e)}"))
                
                self.fix_results_text.append(self.format_status(f"[OK] 成功为 {renamed_joints_count} 个骨骼添加后缀名'{suffix}'"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 没有发现需要添加后缀名的骨骼"))
        else:
            self.fix_results_text.append(self.format_status(f"[OK] 所有骨骼都已正确使用'{suffix}'后缀名"))
        
        return renamed_joints_count

    def joint_alignment_XYZ(self, nodes_to_process=None, target_rotate_order=0):
        """
        检查场景内所有骨骼（包括已绑定骨骼）的旋转顺序是否是目标旋转顺序，
        如果不是则设置为目标旋转顺序
        :param nodes_to_process: 可选参数，指定要处理的骨骼列表，None则处理所有骨骼
        :param target_rotate_order: 目标旋转顺序索引，0=XYZ, 1=YZX, 2=ZXY, 3=XZY, 4=YXZ, 5=ZYX
        :return: 成功设置旋转轴向的骨骼数量
        """
        joint_alignment_xyz_count = 0
        rotate_orders = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
        target_name = rotate_orders[target_rotate_order]
        
        # 存储用户选择（是否修改已绑定骨骼）
        modify_skinned_joints = None
        
        def is_joint_skinned(joint):
            """检查关节是否有皮肤绑定"""
            try:
                # 检查关节的历史中是否有skinCluster节点
                history = cmds.listHistory(joint)
                if history:
                    skin_clusters = cmds.ls(history, type='skinCluster')
                    if skin_clusters:
                        return True
                
                # 检查关节是否是任何skinCluster的影响物体
                all_skin_clusters = cmds.ls(type='skinCluster')
                for skin_cluster in all_skin_clusters:
                    try:
                        influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
                        if influences and joint in influences:
                            return True
                    except:
                        continue
                
                return False
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 检查骨骼绑定状态时出错 {joint}: {e}"))
                return False

        def get_all_joints():
            """
            获取场景中所有骨骼（包括已绑定骨骼）
            返回需要检查的骨骼列表
            """
            try:
                # 获取需要处理的骨骼
                if nodes_to_process is None:
                    all_joints = cmds.ls(type='joint')
                else:
                    # 确保只处理存在的骨骼
                    all_joints = [j for j in nodes_to_process if cmds.objExists(j) and cmds.nodeType(j) == 'joint']
                
                if not all_joints:
                    self.fix_results_text.append(self.format_status("[ERR] 没有找到任何骨骼"))
                    return []
                
                return all_joints
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 查找需要检查的骨骼时出错: {e}"))
                return []

        def ask_user_about_skinned_joints(skinned_joints_count):
            """
            询问用户是否要修改已绑定骨骼的旋转顺序
            返回布尔值：True表示修改所有骨骼，False表示只修改未绑定骨骼
            """
            nonlocal modify_skinned_joints
            
            # 如果已经询问过用户，直接返回之前的选择
            if modify_skinned_joints is not None:
                return modify_skinned_joints
            
            # 弹出对话框询问用户
            result = cmds.confirmDialog(
                title='修改已绑定骨骼',
                message=f'发现 {skinned_joints_count} 个已绑定皮肤的骨骼。\n\n修改已绑定骨骼的旋转顺序可能会影响现有的绑定和动画。\n\n是否要继续修改所有骨骼（包括已绑定骨骼）的旋转顺序？',
                button=['是', '否', '取消'],
                defaultButton='否',
                cancelButton='取消',
                dismissString='取消'
            )
            
            if result == '是':
                modify_skinned_joints = True
                self.fix_results_text.append(self.format_status("[OK] 用户选择修改所有骨骼（包括已绑定骨骼）"))
                return True
            elif result == '否':
                modify_skinned_joints = False
                self.fix_results_text.append(self.format_status("[OK] 用户选择只修改未绑定骨骼"))
                return False
            else:  # 取消
                self.fix_results_text.append(self.format_status("[WARN] 用户取消操作"))
                return None

        def check_and_set_joint_rotation_order(joint, is_skinned):
            """
            检查骨骼的旋转顺序是否为目标旋转顺序，如果不是则设置为目标旋转顺序
            返回布尔值表示是否进行了设置
            """
            try:
                # 获取骨骼的旋转顺序属性
                rotate_order = cmds.getAttr(joint + ".rotateOrder")
                
                if rotate_order == target_rotate_order:
                    status = "[OK]" if not is_skinned else "[WARN]"
                    skinned_note = " (已绑定)" if is_skinned else ""
                    self.fix_results_text.append(self.format_status(f"{status} 骨骼 '{joint}' 的旋转顺序已经是{target_name}{skinned_note}"))
                    return False
                else:
                    # 获取旋转顺序的具体名称
                    rotate_order_name = rotate_orders[rotate_order]
                    
                    status = "[ERR]" if not is_skinned else "[WARN]"
                    skinned_note = " (已绑定)" if is_skinned else ""
                    self.fix_results_text.append(self.format_status(f"{status} 骨骼 '{joint}' 的旋转顺序不是{target_name} (当前: {rotate_order_name}){skinned_note}"))
                    
                    # 如果是已绑定骨骼且用户选择不修改，则跳过
                    if is_skinned and not modify_skinned_joints:
                        self.fix_results_text.append(f"   跳过已绑定骨骼 '{joint}'（用户选择不修改已绑定骨骼）")
                        return False
                    
                    # 设置旋转顺序为目标旋转顺序
                    cmds.setAttr(joint + ".rotateOrder", target_rotate_order)
                    status = "[OK]" if not is_skinned else "[WARN]"
                    skinned_note = " (已绑定)" if is_skinned else ""
                    self.fix_results_text.append(self.format_status(f"{status} 已将骨骼 '{joint}' 的旋转顺序设置为{target_name}{skinned_note}"))
                    return True
                    
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 检查/设置骨骼 {joint} 旋转顺序时出错: {e}"))
                return False

        try:
            # 获取需要检查的骨骼（所有骨骼，包括已绑定）
            all_joints = get_all_joints()
            
            if not all_joints:
                self.fix_results_text.append(self.format_status("[ERR] 没有找到任何骨骼"))
                return joint_alignment_xyz_count
            
            # 统计已绑定和未绑定的骨骼
            skinned_joints = []
            unskinned_joints = []
            
            for joint in all_joints:
                if is_joint_skinned(joint):
                    skinned_joints.append(joint)
                else:
                    unskinned_joints.append(joint)
            
            self.fix_results_text.append(f"发现 {len(all_joints)} 个骨骼:")
            self.fix_results_text.append(f"  - 已绑定骨骼: {len(skinned_joints)} 个")
            self.fix_results_text.append(f"  - 未绑定骨骼: {len(unskinned_joints)} 个")
            
            # 如果有已绑定骨骼，询问用户如何处理
            if skinned_joints:
                user_choice = ask_user_about_skinned_joints(len(skinned_joints))
                if user_choice is None:  # 用户取消
                    return joint_alignment_xyz_count
            else:
                # 没有已绑定骨骼，默认修改所有骨骼
                modify_skinned_joints = True
            
            # 确定要处理的骨骼列表
            if modify_skinned_joints:
                joints_to_process = all_joints
                self.fix_results_text.append(f"将处理所有 {len(joints_to_process)} 个骨骼（包括已绑定骨骼）")
            else:
                joints_to_process = unskinned_joints
                self.fix_results_text.append(f"将处理 {len(joints_to_process)} 个未绑定骨骼")
            
            if not joints_to_process:
                self.fix_results_text.append(self.format_status("[OK] 没有需要处理的骨骼"))
                return joint_alignment_xyz_count
            
            self.fix_results_text.append(f"开始检查并设置 {len(joints_to_process)} 个骨骼的旋转顺序(目标: {target_name})...")
            
            # 检查并设置每个骨骼的旋转顺序
            for joint in joints_to_process:
                is_skinned = joint in skinned_joints
                if check_and_set_joint_rotation_order(joint, is_skinned):
                    joint_alignment_xyz_count += 1
            
            # 打印检查结果总结
            self.fix_results_text.append("=" * 60)
            self.fix_results_text.append(f"旋转顺序检查与设置完成总结(目标: {target_name}):")
            self.fix_results_text.append("=" * 60)
            self.fix_results_text.append(f"  总共检查了 {len(all_joints)} 个骨骼")
            self.fix_results_text.append(f"  成功设置了 {joint_alignment_xyz_count} 个骨骼的旋转顺序为{target_name}")
            
            if modify_skinned_joints:
                self.fix_results_text.append(f"  处理范围: 所有骨骼（包括已绑定骨骼）")
            else:
                self.fix_results_text.append(f"  处理范围: 仅未绑定骨骼")
            
            if joint_alignment_xyz_count == 0:
                if modify_skinned_joints:
                    self.fix_results_text.append(self.format_status(f"[OK] 所有骨骼的旋转顺序已经是{target_name}"))
                else:
                    self.fix_results_text.append(self.format_status(f"[OK] 所有未绑定骨骼的旋转顺序已经是{target_name}"))
            else:
                if modify_skinned_joints:
                    self.fix_results_text.append(self.format_status(f"[OK] 已将 {joint_alignment_xyz_count} 个骨骼的旋转顺序设置为{target_name}"))
                else:
                    self.fix_results_text.append(self.format_status(f"[OK] 已将 {joint_alignment_xyz_count} 个未绑定骨骼的旋转顺序设置为{target_name}"))
            
            self.fix_results_text.append("=" * 60)
            
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 检查并设置骨骼旋转顺序时出错: {e}"))
        
        return joint_alignment_xyz_count
    
    def orient_joints_excluding_end_joints_main(self, nodes_to_process=None, params=None):
        """
        重新定向非末端骨骼的朝向
        :param nodes_to_process: 要处理的骨骼列表
        :param params: 包含orientJoint和secondaryAxisOrient参数的字典
        :return: 修改的骨骼数量
        """
        orient_joints_excluding_end_joints_count = 0
        
        # 设置默认参数
        if params is None:
            params = {}
        
        # 从参数中获取orientJoint和secondaryAxisOrient值
        orient_joint = params.get('orientJoint', 'xyz')
        secondary_axis_orient = params.get('secondaryAxisOrient', 'yup')
        
        def orient_joints_excluding_end_joints():
            # 选择场景中的所有关节
            all_joints = cmds.ls(type='joint', long=True) or []
            
            if not all_joints:
                self.fix_results_text.append(self.format_status("[ERR] 场景中没有找到关节"))
                return 0
            
            # 找出末端关节（没有子关节的关节）
            end_joints = []
            non_end_joints = []
            
            for joint in all_joints:
                # 获取当前关节的所有子关节，并过滤出同样是joint类型的子级
                children = cmds.listRelatives(joint, children=True, type='joint', fullPath=True) or []
                # 如果没有子关节，则是末端关节
                if not children:
                    end_joints.append(joint)
                else:
                    non_end_joints.append(joint)
            
            self.fix_results_text.append(f"找到 {len(all_joints)} 个关节")
            self.fix_results_text.append(f"其中 {len(non_end_joints)} 个为非末端关节，{len(end_joints)} 个为末端关节")
            
            # 如果没有非末端关节，则提前返回
            if not non_end_joints:
                self.fix_results_text.append(self.format_status("[OK] 没有找到需要重新定向的非末端关节"))
                return 0
            
            # 选择所有非末端关节
            cmds.select(non_end_joints, replace=True)
            self.fix_results_text.append("已选择所有非末端关节")
            
            processed_count = 0
            
            # 对每个非末端关节执行 joint 命令来重新定向
            for joint in non_end_joints:
                try:
                    cmds.select(joint, replace=True)
                    # 使用传入的参数
                    cmds.joint(edit=True, orientJoint=orient_joint, secondaryAxisOrient=secondary_axis_orient)
                    self.fix_results_text.append(f"已处理关节: {joint}")
                    processed_count += 1
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 处理关节 {joint} 时出错: {str(e)}"))
            
            # 恢复选择所有非末端关节，方便用户查看
            cmds.select(non_end_joints, replace=True)
            self.fix_results_text.append(self.format_status(f"[OK] 操作完成。成功重新定向了 {processed_count} 个非末端关节"))
            return processed_count

        # 执行函数并返回计数
        orient_joints_excluding_end_joints_count = orient_joints_excluding_end_joints()
        return orient_joints_excluding_end_joints_count

    def check_and_fix_end_joint_axis_alignment(self, nodes_to_process=None):
        def check_and_fix_end_joint_alignment():
            """
            检查并修复场景中末端骨骼的轴向，使其与父级骨骼保持一致
            """
            
            def get_joint_world_matrix(joint):
                """获取骨骼的世界矩阵"""
                return cmds.xform(joint, query=True, worldSpace=True, matrix=True)
            
            def extract_axis_vectors(matrix):
                """从矩阵中提取轴向向量"""
                # Maya矩阵是列主序的，前3列分别是X、Y、Z轴向量
                x_axis = [matrix[0], matrix[1], matrix[2]]
                y_axis = [matrix[4], matrix[5], matrix[6]]
                z_axis = [matrix[8], matrix[9], matrix[10]]
                return x_axis, y_axis, z_axis
            
            def normalize_vector(vector):
                """归一化向量"""
                length = math.sqrt(sum(v**2 for v in vector))
                if length < 0.0001:
                    return vector
                return [v / length for v in vector]
            
            def calculate_angle_between_vectors(v1, v2):
                """计算两个向量之间的角度（度）"""
                dot_product = sum(a*b for a, b in zip(v1, v2))
                dot_product = max(min(dot_product, 1.0), -1.0)  # 修正数值误差
                angle_rad = math.acos(dot_product)
                return math.degrees(angle_rad)
            
            def find_end_joints():
                """查找所有末端骨骼（没有子骨骼的骨骼）"""
                all_joints = cmds.ls(type='joint', long=True)
                end_joints = []
                
                for joint in all_joints:
                    children = cmds.listRelatives(joint, children=True, type='joint', fullPath=True)
                    if not children:  # 没有子骨骼
                        end_joints.append(joint)
                
                return end_joints
            
            def align_joint_axes(child_joint, parent_joint):
                """对齐子骨骼的轴向到父骨骼"""
                try:
                    # 获取世界矩阵
                    parent_matrix = get_joint_world_matrix(parent_joint)
                    child_matrix = get_joint_world_matrix(child_joint)
                    
                    # 提取轴向向量
                    parent_x, parent_y, parent_z = extract_axis_vectors(parent_matrix)
                    child_x, child_y, child_z = extract_axis_vectors(child_matrix)
                    
                    # 归一化向量
                    parent_x = normalize_vector(parent_x)
                    parent_y = normalize_vector(parent_y)
                    parent_z = normalize_vector(parent_z)
                    
                    child_x = normalize_vector(child_x)
                    child_y = normalize_vector(child_y)
                    child_z = normalize_vector(child_z)
                    
                    # 计算需要旋转的角度
                    # 使用四元数或欧拉角计算旋转差异
                    # 这里使用简单的方法：计算X轴旋转
                    
                    # 计算X轴之间的旋转
                    x_angle = calculate_angle_between_vectors(parent_x, child_x)
                    
                    if x_angle > 1.0:  # 如果角度大于1度，进行调整
                        # 选择子骨骼
                        cmds.select(child_joint)
                        
                        # 使用Maya的旋转工具对齐
                        # 方法1：使用aimConstraint临时约束，然后删除
                        temp_constraint = cmds.aimConstraint(
                            parent_joint, 
                            child_joint,
                            aimVector=[1, 0, 0],
                            upVector=[0, 1, 0],
                            worldUpType="vector",
                            worldUpVector=[0, 1, 0]
                        )
                        
                        # 删除约束
                        cmds.delete(temp_constraint)
                        
                        # 冻结变换，使旋转值归零
                        cmds.makeIdentity(child_joint, apply=True, rotate=True)
                        
                        return True
                    
                    return False
                    
                except Exception as e:
                    self.fix_results_text.append(self.format_status(f"[ERR] 对齐骨骼 {child_joint} 时出错: {str(e)}"))
                    return False
            
            # 主逻辑
            self.fix_results_text.append("开始检查末端骨骼轴向对齐...")
            
            # 查找所有末端骨骼
            end_joints = find_end_joints()
            
            if not end_joints:
                self.fix_results_text.append(self.format_status("[OK] 场景中没有找到末端骨骼"))
                return
            
            self.fix_results_text.append(f"找到 {len(end_joints)} 个末端骨骼")
            
            # 检查每个末端骨骼
            misaligned_joints = []
            fixed_joints = []
            
            for end_joint in end_joints:
                # 获取父级骨骼
                parent_joints = cmds.listRelatives(end_joint, parent=True, type='joint', fullPath=True)
                
                if not parent_joints:
                    continue  # 没有父级骨骼（根骨骼）
                
                parent_joint = parent_joints[0]
                
                # 获取世界矩阵
                try:
                    parent_matrix = get_joint_world_matrix(parent_joint)
                    end_matrix = get_joint_world_matrix(end_joint)
                except:
                    continue
                
                # 提取并归一化轴向向量
                parent_x, parent_y, parent_z = extract_axis_vectors(parent_matrix)
                end_x, end_y, end_z = extract_axis_vectors(end_matrix)
                
                parent_x = normalize_vector(parent_x)
                parent_y = normalize_vector(parent_y)
                parent_z = normalize_vector(parent_z)
                
                end_x = normalize_vector(end_x)
                end_y = normalize_vector(end_y)
                end_z = normalize_vector(end_z)
                
                # 检查轴向对齐
                x_angle = calculate_angle_between_vectors(parent_x, end_x)
                y_angle = calculate_angle_between_vectors(parent_y, end_y)
                z_angle = calculate_angle_between_vectors(parent_z, end_z)
                
                # 如果任何一个轴向的角度偏差大于5度，认为是不对齐
                if x_angle > 5.0 or y_angle > 5.0 or z_angle > 5.0:
                    short_name = cmds.ls(end_joint, shortNames=True)[0]
                    parent_short_name = cmds.ls(parent_joint, shortNames=True)[0]
                    
                    misaligned_joints.append({
                        'joint': end_joint,
                        'short_name': short_name,
                        'parent': parent_joint,
                        'parent_short': parent_short_name,
                        'angles': (x_angle, y_angle, z_angle)
                    })
                    
                    self.fix_results_text.append(f"发现不对齐: {short_name} (父级: {parent_short_name})")
                    self.fix_results_text.append(f"  角度偏差: X={x_angle:.2f}°, Y={y_angle:.2f}°, Z={z_angle:.2f}°")
                    
                    # 尝试修复
                    if align_joint_axes(end_joint, parent_joint):
                        fixed_joints.append(short_name)
                        self.fix_results_text.append(self.format_status(f"  [OK] 已修复: {short_name}"))
                    else:
                        self.fix_results_text.append(self.format_status(f"  [ERR] 修复失败: {short_name}"))
            
            # 输出结果总结
            self.fix_results_text.append("="*50)
            self.fix_results_text.append("末端骨骼轴向对齐检查完成")
            self.fix_results_text.append("="*50)
            
            if misaligned_joints:
                self.fix_results_text.append(f"发现 {len(misaligned_joints)} 个不对齐的末端骨骼:")
                for joint_info in misaligned_joints:
                    self.fix_results_text.append(f"- {joint_info['short_name']} (父级: {joint_info['parent_short']})")
                    self.fix_results_text.append(f"  角度: X={joint_info['angles'][0]:.2f}°, Y={joint_info['angles'][1]:.2f}°, Z={joint_info['angles'][2]:.2f}°")
                
                if fixed_joints:
                    self.fix_results_text.append(self.format_status(f"[OK] 成功修复 {len(fixed_joints)} 个骨骼:"))
                    for joint_name in fixed_joints:
                        self.fix_results_text.append(f"- {joint_name}")
                else:
                    self.fix_results_text.append(self.format_status("[ERR] 没有成功修复任何骨骼"))
            else:
                self.fix_results_text.append(self.format_status("[OK] 所有末端骨骼轴向都已正确对齐"))

        check_and_fix_end_joint_alignment()

    def check_and_fix_end_joint_axis_alignment(self, nodes_to_process=None):
        """
        检查并修复末端骨骼与父级轴向一致性
        
        参数:
            nodes_to_process: 要处理的节点列表，如果为None则检查场景中所有末端骨骼
            
        返回:
            int: 修复的末端骨骼数量
        """
        
        def get_end_joints():
            """获取末端骨骼列表"""
            if nodes_to_process:
                # 如果指定了处理节点，只检查这些节点中的末端骨骼
                end_joints = []
                for node in nodes_to_process:
                    if cmds.objectType(node) == 'joint':
                        children = cmds.listRelatives(node, children=True, type='joint') or []
                        if not children:  # 没有子关节的就是末端骨骼
                            end_joints.append(node)
            else:
                # 检查场景中所有末端骨骼
                all_joints = cmds.ls(type='joint', long=True)
                end_joints = [j for j in all_joints if not cmds.listRelatives(j, children=True, type='joint')]
            
            return end_joints
        
        def check_joint_alignment(end_joint, parent_joint):
            """检查单个末端骨骼与父级的轴向对齐情况"""
            # 轴向对应的矩阵索引（Maya列主序矩阵）
            axis_indices = {
                'x': [0, 1, 2],
                'y': [4, 5, 6],
                'z': [8, 9, 10]
            }
            
            # 角度阈值：超过5度视为不一致
            angle_threshold = 5.0
            rad_threshold = math.radians(angle_threshold)
            
            # 获取父子骨骼世界矩阵
            try:
                parent_matrix = cmds.xform(parent_joint, q=True, ws=True, matrix=True)
                end_matrix = cmds.xform(end_joint, q=True, ws=True, matrix=True)
            except:
                return False  # 矩阵获取失败
            
            # 检查各轴向是否一致
            for axis_name, axis in axis_indices.items():
                # 父级轴向向量归一化
                parent_vec = [parent_matrix[axis[0]], parent_matrix[axis[1]], parent_matrix[axis[2]]]
                parent_len = math.sqrt(sum(v**2 for v in parent_vec))
                if parent_len < 0.0001:
                    continue
                parent_norm = [v / parent_len for v in parent_vec]
                
                # 末端骨骼轴向向量归一化
                end_vec = [end_matrix[axis[0]], end_matrix[axis[1]], end_matrix[axis[2]]]
                end_len = math.sqrt(sum(v**2 for v in end_vec))
                if end_len < 0.0001:
                    continue
                end_norm = [v / end_len for v in end_vec]
                
                # 计算夹角
                dot = sum(a*b for a, b in zip(parent_norm, end_norm))
                dot = max(min(dot, 1.0), -1.0)  # 修正数值误差
                angle = math.acos(dot)
                
                if angle > rad_threshold:
                    return True  # 存在轴向不一致
            
            return False  # 轴向一致
        
        def fix_joint_alignment(end_joint):
            """修复单个末端骨骼的轴向对齐"""
            try:
                # 使用指定命令修复末端骨骼轴向
                cmds.joint(end_joint, e=True, oj='none', ch=True, zso=True)
                return True
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 修复末端骨骼 {cmds.ls(end_joint, shortNames=True)[0]} 时出错: {str(e)}"))
                return False
        
        # 主逻辑
        fix_end_joint_alignment_count = 0
        
        # 1. 获取末端骨骼列表
        end_joints = get_end_joints()
        
        if not end_joints:
            self.fix_results_text.append(self.format_status("[OK] 场景中无末端骨骼（无子代的骨骼）"))
            return 0
        
        self.fix_results_text.append(f"找到 {len(end_joints)} 个末端骨骼")
        
        # 2. 检查并修复每个末端骨骼
        for end_joint in end_joints:
            # 获取父级骨骼（仅骨骼类型）
            parent_joint = cmds.listRelatives(end_joint, parent=True, type='joint', fullPath=True)
            if not parent_joint:
                continue  # 无父级（根骨骼）跳过
            
            parent_joint = parent_joint[0]
            
            # 检查轴向是否对齐
            needs_fix = check_joint_alignment(end_joint, parent_joint)
            
            if needs_fix:
                short_name = cmds.ls(end_joint, shortNames=True)[0]
                parent_short_name = cmds.ls(parent_joint, shortNames=True)[0]
                
                self.fix_results_text.append(f"修复末端骨骼: {short_name} (父级: {parent_short_name})")
                
                # 修复轴向对齐
                if fix_joint_alignment(end_joint):
                    fix_end_joint_alignment_count += 1
        
        # 3. 输出结果
        if fix_end_joint_alignment_count > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 成功修复 {fix_end_joint_alignment_count} 个末端骨骼的轴向对齐"))
        else:
            self.fix_results_text.append(self.format_status("[OK] 所有末端骨骼轴向对齐正常，无需修复"))
        
        return fix_end_joint_alignment_count

    def check_and_fix_cpu_gpu(self, nodes_to_process=None):
        """检查并修复CPU/GPU渲染设置"""
        self.fix_results_text.append("开始检查渲染硬件设置...")
        
        # 从UI获取设备选择
        device_choice = self.gpu_device_combo.currentText()
        
        fix_cpu_gpu_count = 0
        
        # 检查当前渲染器
        current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        
        # 根据不同渲染器检查CPU/GPU渲染设置
        if current_renderer == "arnold":
            # 检查Arnold渲染器是否使用CPU渲染
            if cmds.objExists("defaultArnoldRenderOptions"):
                render_device = cmds.getAttr("defaultArnoldRenderOptions.renderDevice")
                
                # 根据用户选择的设备进行检查和修复
                if device_choice == "CPU渲染":
                    # 用户选择检查CPU渲染，如果使用GPU渲染则修复
                    if render_device != 0:  # 0表示CPU渲染
                        cmds.setAttr("defaultArnoldRenderOptions.renderDevice", 0)
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将Arnold渲染器设置为CPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] Arnold渲染器已经是CPU渲染模式"))
                else:  # GPU渲染
                    # 用户选择检查GPU渲染，如果使用CPU渲染则修复
                    if render_device == 0:  # 0表示CPU渲染
                        cmds.setAttr("defaultArnoldRenderOptions.renderDevice", 1)  # 1表示GPU渲染
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将Arnold渲染器设置为GPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] Arnold渲染器已经是GPU渲染模式"))
        
        elif current_renderer == "vray":
            # 检查VRay渲染器是否使用CPU渲染
            if cmds.objExists("vraySettings"):
                engine_type = cmds.getAttr("vraySettings.engine")
                
                # 根据用户选择的设备进行检查和修复
                if device_choice == "CPU渲染":
                    # 用户选择检查CPU渲染，如果使用GPU渲染则修复
                    if engine_type != 0:  # 0表示CPU渲染
                        cmds.setAttr("vraySettings.engine", 0)
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将VRay渲染器设置为CPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] VRay渲染器已经是CPU渲染模式"))
                else:  # GPU渲染
                    # 用户选择检查GPU渲染，如果使用CPU渲染则修复
                    if engine_type == 0:  # 0表示CPU渲染
                        cmds.setAttr("vraySettings.engine", 1)  # 1表示GPU渲染
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将VRay渲染器设置为GPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] VRay渲染器已经是GPU渲染模式"))
        
        elif current_renderer == "redshift":
            # 检查Redshift渲染器是否使用CPU渲染
            if cmds.objExists("redshiftOptions"):
                device_type = cmds.getAttr("redshiftOptions.deviceType")
                
                # 根据用户选择的设备进行检查和修复
                if device_choice == "CPU渲染":
                    # 用户选择检查CPU渲染，如果使用GPU渲染则修复
                    if device_type != 0:  # 0表示CPU渲染
                        cmds.setAttr("redshiftOptions.deviceType", 0)
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将Redshift渲染器设置为CPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] Redshift渲染器已经是CPU渲染模式"))
                else:  # GPU渲染
                    # 用户选择检查GPU渲染，如果使用CPU渲染则修复
                    if device_type == 0:  # 0表示CPU渲染
                        cmds.setAttr("redshiftOptions.deviceType", 1)  # 1表示GPU渲染
                        self.fix_results_text.append(self.format_status(f"  [OK] 已将Redshift渲染器设置为GPU渲染模式"))
                        fix_cpu_gpu_count = 1
                    else:
                        self.fix_results_text.append(self.format_status("  [OK] Redshift渲染器已经是GPU渲染模式"))
        
        else:
            # 对于其他渲染器，根据用户选择进行检查
            if device_choice == "CPU渲染":
                # 对于其他渲染器，如果用户选择检查CPU渲染，则认为正常
                self.fix_results_text.append(self.format_status(f"  [OK] {current_renderer}渲染器默认使用CPU渲染"))
            else:  # GPU渲染
                # 如果用户选择检查GPU渲染，但对于其他渲染器无法确定，则提示信息
                self.fix_results_text.append(self.format_status(f"  [WARN] {current_renderer}渲染器默认使用CPU渲染，无法设置为GPU渲染"))
        
        return fix_cpu_gpu_count

    def check_and_fix_render_software(self, nodes_to_process=None):
        """检查并修复渲染软件设置"""
        self.fix_results_text.append("开始检查渲染软件设置...")
        
        # 从UI获取渲染器选择
        renderer_choice = self.arnold_renderer_combo.currentText()
        
        # 映射渲染器名称到Maya内部名称
        renderer_map = {
            'Arnold': 'arnold',
            'Vray': 'vray',
            'Redshift': 'redshift'
        }
        
        target_renderer = renderer_map.get(renderer_choice, 'arnold')
        
        # 获取当前渲染器
        current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        
        fix_render_software_count = 0
        
        if current_renderer != target_renderer:
            try:
                cmds.setAttr('defaultRenderGlobals.currentRenderer', target_renderer, type='string')
                self.fix_results_text.append(self.format_status(f"  [OK] 已将渲染器设置为 {renderer_choice}"))
                fix_render_software_count = 1
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"  [ERR] 设置渲染器时出错: {str(e)}"))
        else:
            self.fix_results_text.append(self.format_status(f"  [OK] 当前渲染器已经是 {renderer_choice}"))
        
        return fix_render_software_count

    def check_and_fix_ani_rate(self, nodes_to_process=None):
        """检查并修复动画帧率设置"""
        self.fix_results_text.append("开始设置动画帧率...")
        
        # 从UI下拉框获取选中的帧率
        target_fps = self.frame_rate_combo.currentData()
        
        fix_ani_rate_count = 0
        
        try:
            # 映射帧率到时间单位
            fps_to_time_unit = {
                15: 'game',
                24: 'film', 
                25: 'pal',
                30: 'ntsc',
                48: 'show',
                50: 'palf', 
                60: 'ntscf',
                1000: 'millisecond'
            }
            
            # 获取对应的时间单位
            target_time_unit = fps_to_time_unit.get(target_fps, 'ntsc')
            
            # 获取当前帧率设置
            current_time_unit = cmds.currentUnit(query=True, time=True)
            
            # 映射时间单位到帧率（用于显示）
            time_unit_to_fps = {
                'game': 15,
                'film': 24,
                'pal': 25,
                'ntsc': 30,
                'show': 48,
                'palf': 50,
                'ntscf': 60,
                'millisecond': 1000,
                'second': 1,
                'minute': 1/60,
                'hour': 1/3600
            }
            
            current_fps = time_unit_to_fps.get(current_time_unit, 0)
            
            # 检查当前帧率是否已经是目标帧率
            if abs(current_fps - target_fps) < 0.1:
                self.fix_results_text.append(self.format_status(f"  [OK] 当前帧率已经是 {target_fps} FPS，无需修改"))
                fix_ani_rate_count = 0
            else:
                # 设置新的时间单位
                cmds.currentUnit(time=target_time_unit)
                
                # 验证设置是否成功
                new_time_unit = cmds.currentUnit(query=True, time=True)
                new_fps = time_unit_to_fps.get(new_time_unit, 0)
                
                if abs(new_fps - target_fps) < 0.1:
                    self.fix_results_text.append(self.format_status(f"  [OK] 已成功将帧率设置为 {target_fps} FPS"))
                    fix_ani_rate_count = 1
                else:
                    self.fix_results_text.append(self.format_status(f"  [ERR] 设置帧率失败，当前帧率仍为 {new_fps} FPS"))
                    fix_ani_rate_count = 0
                    
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"  [ERR] 设置帧率时出错: {str(e)}"))
            fix_ani_rate_count = 0
        
        return fix_ani_rate_count

    def check_and_fix_timeline_range(self, nodes_to_process=None):
        """检查并修复时间轴范围设置"""
        self.fix_results_text.append("开始设置时间轴范围...")
        
        # 从UI获取开始帧和结束帧
        try:
            target_start_frame = int(self.timeline_start_input.text())
        except ValueError:
            target_start_frame = 0
        try:
            target_end_frame = int(self.timeline_end_input.text())
        except ValueError:
            target_end_frame = 150
        
        fix_timeline_count = 0
        
        try:
            # 获取当前时间轴设置
            current_start_time = cmds.playbackOptions(query=True, minTime=True)
            current_end_time = cmds.playbackOptions(query=True, maxTime=True)
            current_animation_start = cmds.playbackOptions(query=True, animationStartTime=True)
            current_animation_end = cmds.playbackOptions(query=True, animationEndTime=True)
            
            # 检查是否需要修改
            needs_fix = False
            
            if (current_start_time != target_start_frame or 
                current_end_time != target_end_frame or 
                current_animation_start != target_start_frame or 
                current_animation_end != target_end_frame):
                needs_fix = True
            
            if needs_fix:
                # 设置时间轴范围
                cmds.playbackOptions(minTime=target_start_frame, maxTime=target_end_frame)
                cmds.playbackOptions(animationStartTime=target_start_frame, animationEndTime=target_end_frame)
                
                # 验证设置是否成功
                new_start_time = cmds.playbackOptions(query=True, minTime=True)
                new_end_time = cmds.playbackOptions(query=True, maxTime=True)
                new_animation_start = cmds.playbackOptions(query=True, animationStartTime=True)
                new_animation_end = cmds.playbackOptions(query=True, animationEndTime=True)
                
                if (new_start_time == target_start_frame and 
                    new_end_time == target_end_frame and 
                    new_animation_start == target_start_frame and 
                    new_animation_end == target_end_frame):
                    self.fix_results_text.append(self.format_status(f"  [OK] 已成功将时间轴范围设置为 {target_start_frame}-{target_end_frame} 帧"))
                    fix_timeline_count = 1
                else:
                    self.fix_results_text.append(self.format_status(f"  [ERR] 设置时间轴范围失败"))
            else:
                self.fix_results_text.append(self.format_status(f"  [OK] 时间轴范围已经是 {target_start_frame}-{target_end_frame} 帧，无需修改"))
                
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"  [ERR] 设置时间轴范围时出错: {str(e)}"))
        
        return fix_timeline_count

    def check_and_fix_animation_range(self, nodes_to_process=None):
        """检查并修复关键帧动画范围，删除范围外的关键帧并在边界设置关键帧"""
        self.fix_results_text.append("开始修复关键帧动画范围...")
        
        # 从UI获取开始帧和结束帧
        try:
            target_start_frame = int(self.anim_range_start_input.text())
        except ValueError:
            target_start_frame = 0
        try:
            target_end_frame = int(self.anim_range_end_input.text())
        except ValueError:
            target_end_frame = 150
        
        fixed_count = 0
        
        try:
            # 获取场景中所有动画曲线
            anim_curves = cmds.ls(type='animCurve')
            
            if not anim_curves:
                self.fix_results_text.append("场景中没有找到动画曲线")
                return 0
            
            self.fix_results_text.append(f"检查范围: {target_start_frame}-{target_end_frame} 帧")
            self.fix_results_text.append(f"找到 {len(anim_curves)} 条动画曲线")
            
            # 处理每条动画曲线
            for anim_curve in anim_curves:
                try:
                    # 获取动画曲线的所有关键帧时间
                    key_times = cmds.keyframe(anim_curve, query=True, timeChange=True)
                    
                    if not key_times:
                        continue
                    
                    # 检查是否有超出范围的关键帧
                    out_of_range_keys = []
                    for time in key_times:
                        if time < target_start_frame or time > target_end_frame:
                            out_of_range_keys.append(time)
                    
                    if out_of_range_keys:
                        self.fix_results_text.append(f"动画曲线 '{anim_curve}' 有 {len(out_of_range_keys)} 个超出范围的关键帧")
                        
                        # 获取动画曲线连接的属性
                        connections = cmds.listConnections(anim_curve, plugs=True, destination=True)
                        if not connections:
                            continue
                        
                        connected_attr = connections[0]
                        
                        # 在范围开始和结束处设置关键帧
                        try:
                            # 获取开始帧的值
                            start_value = cmds.getAttr(connected_attr, time=target_start_frame)
                            # 在开始帧设置关键帧
                            cmds.setKeyframe(connected_attr, time=target_start_frame, value=start_value)
                            
                            # 获取结束帧的值
                            end_value = cmds.getAttr(connected_attr, time=target_end_frame)
                            # 在结束帧设置关键帧
                            cmds.setKeyframe(connected_attr, time=target_end_frame, value=end_value)
                            
                            # 删除范围外的关键帧
                            for time in out_of_range_keys:
                                cmds.cutKey(anim_curve, time=(time, time))
                            
                            fixed_count += 1
                            self.fix_results_text.append(self.format_status(f"  [OK] 已修复: 在 {target_start_frame} 和 {target_end_frame} 帧设置关键帧，并删除范围外关键帧"))
                            
                        except Exception as e:
                            self.fix_results_text.append(self.format_status(f"  [ERR] 修复失败: {str(e)}"))
                    
                except Exception as e:
                    self.fix_results_text.append(f"处理动画曲线 '{anim_curve}' 时出错: {str(e)}")
            
            if fixed_count > 0:
                self.fix_results_text.append(self.format_status(f"[OK] 成功修复 {fixed_count} 条动画曲线的关键帧范围"))
            else:
                self.fix_results_text.append("没有找到需要修复的关键帧范围问题")
                    
        except Exception as e:
            self.fix_results_text.append(self.format_status(f"[ERR] 修复关键帧动画范围时出错: {str(e)}"))
        
        return fixed_count
    
    def addGeometrySuffix(self, nodes_to_process=None, suffix="_Geo"):
        """
        检查并为场景中所有模型添加指定的后缀名
        :param nodes_to_process: 可选参数，指定要处理的模型列表，None则处理所有模型
        :param suffix: 要添加的后缀，默认为"_Geo"
        :return: 成功修改名称的模型数量
        """
        renamed_geometry_count = 0
        
        # 获取需要处理的模型（有网格形状的变换节点）
        if nodes_to_process is None:
            # 获取所有变换节点
            all_transforms = cmds.ls(type='transform')
        else:
            # 处理传入的节点列表
            all_transforms = []
            for uuid in nodes_to_process:
                node_name = getNodeNameFromUUID(uuid)
                if node_name and cmds.objExists(node_name) and cmds.nodeType(node_name) == 'transform':
                    all_transforms.append(node_name)
        
        # 过滤出有网格形状的变换节点（真正的模型）
        models_to_process = []
        for transform in all_transforms:
            shapes = cmds.listRelatives(transform, shapes=True, type='mesh')
            if shapes:
                models_to_process.append(transform)
        
        if not models_to_process:
            self.fix_results_text.append("没有找到需要处理的模型")
            return 0
        
        self.fix_results_text.append(f"开始检查 {len(models_to_process)} 个模型的命名...")
        
        # 检查并重命名不符合后缀要求的模型
        for model in models_to_process:
            try:
                # 检查模型名称是否以指定后缀结尾
                if not model.endswith(suffix):
                    # 生成新的名称：原名称 + 后缀
                    new_name = model + suffix
                    
                    # 确保新名称在场景中是唯一的
                    if cmds.objExists(new_name):
                        # 如果已存在，添加数字后缀
                        counter = 1
                        while cmds.objExists(f"{new_name}_{counter:02d}"):
                            counter += 1
                        new_name = f"{new_name}_{counter:02d}"
                    
                    # 重命名模型
                    cmds.rename(model, new_name)
                    self.fix_results_text.append(f"  - 已将 '{model}' 重命名为 '{new_name}'")
                    renamed_geometry_count += 1
                else:
                    self.fix_results_text.append(f"  - '{model}' 已符合命名规范")
                    
            except Exception as e:
                self.fix_results_text.append(self.format_status(f"[ERR] 重命名模型 '{model}' 时出错: {str(e)}"))
        
        if renamed_geometry_count > 0:
            self.fix_results_text.append(self.format_status(f"[OK] 已成功为 {renamed_geometry_count} 个模型添加后缀名'{suffix}'"))
        else:
            self.fix_results_text.append(f"所有模型都已正确使用'{suffix}'后缀名")
        
        return renamed_geometry_count

    def select_all_checks(self):
        """全选检查项，但确保互斥项不被同时选中（单击事件）"""
        # 先全部选中
        for check_box in self.check_boxes.values():
            check_box.setChecked(True)
            
        # 然后应用互斥逻辑：优先保留"多余关键帧"，取消"关键帧动画范围"
        if "多余关键帧" in self.check_boxes and "关键帧动画范围" in self.check_boxes:
            self.check_boxes["关键帧动画范围"].setChecked(False)
            self.check_boxes["多余关键帧"].setChecked(True)  # 确保多余关键帧被选中

    def select_none_checks(self):
        for check_box in self.check_boxes.values():
            check_box.setChecked(False)
            
    def get_nodes_to_check(self):
        if self.scope_selection.isChecked():
            selection = cmds.ls(selection=True, uuid=True)
            if not selection:
                cmds.warning("没有选择任何对象！")
                return []
            return selection
        else:
            # 获取所有变换节点和层节点
            transforms = cmds.ls(type="transform", uuid=True)
            display_layers = cmds.ls(type="displayLayer", uuid=True)
            anim_layers = cmds.ls(type="animLayer", uuid=True)
            return transforms + display_layers + anim_layers
    
    def create_selection_list(self, nodes):
        selection_list = om.MSelectionList()
        for node in nodes:
            try:
                node_name = _getNodeName(node)
                if node_name and cmds.objExists(node_name):
                    # 检查节点类型，只添加网格类型的节点
                    node_type = cmds.nodeType(node_name)
                    if node_type == "mesh":
                        selection_list.add(node_name)
                    elif node_type == "transform":
                        # 如果是变换节点，检查是否有网格形状
                        shapes = cmds.listRelatives(node_name, shapes=True, type="mesh", fullPath=True) or []
                        for shape in shapes:
                            # 确保形状节点存在
                            if cmds.objExists(shape):
                                selection_list.add(shape)
            except Exception as e:
                print(f"创建选择列表时出错: {e}")
                continue
        return selection_list
    
    def run_checks(self):
            self.results_text.clear()
            self.results = {}
            
            # 获取要检查的节点
            nodes = self.get_nodes_to_check()
            if not nodes:
                self.results_text.setText("没有找到要检查的对象！")
                return
                
            self.results_text.append(f"开始检查 {len(nodes)} 个对象...\n")
            
            # 创建选择列表用于需要MSelectionList的检查
            selection_list = self.create_selection_list(nodes)
            
            # 运行选中的检查
            for check_name, check_func in self.check_functions.items():
                if check_name not in self.check_boxes or not self.check_boxes[check_name].isChecked():
                    continue
                    
                self.results_text.append(f"正在检查: {check_name}...")
                QtCore.QCoreApplication.processEvents()  # 更新UI
                
                try:
                    # 为"骨骼旋转方向"检查准备参数
                    if check_name == "骨骼旋转方向":
                        # 获取选中的旋转顺序索引
                        target_rotate_order = self.orient_axis_combo.currentIndex()
                        params = {'target_rotate_order': target_rotate_order}
                        result_type, result_data = check_func(nodes, params)

                    # 为"模型面数"检查准备参数
                    elif check_name == "模型面数":
                        # 从UI获取面数上限
                        try:
                            face_limit_value = int(self.face_limit_input.text())
                        except ValueError:
                            face_limit_value = 10000
                        params = {'face_limit': face_limit_value}
                        result_type, result_data = check_func(nodes, params)

                    # 为"镜像骨骼"检查准备参数
                    elif check_name == "镜像骨骼":
                        # 从UI获取左右后缀名
                        left_suffix_text = self.left_suffix_input.text()
                        right_suffix_text = self.right_suffix_input.text()
                        params = {
                            'left_suffix': left_suffix_text,
                            'right_suffix': right_suffix_text
                        }
                        result_type, result_data = check_func(nodes, params)

                    # 为"重叠顶点"检查准备参数
                    elif check_name == "重叠顶点":
                        # 从UI获取容差值
                        try:
                            tolerance_value = float(self.overlap_vertex_tolerance.text())
                        except ValueError:
                            tolerance_value = 0.001
                        params = {'tolerance': tolerance_value}
                        result_type, result_data = check_func(nodes, params)

                    # 为"模型命名"检查准备参数
                    elif check_name == "模型命名":
                        # 从UI获取后缀
                        suffix_text = self.geometry_suffix_input.text()
                        params = {'suffix': suffix_text}
                        result_type, result_data = check_func(nodes, params)

                    # 为"模型高/低于地面"检查准备参数
                    elif check_name == "模型高/低于地面":
                        # 从UI获取容差值
                        try:
                            tolerance_value = float(self.ground_tolerance.text())
                        except ValueError:
                            tolerance_value = 0.001
                        params = {'tolerance': tolerance_value}
                        result_type, result_data = check_func(nodes, params)

                    # 为"渲染硬件"检查准备参数
                    elif check_name == "渲染硬件":
                        # 获取设备选择
                        device_choice = self.gpu_device_combo.currentText()
                        params = {'device': device_choice}
                        # 创建空的MSelectionList，因为checkCPURendering需要这个参数但实际不使用
                        empty_selection = om.MSelectionList()
                        result_type, result_data = check_func(nodes, empty_selection, params)

                    # 为"渲染软件"检查准备参数
                    elif check_name == "渲染软件":
                        # 获取选中的渲染器
                        renderer_choice = self.arnold_renderer_combo.currentText()
                        params = {'renderer': renderer_choice}
                        # 创建一个空的MSelectionList，因为检查函数需要这个参数但实际不使用
                        empty_selection = om.MSelectionList()
                        result_type, result_data = check_func(nodes, empty_selection, params)

                    # 在run_checks方法中，为"骨骼命名"检查准备参数
                    elif check_name == "骨骼命名":
                        # 从UI获取后缀
                        suffix_text = self.joint_suffix_input.text()
                        params = {'suffix': suffix_text}
                        result_type, result_data = check_func(nodes, selection_list, params)

                    # 为"骨骼数量"检查准备参数
                    elif check_name == "骨骼数量":
                        # 从UI获取限制值
                        try:
                            limit_value = int(self.joint_limit_input.text())
                        except ValueError:
                            limit_value = 35
                        params = {'limit': limit_value}
                        result_type, result_data = check_func(nodes, params)

                    # 为"帧率设置"检查准备参数
                    elif check_name == "帧率设置":
                        # 从UI下拉框获取选中的帧率
                        target_fps = self.frame_rate_combo.currentData()
                        params = {'fps': target_fps}
                        result_type, result_data = check_func(nodes, params)

                    # 为"时间轴设置"检查准备参数
                    elif check_name == "时间轴设置":
                        # 从UI获取开始帧和结束帧
                        try:
                            target_start_frame = int(self.timeline_start_input.text())
                        except ValueError:
                            target_start_frame = 0
                        try:
                            target_end_frame = int(self.timeline_end_input.text())
                        except ValueError:
                            target_end_frame = 150
                        params = {
                            'start_frame': target_start_frame,
                            'end_frame': target_end_frame
                        }
                        result_type, result_data = check_func(nodes, params)

                    # 为"关键帧动画范围"检查准备参数
                    elif check_name == "关键帧动画范围":
                        # 从UI获取开始帧和结束帧
                        try:
                            target_start_frame = int(self.anim_range_start_input.text())
                        except ValueError:
                            target_start_frame = 0
                        try:
                            target_end_frame = int(self.anim_range_end_input.text())
                        except ValueError:
                            target_end_frame = 150
                        params = {
                            'start_frame': target_start_frame,
                            'end_frame': target_end_frame
                        }
                        result_type, result_data = check_func(nodes, params)

                    # 为"父骨未朝子"检查准备参数
                    elif check_name == "父骨未朝子":
                        # 获取第一个下拉框的值
                        orient_joint = self.orient_axis_combo1.currentText()
                        params = {'orientJoint': orient_joint}
                        result_type, result_data = check_func(nodes, params)

                    # 判断函数是否需要MSelectionList参数
                    elif check_func.__code__.co_argcount == 2:
                        # 特殊处理权重丢失检查，它返回三个值但我们需要前两个
                        if check_name == "权重丢失":
                            result_type, result_data, _ = check_func(nodes, selection_list)
                        else:
                            result_type, result_data = check_func(nodes, selection_list)
                    else:
                        result_type, result_data = check_func(nodes, None)
                        
                    self.results[check_name] = (result_type, result_data)
                    
                    # 特殊处理"历史记录检查"的结果
                    if check_name == "历史记录检查":
                        if isinstance(result_data, dict) and result_data:
                            self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题:</span>')
                            for node_uuid, issues in result_data.items():
                                node_name = _getNodeName(node_uuid)
                                if node_name:
                                    self.results_text.append(f"    - {node_name}:")
                                    for issue in issues:
                                        self.results_text.append(f"      {issue}")
                            continue

                    # 特殊处理"模型面数"检查的结果显示
                    if check_name == "模型面数":
                        if result_data:
                            self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {len(result_data)} 个模型面数超过限制</span>')
                            for model_info in result_data[:3]:  # 只显示前3个
                                self.results_text.append(f"    - {model_info['display_name']}: {model_info['triangle_count']} 三角面 (限制: {model_info['face_limit']})")
                            if len(result_data) > 3:
                                self.results_text.append(f"    ... 还有 {len(result_data) - 3} 个模型")
                        else:
                            self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                        continue

                    # 显示其他检查的结果
                    if isinstance(result_data, dict):
                        # 特殊处理权重对称性检查结果
                        if check_name == "镜像权重" and 'summary' in result_data:
                            issue_count = result_data['summary']['asymmetric_pairs']
                            if issue_count > 0:
                                self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 对顶点权重不对称</span>')
                            else:
                                self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                        else:
                            issue_count = sum(len(v) for v in result_data.values())
                            if issue_count > 0:
                                # 显示有问题节点的名称
                                problem_nodes = []
                                for node_uuid in result_data.keys():
                                    node_name = _getNodeName(node_uuid)
                                    if node_name:
                                        problem_nodes.append(node_name)
                                
                                if problem_nodes:
                                    # 只显示前5个问题节点，避免输出过多
                                    display_nodes = problem_nodes[:5]
                                    node_list = ", ".join(display_nodes)
                                    if len(problem_nodes) > 5:
                                        node_list += f" 等 {len(problem_nodes)} 个节点"
                                    self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个 - {node_list}</span>')
                                else:
                                    self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个</span>')
                            else:
                                self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                    
                            
                    elif isinstance(result_data, list):
                        issue_count = len(result_data)
                        if issue_count > 0:
                            # 显示有问题节点的名称
                            problem_nodes = []
                            for node_uuid in result_data:
                                node_name = _getNodeName(node_uuid)
                                if node_name:
                                    problem_nodes.append(node_name)
                            
                            if problem_nodes:
                                # 只显示前5个问题节点，避免输出过多
                                display_nodes = problem_nodes[:5]
                                node_list = ", ".join(display_nodes)
                                if len(problem_nodes) > 5:
                                    node_list += f" 等 {len(problem_nodes)} 个节点"
                                self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个 - {node_list}</span>')
                            else:
                                self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个</span>')
                        else:
                            self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                            
                    # 新增：处理"父骨未朝子"检查的特殊情况
                    elif check_name == "父骨未朝子" and result_type == "nodes" and result_data:
                        issue_count = len(result_data)
                        if issue_count > 0:
                            # 显示有问题节点的名称
                            problem_nodes = []
                            for node_uuid in result_data:
                                node_name = _getNodeName(node_uuid)
                                if node_name:
                                    problem_nodes.append(node_name)
                            
                            if problem_nodes:
                                # 只显示前5个问题节点，避免输出过多
                                display_nodes = problem_nodes[:5]
                                node_list = ", ".join(display_nodes)
                                if len(problem_nodes) > 5:
                                    node_list += f" 等 {len(problem_nodes)} 个节点"
                                self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个 - {node_list}</span>')
                            else:
                                self.results_text.append(f'<span style="color: red; font-weight: bold;">  [ERR] 发现问题: {issue_count} 个</span>')
                        else:
                            self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                            
                    else:
                        issue_count = 0
                        self.results_text.append(f'<span style="color: green; font-weight: bold;">  [OK] 通过</span>')
                        
                except Exception as e:
                    self.results_text.append(f'<span style="color: yellow; font-weight: bold;">  [WARN] 检查出错: {str(e)}</span>')
                    
            self.results_text.append("\n检查完成！")
            self.select_problem_btn.setEnabled(True)
                
    def select_problem_objects(self):
        problem_objects = set()
        
        for check_name, (result_type, result_data) in self.results.items():
            if not result_data:
                continue
                
            # 处理权重丢失检查的特殊格式
            if check_name == "权重丢失":
                # 权重丢失检查返回的是 (类型, 结果字典, 问题模型数量)
                if isinstance(result_data, tuple) and len(result_data) >= 2:
                    actual_data = result_data[1]
                    for node_uuid in actual_data.keys():
                        # 跳过全局统计信息键
                        if node_uuid == "global_skin_stats":
                            continue
                        node_name = _getNodeName(node_uuid)
                        if node_name and cmds.objExists(node_name):
                            problem_objects.add(node_name)
                continue
                
            # 处理历史记录检查的特殊格式
            if check_name == "历史记录检查" and isinstance(result_data, dict):
                for node_uuid in result_data.keys():
                    node_name = _getNodeName(node_uuid)
                    if node_name and cmds.objExists(node_name):
                        problem_objects.add(node_name)
                continue
                
            # 处理镜像权重检查的特殊格式
            if check_name == "镜像权重" and isinstance(result_data, dict):
                if 'summary' in result_data and result_data['summary']['asymmetric_pairs'] > 0:
                    # 获取所有涉及的节点
                    if 'details' in result_data:
                        for detail in result_data['details']:
                            # 从详细信息中提取节点名称
                            if "顶点" in detail and "和" in detail:
                                parts = detail.split("顶点 ")[1].split(" 和 ")
                                for part in parts:
                                    node_name = part.split(".vtx")[0]
                                    if node_name and cmds.objExists(node_name):
                                        problem_objects.add(node_name)
                continue
            
            # 处理"父骨未朝子"检查的特殊格式
            if check_name == "父骨未朝子" and result_type == "nodes" and isinstance(result_data, list):
                for node_uuid in result_data:
                    node_name = _getNodeName(node_uuid)
                    if node_name and cmds.objExists(node_name):
                        problem_objects.add(node_name)
                continue
                
            # 处理普通字典类型结果
            if isinstance(result_data, dict):
                for node_uuid in result_data.keys():
                    # 跳过全局统计信息键
                    if node_uuid.startswith("global_"):
                        continue
                    node_name = _getNodeName(node_uuid)
                    if node_name and cmds.objExists(node_name):
                        problem_objects.add(node_name)
            
            # 处理列表类型结果
            elif isinstance(result_data, list):
                # 处理字典列表（如模型对称检查的结果）
                if result_data and isinstance(result_data[0], dict):
                    for item in result_data:
                        if 'node' in item:
                            node_uuid = item['node']
                            node_name = _getNodeName(node_uuid)
                            if node_name and cmds.objExists(node_name):
                                problem_objects.add(node_name)
                else:
                    # 处理普通UUID列表
                    for node_uuid in result_data:
                        node_name = _getNodeName(node_uuid)
                        if node_name and cmds.objExists(node_name):
                            problem_objects.add(node_name)
        
        if problem_objects:
            cmds.select(list(problem_objects))
            self.results_text.append(f"\n已选择 {len(problem_objects)} 个问题对象")
        else:
            self.results_text.append("\n没有找到问题对象")

    def browse_save_path(self):
        """浏览保存路径"""
        # 获取当前输入的路径
        current_path = self.doc_path_input.text().strip()
        
        # 如果当前路径为空，使用桌面作为默认路径
        if not current_path:
            current_path = os.path.expanduser("~/Desktop")
        
        # 打开文件夹选择对话框选择保存目录
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "选择保存目录", 
            current_path
        )
        
        # 如果用户选择了目录，更新输入框（只显示目录路径，不包含文件名）
        if folder_path:
            self.doc_path_input.setText(folder_path)

    def generate_report_filename(self):
        """生成报告文件名"""
        # 获取Maya版本
        maya_version = cmds.about(version=True)
        
        # 获取当前场景文件名
        scene_name = cmds.file(query=True, sceneName=True)
        if scene_name:
            # 提取文件名（不含路径和扩展名）
            base_name = os.path.splitext(os.path.basename(scene_name))[0]
        else:
            base_name = "Untitled"
        
        # 获取当前时间（保存按钮点击时的时间）
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 组合文件名
        filename = f"CheckResults_maya{maya_version}_{base_name}_{current_time}.md"
        return filename

    def format_status(self, text):
        """格式化状态文本，添加颜色和加粗"""
        if '[OK]' in text:
            return f"<span style=\"color:green; font-weight:bold\">{text}</span>"
        elif '[WARN]' in text:
            return f"<span style=\"color:orange; font-weight:bold\">{text}</span>"
        elif '[ERR]' in text:
            return f"<span style=\"color:red; font-weight:bold\">{text}</span>"
        return text

    def save_to_markdown(self):
        """保存检查结果为Markdown文件"""
        save_dir = self.doc_path_input.text().strip()
        
        # 检查目录是否为空
        if not save_dir:
            self.fix_results_text.setText(self.format_status("[ERR] 发现问题：文件地址为空"))
            return
        
        # 检查目录是否存在，如果不存在则尝试创建
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                self.fix_results_text.setText(self.format_status(f"[ERR] 发现问题：无法创建目录 - {str(e)}"))
                return
        
        # 生成文件名（使用当前时间）
        filename = self.generate_report_filename()
        save_path = os.path.join(save_dir, filename)
        
        # 获取检查结果文本
        check_text = self.results_text.toPlainText()
        
        if not check_text.strip():
            self.fix_results_text.setText(self.format_status("[ERR] 发现问题：没有检查结果可保存"))
            return
        
        try:
            # 解析检查结果并生成Markdown报告
            check_data = self.parse_check_results(check_text)
            markdown_content = self.generate_markdown_report(check_data, check_text)
            
            # 保存文件
            self.save_markdown_file(markdown_content, save_path)
            
            # 显示成功消息
            self.fix_results_text.setText(self.format_status(f"[OK] 文件已保存到: {save_path}"))
            
        except Exception as e:
            self.fix_results_text.setText(self.format_status(f"[ERR] 发现问题：保存失败 - {str(e)}"))

    def parse_check_results(self, text):
        """
        解析检查结果文本，提取结构化数据
        """
        lines = text.strip().split('\n')
        results = []
        current_check = ""
        
        for line in lines:
            line = line.strip()
            
            # 跳过开始和结束的统计行
            if line.startswith('开始检查') or line.startswith('检查完成'):
                continue
                
            # 匹配检查项
            if line.startswith('正在检查:'):
                current_check = line.replace('正在检查:', '').strip()
                continue
                
            # 匹配检查结果
            if line.startswith('[OK]') or line.startswith('[ERR]'):
                if line.startswith('[OK] 通过'):
                    results.append({
                        '检查项目': current_check,
                        '状态': self.format_status('[OK] 通过'),
                        '问题数量': 0,
                        '问题对象': '',
                        '严重程度': '无'
                    })
                elif line.startswith('[ERR] 发现问题:'):
                    # 使用正则表达式提取问题数量和对象
                    match = re.search(r'\[ERR\] 发现问题: (\d+) 个(?: - (.*))?', line)
                    if match:
                        problem_count = int(match.group(1))
                        problem_objects = match.group(2) if match.group(2) else '未知对象'
                        
                        # 根据检查项目判断严重程度
                        severity = self.format_status('[WARN] 警告')
                        critical_checks = ['构造历史', '未冻结变换', '模型高/低于地面', '帧率设置', '时间轴设置']
                        if any(critical in current_check for critical in critical_checks):
                            severity = self.format_status('[ERR] 严重')
                        
                        results.append({
                            '检查项目': current_check,
                            '状态': self.format_status('[ERR] 失败'),
                            '问题数量': problem_count,
                            '问题对象': problem_objects,
                            '严重程度': severity
                        })
        
        return results

    def generate_markdown_report(self, check_data, check_text):
        """
        生成Markdown格式的报告
        """
        # 统计信息
        total_checks = len(check_data)
        passed_checks = len([x for x in check_data if '通过' in x['状态']])
        failed_checks = len([x for x in check_data if '失败' in x['状态']])
        critical_issues = len([x for x in check_data if '严重' in x['严重程度']])
        warning_issues = len([x for x in check_data if '警告' in x['严重程度']])
        total_problems = sum([x['问题数量'] for x in check_data])
        
        # 提取开始检查的对象数
        start_match = re.search(r'开始检查 (\d+) 个对象', check_text)
        object_count = start_match.group(1) if start_match else "未知"
        
        # 生成Markdown内容
        markdown_content = f"""# 场景检查报告

    > 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    ## 检查概览

    | 统计项 | 数量 |
    |--------|------|
    | 检查对象数 | {object_count} |
    | 总检查项目 | {total_checks} |
    | 通过项目 | {passed_checks} |
    | 失败项目 | {failed_checks} |
    | 严重问题 | {critical_issues} |
    | 警告问题 | {warning_issues} |
    | 总问题数量 | {total_problems} |
    | 通过率 | {passed_checks/total_checks*100:.1f}% |

    ## 详细检查结果

    | 检查项目 | 状态 | 严重程度 | 问题数量 | 问题对象 |
    |----------|------|----------|----------|----------|
    """
        
        # 添加检查结果表格行
        for check in check_data:
            # 处理问题对象字段，如果太长则截断
            problem_objects = check['问题对象']
            if len(problem_objects) > 50:
                problem_objects = problem_objects[:47] + "..."
            
            # 格式化状态和严重程度
            status_formatted = check['状态']  # 已经在parse_check_results中格式化
            severity_formatted = check['严重程度']  # 已经在parse_check_results中格式化
            
            markdown_content += f"| {check['检查项目']} | {status_formatted} | {severity_formatted} | {check['问题数量']} | {problem_objects} |\n"
        
        # 添加问题详情部分
        failed_checks_list = [check for check in check_data if '失败' in check['状态']]
        if failed_checks_list:
            markdown_content += f"""
    ## {self.format_status('[ERR]')} 问题详情

    以下是所有失败的检查项目详情：

    """
            for check in failed_checks_list:
                markdown_content += f"### {check['检查项目']}\n"
                markdown_content += f"- **状态**: {check['状态']}\n"
                markdown_content += f"- **严重程度**: {check['严重程度']}\n"
                markdown_content += f"- **问题数量**: {check['问题数量']}\n"
                if check['问题对象']:
                    markdown_content += f"- **问题对象**: {check['问题对象']}\n"
                markdown_content += "\n"
        
        # 添加分类统计
        markdown_content += f"""
    ## 分类统计

    ### 按严重程度分类
    - 严重问题: {critical_issues} 项
    - {self.format_status('[WARN]')} 警告问题: {warning_issues} 项
    - {self.format_status('[OK]')} 无问题: {passed_checks} 项

    ### 按问题数量排序（前5名）
    """
        
        # 按问题数量排序
        sorted_by_problems = sorted([check for check in check_data if check['问题数量'] > 0], 
                                key=lambda x: x['问题数量'], reverse=True)
        
        for i, check in enumerate(sorted_by_problems[:5]):
            markdown_content += f"{i+1}. **{check['检查项目']}**: {check['问题数量']} 个问题\n"
        
        # 添加总结
        markdown_content += f"""
    ## 总结与建议

    本次检查共发现 **{total_problems}** 个问题，涉及 **{failed_checks}** 个检查项目。

    ### 建议处理优先级：
    1. 首先处理 **{critical_issues}** 个严重问题
    2. 其次处理 **{warning_issues}** 个警告问题
    3. 重新检查修复后的项目

    ---
    *报告生成完成* {self.format_status('[OK]')}
    """
        
        return markdown_content

    def save_markdown_file(self, markdown_content, save_path):
        """
        将Markdown内容保存到文件
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 写入文件
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

# 显示UI
def show_ui():
    # 查找Maya主窗口
    maya_main_window = None
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == "MayaWindow":
            maya_main_window = widget
            break
            
    global model_checker_ui
    try:
        model_checker_ui.close()
    except:
        pass
        
    model_checker_ui = ModelCheckerUI(maya_main_window)
    model_checker_ui.show()

# 运行UI
if __name__ == "__main__":
    show_ui()
