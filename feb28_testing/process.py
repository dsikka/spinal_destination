import numpy as np
import matplotlib.pyplot as plt
import pylab, csv, os, math, json

plt.close("all")

file = "Keep_1.json"
dir = ("C:\\Users\\Tina\\Documents\\spinal_destination\\feb28_testing\\%s" %(file))

my_json = json.load(open(dir))
m1_tracker = np.array(my_json["Start Point"]["3D pos"])
time = np.array(my_json["Marker 1"]["time"])
sp = np.array(my_json["Start Point wrt Marker in CT"])
pt = np.ones(len(time))
plt.figure()
plt.subplot(2,1,1)
plt.plot(time,m1_tracker[:,0],label = 'tracker')

plt.plot(time,pt*sp[1,3],label = 'real sp')
plt.legend()
plt.subplot(2,1,2)
plt.plot(time,m1_tracker[:,1])
pt = np.ones(len(time))

plt.plot(time,pt*sp[0,3])
plt.show()