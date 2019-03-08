import numpy as np
import matplotlib.pyplot as plt
import pylab, csv, os, math, json

def defellipse(means,covariance):
    # calculate the standard deviations and affine transformation
    eigvals, eigvecs = np.linalg.eig(covariance)
    
    # generate the 4-sigma boundary in the original image's coordinate frame
    sigmas = np.sqrt(eigvals)
    ellipse = np.column_stack(((sigmas[0] * np.cos(x), sigmas[1] * np.sin(x))
                                for x in np.linspace(0, np.pi * 2, 100)))
    ellipse = ((2 * eigvecs @ ellipse).T + means)
    
    return ellipse
    
def findMeanAndCov(trackerData): 
    mean_x = np.mean(trackerData[:,0])
    mean_y = np.mean(trackerData[:,1])
    covariance = np.cov(trackerData[:,0]-mean_x,trackerData[:,1]-mean_y)
    means=[mean_x, mean_y]
    return means, covariance
    
errorx = []
errory = []
avgerror = []

plt.close("all")
expLength = range (1,10)

for expID in expLength:
    singlePoint = False
    file = ("Test_Position_%s.json" %(expID))
    dir = ("C:\\Users\\Tina\\Documents\\spinal_destination\\March_7_Projection\\%s" %(file))
    
    my_json = json.load(open(dir))
    m1_tracker = np.array(my_json["Start Point"]["3D pos"])
    m1_tracker[:,1] = -m1_tracker[:,1]
    time = np.array(my_json["Marker 1"]["time"])
    time = time - time[0]
    sp = np.array(my_json["Start Point wrt Marker in CT"])
    
    if len(time) == 1:
        singlePoint = True
    
    pt = np.ones(len(time))
    plt.figure()
    plt.subplot(2,1,1)
    plt.plot(time,m1_tracker[:,0],label = 'tracker')
    plt.plot(time,pt*sp[0,3],label = 'real sp')
    plt.xlabel('Time (s)')
    plt.ylabel('x (mm)')
    plt.legend()
    plt.subplot(2,1,2)
    plt.plot(time,m1_tracker[:,1],'x')
    plt.plot(time,pt*sp[1,3],'o')
    plt.xlabel('Time (s)')
    plt.ylabel('y (mm)')
    
    if singlePoint == False:
        m1_mean, m1_cov = findMeanAndCov(m1_tracker)
        ellipse = defellipse(m1_mean,m1_cov)
        m1_var_x = np.var(m1_tracker[:,0])
        m1_var_y = np.var(m1_tracker[:,1])
        
    else:
        m1_var_x = 0
        m1_var_y = 0
        
    errorx.append(sp[0,3] - m1_mean[0])
    errory.append(sp[1,3] - m1_mean[1])
    avger = np.sqrt(errorx[expID-1]**2 + errory[expID-1]**2)
    avgerror.append(avger)
    
    bound = defellipse([sp[0,3],sp[1,3]], [[1,0],[0,1]])
    
    print('expID: %s\ntrue sp x: %s\ntrue sp y: %s\nmean in x: %s\nmean in y: %s\nerror in x: %s\nerror in y: %s\nmagnitude of error: %s\nvariance in x: %s\nvariance in y: %s\n' %(expID,sp[0,3],sp[1,3],m1_mean[0],m1_mean[1],errorx[expID-1],errory[expID-1],avgerror[expID-1],m1_var_x,m1_var_y))
    
    
    plt.figure()
    plt.plot(sp[0,3],sp[1,3],'x',color='red',label='target sp')
    plt.plot(m1_mean[0],m1_mean[1],'x',color='blue',label='mean of projected sp')
    alphaAdjust = 0.4
    plt.plot(m1_tracker[:,0],m1_tracker[:,1],'.',alpha=alphaAdjust,color='xkcd:aqua',label='sp data')
    if singlePoint == False:
        plt.plot(ellipse[:,0],ellipse[:,1],label='projected sp STD Contour',color='xkcd:goldenrod')
    plt.plot(bound[:,0],bound[:,1],label='acceptable error (2mm)',color='xkcd:goldenrod',alpha=alphaAdjust)
    plt.legend()

    plt.xlabel('x (mm)')
    plt.ylabel('y (mm)')
    
explist = list(expLength)

plt.figure()
plt.plot(explist,avgerror,'x')
plt.xlabel('experiment ID')
plt.ylabel('magnitude of error (mm)')
plt.show()