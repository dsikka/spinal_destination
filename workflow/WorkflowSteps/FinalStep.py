from __main__ import ctk
from __main__ import qt
from __main__ import slicer
from __main__ import vtk

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
      self.__layout = qt.QFormLayout( self )
      self.__layout.setVerticalSpacing( 5 )

      # Add empty rows
      self.__layout.addRow( "", qt.QWidget() )
      self.__layout.addRow( "", qt.QWidget() )

      self.onReload = qt.QPushButton("Click to reload")
      self.onReload.connect('clicked(bool)', self.reload)
      
      self.QHBox1 = qt.QHBoxLayout()
      self.QHBox1.addWidget(self.onReload)
      self.__layout.addRow(self.QHBox1)

      qt.QTimer.singleShot(0, self.killButton)

    def reload(self):
      slicer.mrmlScene.Clear(0)
      slicer.util.reloadScriptedModule('workflow')

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