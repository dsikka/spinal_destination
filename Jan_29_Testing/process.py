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
    covariance = np.cov(trackerData[:,0],trackerData[:,1])
    means=[mean_x, mean_y]
    return means, covariance
    
plt.close("all")

file = "18-58-08.json"
dir = ("C:\\Users\\tina\\Desktop\\Jan_29_Testing\\%s" %(file))

my_json = json.load(open(dir))
m1_tracker = np.array(my_json["Marker 1"]["3D pos"])

file = "19-00-55.json"
dir = ("C:\\Users\\tina\\Desktop\\Jan_29_Testing\\%s" %(file))

my_json = json.load(open(dir))
m1_tracker_mid = np.array(my_json["Marker 1"]["3D pos"])

file = "19-02-18.json"
dir = ("C:\\Users\\tina\\Desktop\\Jan_29_Testing\\%s" %(file))

my_json = json.load(open(dir))
m1_tracker_far = np.array(my_json["Marker 1"]["3D pos"])

m1_mean, m1_cov = findMeanAndCov(m1_tracker)
ellipse = defellipse(m1_mean,m1_cov)

m1_mean_mid, m1_cov_mid = findMeanAndCov(m1_tracker_mid)
ellipse_mid = defellipse(m1_mean_mid,m1_cov_mid)

m1_mean_far, m1_cov_far = findMeanAndCov(m1_tracker_far)
ellipse_far = defellipse(m1_mean_far,m1_cov_far)


plt.figure()
plt.plot(0,0,'x',color='red')
alphaAdjust = 0.4
plt.plot(m1_tracker[:,0]-m1_mean[0],m1_tracker[:,1]-m1_mean[1],'.',alpha=alphaAdjust,color='xkcd:aqua',label='Near')
plt.plot(ellipse[:,0]-m1_mean[0],ellipse[:,1]-m1_mean[1],label='Near STD Contour',color='xkcd:goldenrod')

plt.plot(m1_tracker_mid[:,0]-m1_mean_mid[0],m1_tracker_mid[:,1]-m1_mean_mid[1],'.',alpha=alphaAdjust,color='xkcd:azure',label='Mid')
plt.plot(ellipse_mid[:,0]-m1_mean_mid[0],ellipse_mid[:,1]-m1_mean_mid[1],label='Mid STD Contour',color='xkcd:lavender')

plt.plot(m1_tracker_far[:,0]-m1_mean_far[0],m1_tracker_far[:,1]-m1_mean_far[1],'.',alpha=alphaAdjust,color='xkcd:darkblue',label='Far')
plt.plot(ellipse_far[:,0]-m1_mean_far[0],ellipse_far[:,1]-m1_mean_far[1],label='Far STD Contour',color='xkcd:pink')
plt.legend()
plt.show()