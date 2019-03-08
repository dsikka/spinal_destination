import vtk, qt, ctk, slicer

import WorkflowSteps

from slicer.ScriptedLoadableModule import *


class workflow (ScriptedLoadableModule):
  def __init__(self, parent):
    parent.title = "workflow"
    parent.categories = ["workflow"]
    parent.dependencies = []
    parent.contributors = ["Brendan Polley (University of Toronto)",
                           "Stewart McLachlin (Sunnybrook Research Institute)",
                           "Cari Whyne (Sunnybrook Research Institute)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = "Help Text Example"
   
    parent.acknowledgementText = 'This is text'
     # replace with organization, grant and thanks.
    self.parent = parent

#
# qSpineGeneratorWidget
#

class workflowWidget (ScriptedLoadableModule):
  def __init__( self, parent=None ):
    print "running something"  
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene( slicer.mrmlScene )
    else:
      self.parent = parent
    self.layout = self.parent.layout()

    if not parent:
      self.setup()
      self.parent.show()
      
    if slicer.mrmlScene.GetTagByClassName( "vtkMRMLScriptedModuleNode" ) != 'ScriptedModule':
      slicer.mrmlScene.RegisterNodeClass(vtkMRMLScriptedModuleNode())

  def setup( self ):
    self.workflow = ctk.ctkWorkflow()
    workflowWidget = ctk.ctkWorkflowStackedWidget()
    workflowWidget.setWorkflow( self.workflow )
  
    nNodes = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScriptedModuleNode')
    self.parameterNode = None
    for n in xrange(nNodes):
      compNode = slicer.mrmlScene.GetNthNodeByClass(n, 'vtkMRMLScriptedModuleNode')
      nodeid = None
      if compNode.GetModuleName() == 'workflow':
        self.parameterNode = compNode
        print 'Found existing workflow parameter node'
        break
    if self.parameterNode == None:
      self.parameterNode = slicer.vtkMRMLScriptedModuleNode()
      self.parameterNode.SetModuleName('workflow')
      slicer.mrmlScene.AddNode(self.parameterNode)

    loginStep = WorkflowSteps.LoginStep('Login', self.parameterNode)
    approachStep = WorkflowSteps.ApproachStep('Approach', self.parameterNode)
    screwStep = WorkflowSteps.ScrewStep('Screw', self.parameterNode)
    doneStep = WorkflowSteps.FinalStep('Final', self.parameterNode)
    
    self.workflow.addTransition(loginStep, approachStep, None, ctk.ctkWorkflow.Forward)
    self.workflow.addTransition(approachStep, screwStep, None, ctk.ctkWorkflow.Forward)
    self.workflow.addTransition(screwStep, doneStep, None, ctk.ctkWorkflow.Forward)

    self.workflow.setInitialStep(loginStep)
    self.workflow.start()
    workflowWidget.visible = True
    self.layout.addWidget( workflowWidget )

  def cleanup(self):
    pass