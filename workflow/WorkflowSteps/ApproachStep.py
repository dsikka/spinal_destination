from __main__ import ctk
from __main__ import qt
from __main__ import slicer

import PythonQt
import PythonQt
import VolumeClipWithModel
import csv
import os
import string
import vtkITK

from Helper import *

class ApproachStep( ctk.ctkWorkflowWidgetStep) :

  def __init__( self, stepid, parameterNode ):
    self.initialize( stepid )
    self.setName( 'Step 2. Review Imaging' )
    #self.setDescription( "Please take the time to review the case imaging. The dropdown box below can be used to jump to specific levels. The slice intersections are shown by the crossing lines in the images. The slice angle can be adjusted." )
    self.startCount = 0
    self.idenCount = 0
    self.levelIndex = 0
    self.highCoord = [0,0,0]
    self.lowCoord = [0,0,0]
    self.highIndex = 0
    self.lowIndex = 0
    self.modCount = 0
    self.labels = 0
    self.lmOn = 0
    self.labelOn = 0
    self.boneThreshold = 150
    self.entry = 1
    self.adjustCount2 = 0
    self.levels = ("C1","C2","C3","C4","C5","C6","C7","T1","T2","T3","T4","T5","T6","T7","T8","T9","T10","T11","T12","L1", "L2", "L3", "L4", "L5","S1")
    self.fiducial = None
    self.oldRedPosition = 0
    self.oldYellowPosition = 0
    self.oldGreenPosition = 0
    self.lThresh = 1000
    self.uThresh = 0
    self.reset()
    self.__parameterNode  = parameterNode
    qt.QTimer.singleShot(0, self.killButton)

  def reset(self):
    self.__vrDisplayNode = None

    self.__roiTransformNode = None
    self.__baselineVolume = None

    self.__roi = None
    self.__roiObserverTag = None

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

    #label for ROI selector
    vertLabel = qt.QLabel( 'Vertebrae Labels:' )
    font = vertLabel.font
    font.setBold(True)
    vertLabel.setFont(font)

    labelText = qt.QLabel("Add Labels:  ")
    self.identify = qt.QPushButton("Click to Identify")
    self.identify.connect('clicked(bool)', self.addFiducials)
    self.identify.setMaximumWidth(170)

    blank = qt.QLabel("  ")
    blank.setMaximumWidth(30)

    self.vertebraeGridBox = qt.QFormLayout()
    self.vertebraeGridBox.addRow(vertLabel)
    self.vertebraeGridBox.addRow(labelText,self.identify)

    self.__layout.addRow(self.vertebraeGridBox)

    # Hide Threshold Details
    threshCollapsibleButton = ctk.ctkCollapsibleButton()
    #roiCollapsibleButton.setMaximumWidth(320)
    threshCollapsibleButton.text = "Bone Threshold Details"
    self.__layout.addWidget(threshCollapsibleButton)
    threshCollapsibleButton.collapsed = False

    # Layout
    threshLayout = qt.QFormLayout(threshCollapsibleButton)

    self.__loadThreshButton = qt.QPushButton("Show Threshold Label")
    threshLayout.addRow(self.__loadThreshButton)
    self.__loadThreshButton.connect('clicked(bool)', self.showThreshold)

    self.__corticalRange = slicer.qMRMLRangeWidget()
    self.__corticalRange.decimals = 0
    self.__corticalRange.singleStep = 1

    cortLabel = qt.QLabel('Choose Cortical Bone Threshold:')
    self.__corticalRange.connect('valuesChanged(double,double)', self.onCorticalChanged)
    threshLayout.addRow(cortLabel)
    threshLayout.addRow(self.__corticalRange)


    # Hide ROI Details
    roiCollapsibleButton = ctk.ctkCollapsibleButton()
    #roiCollapsibleButton.setMaximumWidth(320)
    roiCollapsibleButton.text = "Advanced Options"
    self.__layout.addWidget(roiCollapsibleButton)
    roiCollapsibleButton.collapsed = True

    # Layout
    roiLayout = qt.QFormLayout(roiCollapsibleButton)

    self.__loadLandmarksButton = qt.QPushButton("Show Crop Landmarks")
    roiLayout.addRow(self.__loadLandmarksButton)
    self.__loadLandmarksButton.connect('clicked(bool)', self.showLandmarks)

    #label for ROI selector
    roiLabel = qt.QLabel( 'Select ROI:' )
    font = roiLabel.font
    font.setBold(True)
    roiLabel.setFont(font)

    #creates combobox and populates it with all vtkMRMLAnnotationROINodes in the scene
    self.__roiSelector = slicer.qMRMLNodeComboBox()
    self.__roiSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
    self.__roiSelector.toolTip = "ROI defining the structure of interest"
    self.__roiSelector.setMRMLScene(slicer.mrmlScene)
    self.__roiSelector.addEnabled = 1

    #add label + combobox
    roiLayout.addRow( roiLabel, self.__roiSelector )

    self.__roiSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onROIChanged)

    # the ROI parameters
    # GroupBox to hold ROI Widget
    voiGroupBox = qt.QGroupBox()
    voiGroupBox.setTitle( 'Define VOI' )
    roiLayout.addRow( voiGroupBox )

    # create form layout for GroupBox
    voiGroupBoxLayout = qt.QFormLayout( voiGroupBox )

    # create ROI Widget and add it to the form layout of the GroupBox
    self.__roiWidget = PythonQt.qSlicerAnnotationsModuleWidgets.qMRMLAnnotationROIWidget()
    voiGroupBoxLayout.addRow( self.__roiWidget )

    # Hide VR Details
    vrCollapsibleButton = ctk.ctkCollapsibleButton()
    #roiCollapsibleButton.setMaximumWidth(320)
    vrCollapsibleButton.text = "Rendering Details"
    #self.__layout.addWidget(vrCollapsibleButton)
    vrCollapsibleButton.collapsed = True

    # Layout
    vrLayout = qt.QFormLayout(vrCollapsibleButton)

    # the ROI parameters
    # GroupBox to hold ROI Widget
    vrGroupBox = qt.QGroupBox()
    vrGroupBox.setTitle( 'Define Rendering' )
    vrLayout.addRow( vrGroupBox )

    # create form layout for GroupBox
    vrGroupBoxLayout = qt.QFormLayout( vrGroupBox )

    # create ROI Widget and add it to the form layout of the GroupBox
    self.__vrWidget = PythonQt.qSlicerVolumeRenderingModuleWidgets.qSlicerPresetComboBox()
    #self.__vrWidget = PythonQt.qSlicerVolumeRenderingModuleWidgets.qMRMLVolumePropertyNodeWidget()
    vrGroupBoxLayout.addRow( self.__vrWidget )

    # initialize VR
    self.__vrLogic = slicer.modules.volumerendering.logic()

    lm = slicer.app.layoutManager()
    redWidget = lm.sliceWidget('Red')
    self.__redController = redWidget.sliceController()
    self.__redLogic = redWidget.sliceLogic()

    yellowWidget = lm.sliceWidget('Yellow')
    self.__yellowController = yellowWidget.sliceController()
    self.__yellowLogic = yellowWidget.sliceLogic()

    greenWidget = lm.sliceWidget('Green')
    self.__greenController = greenWidget.sliceController()
    self.__greenLogic = greenWidget.sliceLogic()

    qt.QTimer.singleShot(0, self.killButton)

  # This changes the threshold in each of the three displays but what is it thresholding?
  # Why is that important in generating the ROI?
  def showThreshold(self):
    if self.labelOn == 0:
        print "ON"
        lm = slicer.app.layoutManager()
        redWidget = lm.sliceWidget('Red')
        redController = redWidget.sliceController()

        yellowWidget = lm.sliceWidget('Yellow')
        yellowController = yellowWidget.sliceController()

        greenWidget = lm.sliceWidget('Green')
        greenController = greenWidget.sliceController()

        yellowController.setLabelMapHidden(True)
        greenController.setLabelMapHidden(True)
        redController.setLabelMapHidden(True)
        self.labelOn = 1
        self.__loadThreshButton.setText("Show Threshold Label")
    else:
        lm = slicer.app.layoutManager()
        print "OFF"
        redWidget = lm.sliceWidget('Red')
        redController = redWidget.sliceController()

        yellowWidget = lm.sliceWidget('Yellow')
        yellowController = yellowWidget.sliceController()

        greenWidget = lm.sliceWidget('Green')
        greenController = greenWidget.sliceController()

        yellowController.setLabelMapHidden(False)
        greenController.setLabelMapHidden(False)
        redController.setLabelMapHidden(False)
        self.labelOn = 0
        self.__loadThreshButton.setText("Hide Threshold Label")

  # What is this supposed to bring into view?
  def showLandmarks(self):
    markup = slicer.modules.markups.logic()
    if self.lmOn == 0:
        b = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode2')
        markup.SetAllMarkupsVisibility(b,1)
        self.__loadLandmarksButton.setText("Hide Crop Landmarks")
        self.lmOn = 1
    else:
        b = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode2')
        markup.SetAllMarkupsVisibility(b,0)
        self.__loadLandmarksButton.setText("Show Crop Landmarks")
        self.lmOn = 0


  def onCorticalChanged(self):
    r = self.__redLogic.GetSliceOffset()
    y = self.__yellowLogic.GetSliceOffset()
    g = self.__greenLogic.GetSliceOffset()

    range0 = self.__corticalRange.minimumValue
    range1 = self.__corticalRange.maximumValue

    self.boneThreshold = range0

    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(self.__roiVolume.GetImageData())
    thresh.ThresholdBetween(range0, range1)
    thresh.SetInValue(10)
    thresh.SetOutValue(0)
    thresh.ReplaceOutOn()
    thresh.ReplaceInOn()
    thresh.Update()

    if self.__corticalNode != None:
        self.__corticalNode.SetAndObserveImageData(thresh.GetOutput())

    self.__yellowController.setSliceOffsetValue(y)
    self.__greenController.setSliceOffsetValue(g)
    self.__redController.setSliceOffsetValue(r)


  def addFiducials(self):
      if self.startCount == 0:
        self.begin()
        self.startCount = 1
        self.identify.setText("Stop Identifying")
        msgOne = qt.QMessageBox.warning( self, 'Identify Levels', 'Click on Known Vertebral Body' )

      elif self.startCount == 1:
        self.stop()
        self.startCount = 0
        self.identify.setText("Label Vertebrae")
        markup = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode1')
        markup.SetLocked(1)
        #self.identify.enabled(False)

  def loadLandmarks(self):
    a = slicer.mrmlScene.GetNodesByName('Vertebrae Labels')
    b = a.GetItemAsObject(0)
    b.RemoveAllMarkups()
    rownum = 0
    self.fidObserve = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, self.addIdentityFiducial)

  def begin(self):
      selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
      # place rulers
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      # to place ROIs use the class name vtkMRMLAnnotationROINode
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      placeModePersistence = 1
      interactionNode.SetPlaceModePersistence(placeModePersistence)
      # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
      interactionNode.SetCurrentInteractionMode(1)

  def stop(self):
      selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
      # place rulers
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      # to place ROIs use the class name vtkMRMLAnnotationROINode
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      placeModePersistence = 1
      interactionNode.SetPlaceModePersistence(placeModePersistence)
      # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
      interactionNode.SetCurrentInteractionMode(2)

  def addIdentityFiducial(self, observer, event):

        #print event
        #print "MODIFIED"
        #labels = slicer.mrmlScene.GetNodesByName('Vertebrae Labels')
        #self.fiducial = labels.GetItemAsObject(0)
        #self.fiducial = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode1')
        self.fidNumber = self.fidNode.GetNumberOfFiducials()
        self.fidPosition = [0,0,0]
        self.fidNode.GetNthFiducialPosition(self.fidNumber-1,self.fidPosition)
        print "Label added"
        print self.fidNumber
        print self.fidPosition
        if self.fidNumber == 1 and self.idenCount == 0:
            self.fidNode.SetNthFiducialLabel(0, "Level Chosen")
            qW = qt.QWidget()
            msgTwo = qt.QInputDialog(qW)
            startLevel = msgTwo.getItem(qW,"Identify Levels","Which level did you identify?",["C1","C2","C3","C4","C5","C6","C7","T1","T2","T3","T4","T5","T6","T7","T8","T9","T10","T11","T12","L1", "L2", "L3", "L4", "L5","S1"],0)
            self.idenCount = 1
            self.levelIndex = self.levels.index(startLevel)
            #print self.levelIndex
            self.fidNode.SetNthFiducialLabel(0, startLevel)
            self.fidNode.GetNthFiducialPosition(0,self.highCoord)
            self.fidNode.GetNthFiducialPosition(0,self.lowCoord)
            self.highIndex = self.levelIndex
            self.lowIndex = self.levelIndex

        elif self.fidPosition[2] < self.lowCoord[2]:
            self.fidNode.SetNthFiducialLabel(self.fidNumber - 1, self.levels[self.lowIndex + 1])
            self.lowIndex += 1
            self.lowCoord = self.fidPosition
        elif self.fidPosition[2] > self.highCoord[2]:
            self.fidNode.SetNthFiducialLabel(self.fidNumber - 1, self.levels[self.highIndex - 1])
            self.vSelector.addItem(self.levels[self.highIndex - 1])
            self.highIndex -= 1
            self.highCoord = self.fidPosition

        # Allow ROI to be generated based on added fiducials
        self.autoROI()

  ## What are all the ROI functions below doing?

  def autoROI(self):
    volume = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode1')
    bounds = [0,0,0,0,0,0]
    volume.GetRASBounds(bounds)
    roi = self.__roiSelector.currentNode()

    xCenter = self.highCoord[0]
    yCenter = self.highCoord[1]
    zCenter = (self.highCoord[2]+self.lowCoord[2])/2
    xRadius = 50
    yRadius = 50
    zRadius = (self.highCoord[2]-zCenter) + 10

    roiCenter = [xCenter,yCenter,zCenter]
    roiRadius = [xRadius,yRadius,zRadius]

    roi.SetXYZ(roiCenter)
    roi.SetRadiusXYZ(roiRadius)

  #called when ROI bounding box is altered
  def onROIChanged(self):

    #read ROI node from combobox
    roi = self.__roiSelector.currentNode()

    if roi != None:
      self.__roi = roi

      # create VR node first time a valid ROI is selected
      self.InitVRDisplayNode()

      # update VR settings each time ROI changes
      pNode = self.__parameterNode
      # get scalar volume node loaded in previous step
      v = slicer.mrmlScene.GetNodeByID(pNode.GetParameter('baselineVolumeID'))

      #set parameters for VR display node
      self.__vrDisplayNode.SetAndObserveROINodeID(roi.GetID())
      self.__vrDisplayNode.SetCroppingEnabled(1)
      self.__vrDisplayNode.VisibilityOn()

      if self.__roiObserverTag != None:
        self.__roi.RemoveObserver(self.__roiObserverTag)

      #add observer to ROI. call self.processROIEvents if ROI is altered
      self.__roiObserverTag = self.__roi.AddObserver('ModifiedEvent', self.processROIEvents)

      self.__roiWidget.setMRMLAnnotationROINode(roi)
      self.__roi.SetDisplayVisibility(1)

      roiCenter=[0,0,0]
      roi.GetXYZ(roiCenter)
      camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
      camera.SetFocalPoint(roiCenter)
      camera.SetPosition(roiCenter[0],-600,roiCenter[2])
      camera.SetViewUp([-1,0,0])

      if self.entry == 1:
        self.__roiWidget.setInteractiveMode(0)
        self.entry = 2
    
  def processROIEvents(self,node,event):
    # get the range of intensities inside the ROI

    # get the IJK bounding box of the voxels inside ROI
    roiCenter = [0,0,0]
    roiRadius = [0,0,0]

    #get center coordinate
    self.__roi.GetXYZ(roiCenter)
    lm = slicer.app.layoutManager()
    redWidget = lm.sliceWidget('Red')
    redController = redWidget.sliceController()

    yellowWidget = lm.sliceWidget('Yellow')
    yellowController = yellowWidget.sliceController()

    greenWidget = lm.sliceWidget('Green')
    greenController = greenWidget.sliceController()
    fidNumber = self.fidNode.GetNumberOfFiducials()
    fidPosition = [0,0,0]
    self.fidNode.GetNthFiducialPosition(fidNumber-1,fidPosition)

    yellowController.setSliceOffsetValue(fidPosition[0])
    greenController.setSliceOffsetValue(fidPosition[1])
    redController.setSliceOffsetValue(fidPosition[2])

    #get radius
    self.__roi.GetRadiusXYZ(roiRadius)

    #get IJK coordinates of 8 corners of ROI
    roiCorner1 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
    roiCorner2 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
    roiCorner3 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
    roiCorner4 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]
    roiCorner5 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
    roiCorner6 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
    roiCorner7 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
    roiCorner8 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]

    #get RAS transformation matrix of scalar volume and convert it to IJK matrix
    ras2ijk = vtk.vtkMatrix4x4()
    self.__baselineVolume.GetRASToIJKMatrix(ras2ijk)

    roiCorner1ijk = ras2ijk.MultiplyPoint(roiCorner1)
    roiCorner2ijk = ras2ijk.MultiplyPoint(roiCorner2)
    roiCorner3ijk = ras2ijk.MultiplyPoint(roiCorner3)
    roiCorner4ijk = ras2ijk.MultiplyPoint(roiCorner4)
    roiCorner5ijk = ras2ijk.MultiplyPoint(roiCorner5)
    roiCorner6ijk = ras2ijk.MultiplyPoint(roiCorner6)
    roiCorner7ijk = ras2ijk.MultiplyPoint(roiCorner7)
    roiCorner8ijk = ras2ijk.MultiplyPoint(roiCorner8)

    lowerIJK = [0, 0, 0]
    upperIJK = [0, 0, 0]

    lowerIJK[0] = min(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
    lowerIJK[1] = min(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
    lowerIJK[2] = min(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])

    upperIJK[0] = max(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
    upperIJK[1] = max(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
    upperIJK[2] = max(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])

    #get image data of scalar volume
    image = self.__baselineVolume.GetImageData()

    #create image clipper
    clipper = vtk.vtkImageClip()
    clipper.ClipDataOn()
    clipper.SetOutputWholeExtent(int(lowerIJK[0]),int(upperIJK[0]),int(lowerIJK[1]),int(upperIJK[1]),int(lowerIJK[2]),int(upperIJK[2]))
    clipper.SetInputData(image)
    clipper.Update()
    
    #read upper and lower threshold values from clipped volume
    roiImageRegion = clipper.GetOutput()
    intRange = roiImageRegion.GetScalarRange()
    print intRange[0]
    threshDifference = -1000 - intRange[0]
    self.lThresh = intRange[0] + 1000
    self.uThresh = intRange[1] + threshDifference
    print "lower thresh" + str(int(self.lThresh))

  #set up VR
  def InitVRDisplayNode(self):
    #If VR node exists, load it from saved ID
    if self.__vrDisplayNode == None:
      pNode = self.__parameterNode
      vrNodeID = pNode.GetParameter('vrDisplayNodeID')
      if vrNodeID == '':
        self.__vrDisplayNode = slicer.modules.volumerendering.logic().CreateVolumeRenderingDisplayNode()
        #set rendering type
        #self.__vrDisplayNode = slicer.vtkMRMLGPUTextureMappingVolumeRenderingDisplayNode()
        self.__vrDisplayNode = slicer.vtkMRMLGPURayCastVolumeRenderingDisplayNode()
        slicer.mrmlScene.AddNode(self.__vrDisplayNode)
        # self.__vrDisplayNode.SetExpectedFPS(15)
        self.__vrDisplayNode.UnRegister(slicer.modules.volumerendering.logic())
        v = slicer.mrmlScene.GetNodeByID(self.__parameterNode.GetParameter('baselineVolumeID'))
        Helper.InitVRDisplayNode(self.__vrDisplayNode, v.GetID(), self.__roi.GetID())
        v.AddAndObserveDisplayNodeID(self.__vrDisplayNode.GetID())
      else:
        self.__vrDisplayNode = slicer.mrmlScene.GetNodeByID(vrNodeID)

    viewNode = slicer.util.getNode('vtkMRMLViewNode1')
    self.__vrDisplayNode.AddViewNodeID(viewNode.GetID())

    slicer.modules.volumerendering.logic().CopyDisplayToVolumeRenderingDisplayNode(self.__vrDisplayNode)

    #update opacity and color map
    # self.__vrOpacityMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetScalarOpacity()
    # self.__vrColorMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetRGBTransferFunction()

    #create new opacity map with voxels falling between upper and lower threshold values at 100% opacity. All others at 0%
    # self.__vrOpacityMap.RemoveAllPoints()
    print "lower threshold"
    print self.lThresh
    '''
    self.__vrOpacityMap.AddPoint(-3024 + self.lThresh,0)
    self.__vrOpacityMap.AddPoint(-86.9767+ self.lThresh,0)
    self.__vrOpacityMap.AddPoint(45.3791+ self.lThresh,0.169643)
    self.__vrOpacityMap.AddPoint(139.919+ self.lThresh,0.589286)
    self.__vrOpacityMap.AddPoint(347.907+ self.lThresh,0.607143)
    self.__vrOpacityMap.AddPoint(1224.16+ self.lThresh,0.607143)
    self.__vrOpacityMap.AddPoint(3071+ self.lThresh,0.616071)

    # setup color transfer function once
    # two points at 0 and 500 force all voxels to be same color (any two points will work)
    self.__vrColorMap.RemoveAllPoints()
    self.__vrColorMap.AddRGBPoint(-3024+ self.lThresh, 0,0,0)
    self.__vrColorMap.AddRGBPoint(-86.9767+ self.lThresh, 0,0.25098,1)
    self.__vrColorMap.AddRGBPoint(45.3791+ self.lThresh, 1,0,0)
    self.__vrColorMap.AddRGBPoint(139.919+ self.lThresh, 1,0.894893,0.894893)
    self.__vrColorMap.AddRGBPoint(347.907+ self.lThresh, 1,1,0.25098)
    self.__vrColorMap.AddRGBPoint(1224.16+ self.lThresh, 1,1,1)
    self.__vrColorMap.AddRGBPoint(3071+ self.lThresh, 0.827451,0.658824,1)
    '''
  def onEntry(self,comingFrom,transitionType):
    super(ApproachStep, self).onEntry(comingFrom, transitionType)

    # setup the interface
    lm = slicer.app.layoutManager()
    if lm == None:
        return
    #lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutSideBySideView)

    customLayout = ("<layout type=\"horizontal\" split=\"true\" >"
        " <item>"
        "  <view class=\"vtkMRMLSliceNode\" singletontag=\"Red\">"
        "    <property name=\"orientation\" action=\"default\">Axial</property>"
        "    <property name=\"viewlabel\" action=\"default\">R</property>"
        "    <property name=\"viewcolor\" action=\"default\">#F34A33</property>"
        "  </view>"
        " </item>"
        " <item>"
        "  <view class=\"vtkMRMLSliceNode\" singletontag=\"Yellow\">"
        "    <property name=\"orientation\" action=\"default\">Axial</property>"
        "    <property name=\"viewlabel\" action=\"default\">Y</property>"
        "    <property name=\"viewcolor\" action=\"default\">#EDD54C</property>"
        "  </view>"
        " </item>"
        " <item>"
        "  <view class=\"vtkMRMLSliceNode\" singletontag=\"Green\">"
        "    <property name=\"orientation\" action=\"default\">Axial</property>"
        "    <property name=\"viewlabel\" action=\"default\">G</property>"
        "    <property name=\"viewcolor\" action=\"default\">#6EB04B</property>"
        "  </view>"
        " </item>"
        "</layout>")

    customLayoutId=502

    #layoutManager = slicer.app.layoutManager()
    lm.layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)
    lm.setLayout(customLayoutId)

    markup = slicer.modules.markups.logic()
    markup.AddNewFiducialNode('Vertebrae Labels')
    landmarks = slicer.mrmlScene.GetNodesByName('Vertebrae Labels')
    self.fidNode = landmarks.GetItemAsObject(0)

    slicer.app.applicationLogic().PropagateVolumeSelection(1)

    #create progress bar dialog
    self.progress = qt.QProgressDialog(slicer.util.mainWindow())
    self.progress.minimumDuration = 0
    self.progress.show()
    self.progress.setValue(0)
    self.progress.setMaximum(0)
    self.progress.setCancelButton(0)
    self.progress.setMinimumWidth(500)
    self.progress.setWindowModality(2)

    self.progress.setLabelText('Generating Volume Rendering...')
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress.repaint()

    #read scalar volume node ID from previous step
    pNode = self.__parameterNode
    baselineVolume = Helper.getNodeByID(pNode.GetParameter('baselineVolumeID'))
    self.__baselineVolume = baselineVolume
    
    roiTransformID = pNode.GetParameter('roiTransformID')
    roiTransformNode = None

    if roiTransformID != '':
      roiTransformNode = Helper.getNodeByID(roiTransformID)
    else:
      roiTransformNode = slicer.vtkMRMLLinearTransformNode()
      slicer.mrmlScene.AddNode(roiTransformNode)
      pNode.SetParameter('roiTransformID', roiTransformNode.GetID())

    dm = vtk.vtkMatrix4x4()
    baselineVolume.GetIJKToRASDirectionMatrix(dm)
    dm.SetElement(0,3,0)
    dm.SetElement(1,3,0)
    dm.SetElement(2,3,0)
    dm.SetElement(0,0,abs(dm.GetElement(0,0)))
    dm.SetElement(1,1,abs(dm.GetElement(1,1)))
    dm.SetElement(2,2,abs(dm.GetElement(2,2)))
    roiTransformNode.SetAndObserveMatrixTransformToParent(dm)

    Helper.SetBgFgVolumes(pNode.GetParameter('baselineVolumeID'))
    Helper.SetLabelVolume(None)

    # use this transform node to align ROI with the axes of the baseline
    # volume
    roiTfmNodeID = pNode.GetParameter('roiTransformID')
    if roiTfmNodeID != '':
      self.__roiTransformNode = Helper.getNodeByID(roiTfmNodeID)
    else:
      Helper.Error('Internal error! Error code CT-S2-NRT, please report!')

    # get the roiNode from parameters node, if it exists, and initialize the
    # GUI
    self.updateWidgetFromParameterNode(pNode)

    if self.__roi != None:
      self.__roi.SetDisplayVisibility(0)
      self.InitVRDisplayNode()

    #close progress bar
    self.progress.setValue(2)
    self.progress.repaint()
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress.close()
    self.progress = None

    #turn off rendering to save memory
    slicer.mrmlScene.GetNodesByName('GPURayCastVolumeRendering').GetItemAsObject(0).SetVisibility(0)
    #pNode.SetParameter('currentStep', self.stepid)

    # Enable Slice Intersections
    viewNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSliceCompositeNode')
    viewNodes.UnRegister(slicer.mrmlScene)
    viewNodes.InitTraversal()
    viewNode = viewNodes.GetNextItemAsObject()
    while viewNode:
        viewNode.SetSliceIntersectionVisibility(1)
        viewNode = viewNodes.GetNextItemAsObject()

    self.redTransform = vtk.vtkTransform()
    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
    self.redTransform.SetMatrix(viewSlice.GetSliceToRAS())
    #print "Red Transform"
    #print self.redTransform
    self.yellowTransform = vtk.vtkTransform()
    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeYellow')
    self.yellowTransform.SetMatrix(viewSlice.GetSliceToRAS())
    #print "Yellow Transform"
    #print self.yellowTransform
    self.greenTransform = vtk.vtkTransform()
    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
    self.greenTransform.SetMatrix(viewSlice.GetSliceToRAS())
    #print "Green Transform"
    #print self.greenTransform

    n =  self.__baselineVolume
    for color in ['Red', 'Yellow', 'Green']:
        a = slicer.app.layoutManager().sliceWidget(color).sliceLogic().GetSliceNode().GetFieldOfView()
        slicer.app.layoutManager().sliceWidget(color).sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(n.GetID())
  
    lm.sliceWidget("Yellow").sliceController().fitSliceToBackground()
    lm.sliceWidget("Red").sliceController().fitSliceToBackground()
    lm.sliceWidget("Green").sliceController().fitSliceToBackground()

    qt.QTimer.singleShot(0, self.killButton)
    self.showThreshold()
    self.loadLandmarks()
    

  def validate( self, desiredBranchId ):
    validationSuceeded = True
    super(ApproachStep, self).validate(validationSuceeded, desiredBranchId)


  def onExit(self, goingTo, transitionType):

    inputModel = slicer.mrmlScene.GetNodeByID('vtkMRMLModelNode4')
    #self.clipBody(inputModel)

    pNode = self.__parameterNode
    if self.__roi != None:
        self.__roi.RemoveObserver(self.__roiObserverTag)
        self.__roi.SetDisplayVisibility(0)

    if self.__roiSelector.currentNode() != None:
        pNode.SetParameter('roiNodeID', self.__roiSelector.currentNode().GetID())

    if self.__vrDisplayNode != None:
        #self.__vrDisplayNode.VisibilityOff()
        pNode.SetParameter('vrDisplayNodeID', self.__vrDisplayNode.GetID())

    if goingTo.id() == 'Screw': # Change to next step
        self.doStepProcessing()

    super(ApproachStep, self).onExit(goingTo, transitionType)

    # Enable Slice Intersections
    viewNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSliceCompositeNode')
    viewNodes.UnRegister(slicer.mrmlScene)
    viewNodes.InitTraversal()
    viewNode = viewNodes.GetNextItemAsObject()
    while viewNode:
        viewNode.SetSliceIntersectionVisibility(0)
        viewNode = viewNodes.GetNextItemAsObject()

    rulers = slicer.mrmlScene.GetNodesByClass('vtkMRMLAnnotationRulerNode')
    for x in range(0,rulers.GetNumberOfItems()):
        rulerX = rulers.GetItemAsObject(x)
        rulerX.SetDisplayVisibility(0)

    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
    viewSlice.GetSliceToRAS().DeepCopy(self.redTransform.GetMatrix())
    viewSlice.UpdateMatrices()
    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeYellow')
    viewSlice.GetSliceToRAS().DeepCopy(self.yellowTransform.GetMatrix())
    viewSlice.UpdateMatrices()
    viewSlice = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
    viewSlice.GetSliceToRAS().DeepCopy(self.greenTransform.GetMatrix())
    viewSlice.UpdateMatrices()

  def updateWidgetFromParameterNode(self, parameterNode):
    roiNodeID = parameterNode.GetParameter('roiNodeID')

    if roiNodeID != '':
      self.__roi = slicer.mrmlScene.GetNodeByID(roiNodeID)
      self.__roiSelector.setCurrentNode(Helper.getNodeByID(self.__roi.GetID()))
    else:
      roi = slicer.vtkMRMLAnnotationROINode()
      roi.Initialize(slicer.mrmlScene)
      parameterNode.SetParameter('roiNodeID', roi.GetID())
      self.__roiSelector.setCurrentNode(roi)

    baselineROIVolume = Helper.getNodeByID(parameterNode.GetParameter('baselineVolumeID'))
    baselineROIRange = baselineROIVolume.GetImageData().GetScalarRange()
    self.__roiVolume = baselineROIVolume

    self.__corticalRange.minimum = -1000
    self.__corticalRange.maximum = baselineROIRange[1]

    vl = slicer.modules.volumes.logic()
    self.__corticalNode = vl.CreateAndAddLabelVolume(slicer.mrmlScene, baselineROIVolume, 'corticalROI_segmentation')
    #self.__cancellousNode = vl.CreateAndAddLabelVolume(slicer.mrmlScene, baselineROIVolume, 'cancellousROI_segmentation')

    Helper.SetLabelVolume(None)
    labelsColorNode = slicer.modules.colors.logic().GetColorTableNodeID(10)
    self.__corticalNode.GetDisplayNode().SetAndObserveColorNodeID(labelsColorNode)
    Helper.SetLabelVolume(self.__corticalNode.GetID())

    thresholdRange = str(0.5*(baselineROIRange[0]+baselineROIRange[1]))+','+str(baselineROIRange[1])
    if thresholdRange != '':
        rangeArray = string.split(thresholdRange, ',')

        #self.__corticalRange.minimumValue = float(rangeArray[0])
        self.__corticalRange.minimumValue = 150
        self.__corticalRange.maximumValue = float(rangeArray[1])

        #self.__cancellousRange.minimumValue = float(rangeArray[0])
        #self.__cancellousRange.maximumValue = float(rangeArray[1])
    else:
        Helper.Error('Unexpected parameter values!')

    #self.onCancellousChanged()
    self.onCorticalChanged()
    #print "label should be made"

  def grayModel(self, volumeNode):
    parameters = {}
    parameters["InputVolume"] = volumeNode.GetID()
    parameters["Threshold"] = self.boneThreshold
    print "Bone Threshold = " + str(self.boneThreshold)
    outModel = slicer.vtkMRMLModelNode()
    slicer.mrmlScene.AddNode( outModel )
    parameters["OutputGeometry"] = outModel.GetID()
    grayMaker = slicer.modules.grayscalemodelmaker
    #outModel.GetDisplayNode().SetColor(0.95, 0.84, 0.57)
    return (slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True))

  # What does this do?
  # Takes the previously added fiducials and adds additional fiducials?
  def addCropFiducials(self):
    landmarks = slicer.mrmlScene.GetNodesByName('Crop Landmarks')
    cropLandmarks = landmarks.GetItemAsObject(0)

    if cropLandmarks == None:
        print "Adding Landmarks"
        markup = slicer.modules.markups.logic()
        markup.AddNewFiducialNode('Crop Landmarks')
    else:
        print "Other option"
        cropLandmarks.RemoveAllMarkups()
    self.fiducial = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode1')
    self.fidNumber = self.fiducial.GetNumberOfFiducials()
    for i in range(0,self.fidNumber):
        coords = [0,0,0]
        # Get the position of each of the marked fiducials that were identified by the surgeon
        self.fiducial.GetNthFiducialPosition(i,coords)
        label = self.fiducial.GetNthFiducialLabel(i)
        if label[0] == 'L' or label[0] == 'S':
            if label[1] == '1' or label[1] == '2':
                # Using the other points identified, generate a bounding structure?
                slicer.modules.markups.logic().AddFiducial(coords[0],coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]-50,coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]+50,coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]-90,coords[1]-100,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]+90,coords[1]-100,coords[2])
            else:
                slicer.modules.markups.logic().AddFiducial(coords[0],coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]-70,coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]+70,coords[1]+70,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]-100,coords[1]-100,coords[2])
                slicer.modules.markups.logic().AddFiducial(coords[0]+100,coords[1]-100,coords[2])
        elif label[0] == 'T':
            slicer.modules.markups.logic().AddFiducial(coords[0],coords[1]+70,coords[2])
            slicer.modules.markups.logic().AddFiducial(coords[0]-50,coords[1]+70,coords[2])
            slicer.modules.markups.logic().AddFiducial(coords[0]+50,coords[1]+70,coords[2])
            slicer.modules.markups.logic().AddFiducial(coords[0]-90,coords[1]-100,coords[2])
            slicer.modules.markups.logic().AddFiducial(coords[0]+90,coords[1]-100,coords[2])
    #a = slicer.modules.markups.logic()
    b = slicer.mrmlScene.GetNodeByID('vtkMRMLMarkupsFiducialNode2')
    markup.SetAllMarkupsVisibility(b,0)

  def cropVolumeFromLandmarks(self, name, clipOutside):
    # Input Volume
    inputVolume = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode1')

    # Create empty model node
    
    clippingModel = slicer.vtkMRMLModelNode()
    clippingModel.SetName('clipModel')
    slicer.mrmlScene.AddNode(clippingModel)
    

    # Create output volume
    outputVolume = slicer.vtkMRMLScalarVolumeNode()
    outputVolume.SetName(name)
    slicer.mrmlScene.AddNode(outputVolume)

    # Get crop landmarks
    landmarks = slicer.mrmlScene.GetNodesByName('Crop Landmarks')
    cropLandmarks = landmarks.GetItemAsObject(0)

    # Clip volume
    #logic = VolumeClipWithModelLogic()
    logic = VolumeClipWithModel.VolumeClipWithModelLogic()
    clipOutsideSurface = clipOutside
    fillValue = -1000
    logic.updateModelFromMarkup(cropLandmarks, clippingModel)
    logic.clipVolumeWithModel(inputVolume, clippingModel, clipOutsideSurface, fillValue, outputVolume)
    logic.showInSliceViewers(outputVolume, ["Red", "Yellow", "Green"])
    clippingModel.SetDisplayVisibility(0)

  def doStepProcessing(self):
    landmarks = slicer.mrmlScene.GetNodesByName('Crop Landmarks')
    cropLandmarks = landmarks.GetItemAsObject(0)
    if cropLandmarks == None:
        print "No Crop Landmarks"
        self.addCropFiducials()
    '''
    prepare roi image for the next step
    '''
    #create progress bar dialog
    self.progress2 = qt.QProgressDialog(slicer.util.mainWindow())
    self.progress2.minimumDuration = 0
    self.progress2.show()
    self.progress2.setValue(0)
    self.progress2.setMaximum(0)
    self.progress2.setCancelButton(0)
    self.progress2.setMinimumWidth(500)
    self.progress2.setWindowModality(2)

    self.progress2.setLabelText('Generating Surface Model...')
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress2.repaint()

    self.cropVolumeFromLandmarks('opening', True)
    self.cropVolumeFromLandmarks('body', False)
    vols = slicer.mrmlScene.GetNodesByName('opening')
    cropVolume = vols.GetItemAsObject(0)
    self.grayModel(cropVolume)
    outModel = slicer.mrmlScene.GetNodeByID('vtkMRMLModelNode6')
    outModel.GetDisplayNode().SetColor(1, 0.97, 0.79)

    logic = slicer.modules.volumerendering.logic()
    a = slicer.mrmlScene.GetNodesByName('body')
    b = a.GetItemAsObject(0)
    c = slicer.mrmlScene.GetNodesByName('GPURayCastVolumeRendering').GetItemAsObject(0)
    logic.UpdateDisplayNodeFromVolumeNode(c,b)
    d = slicer.mrmlScene.GetNodeByID('vtkMRMLAnnotationROINode1')

    c.SetAndObserveROINodeID(d.GetID())
    c.SetVisibility(0)

    #close progress bar
    self.progress2.setValue(2)
    self.progress2.repaint()
    slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
    self.progress2.close()
    self.progress2 = None
    self.InitVRDisplayNode()

    slicer.mrmlScene.RemoveNode(self.__corticalNode)