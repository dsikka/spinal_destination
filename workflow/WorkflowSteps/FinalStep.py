from __main__ import qt, ctk, vtk, slicer

from Helper import *

class FinalStep(ctk.ctkWorkflowWidgetStep):
    
    def __init__( self, stepid, parameterNode):
      self.initialize( stepid )
      self.setName( 'End Step' )
      self.setDescription( 'Process Completed' )
      self.__parameterNode  = parameterNode
    
    def killButton(self):
      # hide useless button
      bl = slicer.util.findChildren(text='Final')
      if len(bl):
        bl[0].hide()

    def createUserInterface( self ): 
      qt.QTimer.singleShot(0, self.killButton)
    
    def validate( self, desiredBranchId ):
      validationSuceeded = True
      super(FinalStep, self).validate(validationSuceeded, desiredBranchId)
      
    def onEntry(self, comingFrom, transitionType):
      super(FinalStep, self).onEntry(comingFrom, transitionType)
      qt.QTimer.singleShot(0, self.killButton)
      
    def onExit(self, goingTo, transitionType):
      super(FinalStep, self).onExit(goingTo, transitionType)
      
    def doStepProcessing(self):
        print('Done')