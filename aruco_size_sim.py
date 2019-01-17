import cv2
import numpy as np
import matplotlib.pyplot as plt

# this script looks at the smallest possible marker size by comparing the transformation matrix given by slicer against the matrix reconstructed using the pixel values of the aruco marker
output=[]
# loop through a bunch of potential marker sizes (mm)
for size in range(10,30):
    
    # aruco markers detects a bunch of small squares within the square. Therefore, make a bunch of coords based on the simulated marker size. Specifically, our marker has 7 corners to detect per edge
    X, Y = np.meshgrid(np.linspace(-size/2, size/2, 7),np.linspace(-size/2, size/2, 7))
    pos = np.array([X.flatten(), Y.flatten(), np.zeros(49), np.ones(49)])
    
    #pos = np.array([[-size/2, size/2, size/2, -size/2],
    #                [size/2, size/2, -size/2, -size/2],
    #                [0, 0, 0, 0],
    #                [1, 1, 1, 1]])
    
    # copied from Slicer 
    Rt = np.array([[0.99, 0.03, -0.13, 115.33],
        [0.05, -0.98, 0.18, -185.54],
        [-0.12, -0.18, -0.98, 626.85]]);
    
    # Rodrigues reconstructes the rotation matrix becoz Slicer doesn't give enough digits    
    Rt[:, :3] = cv2.Rodrigues(cv2.Rodrigues(Rt[:, :3])[0])[0]
    
    # Sam's camera matrix
    fx = 5.9596203089288861e2;
    fy = 5.9780697114621512e2;
    cx = 3.1953140232090112e2;
    cy = 2.6188803044119754e2;
    
    f = np.array([[fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]])
    
    error = []
    for x in range(0,100):
        # matrix multiplication is weird = @    
        pix = f @ Rt @ pos
        pix = pix / pix[2] # normalizing such that it matches the documentation
        noise = np.random.uniform(-1,1,(2,49)) # simulate pixel noise
        pix[:2] = pix[:2] + noise
        
        distCoeffs = None
        
        # solves for the transformation matrix 
        ret, rotvec, transvec = cv2.solvePnP(pos[:3].T,pix[:2].T,f,distCoeffs)
        
        # reconstruct the rotation matrix becoz PnP gives a rotation vector
        rotmat = cv2.Rodrigues(rotvec)[0]
        
        # calculate absolute error along X, Y, Z
        error.append(np.abs((transvec.flat - Rt[:,3])))
    
    output.append(np.average(error,0))

output = np.array(output)
inputs = np.arange(10,30)
plt.ion()
plt.figure()
plt.clf()
plt.subplot(3,1,1)
plt.plot(inputs,output[:,0])
plt.ylabel('Error in X (mm)')
plt.subplot(3,1,2)
plt.plot(inputs,output[:,1])
plt.ylabel('Error in Y (mm)')
plt.subplot(3,1,3)
plt.plot(inputs,output[:,2])
plt.ylabel('Error in Z (mm)')
plt.suptitle('Marker size vs Position error')
plt.xlabel('Marker size (mm)')