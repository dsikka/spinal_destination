from __main__ import vtk, qt, ctk, slicer

import WorkflowSteps
#
# workflow
#

class workflow:
  def __init__(self, parent):
    #ScriptedLoadableModule.__init__(self, parent)
    parent.title = "workflow" # TODO make this more human readable by adding spaces
    parent.categories = ["Examples"]
    parent.dependencies = []
    parent.contributors = ["Brendan Polley (University of Toronto)",
                           "Stewart McLachlin (Sunnybrook Research Institute)",
                           "Cari Whyne (Sunnybrook Research Institute)"]  # replace with "Firstname Lastname (Organization)"
    parent.helpText = ""
    parent.acknowledgementText = ""
     # replace with organization, grant and thanks.
    self.parent = parent
#
# workflowWidget
#

class workflowWidget:
  def __init__(self, parent=None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout( qt.QVBoxLayout() )
      self.parent.setMRMLScene( slicer.mrmlScene )
    else:
      self.parent = parent
    self.layout = self.parent.layout()

    if not parent:
      self.setup()
      self.parent.show()
      
    if slicer.mrmlScene.GetTagByClassName( "vtkMRMLScriptedModuleNode" ) != 'ScriptedModule':
      slicer.mrmlScene.RegisterNodeClass(vtkMRMLScriptedModuleNode())

  def setup(self):
    workflow = ctk.ctkWorkflow()
    workflowWidget = ctk.ctkWorkflowStackedWidget()
    workflowWidget.setWorkflow(workflow)

    # Set-up steps
    loginStep = WorkflowSteps.LoginStep('Login')
    approachStep = WorkflowSteps.ApproachStep('Approach')
    workflow.addTransition( loginStep, approachStep, None, ctk.ctkWorkflow.Forward)
    #approachStep = WorkflowSteps.ApproachStep()
    #screwStep = WorkflowSteps.ScrewStep()
    #endStep = WorkflowSteps.EndStep()

    #Add Transitions
    #workflow.addTransition(loginStep, approachStep, None, ctk.ctkWorkflow.Forward)
    #workflow.addTransition(approachStep, screwStep, None, ctk.ctkWorkflow.Forward)
    #workflow.addTransition(screwStep, endStep, None, ctk.ctkWorkflow.Forward)

    workflow.setInitialStep(loginStep)
    workflow.start()
    workflowWidget.visible = True
    self.layout.addWidget(workflowWidget)

#
# workflowLogic
#

