READ ME

Setting up Plus Sever and Slicer
- Install the latest version of Plus Server and Slicer 3D
- Calibrate your camera using [add in remaining camera calibration steps]
- The calibration file (called camera_calibration.yml) should be added under config\OpticalMarkerTracker within your Plus Server Directory
- Edit your PlusDeviceSet_Server_OpticalMarkerTracker_Mmf.xml config file: 
	1) Be sure that the path to the camera calibration file within the PlusDeviceSet_Server_OpticalMarkerTracker_Mmf.xml config file
	is correct
	2) Under <DataSource> change the MarkerSizeMm for all markers to the current size (in mm). For example, for a 22 mm marker, update the config file to have all values as: MarkerSizeMm="22"
- Add this calibration file to the same directory as where the spinal_destination repo was cloned
- Clean up the camera calibration file in this location by making the following changes:
	1) Change the first line such that %YAML:1.0 --> # YAML:1.0
	2) Remove the !! opencv_matrix text found on lines 5 and 11 of the file
- [Add something about adding all the required extensions to slicer]
- Add the location to Plus Server and its bin directory to your PATH variable
- Step-up pyyaml for Slicer
	1) Start your Command Prompt as Administrator (if you're using windows, or use sudo for mac/linux)
	2) Go to your Slicer 3D directory (usually found under Program Files)
	3) Go to your bin directory
	4) Run the following command from within the bin directory:"PythonSicer.exe" -m pip install pyyaml
- You should now be able to run the extension.