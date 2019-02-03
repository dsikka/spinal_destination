import qt, ctk, vtk, slicer

import DICOM
import os

class LoginStep(ctk.ctkWorkflowWidgetStep):

    def __init__( self, stepid ):
      self.initialize( stepid )
      self.setName( 'Step 1. Load Volume' )
      self.setDescription('Select the path of the spine CT volume')
      self.loadCaseSelector = None

    def createUserInterface( self ):
      layout = qt.QFormLayout( self )
      layout.setVerticalSpacing( 5 )

      loadCaseGroupBox = qt.QGroupBox()
      loadCaseGroupBox.title = "Load Volume"
      loadCaseGroupBox.setToolTip("Select the volume to load.")

      loadCaseFormLayout = qt.QFormLayout(loadCaseGroupBox)
      loadCaseFormLayout.setContentsMargins(10,10,10,10)

      self.loadCaseSelector = ctk.ctkPathLineEdit()
      self.loadCaseSelector.filters = ctk.ctkPathLineEdit.Files
      loadCaseFormLayout.addRow("NRRD Volume:", self.loadCaseSelector)
      self.loadCaseSelector.connect('currentPathChanged(const QString)', self.loadSavedCase)
      layout.addWidget(loadCaseGroupBox)


    def loadSavedCase(self):
      if os.path.isfile(self.loadCaseSelector.currentPath) != False and self.loadCaseSelector.currentPath.endswith('.nrrd') != False: 
        slicer.util.loadVolume(self.loadCaseSelector.currentPath)
        self.volume = slicer.mrmlScene.GetNodeByID('vtkMRMLScalarVolumeNode1')
      else:
        raise ValueError("Could not load file from given path")

    #called when entering step
    def onEntry(self, comingFrom, transitionType):
      super(LoginStep, self).onEntry(comingFrom, transitionType)
      # setup the interface
      lm = slicer.app.layoutManager()
      if lm == None: 
        return 
      lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalWidescreenView)      
      
    #check that conditions have been met before proceeding to next step
    def validate( self, desiredBranchId ):
      validationSuceeded = True
      super(LoginStep, self).validate(validationSuceeded, desiredBranchId)

    #called when exiting step         
    def onExit(self, goingTo, transitionType):
      super(LoginStep, self).onExit(goingTo, transitionType)