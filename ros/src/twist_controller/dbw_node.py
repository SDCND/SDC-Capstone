#!/usr/bin/env python

import rospy
from std_msgs.msg import Bool, Float64 
from dbw_mkz_msgs.msg import ThrottleCmd, SteeringCmd, BrakeCmd, SteeringReport
from geometry_msgs.msg import TwistStamped
from geometry_msgs.msg import PoseStamped
import math

from twist_controller import Controller

'''
You can build this node only after you have built (or partially built) the `waypoint_updater` node.

You will subscribe to `/twist_cmd` message which provides the proposed linear and angular velocities.
You can subscribe to any other message that you find important or refer to the document for list
of messages subscribed to by the reference implementation of this node.

One thing to keep in mind while building this node and the `twist_controller` class is the status
of `dbw_enabled`. While in the simulator, its enabled all the time, in the real car, that will
not be the case. This may cause your PID controller to accumulate error because the car could
temporarily be driven by a human instead of your controller.

We have provided two launch files with this node. Vehicle specific values (like vehicle_mass,
wheel_base) etc should not be altered in these files.

We have also provided some reference implementations for PID controller and other utility classes.
You are free to use them or build your own.

Once you have the proposed throttle, brake, and steer values, publish it on the various publishers
that we have created in the `__init__` function.

'''

class DBWNode(object):
    def __init__(self):
        rospy.init_node('dbw_node')

        vehicle_mass = rospy.get_param('~vehicle_mass', 1736.35)
        fuel_capacity = rospy.get_param('~fuel_capacity', 13.5)
        brake_deadband = rospy.get_param('~brake_deadband', .1)
        decel_limit = rospy.get_param('~decel_limit', -5)
        accel_limit = rospy.get_param('~accel_limit', 1.)
        wheel_radius = rospy.get_param('~wheel_radius', 0.2413)
        wheel_base = rospy.get_param('~wheel_base', 2.8498)
        steer_ratio = rospy.get_param('~steer_ratio', 14.8)
        max_lat_accel = rospy.get_param('~max_lat_accel', 3.)
        max_steer_angle = rospy.get_param('~max_steer_angle', 8.)
        vehicle_total_mass = vehicle_mass + 25.0 + 70.0 + 30.0 # additional weight (gas, passenger, load)

        self.steer_pub = rospy.Publisher('/vehicle/steering_cmd',
                                         SteeringCmd, queue_size=1)
        self.throttle_pub = rospy.Publisher('/vehicle/throttle_cmd',
                                            ThrottleCmd, queue_size=1)
        self.brake_pub = rospy.Publisher('/vehicle/brake_cmd',
                                         BrakeCmd, queue_size=1)

        # TODO: Create `TwistController` object
        # self.controller = TwistController(<Arguments you wish to provide>)

        # TwistController
        # def __init__(self, wheel_base, steer_ratio, max_lat_accel, 
        #              max_steer_angle, decel_limit, accel_limit, vehicle_total_mass, 
        #              brake_deadband, wheel_radius):
        self.controller = Controller(wheel_base, steer_ratio, max_lat_accel, 
                                     max_steer_angle, decel_limit, accel_limit, vehicle_total_mass, 
                                     brake_deadband, wheel_radius)

        self.curr_velocity = None
        self.target_velocity = None
        self.dbw_enabled = True # as described in the top section, it can be disabled if car is driven by human
        self.pose = None

        # TODO: Subscribe to all the topics you need to
        rospy.Subscriber("/current_velocity", TwistStamped, self.velocity_cb)
        rospy.Subscriber("/twist_cmd", TwistStamped, self.twist_cb)
        rospy.Subscriber("/vehicle/dbw_enabled", Bool, self.dbw_cb)
        rospy.Subscriber("/current_pose", PoseStamped, self.pose_cb)

        self.loop()

    def loop(self):
        rate = rospy.Rate(50) # 50Hz
        while not rospy.is_shutdown():
            # TODO: Get predicted throttle, brake, and steering using `twist_controller`
            # You should only publish the control commands if dbw is enabled
            # throttle, brake, steering = self.controller.control(<proposed linear velocity>,
            #                                                     <proposed angular velocity>,
            #                                                     <current linear velocity>,
            #                                                     <dbw status>,
            #                                                     <any other argument you need>)
            # if <dbw is enabled>:
            #   self.publish(throttle, brake, steer)

            if not self.curr_velocity:
                rospy.logwarn('no current velocity has been set')
                rate.sleep()
                continue

            if not self.target_velocity:
                rospy.logwarn('no target velocity has been set')
                rate.sleep()
                continue

            if not self.pose:
                rospy.logwarn('no pose has been set')
                rate.sleep()
                continue

            if not self.dbw_enabled:
                rospy.logdebug('no driving by wire - human in control')
                # Reset PID controller
                self.controller.reset()
                rate.sleep()
                continue

            throttle, brake, steer = self.controller.control(self.curr_velocity.linear.x, self.target_velocity.linear.x, self.target_velocity.angular.z)
            self.publish(throttle, brake, steer)

            rate.sleep()

    def velocity_cb(self, msg):
        self.curr_velocity = msg.twist

    def twist_cb(self, msg):
        self.target_velocity = msg.twist

    def dbw_cb(self, msg):
        self.dbw_enabled = msg.data
        rospy.loginfo('received dbw_enabled %s', str(msg.data))

    def pose_cb(self, msg):
        self.pose = msg.pose

    def publish(self, throttle, brake, steer):
        tcmd = ThrottleCmd()
        tcmd.enable = True
        tcmd.pedal_cmd_type = ThrottleCmd.CMD_PERCENT
        tcmd.pedal_cmd = throttle
        self.throttle_pub.publish(tcmd)

        scmd = SteeringCmd()
        scmd.enable = True
        scmd.steering_wheel_angle_cmd = steer
        self.steer_pub.publish(scmd)

        bcmd = BrakeCmd()
        bcmd.enable = True
        bcmd.pedal_cmd_type = BrakeCmd.CMD_TORQUE
        bcmd.pedal_cmd = brake
        self.brake_pub.publish(bcmd)


if __name__ == '__main__':
    DBWNode()
