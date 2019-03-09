from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

import PythonQt
import csv
import cv2
import inspect
import math
import numpy as np
import os
import string
import subprocess
import time
import yaml

from Helper import *

class ScrewStep(ctk.ctkWorkflowWidgetStep):
    
    def __init__( self, stepid, parameterNode):
        self.initialize( stepid )
        self.setName( 'Step 3. Entry Point and Fiducial Insertion' )
        self.coords = [0,0,0]
        self.fiduciallist = []

        self.currentFidIndex = 0
        self.currentFidLabel = None

        self.viewDirection = "Right"

        self.startCount = 0
        self.fidCount = 0
        self.fidObserve = None
        self.fidObserve2 = None
        self.fidObserve3 = None
        self.fidNode = None
        self.fidNode2 = None
        self.fidNode3 = None
        self.node = None

        self.navOn = 0

        self.markups = slicer.modules.markups.logic()
        self.cylinderModel = None
        self.cubeModel = None
        self.transformSet = False

        # Expects to be in the same directory as where the repo is cloned
        self.camera_config_path = os.path.abspath(os.path.join(__file__ ,"../../../../camera_calibration.yml"))
        self.cy = None
        self.fy = None
        self.cx = None
        self.fx = None

        self.realWorldTransformNode_m0 = None
        self.realWorldTransformNode_m1 = None
        self.realWorldTransformNode_m2 = None
        self.realWorldTransformNode_m3 = None
        self.realWorldTransformNode_m4 = None

        self.plusServerArgs = ['PlusServer', '--config-file=PlusDeviceSet_Server_OpticalMarkerTracker_Mmf.xml']

        self.offsets = None
        self.cube_length = 0

        self.transforms = {'Marker0ToTracker': {'node': self.realWorldTransformNode_m0, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker1ToTracker': {'node': self.realWorldTransformNode_m1, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker2ToTracker': {'node': self.realWorldTransformNode_m2, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker3ToTracker': {'node': self.realWorldTransformNode_m3, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker4ToTracker': {'node': self.realWorldTransformNode_m4, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)}}

        self.transformNodeObserverTags = []
        # Variable for storing the real world transforms as they are streamed
        self.realWorldTransformNode = None
        # Create Variables for storing the transforms from aruco marker relative to start point, the node for the
        # fiducial node
        self.ctTransform = None
        self.spInMarker = []
        self.anatomPoints = []
        self.detectedSPs = []
        self.markerPoints = []

        self.displayMarkerSphere = None
        self.startPointSphere = None
        self.marker2Sphere = None
        self.connectorNodeObserverTagList = []

        self.cnode_1 = None
        self.cnode_2 = None
        self.process = None
        self.aruco_position_matrix = None
        self.apoints_set = False
        self.camera_matrix = None
        self.dist_matrix = None

        self.__parameterNode  = parameterNode

    def killButton(self):
        # hide useless button
        bl = slicer.util.findChildren(text='Final')
        if len(bl):
            bl[0].hide()

    def createUserInterface( self ):

        self.__layout = qt.QFormLayout( self )
        self.__layout.setVerticalSpacing( 5 )

        # Add empty rows
        self.__layout.addRow( "", qt.QWidget() )
        self.__layout.addRow( "", qt.QWidget() )

        viewText = qt.QLabel("Viewpoint:")
        self.views = ctk.ctkComboBox()
        self.views.toolTip = "Select your view point."
        self.views.addItem("Left")
        self.views.addItem("Right")
        self.connect(self.views, PythonQt.QtCore.SIGNAL('activated(QString)'), self.cameraSide)

        workText = qt.QLabel("Screw Insertion Workflow")
        self.QHBox = qt.QHBoxLayout()
        self.QHBox.addWidget(workText)
        self.__layout.addRow(self.QHBox)
        self.startMeasurements = qt.QPushButton("Click to Add")
        self.startMeasurements.connect('clicked(bool)', self.addFiducials)
        self.markerPosition = qt.QPushButton("Click to Add")
        self.markerPosition.connect('clicked(bool)', self.addPositions)
        self.adjustClamp = qt.QPushButton("Click to Adjust")
        self.adjustClamp.connect('clicked(bool)', self.moveAruco)
        self.adjustClamp.enabled = False
        self.findSP = qt.QPushButton("Click to find startpoint")
        self.findSP.connect('clicked(bool)', self.findStartPoints)
        self.findSP.enabled = False
        self.stopTracking = qt.QPushButton("Click to stop tracking")
        self.stopTracking.connect('clicked(bool)', self.stopSPTracking)
        self.stopTracking.enabled = False
        self.aPoints= qt.QPushButton("Click to choose points")
        self.aPoints.connect('clicked(bool)', self.selectAPoints)
        self.aPoints.enabled = False

        self.fiducial = ctk.ctkComboBox()
        self.fiducial.toolTip = "Select an insertion site."
        self.fiducial.addItems(self.fiduciallist)
        self.connect(self.fiducial, PythonQt.QtCore.SIGNAL('activated(QString)'), self.fidChanged)

        eText = qt.QLabel("1. Add Entry Point:")
        self.QHBox1 = qt.QHBoxLayout()
        self.QHBox1.addWidget(eText)
        self.QHBox1.addWidget(self.startMeasurements)
        self.__layout.addRow(self.QHBox1)

        sText = qt.QLabel("2. Active Entry Point:")
        self.QHBox2 = qt.QHBoxLayout()
        self.QHBox2.addWidget(sText)
        self.QHBox2.addWidget(self.fiducial)
        self.__layout.addRow(self.QHBox2)

        qText = qt.QLabel("3. Add Clamp Position Point")
        self.arucoBox = qt.QHBoxLayout()
        self.arucoBox.addWidget(qText)
        self.arucoBox.addWidget(self.markerPosition)
        self.__layout.addRow(self.arucoBox)

        mText = qt.QLabel("4. Adjust Clamp Position")
        self.clampBox = qt.QHBoxLayout()
        self.clampBox.addWidget(mText)
        self.clampBox.addWidget(self.adjustClamp)
        self.__layout.addRow(self.clampBox)

        aText = qt.QLabel("5. Add anatomical points:")
        self.anatomBox = qt.QHBoxLayout()
        self.anatomBox.addWidget(aText)
        self.anatomBox.addWidget(self.aPoints)
        self.__layout.addRow(self.anatomBox)

        tText = qt.QLabel("6. Start Tracking")
        self.trackingBox = qt.QHBoxLayout()
        self.trackingBox.addWidget(tText)
        self.trackingBox.addWidget(self.findSP)
        self.__layout.addRow(self.trackingBox)

        stText = qt.QLabel("7. Stop Tracking")
        self.trackingBoxStop = qt.QHBoxLayout()
        self.trackingBoxStop.addWidget(stText)
        self.trackingBoxStop.addWidget(self.stopTracking)
        self.__layout.addRow(self.trackingBoxStop)

        self.transformGrid = qt.QGridLayout()
        self.__layout.addRow(self.transformGrid)

        self.delSP = qt.QPushButton("Remove Start Point")
        self.delSP.enabled = False
        self.delSP.connect('clicked(bool)', self.delStartPoint)

        self.QHBox4 = qt.QHBoxLayout()
        self.QHBox4.addWidget(self.delSP)
        self.__layout.addRow(self.QHBox4)

        navCollapsibleButton = ctk.ctkCollapsibleButton()
        navCollapsibleButton.text = "Navigation"
        self.__layout.addWidget(navCollapsibleButton)
        navCollapsibleButton.collapsed = True

        # Layout
        navLayout = qt.QFormLayout(navCollapsibleButton)
        self.resetSliceButton = qt.QPushButton("Reset Slice Views")
        navLayout.addRow(self.resetSliceButton)
        self.resetSliceButton.connect('clicked(bool)', self.resetSliceViews)

        qt.QTimer.singleShot(0, self.killButton)

    def selectAPoints(self):
        sps = slicer.mrmlScene.GetNodesByName('AnatomicalPoints')
        node = sps.GetItemAsObject(0)
        if node.GetNumberOfFiducials() == 2:
            msgOne = qt.QMessageBox.warning( self, 'Anatomical Points', 'Two Antomical Points already selected' )
            return
        else:
            # Set Anatomical Points as the active nodes
            # Only show this message if the number of markups in the list is 0
            msgOne = qt.QMessageBox.warning( self, 'Anatomical Points', 'Add points to two known anatomical locations' )
            node = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode5')
            self.markups.SetActiveListID(node)
            self.begin()

    def checkAPoints(self, node, event):
        if node.GetNumberOfFiducials() == 2:
            self.stop()
            self.apoints_set = True

    def stopSPTracking(self):
        self.cnode_1.Stop()
        self.cnode_2.Stop()
        self.process.terminate()

        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalWidescreenView)
        self.removeObservers()

    def updateOffsets(self):
        bounds = [0,0,0,0,0,0]
        cube = slicer.util.getNode('ArucoCube')
        cube.GetRASBounds(bounds)
        self.cube_length = np.absolute(bounds[1] - bounds[0])

        self.offsets = {'Marker0ToTracker': {'matrix': None, 'transform': None, 'offset': (1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, self.cube_length/2, 0, 0, 0, 1)},
        'Marker1ToTracker': {'matrix': None, 'transform': None, 'offset': (-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, self.cube_length/2, 0, 0, 0, 1)},
        'Marker2ToTracker': {'matrix': None, 'transform': None, 'offset': (0, 0, 1, 0, 0, -1, 0, 0, 1, 0, 0, self.cube_length/2, 0, 0, 0, 1)},
        'Marker3ToTracker': {'matrix': None, 'transform': None, 'offset': (1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, self.cube_length/2, 0, 0, 0, 1)},
        'Marker4ToTracker': {'matrix': None, 'transform': None, 'offset': (0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, self.cube_length/2, 0, 0, 0, 1)}}

    def addObservers(self):
        transformModifiedEvent = 15000
        nodes = [self.realWorldTransformNode]
        funcs = [self.onTransformOfInterestNodeModified]
        for _, (node, func) in enumerate(zip(nodes, funcs)):
            transformNode = node
            while transformNode:
                print "Add observer to {0}".format(transformNode.GetName())
                self.transformNodeObserverTags.append([transformNode,transformNode.AddObserver(transformModifiedEvent, func)])
                transformNode = transformNode.GetParentTransformNode()

    def removeObservers(self):
        print("Remove observers")
        for nodeTagPair in self.transformNodeObserverTags:
            nodeTagPair[0].RemoveObserver(nodeTagPair[1])
    
    def get_3d_coordinates(self, transform_real_world_interest):
        Xc2 = transform_real_world_interest.GetElement(0, 3)
        Yc2 = transform_real_world_interest.GetElement(1, 3)
        Zc2 = transform_real_world_interest.GetElement(2, 3)
        return Xc2, Yc2, Zc2

    def onTransformOfInterestNodeModified(self, observer, eventId):
        # Create matrix to store the transform for camera to aruco marker
        matrix, transform_real_world_interest = self.create_4x4_vtk_mat_from_node(self.realWorldTransformNode)

        rotation_matrix = np.array([[matrix.GetElement(0, 0), matrix.GetElement(0, 1), matrix.GetElement(0, 2)],
        [matrix.GetElement(1, 0), matrix.GetElement(1, 1), matrix.GetElement(1, 2)], 
        [matrix.GetElement(2, 0), matrix.GetElement(2, 1), matrix.GetElement(2, 2)]], dtype=np.float32)
        rvec = cv2.Rodrigues(rotation_matrix)

        tvec = np.array([[matrix.GetElement(0, 3)], [matrix.GetElement(1, 3)], [matrix.GetElement(2, 3)]], dtype=np.float32)
        Xc2, Yc2, Zc2 = self.get_3d_coordinates(transform_real_world_interest)
        [x2, y2] = [0, 0]
        [x2, y2] = self.transform_3d_to_2d(Xc2, Yc2, Zc2)
        vtk_marker_matrix = self.create_4x4_vtk_mat(x2, y2)
        # self.displayMarkerSphere.SetMatrixTransformToParent(vtk_marker_matrix)
        # Multiply start point in marker space calculated form the CT model by the
        # camera to aruco transform to get the start point in 3D camera space.

        offset = self.offsets['Marker0ToTracker']['offset']
        offset_matrix = vtk.vtkMatrix4x4()
        offset_matrix.DeepCopy(offset)

        self.applyPerspectiveTransform('InsertionLandmarks', self.spInMarker, tvec, rvec, matrix, offset_matrix, self.heatmap_nodes_sp, self.test_node_sp)
        self.applyPerspectiveTransform('AnatomicalPoints', self.anatomPoints, tvec, rvec, matrix, offset_matrix, self.heatmap_nodes_al, self.test_node_al)

    def applyPerspectiveTransform(self, markupList, pointList, tvec, rvec, matrix, offset_matrix, heatmap_nodes, test_node):
        p = slicer.mrmlScene.GetNodesByName(markupList)
        node = p.GetItemAsObject(0)

        for i in range(node.GetNumberOfFiducials()):
            curr_marker = offset_matrix.MultiplyPoint(pointList[i])
            point = np.array([[curr_marker[0]], [curr_marker[1]], [curr_marker[2]]], dtype=np.float32)

            print('tvec: ', tvec.T)
            print('rvec: ', rvec[0].T)

            print('matrix: ', matrix.__str__())
            imgPoints = cv2.projectPoints(point.T, rvec[0].T , tvec.T, self.camera_matrix, self.dist_matrix)
            imgPoints = imgPoints[0][0]
            startPointinCamera = matrix.MultiplyPoint(curr_marker)

            # Set calculated 3d start point in camera space
            Xc = startPointinCamera[0]
            Yc = startPointinCamera[1]
            Zc = startPointinCamera[2]

            # Perform 3D (Camera) to 2D project sp
            [x, y] = [0, 0]
            [x, y] = self.transform_3d_to_2d(Xc, Yc, Zc)
            
            vtk_sp_matrix = self.create_4x4_vtk_mat(x, y)
            print('img_points: ', imgPoints)
            open_cv_sp_matrix = self.create_4x4_vtk_mat(imgPoints[0][0], imgPoints[0][1])
            for sph in heatmap_nodes[i]:
                sph.SetMatrixTransformToParent(vtk_sp_matrix)
            test_node[0].SetMatrixTransformToParent(open_cv_sp_matrix)
            print markupList , ' point number: ', i


    def create_4x4_vtk_mat(self, x, y):
        sp_matrix = [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, 0, 0, 0, 0, 1]
        vtk_sp_matrix = vtk.vtkMatrix4x4()
        vtk_sp_matrix.DeepCopy(sp_matrix)
        return vtk_sp_matrix

    @staticmethod
    def create_4x4_vtk_mat_from_node(node):
        matrix = vtk.vtkMatrix4x4()
        transform_real_world_interest = node.GetMatrixTransformToParent()
        matrix.DeepCopy(transform_real_world_interest)
        return matrix, transform_real_world_interest

    def addTransforms(self):
        for (k,v) in self.transforms.items():
            matrix = vtk.vtkMatrix4x4()
            matrix.DeepCopy(v['coords'])
            transform = slicer.vtkMRMLLinearTransformNode()
            transform.SetName(k)
            slicer.mrmlScene.AddNode(transform)
            transform.ApplyTransformMatrix(matrix)
            if k == 'Marker0ToTracker':
                self.realWorldTransformNode = transform

    def transform_3d_to_2d(self, Xc, Yx, Zc):
        x = np.round((Xc * self.fx / Zc) + self.cx)
        y = np.round((Yx * self.fy / Zc) + self.cy)
        return [x, y]

    def findStartPoints(self):
        if self.transformSet is False or self.apoints_set is False:
            msgOne = qt.QMessageBox.warning( self, 'Adjustment or Points missing', 'Please adjust the aruco cube and select antomical points first' )
            return
        # Start OpenIGT Connections
        self.cnode_1.Start()
        self.cnode_2.Start()

        # Launch Plus Server using a new process
        self.process = subprocess.Popen(self.plusServerArgs)

        # Update Red Slice View
        sliceController = slicer.app.layoutManager().sliceWidget("Red").sliceController()

        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

        self.aruco_position_matrix = vtk.vtkMatrix4x4()
        transformCube = slicer.util.getNode('Cube Position')
        self.aruco_position_matrix.DeepCopy(transformCube.GetMatrixTransformToParent())
        # Invert to get marker to CT origin
        self.aruco_position_matrix.Invert()

        # Create list of concentric circles to act as heat maps.
        # One collection of three spheres for each start point and anatomical landmark
        self.heatmap_nodes_sp = []
        self.heatmap_nodes_al = []
        self.test_node_sp = []
        self.test_node_al = []
        self.heatmap_nodes_sp_colours = [[0, 1.0, 0], [1.0, 1.0, 0], [1.0, 0, 0]]
        self.heatmap_nodes_al_colours = [[1.0, 0, 1.0], [0, 1.0, 1.0], [1.0, 0.5, 0]]
        
        self.putAtArucoCentre('InsertionLandmarks', self.spInMarker, self.heatmap_nodes_sp, self.heatmap_nodes_sp_colours, self.test_node_sp)
        self.putAtArucoCentre('AnatomicalPoints', self.anatomPoints, self.heatmap_nodes_al, self.heatmap_nodes_al_colours, self.test_node_al)
        self.addObservers()

    def putAtArucoCentre(self, markupList, listToAdd, heatmap_node_list, colour_list, test_node):
        p = slicer.mrmlScene.GetNodesByName(markupList)
        node = p.GetItemAsObject(0)
        for i in range(node.GetNumberOfFiducials()):
            coord = [0, 0, 0]
            node.GetNthFiducialPosition(i, coord)
            coord.append(1)
            print 'coord: ', coord
            # Multiply to put start point relative to aruco marker cube origin
            point = self.aruco_position_matrix.MultiplyPoint(coord)
            listToAdd.append(point)
            # Create Models for Display
            names = ['center_cyl_{}'.format(i) + markupList, 'intermediate_cyl_{}'.format(i) + markupList,
                     'outer_cyl_{}'.format(i) + markupList]
            print(names)
            concentric_cylinders = []
            cylinder_model_nodes = []
            display_marker_cylinders = []
            for j in range(0, 1):
                if slicer.mrmlScene.GetFirstNodeByName(names[j]) is None:
                    model_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
                    model_node.SetName(names[j])
                else:
                    model_node = slicer.mrmlScene.GetFirstNodeByName(names[j])
                cyl = vtk.vtkSphereSource()
                cyl.SetRadius(3 * (j + 1))
                # cyl.SetHeight(60.0)
                cyl.Update()
                model_node.SetAndObservePolyData(cyl.GetOutput())
                model_node.CreateDefaultDisplayNodes()
                model_node.GetDisplayNode().SetSliceIntersectionVisibility(True)
                model_node.GetDisplayNode().SetSliceDisplayMode(1)
                model_node.GetDisplayNode().SetColor(colour_list[j][0], colour_list[j][1], colour_list[j][2])
                concentric_cylinders.append(cyl)
                cylinder_model_nodes.append(model_node)
                if slicer.mrmlScene.GetFirstNodeByName(names[j] + 't_form') is None:
                    t_form_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode')
                    t_form_node.SetName(names[j] + 't_form')
                else:
                    t_form_node = slicer.mrmlScene.GetFirstNodeByName(names[j] + 't_form')
                model_node.SetAndObserveTransformNodeID(t_form_node.GetID())
                display_marker_cylinders.append(t_form_node)
            heatmap_node_list.append(display_marker_cylinders)
            if slicer.mrmlScene.GetFirstNodeByName('test_node' + markupList) is None:
                model_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
                model_node.SetName('test_node' + markupList)
            else:
                model_node = slicer.mrmlScene.GetFirstNodeByName('test_node' + markupList)
            sph = vtk.vtkSphereSource()
            sph.SetRadius(3)
            sph.Update()
            model_node.SetAndObservePolyData(sph.GetOutput())
            model_node.CreateDefaultDisplayNodes()
            model_node.GetDisplayNode().SetSliceIntersectionVisibility(True)
            model_node.GetDisplayNode().SetSliceDisplayMode(1)
            model_node.GetDisplayNode().SetColor(colour_list[1][0], colour_list[1][1], colour_list[1][2])
            if slicer.mrmlScene.GetFirstNodeByName('test_node' + markupList + 't_form') is None:
                t_form_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode')
                t_form_node.SetName('test_node' + markupList + 't_form')
            else:
                t_form_node = slicer.mrmlScene.GetFirstNodeByName('test_node' + markupList + 't_form')
            model_node.SetAndObserveTransformNodeID(t_form_node.GetID())
            test_node.append(t_form_node)

    def enableClampAdjust(self, node, event):
        self.addPositions()
        if node.GetNumberOfFiducials() > 0:
            self.adjustClamp.enabled = True
            self.findSP.enabled = True
            self.stopTracking.enabled = True
            self.aPoints.enabled = True

    def enableSPRemoval(self, node, event):
        if node.GetNumberOfFiducials() > 0:
            self.delSP.enabled = True
            if self.transformSet:
                self.findSP.enabled = True
                self.stopTracking.enabled = True
      
    def moveAruco(self):
        if self.node is not None and self.node.GetNumberOfFiducials() > 1:
            currentNum = self.node.GetNumberOfFiducials()
            for i in range(currentNum):
                self.node.RemoveMarkup(i)
                if i > 0:
                    self.node.SetNthFiducialVisibility(i, 0)

        coords =[0, 0, 0]
        self.postions = slicer.mrmlScene.GetNodesByName('Aruco Position Points')
        self.node = self.postions.GetItemAsObject(0)
        self.node.GetNthFiducialPosition(0,coords)
        cylinderMatrix = vtk.vtkMatrix4x4()
        cylinderMatrix.DeepCopy((1, 0, 0, coords[0], 0, 0, -1, coords[1], 0, 1, 0, coords[2], 0, 0, 0, 1))
        cubeMatrix = vtk.vtkMatrix4x4()
        cubeMatrix.DeepCopy((1, 0, 0, coords[0], 0, 0, -1, -25 + coords[1], 0, 1, 0, coords[2], 0, 0, 0, 1))

        if self.transformSet is False:
            transformClamp  = slicer.vtkMRMLLinearTransformNode()
            transformCube  = slicer.vtkMRMLLinearTransformNode()
            transformClamp.SetName('Clamp Position')
            transformCube.SetName('Cube Position')
            slicer.mrmlScene.AddNode(transformClamp)
            slicer.mrmlScene.AddNode(transformCube)
            transformClamp.ApplyTransformMatrix(cylinderMatrix)
            transformCube.ApplyTransformMatrix(cubeMatrix)
            self.transformSet = True
        else:
            transformClamp = slicer.util.getNode('Clamp Position')
            transformClamp.SetMatrixTransformToParent(cylinderMatrix)
            transformCube = slicer.util.getNode('Cube Position')
            transformCube.SetMatrixTransformToParent(cubeMatrix)

        self.cylinderModel.SetName('Clamp')
        self.cylinderModel.SetAndObserveTransformNodeID(transformClamp.GetID())
        self.cubeModel.SetAndObserveTransformNodeID(transformCube.GetID())
          
    def addPositions(self):
        if self.startCount == 0:
            pos = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode4')
            self.markups.SetActiveListID(pos)
            self.postions = slicer.mrmlScene.GetNodesByName('Aruco Position Points')
            self.node = self.postions.GetItemAsObject(0)
            self.begin()
            self.startCount = 1
            self.markerPosition.setText("Place Aruco Position")
        elif self.startCount == 1:
            self.stop()
            self.markerPosition.setText("Add Aruco Position")
            self.startCount = 0
            self.startMeasurements.setText("Add Entry Pt")
  
    def enableNavigation(self):
        if self.navOn == 0:
            lm = slicer.app.layoutManager()
            if lm == None: 
                return 
            lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalWidescreenView)
            viewNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSliceCompositeNode')
            viewNodes.UnRegister(slicer.mrmlScene)
            viewNodes.InitTraversal()
            viewNode = viewNodes.GetNextItemAsObject()
            while viewNode:
                viewNode.SetSliceIntersectionVisibility(1)
                viewNode = viewNodes.GetNextItemAsObject()
                self.navOn = 1
            n =  self.__baselineVolume
            for color in ['Red', 'Yellow', 'Green']:
                a = slicer.app.layoutManager().sliceWidget(color).sliceLogic().GetSliceNode().GetFieldOfView()
                slicer.app.layoutManager().sliceWidget(color).sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(n.GetID())
                slicer.app.layoutManager().sliceWidget(color).sliceLogic().GetSliceNode().SetFieldOfView(150,150,a[2]) 
        else:
            lm = slicer.app.layoutManager()
            if lm == None: 
                return 
            lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
            self.navOn = 0  
            
    def resetSliceViews(self):
        for i in range(0,3):
            if i == 0:
                viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
                viewSlice.GetSliceToRAS().DeepCopy(self.redTransform.GetMatrix()) 
            elif i == 1:
                viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeYellow')
                viewSlice.GetSliceToRAS().DeepCopy(self.yellowTransform.GetMatrix())
                
            elif i == 2:
                viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
                viewSlice.GetSliceToRAS().DeepCopy(self.greenTransform.GetMatrix())
            
            viewSlice.UpdateMatrices()    

    def sliceChange(self):
        coords = [0,0,0]
        if self.fidNode != None:
          # Get the position/coordinates of the selected fiducial
          self.fidNode.GetNthFiducialPosition(self.currentFidIndex,coords)
               
          lm = slicer.app.layoutManager()
          redWidget = lm.sliceWidget('Red')
          redController = redWidget.sliceController()
        
          yellowWidget = lm.sliceWidget('Yellow')
          yellowController = yellowWidget.sliceController()
        
          greenWidget = lm.sliceWidget('Green')
          greenController = greenWidget.sliceController()
        
          yellowController.setSliceOffsetValue(coords[0])
          greenController.setSliceOffsetValue(coords[1])
          redController.setSliceOffsetValue(coords[2])

          self.fidNode.UpdateScene(slicer.mrmlScene)
        else:
            return
        
    def fidChanged(self, fid):
        if self.fiducial.currentText != "Select an insertion landmark":
            self.currentFidLabel = self.fiducial.currentText
            self.currentFidIndex = self.fiducial.currentIndex
            self.fidNode.GetNthFiducialPosition(self.currentFidIndex,self.coords)
        self.sliceChange()
        self.cameraFocus(self.coords)

    def updateComboBox(self):
        fidLabel = self.fidNode.GetNthFiducialLabel(self.fidCount - 1)
        self.fiducial.addItem(fidLabel)
        self.fiducial.setCurrentIndex(self.fidCount - 1)
        self.fidChanged(fidLabel)

    def delStartPoint(self):
        self.fidNode.RemoveMarkup(self.fiducial.currentIndex)
        self.fiducial.removeItem(self.fiducial.currentIndex)
        if self.fidNode.GetNumberOfFiducials() <= 0:
            self.delSP.enabled = False
            self.findSP.enabled = False
            self.stopTracking.enabled = False
            
    def cameraSide(self, text):
        camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
        if text == "Right":
            camera.SetViewUp([-1,0,0])
            self.viewDirection = "Right"
        else:
            camera.SetViewUp([1,0,0])
            self.viewDirection = "Left"
               
    def cameraFocus(self, position):
        # Set camera position to the position of the sp selected
        camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
        camera.SetFocalPoint(*position)
        camera.SetPosition(position[0],-400,position[2])
        if self.viewDirection == "Right":
            camera.SetViewUp([-1,0,0])
        else:
            camera.SetViewUp([1,0,0])
        camera.ResetClippingRange()
    
    def addFiducials(self):
        if self.startCount == 0:
            pos = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode3')
            self.markups.SetActiveListID(pos)
            self.begin()
            self.startCount = 1
            self.startMeasurements.setText("Place Entry Pt")
        elif self.startCount == 1:
            self.stop()
            self.startCount = 0
            self.startMeasurements.setText("Add Entry Pt")
        
    def begin(self):
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # place rulers
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        # to place ROIs use the class name vtkMRMLAnnotationROINode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        #placeModePersistence = 1
        #interactionNode.SetPlaceModePersistence(placeModePersistence)
        # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
        interactionNode.SetCurrentInteractionMode(1)

    def stop(self):
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # place rulers
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        # to place ROIs use the class name vtkMRMLAnnotationROINode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        #placeModePersistence = 1
        #interactionNode.SetPlaceModePersistence(placeModePersistence)
        # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
        interactionNode.SetCurrentInteractionMode(2)
                         
    def addFiducialToTable(self, node, event):
        self.fidNode.UpdateScene(slicer.mrmlScene)
        self.fidCount = self.fidNode.GetNumberOfFiducials()
        self.addFiducials()
        if node.GetNumberOfFiducials() > self.fiducial.count:
            self.updateComboBox()
        self.stop()
          
    def validate( self, desiredBranchId ):
        validationSuceeded = True
        super(ScrewStep, self).validate(validationSuceeded, desiredBranchId)
        
    def onEntry(self, comingFrom, transitionType):
        self.markups.AddNewFiducialNode('InsertionLandmarks')
        self.markups.AddNewFiducialNode('Aruco Position Points')
        self.markups.AddNewFiducialNode('AnatomicalPoints')

        landmarks = slicer.mrmlScene.GetNodesByName('InsertionLandmarks')
        landmarks2 = slicer.mrmlScene.GetNodesByName('Aruco Position Points')
        landmarks3 = slicer.mrmlScene.GetNodesByName('AnatomicalPoints')

        self.fidNode = landmarks.GetItemAsObject(0)
        self.fidNode2 = landmarks2.GetItemAsObject(0)
        self.fidNode3 = landmarks3.GetItemAsObject(0)

        self.displayNode = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsDisplayNode3')
        self.displayNode.SetSelectedColor(1.0, 0, 0.2)
        self.displayNode.SetGlyphScale(5)

        self.fidObserve = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, self.addFiducialToTable)
        self.fidObserve2 = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, self.enableSPRemoval)
        self.fidObserve3 = self.fidNode2.AddObserver(self.fidNode2.MarkupAddedEvent, self.enableClampAdjust)
        self.fidObserve4 = self.fidNode3.AddObserver(self.fidNode3.MarkupAddedEvent, self.checkAPoints)

        slicer.modules.models.logic().SetAllModelsVisibility(1)

        a = slicer.mrmlScene.GetNodesByName('clipModel').GetItemAsObject(0).SetDisplayVisibility(0)
        b = slicer.mrmlScene.GetNodesByName('clipModel').GetItemAsObject(1).SetDisplayVisibility(0)

        super(ScrewStep, self).onEntry(comingFrom, transitionType)

        lm = slicer.app.layoutManager()
        if lm == None: 
            return 
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)

        self.redTransform = vtk.vtkTransform()
        viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
        self.redTransform.SetMatrix(viewSlice.GetSliceToRAS())
        self.yellowTransform = vtk.vtkTransform()
        viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeYellow')
        self.yellowTransform.SetMatrix(viewSlice.GetSliceToRAS())
        self.greenTransform = vtk.vtkTransform()
        viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
        self.greenTransform.SetMatrix(viewSlice.GetSliceToRAS())

        pNode = self.__parameterNode
        pNode.SetParameter('currentStep', self.stepid)
        self.approach = str(pNode.GetParameter('approach'))
        baselineVolume = Helper.getNodeByID(pNode.GetParameter('baselineVolumeID'))
        self.__baselineVolume = baselineVolume

        inputModel = slicer.mrmlScene.GetNodeByID('vtkMRMLModelNode4')
        inputModel.SetDisplayVisibility(0)
        clipROI = slicer.mrmlScene.GetNodeByID('vtkMRMLAnnotationROINode1')
        clipROI.GetXYZ(self.coords)

        camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
        camera.SetFocalPoint(self.coords)
        camera.SetPosition(self.coords[0], -360 ,self.coords[2])
        camera.SetViewUp([-1,0,0])

        self.loadFiducials()
        self.enableNavigation()
        self.setOpenIGTConnections()
        self.parseCameraConfig()
        self.addTransforms()
        self.updateOffsets()
        self.stop()

    def parseCameraConfig(self):
        try:
            with open(self.camera_config_path, 'r') as stream:
                data = yaml.load(stream)
                self.cy = data['camera_matrix']['data'][5]
                self.fy = data['camera_matrix']['data'][4]
                self.cx = data['camera_matrix']['data'][2]
                self.fx = data['camera_matrix']['data'][0]
                self.camera_matrix = np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]], dtype=np.float32)
                #self.camera_matrix = np.zeros((3, 3), dtype=np.float32)
                self.dist_matrix = np.array(data['distortion_coefficients']['data'], dtype=np.float32)
                #self.dist_matrix = np.zeros((1, 5), dtype=np.float32)
        except yaml.YAMLError as exc:
            print exc

    def setOpenIGTConnections(self):
        self.cnode_1 = slicer.vtkMRMLIGTLConnectorNode()
        slicer.mrmlScene.AddNode(self.cnode_1)
        self.cnode_1.SetName('Connector1')
        self.cnode_1.SetTypeClient('localhost', 18944)

        self.cnode_2 = slicer.vtkMRMLIGTLConnectorNode()
        slicer.mrmlScene.AddNode(self.cnode_2)
        self.cnode_2.SetName('Connector2')
        self.cnode_2.SetTypeClient('localhost', 18945)
        events = [[slicer.vtkMRMLIGTLConnectorNode.ConnectedEvent, self.onConnectorNodeConnected], [slicer.vtkMRMLIGTLConnectorNode.DisconnectedEvent, self.onConnectorNodeDisconnected]]
        for tagEventHandler in events:
            connectorNodeObserverTag_2 = self.cnode_2.AddObserver(tagEventHandler[0], tagEventHandler[1])
            connectorNodeObserverTag_1 = self.cnode_1.AddObserver(tagEventHandler[0], tagEventHandler[1])
            self.connectorNodeObserverTagList.append(connectorNodeObserverTag_1)
            self.connectorNodeObserverTagList.append(connectorNodeObserverTag_2)

    def onConnectorNodeConnected(self, caller, event, force=False):
        print 'Connected'
        time.sleep(6)
        lm = slicer.app.layoutManager()
        lm.sliceWidget("Red").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID('vtkMRMLVectorVolumeNode1')
        reslicer = slicer.modules.volumereslicedriver.logic()
        reslicer.SetModeForSlice(reslicer.MODE_TRANSVERSE, slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed'))
        reslicer.SetFlipForSlice(True, slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed'))
        reslicer.SetDriverForSlice('vtkMRMLVectorVolumeNode1', slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed'))
        lm.sliceWidget("Red").sliceController().fitSliceToBackground()

    def onConnectorNodeDisconnected(self, caller, event, force=False):
        print 'Connector Disconnected'

    def loadFiducials(self):
        cubeModelPath = os.path.join(os.path.dirname(__file__), os.pardir , 'Resources/Fiducials/marker-with-indicator.stl')
        cylinderModelPath = os.path.join(os.path.dirname(__file__), os.pardir , 'Resources/Fiducials/CylinderModel.vtk')
        #clipCubeModelPath = os.path.join(os.path.dirname(__file__), os.pardir , 'Resources/Fiducials/Clip-cube.stl')
        slicer.util.loadModel(cubeModelPath, True)
        self.cubeModel = slicer.util.getNode('marker-with-indicator')
        self.cubeModel.SetName('ArucoCube')
        self.cylinderModel = slicer.modules.models.logic().AddModel(cylinderModelPath)
        #slicer.util.loadModel(clipCubeModelPath)

    def onExit(self, goingTo, transitionType):
        super(ScrewStep, self).onExit(goingTo, transitionType)
