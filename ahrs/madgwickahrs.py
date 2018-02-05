# -*- coding: utf-8 -*-
"""
    Copyright (c) 2015 Jonas Böer, jonas.boeer@student.kit.edu

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import warnings
import numpy as np
from numpy.linalg import norm
from quaternion import Quaternion
import sys
sys.path.insert(0, "/home/debian/dobby/imu/")
from dobby_imu import MPU9250

class AHRS:
    samplePeriod = 1/256
    quaternion = Quaternion(1, 0, 0, 0)
    beta = 1

    def __init__(self, sampleperiod=None, quaternion=None, beta=None):
        """
        Initialize the class with the given parameters.
        :param sampleperiod: The sample period
        :param quaternion: Initial quaternion
        :param beta: Algorithm gain beta
        :return:
        """
        if sampleperiod is not None:
            self.samplePeriod = sampleperiod
        if quaternion is not None:
            self.quaternion = quaternion
        if beta is not None:
            self.beta = beta

    def update(self):
        """
        Perform one update step with data from a AHRS sensor array
        :param gyroscope: A three-element array containing the gyroscope data in radians per second.
        :param accelerometer: A three-element array containing the accelerometer data. Can be any unit since a normalized value is used.
        :param magnetometer: A three-element array containing the magnetometer data. Can be any unit since a normalized value is used.
        :return:
        """
        q = self.quaternion


        # Normalise accelerometer measurement
        if self.norm(MPU9250.accel_data) is 0:
            warnings.warn("accelerometer is zero")
            return
        MPU9250.accel_data /= self.norm(MPU9250.accel_data)

        # Normalise magnetometer measurement
        if self.norm(MPU9250.mag_data) is 0:
            warnings.warn("magnetometer is zero")
            return
        MPU9250.mag_data /= self.norm(MPU9250.mag_data)

        h = q * (Quaternion(0, MPU9250.mag_data[0], MPU9250.mag_data[1], MPU9250.mag_data[2]) * q.conj())
        b = np.array([0, self.norm(h[1:3]), 0, h[3]])

        # Gradient descent algorithm corrective step
        f = np.array([
            2*(q[1]*q[3] - q[0]*q[2]) - MPU9250.accel_data[0],
            2*(q[0]*q[1] + q[2]*q[3]) - MPU9250.accel_data[1],
            2*(0.5 - q[1]**2 - q[2]**2) - MPU9250.accel_data[2],
            2*b[1]*(0.5 - q[2]**2 - q[3]**2) + 2*b[3]*(q[1]*q[3] - q[0]*q[2]) - MPU9250.mag_data[0],
            2*b[1]*(q[1]*q[2] - q[0]*q[3]) + 2*b[3]*(q[0]*q[1] + q[2]*q[3]) - MPU9250.mag_data[1],
            2*b[1]*(q[0]*q[2] + q[1]*q[3]) + 2*b[3]*(0.5 - q[1]**2 - q[2]**2) - MPU9250.mag_data[2]
        ])
        j = np.array([
            [-2*q[2],                  2*q[3],                  -2*q[0],                  2*q[1]],
            [2*q[1],                   2*q[0],                  2*q[3],                   2*q[2]],
            [0,                        -4*q[1],                 -4*q[2],                  0],
            [-2*b[3]*q[2],             2*b[3]*q[3],             -4*b[1]*q[2]-2*b[3]*q[0], -4*b[1]*q[3]+2*b[3]*q[1]],
            [-2*b[1]*q[3]+2*b[3]*q[1], 2*b[1]*q[2]+2*b[3]*q[0], 2*b[1]*q[1]+2*b[3]*q[3],  -2*b[1]*q[0]+2*b[3]*q[2]],
            [2*b[1]*q[2],              2*b[1]*q[3]-4*b[3]*q[1], 2*b[1]*q[0]-4*b[3]*q[2],  2*b[1]*q[1]]
        ])
        step = j.T.dot(f)
        step /= self.norm(step)  # normalise step magnitude

        # Compute rate of change of quaternion
        qdot = (q * Quaternion(0, MPU9250.gyro_data[0], MPU9250.gyro_data[1], MPU9250.gyro_data[2])) * 0.5 - self.beta * step.T

        # Integrate to yield quaternion
        q += qdot * self.samplePeriod
        self.quaternion = Quaternion(q / self.norm(q))  # normalise quaternion

    def update_imu(self):
        """
        Perform one update step with data from a IMU sensor array
        :param gyroscope: A three-element array containing the gyroscope data in radians per second.
        :param accelerometer: A three-element array containing the accelerometer data. Can be any unit since a normalized value is used.
        """
        q = self.quaternion

        # Normalise accelerometer measurement
        if self.norm(MPU9250.accel_data) is 0:
            warnings.warn("MPU9250.accel_data is zero")
            return
        MPU9250.accel_data /= self.norm(MPU9250.accel_data)

        # Gradient descent algorithm corrective step
        f = np.array([
            2*(q[1]*q[3] - q[0]*q[2]) - MPU9250.accel_data[0],
            2*(q[0]*q[1] + q[2]*q[3]) - MPU9250.accel_data[1],
            2*(0.5 - q[1]**2 - q[2]**2) - MPU9250.accel_data[2]
        ])
        j = np.array([
            [-2*q[2], 2*q[3], -2*q[0], 2*q[1]],
            [2*q[1], 2*q[0], 2*q[3], 2*q[2]],
            [0, -4*q[1], -4*q[2], 0]
        ])
        step = j.T.dot(f)
        step /= self.norm(step)  # normalise step magnitude

        # Compute rate of change of quaternion
        qdot = (q * Quaternion(0, MPU9250.gyro_data[0], MPU9250.gyro_data[1], MPU9250.gyro_data[2])) * 0.5 - self.beta * step.T

        # Integrate to yield quaternion
        q += qdot * self.samplePeriod
        self.quaternion = Quaternion(q / self.norm(q))  # normalise quaternion

    def norm(self, x):
        norm_data = 0
        for i in range(len(x)):
            norm_data = norm_data + x[i]*x[i]

        norm_data = math.sqrt(norm_data)
        return norm_data
