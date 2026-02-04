import rclpy
import threading
import time
from goto_goal import GoToGoalNode
from detect_aruco2 import ArucoDetector
from rclpy.executors import MultiThreadedExecutor



def main():
    rclpy.init()

    detector = ArucoDetector()
    rover_driver = GoToGoalNode()

    executor = MultiThreadedExecutor()
    executor.add_node(detector)
    executor.add_node(rover_driver)

    print("Started Aruco Detector and GoToGoalNode.")
    # Wait for detection
    while rclpy.ok():
        if detector.detections:
            tag_coord = detector.detections.copy()
            print(f"Found tag:\n{tag_coord}")
            break
        rclpy.spin_once(detector, timeout_sec=0.1)

    detector.destroy_node()
    print("Detector killed")

    x, y, z = tag_coord[0]["position"]
    rover_driver.send_goal(float(x), float(-y))

    # Spin until goal finishes
    executor.spin()
    rclpy.shutdown()



if __name__ == '__main__':
    main()





    
