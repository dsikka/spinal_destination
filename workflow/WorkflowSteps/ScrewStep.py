from __main__ import qt, ctk, vtk, slicer

from Helper import *
import PythonQt
import math
import os
import string
import time
import inspect
import csv
import numpy as np

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
      self.node = None
      
      self.navOn = 0
 
      self.markups = slicer.modules.markups.logic()
      self.cylinderModel = None
      self.cubeModel = None
      self.transformSet = False

      # Camera calibration parameters; hardcoded for the web
      self.cy = 2.3184788479005914e+002
      self.fy = 6.4324331025844515e+002
      self.cx = 3.1163816392087517e+002
      self.fx = 6.4367706296746178e+002

      self.transforms = {'1': {'name': "Marker8ToTracker", 'coords': (0.9609, 0.07138, 0.2674, -3.73997, 0.119422, -0.978532, -0.16797, 48.6033, 0.249646, 0.19334, -0.94884, 353.367, 0, 0, 0, 1)},
      '2': {'name': 'Marker5ToTracker', 'coords': (0.98296, 0.06894, 0.1704, -41.82, 0.1203, -0.942275, -0.312499, 8.54265, 0.139009, 0.327666, -0.934511, 356.768, 0, 0, 0, 1)},
      '3': {'name': 'Marker7ToTracker', 'coords': (0.97637, 0.11012, 0.18597, -45.0335, 0.11645, -0.9929, -0.023417, 46.947, 0.182073, 0.04452, -0.982277, 347.387, 0, 0, 0, 1)},
      '4': {'name': 'Marker2ToTracker', 'coords': (0.99446, -0.03001, -0.1006, 145.087, 0.020221, -0.88597, 0.46331, -75.631, -0.10319, -0.46278, -0.88045, 433.75, 0, 0, 0, 1)},
      '5': {'name': 'Marker4ToTracker', 'coords': (0.94116, 0.066682, 0.33133, 85.548, 0.15165, -0.95944, -0.23767, -21.676, 0.30204, 0.273924, -0.913092, 400.461, 0, 0, 0, 1)},
      '6': {'name': 'Marker3ToTracker', 'coords': (0.96055, 0.073, 0.2683, 27.383, 0.14246, -0.958067, -0.248621, -29.7239, 0.238861, 0.277036, -0.930697, 380.305, 0, 0, 0, 1)}}

      self.transformNodeObserverTags = []
      # Variable for storing the real world transforms as they are streamed
      self.realWorldTransformNode = None
      # Create Variables for storing the transforms from aruco marker relative to start point, the node for the
      # fiducial node
      self.ctTransform = None
      self.spInMarker = []
      self.detectedSPs = []
      self.markerPoints = []

      self.displayMarkerSphere = None
      self.startPointSphere = None
      self.marker2Sphere = None
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

      qText = qt.QLabel("3. Add clamp position points")
      self.arucoBox = qt.QHBoxLayout()
      self.arucoBox.addWidget(qText)
      self.arucoBox.addWidget(self.markerPosition)
      self.__layout.addRow(self.arucoBox)

      mText = qt.QLabel("4. Adjust Clamp Position")
      self.clampBox = qt.QHBoxLayout()
      self.clampBox.addWidget(mText)
      self.clampBox.addWidget(self.adjustClamp)
      self.__layout.addRow(self.clampBox)

      tText = qt.QLabel("5. Start Tracking")
      self.trackingBox = qt.QHBoxLayout()
      self.trackingBox.addWidget(tText)
      self.trackingBox.addWidget(self.findSP)
      self.__layout.addRow(self.trackingBox)

      stText = qt.QLabel("6. Stop Tracking")
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

    def stopSPTracking(self):
      lm = slicer.app.layoutManager()
      lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalWidescreenView)
      self.removeObservers()

    def addObservers(self):
      transformModifiedEvent = 15000
      nodes = [self.realWorldTransformNode]
      funcs = [self.onTransformOfInterestNodeModified]
      #for i, (node, func)
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
      # Multiply start point in marker space calculated form the CT model by the
      # camera to aruco transform to get the start point in 3D camera space.
      sps = slicer.mrmlScene.GetNodesByName('InsertionLandmarks')
      node = sps.GetItemAsObject(0)

      for i in range(node.GetNumberOfFiducials()):
        startPointinCamera = matrix.MultiplyPoint(self.spInMarker[i])
        # Set calculated 3d start point in camera space
        Xc = startPointinCamera[0]
        Yc = startPointinCamera[1]
        Zc = startPointinCamera[2]
        # Get Marker 3D
        Xc2, Yc2, Zc2 = self.get_3d_coordinates(transform_real_world_interest)
        # Perform 3D (Camera) to 2D project
        [x2, y2] = [0, 0]
        [x2, y2] = self.transform_3d_to_2d(Xc2, Yc2, Zc2)
        #self.markerPoints[i] = [x2,y2]
        # Perform 3D (Camera) to 2D project sp
        [x, y] = [0, 0]
        [x, y] = self.transform_3d_to_2d(Xc, Yc, Zc)
        #self.detectedSPs[i] = [x, y]
        vtk_sp_matrix = self.create_4x4_vtk_mat(x, y)
        # Setup Marker Matrix
        vtk_marker_matrix = self.create_4x4_vtk_mat(x2, y2)
        # Update Nodes

        # ONLY CURRENTLY SHOWING ONE DISPLAY NODE
        # WILL UPDATE WHEN DISPLAY IS FINALIZED
        #self.startPointSphere.SetMatrixTransformToParent(vtk_sp_matrix)
        #self.displayMarkerSphere.SetMatrixTransformToParent(vtk_marker_matrix)
        print "Start point number: ", i
        print x, y

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
        transform.SetName(v['name'])
        slicer.mrmlScene.AddNode(transform)
        transform.ApplyTransformMatrix(matrix)
        if v['name'] == 'Marker8ToTracker':
          self.realWorldTransformNode = transform

    def transform_3d_to_2d(self, Xc, Yx, Zc):
        x = np.round((Xc * self.fx / Zc) + self.cx)
        y = np.round((Yx * self.fy / Zc) + self.cy)
        return [x, y]

    def findStartPoints(self):
      if self.transformSet is False:
        msgOne = qt.QMessageBox.warning( self, 'Click to adjust Aruco Position', 'Please Adjust Aruco Cube First' )
        return

      lm = slicer.app.layoutManager()
      lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

      self.addTransforms()
      '''
      sphereModelPath = os.path.join(os.path.dirname(__file__), os.pardir , 'Resources/Fiducials/SphereModel.vtk')
      displayMarkerSphere = slicer.modules.models.logic().AddModel(sphereModelPath)
      startPointSphere = slicer.modules.models.logic().AddModel(sphereModelPath)

      
      displayMatrix = vtk.vtkMatrix4x4()
      displayMatrix.DeepCopy((1, 0, 0, 262, 0, 1, 0, 243, 0, 0, 1, 0, 0, 0, 0, 1))

      self.displayMarkerSphere  = slicer.vtkMRMLLinearTransformNode()
      self.displayMarkerSphere.SetName('Aurco Marker Display')
      slicer.mrmlScene.AddNode(self.displayMarkerSphere)
      self.displayMarkerSphere.ApplyTransformMatrix(displayMatrix)

      displayMarkerSphere.SetName('Aruco Display')
      displayMarkerSphere.SetAndObserveTransformNodeID(self.displayMarkerSphere.GetID())

      spDisplayMatrix = vtk.vtkMatrix4x4()
      spDisplayMatrix.DeepCopy((1, 0, 0, 328, 0, 1, 0, 239, 0, 0, 1, 0, 0, 0, 0, 1))

      self.startPointSphere  = slicer.vtkMRMLLinearTransformNode()
      self.startPointSphere.SetName('Aurco Marker Display')
      slicer.mrmlScene.AddNode(self.startPointSphere)
      self.startPointSphere.ApplyTransformMatrix(spDisplayMatrix)

      startPointSphere.SetName('SP Display')
      startPointSphere.SetAndObserveTransformNodeID(self.startPointSphere.GetID())
      '''

      aruco_position_matrix = vtk.vtkMatrix4x4()
      transformCube = slicer.util.getNode('Cube Position')
      aruco_position_matrix.DeepCopy(transformCube.GetMatrixTransformToParent())
      # Invert to get marker to CT origin
      aruco_position_matrix.Invert()

      # Rotate the start point in CT space to match the real world space
      fix_rotation_matrix = [[0, 0, 0, 1], [0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]]

      sps = slicer.mrmlScene.GetNodesByName('InsertionLandmarks')
      node = sps.GetItemAsObject(0)
      # Get the position of the first startpoint fiducial in the Slicer scene
      for i in range(node.GetNumberOfFiducials()):
        coord = [0, 0, 0]
        node.GetNthFiducialPosition(i, coord)
        coord.append(1)
        print 'coord: ', coord
        # Multiply to put start point relative to aruco marker cube origin
        spinMarker = aruco_position_matrix.MultiplyPoint(coord)
        spinMarker = np.matmul(fix_rotation_matrix, spinMarker)
        # Add the offset to cube face
        # Why did we choose this much offset?
        spinMarker[1] = spinMarker[1] + (18 / 2)
        self.spInMarker.append(spinMarker)

      self.onTransformOfInterestNodeModified(0, 0)
      self.addObservers()

    def enableClampAdjust(self, node, event):
      if node.GetNumberOfFiducials() > 0:
        self.adjustClamp.enabled = True
        self.findSP.enabled = True
        self.stopTracking.enabled = True

    def enableSPRemoval(self, node, event):
      if node.GetNumberOfFiducials() > 0:
        self.delSP.enabled = True
        if self.transformSet == True:
          self.findSP.enabled = True
          self.stopTracking.enabled = True
      
    def moveAruco(self):
      coords =[0, 0, 0]
      self.postions = slicer.mrmlScene.GetNodesByName('Aruco Position Points')
      self.node = self.postions.GetItemAsObject(0)
      self.node.GetNthFiducialPosition(0,coords)
      cylinderMatrix = vtk.vtkMatrix4x4()
      cylinderMatrix.DeepCopy((1, 0, 0, coords[0], 0, 0, -1, coords[1], 0, 1, 0, coords[2], 0, 0, 0, 1))
      cubeMatrix = vtk.vtkMatrix4x4()
      cubeMatrix.DeepCopy((1, 0, 0, coords[0], 0, 0, -1, -25 + coords[1], 0, 1, 0, coords[2], 0, 0, 0, 1))

      if self.node is not None and self.node.GetNumberOfFiducials() > 1:
          currentNum = self.node.GetNumberOfFiducials()
          for i in range(currentNum):
            self.node.RemoveMarkup(i)
            if i > 0:
              self.node.SetNthFiducialVisibility(i, 0)

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
      landmarks = slicer.mrmlScene.GetNodesByName('InsertionLandmarks')
      landmarks2 = slicer.mrmlScene.GetNodesByName('Aruco Position Points')
      self.fidNode = landmarks.GetItemAsObject(0)
      self.fidNode2 = landmarks2.GetItemAsObject(0)

      self.displayNode = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsDisplayNode3')
      self.displayNode.SetSelectedColor(1.0, 0, 0.2)
      self.displayNode.SetGlyphScale(5)
      
      self.fidObserve = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, self.addFiducialToTable)
      self.fidObserve2 = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, self.enableSPRemoval)
      self.fidObserve3 = self.fidNode2.AddObserver(self.fidNode2.MarkupAddedEvent, self.enableClampAdjust)
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
    
      self.loadFiducials()
      self.enableNavigation()

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