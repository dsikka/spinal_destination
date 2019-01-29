import os
import unittest
import vtk, qt, ctk, slicer
from qt import *
from slicer.ScriptedLoadableModule import *
import datetime, time, json
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
        self.parent.contributors = ["STDS Team"]
        self.parent.helpText = ""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = ""
        self.logic = None
        self._save_file_path = ''
        self._save_file_created = False


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

        # Define combo box selector member variables:
        self.transform2OfInterestSelector = slicer.qMRMLNodeComboBox()
        self.transform2OfInterestSelectorLabel = qt.QLabel()
        self.fiducialOfInterestSelector = slicer.qMRMLNodeComboBox()
        self.fiducialOfInterestSelectorLabel = qt.QLabel()
        self.transformOfInterestSelector = slicer.qMRMLNodeComboBox()
        self.transformOfInterestSelectorLabel = qt.QLabel()
        self.second_marker_selector = slicer.qMRMLNodeComboBox()
        self.second_marker_selector_label = qt.QLabel()

        # Save To Directory Selector
        self._write_to_dir = ctk.ctkPathLineEdit()
        self._write_to_dir.filters = ctk.ctkPathLineEdit.Dirs
        self._write_to_dir.settingKey = "dir"
        parametersFormLayout.addRow("CSV File Write Directory:", self._write_to_dir)

        # Transform of interest selector in the CT.
        # This transform should be the transform linked to the marker model in the CT
        # image space.
        text = "CT Transform of Interest: "
        node_types = ["vtkMRMLTransformNode"]
        tool_tip_text = "Pick CT transform of interest"
        self.create_selector(self.transformOfInterestSelectorLabel,
                             self.transformOfInterestSelector,
                             text,
                             node_types,
                             tool_tip_text)
        parametersFormLayout.addRow(self.transformOfInterestSelectorLabel, self.transformOfInterestSelector)

        # Fiducial of interest selector.
        # We need to select the Fiducial marker placed on the start point location in
        # Slicer by the surgery planner.
        self.create_selector(self.fiducialOfInterestSelectorLabel,
                             self.fiducialOfInterestSelector,
                             "fiducial of Interest: ",
                             ["vtkMRMLMarkupsFiducialNode"],
                             "Pick fiducial of interest")
        parametersFormLayout.addRow(self.fiducialOfInterestSelectorLabel, self.fiducialOfInterestSelector)

        # Real World Transform of interest.
        # This Transform should be a dummy transform not connected to a model in Slicer.
        # The Transform will receive streaming transform data relating to the aruco
        # fiducial seen in the camera 3D space.
        self.create_selector(self.transform2OfInterestSelectorLabel,
                             self.transform2OfInterestSelector,
                             "Transform of Interest for Real World: ",
                             ["vtkMRMLTransformNode"],
                             "Pick transform of interest for Real World")
        parametersFormLayout.addRow(self.transform2OfInterestSelectorLabel, self.transform2OfInterestSelector)

        # Real World Transform of interest 2.
        # This Transform should be a dummy transform not connected to a model in Slicer.
        # The Transform will receive streaming transform data relating to the aruco
        # fiducial seen in the camera 3D space. To be used for testing multi marker tracking.
        self.create_selector(self.second_marker_selector_label,
                             self.second_marker_selector,
                             "Transform of Interest 2: ",
                             ["vtkMRMLTransformNode"],
                             "Testing Multi Marker Tracking")
        parametersFormLayout.addRow(self.second_marker_selector_label,
                                    self.second_marker_selector)
        # start endless button
        self.startEndlessButton = qt.QPushButton("Start")
        self.startEndlessButton.toolTip = "Start"
        self.startEndlessButton.enabled = True
        self.layout.addWidget(self.startEndlessButton)

        # stop endless button
        self.stopEndlessButton = qt.QPushButton("Stop")
        self.stopEndlessButton.toolTip = "Stop"
        self.stopEndlessButton.enabled = True
        self.layout.addWidget(self.stopEndlessButton)

        # connections
        self.startEndlessButton.connect('clicked(bool)', self.onStartEndless)
        self.stopEndlessButton.connect('clicked(bool)', self.onStopEndless)

        # Add vertical spacer
        self.layout.addStretch(1)

    def create_selector(self, label, selector, text, node_types, tool_tip_text):
        label.setText(text)
        selector.nodeTypes = node_types
        selector.noneEnabled = False
        selector.addEnabled = False
        selector.removeEnabled = True
        selector.setMRMLScene(slicer.mrmlScene)
        selector.setToolTip(tool_tip_text)

    def cleanup(self):
        pass

    def onStartEndless(self):
        if os.path.isdir(self._write_to_dir.currentPath):
            self.logic = displayerLogic()
            transformOfInterest = self.transformOfInterestSelector.currentNode()
            # Get currently selected fiducial
            fiducialOfInterest = self.fiducialOfInterestSelector.currentNode()
            # Get Real World to Marker Transform Node
            realWorldTransformNode = self.transform2OfInterestSelector.currentNode()
            realWorldTransformNode2 = self.second_marker_selector.currentNode()
            # Passing in fiducial of interest
            self.logic.run(transformOfInterest, fiducialOfInterest, realWorldTransformNode, realWorldTransformNode2,
                           self._write_to_dir.currentPath)
        else:
            print('Select Save Directory!')

    def onStopEndless(self):
        self.logic.stopEndless()


#
# TrackingErrorCalculatorLogic
#

def get_3d_coordinates(transform_real_world_interest):
    Xc2 = transform_real_world_interest.GetElement(0, 3)
    Yc2 = transform_real_world_interest.GetElement(1, 3)
    Zc2 = transform_real_world_interest.GetElement(2, 3)
    return Xc2, Yc2, Zc2


class displayerLogic(ScriptedLoadableModuleLogic):
    def __init__(self, parent=None):
        ScriptedLoadableModuleLogic.__init__(self, parent)
        self.cy = 2.6188803044119754e+002
        self.fy = 5.9780697114621512e+002
        self.cx = 3.1953140232090112e+002
        self.fx = 5.9596203089288861e+002
        self.transformNodeObserverTags = []
        self.transformOfInterestNode = None
        # Variable for storing the real world transforms as they are streamed
        self.realWorldTransformNode = None
        self.realWorldTransformNode2 = None
        # Create Variables for storing the transforms from aruco marker relative to start point, the node for the
        # fiducial node
        self.ctTransform = None
        self.fiducialNode = None
        self.spInMarker = None
        # Create popup window variables for point display
        self.display_image = None
        self.display_pixmap = None
        self.display_widget = None
        self.width = 640
        self.height = 480

        self.displayMarkerSphere = None
        self.startPointSphere = None
        self.marker2Sphere = None

        # For saving data:
        self._save_file_dir = ''
        self._marker_1_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._marker_2_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._start_point_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._transform_dictionary = {''}

    def addObservers(self):
        transformModifiedEvent = 15000
        nodes = [self.realWorldTransformNode, self.realWorldTransformNode2]
        funcs = [self.onTransformOfInterestNodeModified, self.on_transform_2_modified]
        for _, (node, func) in enumerate(zip(nodes, funcs)):
            transformNode = node
            while transformNode:
                print
                "Add observer to {0}".format(transformNode.GetName())
                self.transformNodeObserverTags.append(
                    [transformNode,
                     transformNode.AddObserver(transformModifiedEvent, func)])
                transformNode = transformNode.GetParentTransformNode()

    def removeObservers(self):
        print("Remove observers")
        for nodeTagPair in self.transformNodeObserverTags:
            nodeTagPair[0].RemoveObserver(nodeTagPair[1])

    def onTransformOfInterestNodeModified(self, observer, eventId):
        if self.spInMarker is not None:
            # Create matrix to store the transform for camera to aruco marker
            matrix, transform_real_world_interest = self.create_4x4_vtk_mat_from_node(self.realWorldTransformNode)
            # Multiply start point in marker space calculated form the CT model by the
            # camera to aruco transform to get the start point in 3D camera space.
            startPointinCamera = matrix.MultiplyPoint(self.spInMarker)
            # Set calculated 3d start point in camera space
            Xc = startPointinCamera[0]
            Yc = startPointinCamera[1]
            Zc = startPointinCamera[2]

            # Perform 3D (Camera) to 2D project sp
            x, y = self.transform_3d_to_2d(Xc, Yc, Zc)

            # Get Marker 3D
            Xc2, Yc2, Zc2 = get_3d_coordinates(transform_real_world_interest)

            # Perform 3D (Camera) to 2D project
            x2, y2 = self.transform_3d_to_2d(Xc2, Yc2, Zc2)

            # Save to Collection
            t = time.time()
            self._marker_1_collection['time'].append(t)
            self._marker_1_collection['3D pos'].append([Xc2, Yc2, Zc2])
            self._marker_1_collection['2D pos'].append([x2, y2])

            self._start_point_collection['time'].append(t)
            self._start_point_collection['3D pos'].append([Xc, Yc, Zc])
            self._start_point_collection['2D pos'].append([x, y])

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
            # Setup SP matrix
            vtk_sp_matrix = self.create_4x4_vtk_mat(x, y)

            # Setup Marker Matrix
            vtk_marker_matrix = self.create_4x4_vtk_mat(x2, y2)

            # Update Nodes
            self.startPointSphere.SetMatrixTransformToParent(vtk_sp_matrix)
            self.displayMarkerSphere.SetMatrixTransformToParent(vtk_marker_matrix)

    def transform_3d_to_2d(self, Xc, Yx, Zc):
        x = numpy.round((Xc * self.fx / Zc) + self.cx)
        y = numpy.round((Yx * self.fy / Zc) + self.cy)
        return x, y

    def on_transform_2_modified(self, observer, eventid):
        """This method is the observer method for changes in the second transform position"""

        matrix_2, transform_2 = self.create_4x4_vtk_mat_from_node(self.realWorldTransformNode2)

        x, y, z = get_3d_coordinates(transform_2)

        x_camera, y_camera = self.transform_3d_to_2d(x, y, z)

        # Save to collection
        self._marker_2_collection['time'].append(time.time())
        self._marker_2_collection['3D pos'].append([x, y, z])
        self._marker_2_collection['2D pos'].append([x_camera, y_camera])

        # Setup Marker 2 Matrix
        vtk_marker_matrix_2 = self.create_4x4_vtk_mat(x_camera, y_camera)

        self.marker2Sphere.SetMatrixTransformToParent(vtk_marker_matrix_2)

    @staticmethod
    def create_4x4_vtk_mat_from_node(node):
        matrix = vtk.vtkMatrix4x4()
        transform_real_world_interest = node.GetMatrixTransformToParent()
        matrix.DeepCopy(transform_real_world_interest)
        return matrix, transform_real_world_interest

    def create_4x4_vtk_mat(self, x, y):
        sp_matrix = [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, 0, 0, 0, 0, 1]
        vtk_sp_matrix = vtk.vtkMatrix4x4()
        vtk_sp_matrix.DeepCopy(sp_matrix)
        return vtk_sp_matrix

    def run(self, transformOfInterest, fiducialOfInterest, realWorldTransformNode, realWorldTransferNode2,
            directory_path):
        # Get Spheres for display
        self.displayMarkerSphere = slicer.util.getNode('Marker_Sphere')
        self.startPointSphere = slicer.util.getNode('Sphere_Transform')
        self.marker2Sphere = slicer.util.getNode('Marker_2')

        self.transformNodeObserverTags = []
        self.transformOfInterestNode = transformOfInterest

        # Make the transform from camera origin to marker origin in the real world available for use in this class
        self.realWorldTransformNode = realWorldTransformNode
        self.realWorldTransformNode2 = realWorldTransferNode2
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
        self.on_transform_2_modified(0, 0)
        # start the updates
        self.addObservers()

        # For saving data:
        self._save_file_dir = directory_path.replace('/', '\\')

        return True

    def stop(self):
        self.removeObservers()

    def stopEndless(self):
        print("end of points")
        self.stop()
        self._output_to_file()

    def updateWidget(self):
        self.display_pixmap = qt.QPixmap.fromImage(self.display_image)
        self.display_widget.setPixmap(self.display_pixmap)

    def fillBlack(self):
        self.display_image.fill(0x00000000)
        self.display_pixmap = qt.QPixmap.fromImage(self.display_image)
        self.display_widget.setPixmap(self.display_pixmap)

    def _output_to_file(self):
        if os.path.isdir(self._save_file_dir):
            data = {'Marker 1': self._marker_1_collection,
                    'Marker 2': self._marker_2_collection,
                    'Start Point': self._start_point_collection}
            d_time = datetime.datetime.now()
            if not os.path.isdir(os.path.join(self._save_file_dir, d_time.strftime("%Y-%m-%d"))):
                os.mkdir(os.path.join(self._save_file_dir, d_time.strftime("%Y-%m-%d")))
            filepath = os.path.join(self._save_file_dir, d_time.strftime("%Y-%m-%d"),
                                    d_time.strftime("%H-%M-%S") + '.json')
            with open(filepath, 'w') as outfile:
                json.dump(data, outfile)


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
