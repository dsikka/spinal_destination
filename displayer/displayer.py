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
        self.parent.title = "displayer"
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
        self.logic = displayerLogic()
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
        self.logic = displayerLogic()
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
    def __init__(self, parent=None):
        ScriptedLoadableModuleLogic.__init__(self, parent)
        self.transformNodeObserverTags = []
        self.transformOfInterestNode = None
        # Variable for storing the real world transforms as they are streamed
        self.realWorldTransformNode = None
        self.numPoints = 0
        self.counter = 0
        self.xPosList = []
        self.yPosList = []
        self.zPosList = []
        # Create Variables for storing the transforms from aruco marker relative to start point, the node for the fiducial node
        self.ctTransform = None
        self.fiducialNode = None
        self.spInMarker = None
        # Create popup window variables for point display
        self.display_image = None
        self.display_pixmap = None
        self.display_widget = None
        self.width = 640
        self.height = 480

    def addObservers(self):
        transformModifiedEvent = 15000
        transformNode = self.realWorldTransformNode
        while transformNode:
            print
            "Add observer to {0}".format(transformNode.GetName())
            self.transformNodeObserverTags.append(
                [transformNode,
                 transformNode.AddObserver(transformModifiedEvent, self.onTransformOfInterestNodeModified)])
            transformNode = transformNode.GetParentTransformNode()

    def removeObservers(self):
        print
        "Remove observers"
        for nodeTagPair in self.transformNodeObserverTags:
            nodeTagPair[0].RemoveObserver(nodeTagPair[1])

    def outputResults(self):
        # compute medians and show in GUI
        medianX = numpy.median(numpy.array(self.xPosList))
        medianY = numpy.median(numpy.array(self.yPosList))
        medianZ = numpy.median(numpy.array(self.zPosList))
        self.updateResultsGUI(medianX, medianY, medianZ)
        # write data and medians to csv file
        csv = open(self.filestring, "w")
        csv.write("DATA MEDIANS:\n")
        csv.write("Med X,{:f}\n".format(medianX))
        csv.write("Med Y,{:f}\n".format(medianY))
        csv.write("Med Z,{:f}\n".format(medianZ))
        csv.write("\nRAW DATA:\n")
        csv.write("Point Index, X Pos, Y Pos, Z Pos\n")
        for index in range(0, len(self.xPosList)):
            x = self.xPosList[index]
            y = self.yPosList[index]
            z = self.zPosList[index]
            row = "{:d},{:f},{:f},{:f}\n".format(index, x, y, z)
            csv.write(row)
        csv.close()

    def onTransformOfInterestNodeModified(self, observer, eventId):
        if (self.counter == self.numPoints):
            print("end of points")
            self.stop()
            # self.outputResults()
        elif self.spInMarker is not None:
            # Create matrix to store the transform for camera to aruco marker
            matrix = vtk.vtkMatrix4x4()
            transform_real_world_interest = self.realWorldTransformNode.GetMatrixTransformToParent()
            matrix.DeepCopy(transform_real_world_interest)
            # Multiply start point in marker space calculated form the CT model by the
            # camera to aruco transform to get the start point in 3D camera space.
            startPointinCamera = matrix.MultiplyPoint(self.spInMarker)
            # Set calculated 3d start point in camera space
            Xc = startPointinCamera[0]
            Yx = startPointinCamera[1]
            Zc = startPointinCamera[2]

            # Intrinsic camera values
            fx = 5.9596203089288861e+002
            fy = 5.9780697114621512e+002
            cx = 3.1953140232090112e+002
            cy = 2.6188803044119754e+002

            # Perform 3D (Camera) to 2D project
            x = numpy.round((Xc * fx / Zc) + cx)
            y = numpy.round((Yx * fy / Zc) + cy)

            # Get Marker 2D
            Xc2 = transform_real_world_interest.GetElement(0, 3)
            Yc2 = transform_real_world_interest.GetElement(1, 3)
            Zc2 = transform_real_world_interest.GetElement(2, 3)

            # Perform 3D (Camera) to 2D project
            x2 = numpy.round((Xc2 * fx / Zc2) + cx)
            y2 = numpy.round((Yc2 * fy / Zc2) + cy)

            # Update Graphics
            self.fillBlack()
            for i in range(-2, 2):
                for j in range(-2, 2):
                    if i + x > 0 and i + x < self.width and j + y > 0 and i + y < self.height:
                        self.display_image.setPixel(x + i, y + j, 0xFFFFFFFF)
                    if i + x2 > 0 and i + x2 < self.width and j + y2 > 0 and i + y2 < self.height:
                        self.display_image.setPixel(x2 + i, y2 + j, 0xFFFF00FF)

            self.updateWidget()
            # self.updateWidget(int(x), int(y), 0xFFFFFFFF)

            # todo:Apply distortion values
            print('camera point', x, y)
            print('marker', x2, y2)

            # Display point somewhere

            self.counter += 1

    def run(self, transformOfInterest, numPoints, filestring, updateResultsGUI, fiducialOfInterest,
            realWorldTransformNode):
        self.transformNodeObserverTags = []
        self.updateResultsGUI = updateResultsGUI
        self.filestring = filestring
        self.transformOfInterestNode = transformOfInterest
        # Make the transform from camera origin to marker origin in the real world available for use in this class
        self.realWorldTransformNode = realWorldTransformNode
        self.numPoints = numPoints
        self.counter = 0
        self.xPosList = []
        self.yPosList = []
        self.zPosList = []
        # Calculate CT to marker (in CT space) transform
        # Should be saved globally into fiducialNode and ctTransform
        matrix = vtk.vtkMatrix4x4()
        # Transform is from CT origin to aruco marker
        matrix.DeepCopy(self.transformOfInterestNode.GetMatrixTransformToParent())
        # Invert to get marker to CT origin
        matrix.Invert()

        # Store the start point position in CT space in the variable coord
        coord = [0, 0, 0]
        self.fiducialNode = fiducialOfInterest
        fiducialOfInterest.GetNthFiducialPosition(0, coord)
        coord.append(1)

        # Multiply to put start point relative to marker model origin
        self.spInMarker = matrix.MultiplyPoint(coord)

        # Rotate the start point in CT space to match the real world space
        fix_rotation_matrix = [[0, 0, 0, 1], [0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]]
        self.spInMarker = numpy.matmul(fix_rotation_matrix, self.spInMarker)
        # Add the offset to cube face
        self.spInMarker[1] = self.spInMarker[1] + (18 / 2)

        print('spInMarker', self.spInMarker)
        self.ctTransform = [[1, 0, 0, self.spInMarker[0]], [0, 1, 0, self.spInMarker[1]], [0, 0, 1, self.spInMarker[2]],
                            [0, 0, 0, 1]]
        # Setup widget
        self.display_image = qt.QImage(640, 480, QImage.Format_RGB32)
        self.display_image.fill(0x00000000)
        self.display_pixmap = qt.QPixmap.fromImage(self.display_image)
        self.display_widget = qt.QLabel()
        self.display_widget.setPixmap(self.display_pixmap)
        self.display_widget.show()
        self.onTransformOfInterestNodeModified(0, 0)
        # start the updates
        self.addObservers()
        return True

    def stop(self):
        self.removeObservers()

    def stopEndless(self):
        print("end of points")
        self.stop()
        # self.outputResults()

    def updateWidget(self):
        self.display_pixmap = qt.QPixmap.fromImage(self.display_image)
        self.display_widget.setPixmap(self.display_pixmap)

    def fillBlack(self):
        self.display_image.fill(0x00000000)
        self.display_pixmap = qt.QPixmap.fromImage(self.display_image)
        self.display_widget.setPixmap(self.display_pixmap)


class displayerTest(ScriptedLoadableModuleTest):
    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
    """
        self.setUp()
        self.test_TrackingErrorCalculator1()

    def test_TrackingErrorCalculator1(self):
        self.delayDisplay('Test passed!')
