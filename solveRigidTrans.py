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
    
A = [[-130.62216549142354, -123.93782605272432, -25.37971607064188],[-151.31974506680774, -125.68177039146059, -22.253940594176328],[-150.17577815524487, -117.79141664585586, -57.933745181572974]]
B = [[-17.397079467773438, -22.539541244506836, 410.8363952636719],[-18.7603702545166, -1.6178241968154907, 412.1111755371094],[15.940749168395996, -7.093510150909424, 422.2336120605469]]
R, t = resolve_rigid_transform(A,B)
det = np.linalg.det(R)
print(det)
A = np.array(A)
B = np.array(B)

print (np.sum((A - A[0])**2, 1))
print (np.sum((B - B[0])**2, 1))