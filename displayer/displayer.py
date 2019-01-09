import os
import unittest
import vtk, qt, ctk, slicer
from qt import *
from slicer.ScriptedLoadableModule import *
import logging
import numpy
import csv


#
# displayer
#

class displayer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "TrackingErrorCalculator"
        self.parent.categories = ["IGT"]
        self.parent.dependencies = []
        self.parent.contributors = ["Mark Asselin (PerkLab, Queen's University)"]
        self.parent.helpText = ""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = ""
        self.logic = None


#
# TrackingErrorCalculatorWidget
#

class displayerWidget(ScriptedLoadableModuleWidget):
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # parameters area
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    # Transform of interest selector in the CT.
    # This transform should be the transform linked to the marker model in the CT
    # image space.
    self.transformOfInterestSelectorLabel = qt.QLabel()
    self.transformOfInterestSelectorLabel.setText("CT Transform of Interest: ")
    self.transformOfInterestSelector = slicer.qMRMLNodeComboBox()
    self.transformOfInterestSelector.nodeTypes = (["vtkMRMLTransformNode"])
    self.transformOfInterestSelector.noneEnabled = False
    self.transformOfInterestSelector.addEnabled = False
    self.transformOfInterestSelector.removeEnabled = True
    self.transformOfInterestSelector.setMRMLScene(slicer.mrmlScene)
    self.transformOfInterestSelector.setToolTip("Pick CT transform of interest")
    parametersFormLayout.addRow(self.transformOfInterestSelectorLabel, self.transformOfInterestSelector)

    # Fiducial of interest selector.
    # We need to select the Fiducial marker placed on the start point location in
    # Slicer by the surgery planner.
    self.fiducialOfInterestSelectorLabel = qt.QLabel()
    self.fiducialOfInterestSelectorLabel.setText("fiducial of Interest: ")
    self.fiducialOfInterestSelector = slicer.qMRMLNodeComboBox()
    self.fiducialOfInterestSelector.nodeTypes = (["vtkMRMLMarkupsFiducialNode"])
    self.fiducialOfInterestSelector.noneEnabled = False
    self.fiducialOfInterestSelector.addEnabled = False
    self.fiducialOfInterestSelector.removeEnabled = True
    self.fiducialOfInterestSelector.setMRMLScene(slicer.mrmlScene)
    self.fiducialOfInterestSelector.setToolTip("Pick fiducial of interest")
    parametersFormLayout.addRow(self.fiducialOfInterestSelectorLabel, self.fiducialOfInterestSelector)

    # Real World Transform of interest.
    # This Transform should be a dummy transform not connected to a model in Slicer.
    # The Transform will receive streaming transform data relating to the aruco
    # fiducial seen in the camera 3D space.
    self.transform2OfInterestSelectorLabel = qt.QLabel()
    self.transform2OfInterestSelectorLabel.setText("Transform of Interest for Real World: ")
    self.transform2OfInterestSelector = slicer.qMRMLNodeComboBox()
    self.transform2OfInterestSelector.nodeTypes = (["vtkMRMLTransformNode"])
    self.transform2OfInterestSelector.noneEnabled = False
    self.transform2OfInterestSelector.addEnabled = False
    self.transform2OfInterestSelector.removeEnabled = True
    self.transform2OfInterestSelector.setMRMLScene(slicer.mrmlScene)
    self.transform2OfInterestSelector.setToolTip("Pick transform of interest for Real World")
    parametersFormLayout.addRow(self.transform2OfInterestSelectorLabel, self.transform2OfInterestSelector)

    # num points selector
    self.numPointsSliderWidget = ctk.ctkSliderWidget()
    self.numPointsSliderWidget.singleStep = 1
    self.numPointsSliderWidget.minimum = 10
    self.numPointsSliderWidget.maximum = 5000
    self.numPointsSliderWidget.value = 5
    self.numPointsSliderWidget.setToolTip("Set the number of points to monitor the transform for.")
    parametersFormLayout.addRow("Num Points:", self.numPointsSliderWidget)

    # results form
    resultsCollapsibleButton = ctk.ctkCollapsibleButton()
    resultsCollapsibleButton.text = "Median 3DOF positions of most recent trial"
    self.layout.addWidget(resultsCollapsibleButton)
    resultsFormLayout = qt.QFormLayout(resultsCollapsibleButton)

    self.medianPosXLabel = qt.QLabel("Pos x (mm): ")
    self.medianPosXValueLabel = qt.QLabel()

    self.medianPosYLabel = qt.QLabel("Pos y (mm): ")
    self.medianPosYValueLabel = qt.QLabel()

    self.medianPosZLabel = qt.QLabel("Pos z (mm): ")
    self.medianPosZValueLabel = qt.QLabel()

    resultsFormLayout.addRow(self.medianPosXLabel, self.medianPosXValueLabel)
    resultsFormLayout.addRow(self.medianPosYLabel, self.medianPosYValueLabel)
    resultsFormLayout.addRow(self.medianPosZLabel, self.medianPosZValueLabel)

    # write data and results form
    writeDataCollapsibleButton = ctk.ctkCollapsibleButton()
    writeDataCollapsibleButton.text = "Write data from most recent trial to csv"
    self.layout.addWidget(writeDataCollapsibleButton)
    writeDataFormLayout = qt.QFormLayout(writeDataCollapsibleButton)

    # field of view and positions text boxes
    self.fileDirLabel = "Output Dir:"
    self.fileDirTextBox = qt.QLineEdit()
    self.baseFilenameLabel = "Filename:"
    self.baseFilenameTextBox = qt.QLineEdit()
    self.metadataLabel = "Metadata:"
    self.metadataTextBox = qt.QLineEdit()

    writeDataFormLayout.addRow(self.fileDirLabel, self.fileDirTextBox)
    writeDataFormLayout.addRow(self.baseFilenameLabel, self.baseFilenameTextBox)
    writeDataFormLayout.addRow(self.metadataLabel, self.metadataTextBox)

    # start button
    self.startButton = qt.QPushButton("Start Sample Collection")
    self.startButton.toolTip = "Collect a sample."
    self.startButton.enabled = True
    self.layout.addWidget(self.startButton)

    # stop button
    self.stopButton = qt.QPushButton("Stop Sample Collection")
    self.stopButton.toolTip = "Collect a sample."
    self.stopButton.enabled = True
    self.layout.addWidget(self.stopButton)

    # start endless button
    self.startEndlessButton = qt.QPushButton("Start Endless Sample Collection")
    self.startEndlessButton.toolTip = "Collect samples until stop button is pressed (or 20,000 samples is reached)."
    self.startEndlessButton.enabled = True
    self.layout.addWidget(self.startEndlessButton)

    # stop endless button
    self.stopEndlessButton = qt.QPushButton("Stop Endless Sample Collection")
    self.stopEndlessButton.toolTip = "Stop collecting endless samples."
    self.stopEndlessButton.enabled = True
    self.layout.addWidget(self.stopEndlessButton)

    # connections
    self.startButton.connect('clicked(bool)', self.onStart)
    self.stopButton.connect('clicked(bool)', self.onStop)
    self.startEndlessButton.connect('clicked(bool)', self.onStartEndless)
    self.stopEndlessButton.connect('clicked(bool)', self.onStopEndless)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def updateResultsGUI(self, medianX, medianY, medianZ):
    self.medianPosXValueLabel.setText("{0:.3f}".format(medianX))
    self.medianPosYValueLabel.setText("{0:.3f}".format(medianY))
    self.medianPosZValueLabel.setText("{0:.3f}".format(medianZ))

  def onStart(self):
    self.logic = TrackingErrorCalculatorLogic()
    transformOfInterest = self.transformOfInterestSelector.currentNode()
    # Get currently selected fiducial
    fiducialOfInterest = self.fiducialOfInterestSelector.currentNode()
    # Get Real World to Marker Transform Node
    realWorldTransformNode = self.transform2OfInterestSelector.currentNode()
    numPoints = self.numPointsSliderWidget.value
    dirPath = str(self.fileDirTextBox.text)
    baseFilename = str(self.baseFilenameTextBox.text)
    metadata = str(self.metadataTextBox.text)
    filestring = dirPath + baseFilename + "_" + metadata + ".csv"
    # Passing in fiducial of interest
    self.logic.run(transformOfInterest, numPoints, filestring, self.updateResultsGUI, fiducialOfInterest,
                   realWorldTransformNode)

  def onStop(self):
    self.logic.stop()

  def onStartEndless(self):
    self.logic = TrackingErrorCalculatorLogic()
    transformOfInterest = self.transformOfInterestSelector.currentNode()
    # Get currently selected fiducial
    fiducialOfInterest = self.fiducialOfInterestSelector.currentNode()
    # Get Real World to Marker Transform Node
    realWorldTransformNode = self.transform2OfInterestSelector.currentNode()
    numPoints = 200000
    dirPath = str(self.fileDirTextBox.text)
    baseFilename = str(self.baseFilenameTextBox.text)
    metadata = str(self.metadataTextBox.text)
    filestring = dirPath + baseFilename + "_" + metadata + ".csv"
    # Passing in fiducial of interest
    self.logic.run(transformOfInterest, numPoints, filestring, self.updateResultsGUI, fiducialOfInterest,
                   realWorldTransformNode)

  def onStopEndless(self):
    self.logic.stopEndless()


#
# TrackingErrorCalculatorLogic
#

class displayerLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def hasImageData(self, volumeNode):
        """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
        if not volumeNode:
            logging.debug('hasImageData failed: no volume node')
            return False
        if volumeNode.GetImageData() is None:
            logging.debug('hasImageData failed: no image data in volume node')
            return False
        return True

    def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
        """Validates if the output is not the same as input
    """
        if not inputVolumeNode:
            logging.debug('isValidInputOutputData failed: no input volume node defined')
            return False
        if not outputVolumeNode:
            logging.debug('isValidInputOutputData failed: no output volume node defined')
            return False
        if inputVolumeNode.GetID() == outputVolumeNode.GetID():
            logging.debug(
                'isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
            return False
        return True

    def takeScreenshot(self, name, description, type=-1):
        # show the message even if not taking a screen shot
        slicer.util.delayDisplay(
            'Take screenshot: ' + description + '.\nResult is available in the Annotations module.', 3000)

        lm = slicer.app.layoutManager()
        # switch on the type to get the requested window
        widget = 0
        if type == slicer.qMRMLScreenShotDialog.FullLayout:
            # full layout
            widget = lm.viewport()
        elif type == slicer.qMRMLScreenShotDialog.ThreeD:
            # just the 3D window
            widget = lm.threeDWidget(0).threeDView()
        elif type == slicer.qMRMLScreenShotDialog.Red:
            # red slice window
            widget = lm.sliceWidget("Red")
        elif type == slicer.qMRMLScreenShotDialog.Yellow:
            # yellow slice window
            widget = lm.sliceWidget("Yellow")
        elif type == slicer.qMRMLScreenShotDialog.Green:
            # green slice window
            widget = lm.sliceWidget("Green")
        else:
            # default to using the full window
            widget = slicer.util.mainWindow()
            # reset the type so that the node is set correctly
            type = slicer.qMRMLScreenShotDialog.FullLayout

        # grab and convert to vtk image data
        qimage = ctk.ctkWidgetsUtils.grabWidget(widget)
        imageData = vtk.vtkImageData()
        slicer.qMRMLUtils().qImageToVtkImageData(qimage, imageData)

        annotationLogic = slicer.modules.annotations.logic()
        annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

    def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
        """
    Run the actual algorithm
    """

        if not self.isValidInputOutputData(inputVolume, outputVolume):
            slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
            return False

        logging.info('Processing started')

        # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
        cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(),
                     'ThresholdValue': imageThreshold, 'ThresholdType': 'Above'}
        cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

        # Capture screenshot
        if enableScreenshots:
            self.takeScreenshot('displayerTest-Start', 'MyScreenshot', -1)

        logging.info('Processing completed')

        return True


class displayerTest(ScriptedLoadableModuleTest):
    """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
    """
        self.setUp()
        self.test_displayer1()

    def test_displayer1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

        self.delayDisplay("Starting the test")
        #
        # first, get some data
        #
        import urllib
        downloads = (
            ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

        for url, name, loader in downloads:
            filePath = slicer.app.temporaryPath + '/' + name
            if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
                logging.info('Requesting download %s from %s...\n' % (name, url))
                urllib.urlretrieve(url, filePath)
            if loader:
                logging.info('Loading %s...' % (name,))
                loader(filePath)
        self.delayDisplay('Finished with download and loading')

        volumeNode = slicer.util.getNode(pattern="FA")
        logic = displayerLogic()
        self.assertIsNotNone(logic.hasImageData(volumeNode))
        self.delayDisplay('Test passed!')
