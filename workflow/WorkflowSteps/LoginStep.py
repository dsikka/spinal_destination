import DICOM
import os
import qt, ctk, vtk, slicer

class LoginStep(ctk.ctkWorkflowWidgetStep):

    def __init__( self, stepid, parameterNode):
      self.initialize( stepid )
      self.setName( 'Step 1. Load Volume' )
      self.setDescription('Select the path of the spine CT volume')
      self.loadCaseSelector = None
      self.__parameterNode  = parameterNode
      qt.QTimer.singleShot(0, self.killButton)

    def killButton(self):
      # hide useless button
      bl = slicer.util.findChildren(text='Final')
      if len(bl):
        bl[0].hide()

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

      activeVolumeGroupBox = qt.QGroupBox()
      activeVolumeGroupBox.title = "Active Volume Data"
      layout.addWidget(activeVolumeGroupBox)
      activeVolumeFormLayout = qt.QFormLayout(activeVolumeGroupBox)
      activeVolumeFormLayout.setContentsMargins(10,10,10,10)

      self.__inputSelector = slicer.qMRMLNodeComboBox()
      self.__inputSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      self.__inputSelector.addEnabled = False
      self.__inputSelector.removeEnabled = False
      self.__inputSelector.setMRMLScene( slicer.mrmlScene )
      activeVolumeFormLayout.addRow(self.__inputSelector )
      qt.QTimer.singleShot(0, self.killButton)

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
      qt.QTimer.singleShot(0, self.killButton)    
      
    #check that conditions have been met before proceeding to next step
    def validate( self, desiredBranchId ):
      validationSuceeded = True
      super(LoginStep, self).validate(validationSuceeded, desiredBranchId)

    #called when exiting step         
    def onExit(self, goingTo, transitionType):
      baseline = self.__inputSelector.currentNode()
      if baseline != None:
        baselineID = baseline.GetID()
        if baselineID != '':
          self.__parameterNode.SetParameter('baselineVolumeID', baselineID)
      super(LoginStep, self).onExit(goingTo, transitionType)