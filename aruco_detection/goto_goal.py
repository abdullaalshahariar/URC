#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from rclpy.duration import Duration
import math
import threading
import sys


class GoToGoalNode(Node):
    def __init__(self):
        super().__init__('go_to_goal_node')
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._goal_handle = None
        self.get_logger().info('Waiting for Nav2 action server...')
        self._action_client.wait_for_server()
        self.get_logger().info('Nav2 action server available!')
    
    def send_goal(self, x: float, y: float, yaw: float = 0.0):
        goal_msg = NavigateToPose.Goal()
        
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0
        
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0
        
        self.get_logger().info(f'Navigating to: x={x}, y={y}, yaw={yaw}')
        
        send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)
        
        return send_goal_future
    
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected!')
            return
        
        self.get_logger().info('Goal accepted!')
        self._goal_handle = goal_handle
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)
    
    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status
        
        if status == 4:  
            self.get_logger().info('Goal reached successfully!')
        elif status == 5:  
            self.get_logger().warn('Goal was canceled')
        elif status == 6: 
            self.get_logger().error('Goal was aborted')
        else:
            self.get_logger().info(f'Navigation finished with status: {status}')
        
        self._goal_handle = None
    
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        current_pose = feedback.current_pose.pose.position
        self.get_logger().info(
            f'Current position: x={current_pose.x:.2f}, y={current_pose.y:.2f}',
            throttle_duration_sec=2.0
        )
    
    def stop_goal(self):
        if self._goal_handle is not None:
            self.get_logger().info('Canceling current goal...')
            self._goal_handle.cancel_goal_async()
        else:
            self.get_logger().info('No active goal to stop.')



