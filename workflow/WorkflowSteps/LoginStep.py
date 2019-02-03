from __main__ import qt, ctk, vtk, slicer

from Helper import *
import DICOM
import os
import math
from itertools import izip_longest # just zip_longest for python 3.X
import SampleData
from collections import defaultdict

class LoginStep(ctk.ctkWorkflowWidgetStep):

    def __init__(self, stepid):
      self.initialize(stepid)
      self.setName( 'Step 1: Load Volume')
      self.setDescription( 'Load the CT volume')
      print 'LoginStep'

    def killButton(self):
      # hide useless button
      bl = slicer.util.findChildren(text='Final')
      if len(bl):
        bl[0].hide()

    def createUserInterface(self):
      print 'Inside interface step'

      
      self.__layout = qt.QFormLayout( self )
      self.__layout.setVerticalSpacing( 5 )
      # Add empty rows
      
      self.__layout.addRow( "", qt.QWidget() )
      self.__layout.addRow( "", qt.QWidget() )
      
	    # Load Case group box
      loadCaseGroupBox = qt.QGroupBox()
      loadCaseGroupBox.title = "Load Volume"
      loadCaseGroupBox.setToolTip("Select the volume to load.")
      self.__layout.addWidget(loadCaseGroupBox)
      loadCaseFormLayout = qt.QFormLayout(loadCaseGroupBox)
      loadCaseFormLayout.setContentsMargins(10,10,10,10)

      self.loadCaseSelector = ctk.ctkPathLineEdit()
      self.loadCaseSelector.filters = ctk.ctkPathLineEdit.Files
      loadCaseFormLayout.addRow("NRRD Volume:", self.loadCaseSelector)
      self.loadCaseSelector.connect('currentPathChanged(const QString)', self.loadSavedCase)

      activeVolumeGroupBox = qt.QGroupBox()
      activeVolumeGroupBox.title = "Active Volume Data"
      self.__layout.addWidget(activeVolumeGroupBox)
      activeVolumeFormLayout = qt.QFormLayout(activeVolumeGroupBox)
      activeVolumeFormLayout.setContentsMargins(10,10,10,10)

      # select volume
      # creates combobox and populates it with all vtkMRMLScalarVolumeNodes in the scene
      self.__inputSelector = slicer.qMRMLNodeComboBox()
      self.__inputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      self.__inputSelector.addEnabled = False
      self.__inputSelector.removeEnabled = False
      self.__inputSelector.setMRMLScene( slicer.mrmlScene )
      activeVolumeFormLayout.addRow(self.__inputSelector )
      
      # Case Details
      self.libraryCollapsibleButton = ctk.ctkCollapsibleButton()
      self.libraryCollapsibleButton.text = "Saved Case Details"
      activeVolumeFormLayout.addRow(self.libraryCollapsibleButton)
      self.libraryCollapsibleButton.collapsed = True
      
      self.libraryLayout = qt.QFormLayout(self.libraryCollapsibleButton)
      self.libraryDetailsLabel = qt.QLabel('Case Details Here')
      self.libraryLayout.addWidget(self.libraryDetailsLabel)
      # self.updateWidgetFromParameters(self.parameterNode())
      qt.QTimer.singleShot(0, self.killButton)
      

    def loadSavedCase(self):
        if os.path.isfile(self.loadCaseSelector.currentPath) != False: 
            slicer.util.loadVolume(self.loadCaseSelector.currentPath)
            self.volume = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode1')  # on desktop change this back to 1
            self.libraryDetailsLabel.setText(self.loadCaseSelector.currentPath)

    #called when entering step
    def onEntry(self, comingFrom, transitionType):
      print 'Entered'
      super(LoginStep, self).onEntry(comingFrom, transitionType)
      # setup the interface
      
      lm = slicer.app.layoutManager()
      if lm == None: 
        return 
      lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalWidescreenView)
      qt.QTimer.singleShot(0, self.killButton)
    
    #check that conditions have been met before proceeding to next step
    def validate( self, desiredBranchId ):
      validationSuceeded = True
      super(LoginStep, self).validate(validationSuceeded, desiredBranchId)
      '''
      self.__parent.validate( desiredBranchId )
      
      #read current scalar volume node
      self.__baseline = self.__inputSelector.currentNode()  
     
      #if scalar volume exists proceed to next step and save node ID as 'baselineVolumeID'
      pNode = self.parameterNode()
      if self.__baseline != None:
        baselineID = self.__baseline.GetID()
        if baselineID != '':
          pNode = self.parameterNode()
          pNode.SetParameter('baselineVolumeID', baselineID)
          self.__parent.validationSucceeded(desiredBranchId)
      else:
        self.__parent.validationFailed(desiredBranchId, 'Error','Please load a volume before proceeding')
      '''
        
    #called when exiting step         
    def onExit(self, goingTo, transitionType):
      super(LoginStep, self).onExit(goingTo, transitionType)