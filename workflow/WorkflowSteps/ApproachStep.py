import qt, ctk, slicer

import PythonQt
import string
import vtkITK
import VolumeClipWithModel
import csv
import os
import LoginStep as LoginStepModule

class ApproachStep( ctk.ctkWorkflowWidgetStep ) :

  def __init__( self, stepid ):
    self.initialize( stepid )
    self.setName( 'Step 2. Model Markup' )
    qt.QTimer.singleShot(0, self.killButton)

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
    qt.QTimer.singleShot(0, self.killButton)
    
  def onEntry(self,comingFrom,transitionType):
    super(ApproachStep, self).onEntry(comingFrom, transitionType)

  def validate( self, desiredBranchId ):
    validationSuceeded = True
    super(LoginStep, self).validate(validationSuceeded, desiredBranchId)

  def onExit(self, goingTo, transitionType):
    super(ApproachStep, self).onExit(goingTo, transitionType)