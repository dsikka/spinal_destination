import csv
import datetime, time, json
import logging
import numpy
import os
import unittest
import vtk, qt, ctk, slicer

from qt import *
from slicer.ScriptedLoadableModule import *


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
        self.fiducialOfInterestSelector = slicer.qMRMLNodeComboBox()
        self.fiducialOfInterestSelectorLabel = qt.QLabel()
        self.transformOfInterestSelector = slicer.qMRMLNodeComboBox()
        self.transformOfInterestSelectorLabel = qt.QLabel()

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
                             "Start Point Model: ",
                             ["vtkMRMLTransformNode"],
                             "Pick Start Point")
        parametersFormLayout.addRow(self.fiducialOfInterestSelectorLabel, self.fiducialOfInterestSelector)
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

        # Create Models for Display
        names = ['center_sph', 'intermediate_sph', 'outer_sph']
        self.concentric_cylinders = []
        self.cylinder_model_nodes = []
        self.t_form_nodes = []

        for i in range(0, 3):
            if slicer.mrmlScene.GetFirstNodeByName(names[i]) is None:
                model_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
                model_node.SetName(names[i])
            else:
                model_node = slicer.mrmlScene.GetFirstNodeByName(names[i])

            cyl = vtk.vtkSphereSource()
            cyl.SetRadius(10.0 * (i + 1))
            #cyl.SetHeight(60.0)
            cyl.Update()

            model_node.SetAndObservePolyData(cyl.GetOutput())
            model_node.CreateDefaultDisplayNodes()
            model_node.GetDisplayNode().SetSliceIntersectionVisibility(True)
            model_node.GetDisplayNode().SetSliceDisplayMode(0)
            model_node.GetDisplayNode().SetColor(i / 3.0, i / 6.0, i / 9.0)
            self.concentric_cylinders.append(cyl)
            self.cylinder_model_nodes.append(model_node)
            if slicer.mrmlScene.GetFirstNodeByName(names[i] + 't_form') is None:
                t_form_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode')
                t_form_node.SetName(names[i] + 't_form')
            else:
                t_form_node = slicer.mrmlScene.GetFirstNodeByName(names[i] + 't_form')
            model_node.SetAndObserveTransformNodeID(t_form_node.GetID())
            self.t_form_nodes.append(t_form_node)

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
        print('start')
        if os.path.isdir(self._write_to_dir.currentPath):
            self.logic = displayerLogic()
            transformOfInterest = self.transformOfInterestSelector.currentNode()
            # Get currently selected fiducial
            fiducialOfInterest = self.fiducialOfInterestSelector.currentNode()
            # Passing in fiducial of interest
            self.logic.run(transformOfInterest, fiducialOfInterest, self._write_to_dir.currentPath, self.t_form_nodes)
        else:
            print('Select Save Directory!')

    def onStopEndless(self):
        print('stop')
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
        self.cy = 2.3184788479005914e+002
        self.fy = 6.4324331025844515e+002
        self.cx = 3.1163816392087517e+002
        self.fx = 6.4367706296746178e+002

        self.transformNodeObserverTags = []
        self.transformOfInterestNode = None
        # Variable for storing the real world transforms as they are streamed
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

        self.display_marker_cylinders = None
        self.display_marker_cylinders_transform_nodes = []

        # For saving data:
        self._save_file_dir = ''
        self._marker_1_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._marker_2_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._start_point_collection = {'time': [], '3D pos': [], '2D pos': []}
        self._transform_dictionary = {''}

        self.realWorldTransformNode_m0 = None
        self.realWorldTransformNode_m1 = None
        self.realWorldTransformNode_m2 = None
        self.realWorldTransformNode_m3 = None
        self.realWorldTransformNode_m4 = None

        # Should be updated on entry once the aruco cube has been loaded
        self.offsets = None
        self.cube_length = 0

        self.transforms = {'Marker0ToTracker': {'node': self.realWorldTransformNode_m0, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker1ToTracker': {'node': self.realWorldTransformNode_m1, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker2ToTracker': {'node': self.realWorldTransformNode_m2, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker3ToTracker': {'node': self.realWorldTransformNode_m3, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)},
        'Marker4ToTracker': {'node': self.realWorldTransformNode_m4, 'coords': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)}}

    def euc_distance(parent_matrix, matrix):
        x, y, z = parent_matrix.GetElement(0, 3), parent_matrix.GetElement(1, 3), parent_matrix.GetElement(2, 3)
        x2, y2, z2 = matrix.GetElement(0, 3), matrix.GetElement(1, 3), matrix.GetElement(2, 3)
        #print(x, y, z, x2, y2, z2)
        return np.sqrt((x - x2) ** 2 + (y - y2) ** 2 + (z - z2) ** 2)

    def updateOffsets(self):
        # Dimensions are in mm
        bounds = [0,0,0,0,0,0]
        cube = slicer.util.getNode('ArucoCube')
        cube.GetRASBounds(bounds)
        self.cube_length = np.absolute(bounds[1] - bounds[0])

        self.offsets = {'Marker0ToTracker': {'matrix': None, 'transform': None, 'offset': (1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, self.cube_length/2, 0, 0, 0, 1)},
        'Marker1ToTracker': {'matrix': None, 'transform': None, 'offset': (-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, self.cube_length/2, 0, 0, 0, 1)},
        'Marker2ToTracker': {'matrix': None, 'transform': None, 'offset': (0, 0, 1, 0, 0, -1, 0, 0, 1, 0, 0, self.cube_length/2, 0, 0, 0, 1)},
        'Marker3ToTracker': {'matrix': None, 'transform': None, 'offset': (1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, self.cube_length/2, 0, 0, 0, 1)},
        'Marker4ToTracker': {'matrix': None, 'transform': None, 'offset': (0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, self.cube_length/2, 0, 0, 0, 1)}}

    def addObservers(self):
        transformModifiedEvent = 15000
        for (k,v) in self.transforms.items():
            transform_node = v['node']
            while transform_node:
                print "Add observer to {0}".format(transform_node.GetName())
                self.transformNodeObserverTags.append([transform_node, transform_node.AddObserver(transformModifiedEvent, self.onTransformOfInterestNodeModified)])
                transform_node = transform_node.GetParentTransformNode()

    def removeObservers(self):
        print("Remove observers")
        for nodeTagPair in self.transformNodeObserverTags:
            nodeTagPair[0].RemoveObserver(nodeTagPair[1])

    def onTransformOfInterestNodeModified(self, observer, eventId):
        # Calculate the expected distance between two cude faces
        validNodes = []
        expected = self.cube_length * np.sqrt(2) / 2
        name = observer.GetName()
        parent_matrix, parent_transform = self.create_4x4_vtk_mat_from_node(self.transforms[name]['node'])
        self.offsets[name]['matrix'] = parent_matrix
        self.offsets[name]['transform'] = parent_transform
        validNodes = [name]
        for (k,v) in self.transforms.items():
            matrix, transform_real_world_interest = self.create_4x4_vtk_mat_from_node(v['node'])
            
            # Better check?
            x, y, z = matrix.GetElement(0, 3), matrix.GetElement(1, 3), matrix.GetElement(2, 3)
            data_sum = x + y + z
            # Create matrix to store the transform for camera to aruco marker
            if data_sum > 0 and k != name:
                print 'parent: ', name
                print 'other: ', k
                # Compare matrix of current node to that of the observer
                # if within some bounds, add it to the list of validNodes
                # if not within bounds, do not add
                face_distance = euc_distance(parent_matrix, matrix)
                print 'distance: ', face_distance
                if np.abs(face_distance - expected) < 50:
                    validNodes.append(k)
                    v['transform'] = transform_real_world_interest
                    v['matrix'] = matrix
            
        print validNodes
        Xc_sum = 0
        Yc_sum = 0
        Zc_sum = 0
        Xc2_sum = 0
        Yc2_sum = 0
        Zc2_sum = 0
        for j in range(len(validNodes)):
            # Get the appropriate offset (based on the face of the cube)
            # Apply it to the stored start point, which is currently at the center of the cube
            offset = self.offsets[validNodes[j]]['offset']
            offset_matrix = vtk.vtkMatrix4x4()
            offset_matrix.DeepCopy(offset)
            curr_marker = offset_matrix.MultiplyPoint(self.spInMarker)
            
            matrix = self.offsets[validNodes[j]]['matrix']
            startPointinCamera = matrix.MultiplyPoint(curr_marker)
            
            # Set calculated 3d start point in camera space
            
            Xc_sum += startPointinCamera[0]
            Yc_sum += startPointinCamera[1]
            Zc_sum += startPointinCamera[2]
            # Get Marker 3D
            Xc2, Yc2, Zc2 = self.get_3d_coordinates(self.offsets[validNodes[j]]['transform'])
            
            t = time.time()
            self._marker_1_collection['time'].append(t)
            self._marker_1_collection['3D pos'].append([Xc2, Yc2, Zc2])
            self._start_point_collection['3D pos'].append([startPointinCamera[0], startPointinCamera[1], startPointinCamera[2]])
            
            Xc2_sum += Xc2
            Yc2_sum += Yc2
            Zc2_sum += Zc2
            # Perform 3D (Camera) to 2D project
            # Use the average to determine the startpoint
            # Save to Collection
            
            # todo:Apply distortion values
            print('camera point', x, y)
            print('marker', x2, y2)

            # Display point somewhere
            # Setup SP matrix
            vtk_sp_matrix = self.create_4x4_vtk_mat(x, y)

            # Setup Marker Matrix
            vtk_marker_matrix = self.create_4x4_vtk_mat(x2, y2)

            for cyl in self.display_marker_cylinders:
                cyl.SetMatrixTransformToParent(vtk_sp_matrix)

        Xc2 = Xc2_sum/len(validNodes)
        Yc2 = Yc2_sum/len(validNodes)
        Zc2 = Zc2_sum/len(validNodes)
    
        Xc = Xc_sum/len(validNodes)
        Yc = Yc_sum/len(validNodes)
        Zc = Zc_sum/len(validNodes)
    
        [x2, y2] = [0, 0]
        [x2, y2] = self.transform_3d_to_2d(Xc2, Yc2, Zc2)
        self._marker_1_collection['2D pos'].append([x2, y2])
    
        # Perform 3D (Camera) to 2D project sp
        [x, y] = [0, 0]
        [x, y] = self.transform_3d_to_2d(Xc, Yc, Zc)
        self._start_point_collection['2D pos'].append([x, y])

    
        vtk_sp_matrix = self.create_4x4_vtk_mat(x, y)
        # Setup Marker Matrix
        vtk_marker_matrix = self.create_4x4_vtk_mat(x2, y2)
        # Update Nodes
    
        # ONLY CURRENTLY SHOWING ONE DISPLAY NODE
        # WILL UPDATE WHEN DISPLAY IS FINALIZED
        #self.startPointSphere.SetMatrixTransformToParent(vtk_sp_matrix)
        #self.displayMarkerSphere.SetMatrixTransformToParent(vtk_marker_matrix)
        print "Start point number: ", i
        print x, y

    def addTransforms(self):
        for (k,v) in self.transforms.items():
            matrix = vtk.vtkMatrix4x4()
            matrix.DeepCopy(v['coords'])
            transform = slicer.vtkMRMLLinearTransformNode()
            transform.SetName(k)
            slicer.mrmlScene.AddNode(transform)
            transform.ApplyTransformMatrix(matrix)
            v['node'] = transform

    def transform_3d_to_2d(self, Xc, Yx, Zc):
        x = numpy.round((Xc * self.fx / Zc) + self.cx)
        y = numpy.round((Yx * self.fy / Zc) + self.cy)
        return x, y

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

    def run(self, transformOfInterest, fiducialOfInterest, directory_path, cylinder_nodes):
        # Get Spheres for display
        self.displayMarkerSphere = slicer.mrmlScene.GetFirstNodeByName('Marker_Sphere')
        self.startPointSphere = slicer.mrmlScene.GetFirstNodeByName('Sphere_Transform')
        self.marker2Sphere = slicer.mrmlScene.GetFirstNodeByName('Marker_2')

        self.transformNodeObserverTags = []
        self.transformOfInterestNode = transformOfInterest

        self.display_marker_cylinders = cylinder_nodes

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
        matrix2 = vtk.vtkMatrix4x4()
        matrix2.DeepCopy(self.fiducialNode.GetMatrixTransformToParent())
        coord[0] = matrix2.GetElement(0, 3)
        coord[1] = matrix2.GetElement(1, 3)
        coord[2] = matrix2.GetElement(2, 3)
        coord.append(1)
        #print('coord', coord)
        # Multiply to put start point relative to marker model origin
        self.spInMarker = matrix.MultiplyPoint(coord)
        self.ctTransform = [[1, 0, 0, self.spInMarker[0]], [0, 1, 0, self.spInMarker[1]], [0, 0, 1, self.spInMarker[2]],
                            [0, 0, 0, 1]]


        #self.on_transform_2_modified(0, 0)
        # start the updates
        self.addTransforms()
        self.updateOffsets()
        self.addObservers()
        self.onTransformOfInterestNodeModified(0, 0)
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
                    'Start Point': self._start_point_collection,
                    'Start Point wrt Marker in CT': self.ctTransform}
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
