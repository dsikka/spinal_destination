import numpy as np

def resolve_rigid_transform(A, B):
    ''' find the least squares rigid transform R, d that transforms A into B '''
    abar = np.average(A, 1)
    bbar = np.average(B, 1)
    A = A - np.transpose([abar])
    B = B - np.transpose([bbar])
    C = B@A.T
    u, s, vh = np.linalg.svd(C)
    R = u@vh
    return R, bbar - R@abar
    
A = [[-131.96, -122.65,-27.44],[-130.55,-124.50,-25.83],[-131.00,-123.46,-26.28]]
B = [[19.09, 65.5,591.2],[18.24,65.34,591.14],[19.28,69.97,594.40]]
R, t = resolve_rigid_transform(A,B)
det = np.linalg.det(R)
print(det)
