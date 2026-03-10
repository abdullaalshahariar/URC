import rclpy
import threading
import time
from goto_goal import GoToGoalNode
from detect_aruco2 import ArucoDetector
from rclpy.executors import MultiThreadedExecutor
import math
import numpy as np


class PentaGon:
    def __init__(self, radius=10, h=0, k=0, theta=0):
        self.radius = radius
        self.angle = (math.pi*2)/5

        self.trans_matrix = np.array(
            [
                [math.cos(theta), -math.sin(theta), h],
                [math.sin(theta),  math.cos(theta), k],
                [0,                0,               1]
            ])

    def generate_points(self):
        points = []

        angle = self.angle
        for i in range(5):
            angle = self.angle*i

            x = self.radius*math.cos(angle)
            y = self.radius*math.sin(angle)

            p = np.array([x, y, 1])
            p = self.trans_matrix @ p
            
            points.append((float(p[0]), float(p[1])))
        

        return points


def wait_for_result(node, future):
    """Waits for an action to finish.
    Careful s=using this function. If the nodes 
    are not running in seprate threads, this will block
    the execution of the nodes."""

    while rclpy.ok() and not future.done():
        time.sleep(0.1)
    
    return future.result()



def main():
    rclpy.init()
    detector = ArucoDetector()
    rover_driver = GoToGoalNode()

    executor = MultiThreadedExecutor()
    executor.add_node(detector)
    executor.add_node(rover_driver)
    
    #The executor runs on a seprate thread
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        # Phase 1: spinn and detect arico
        print("Phase 1: initial aruco")
        spin_future = rover_driver.rotate_360()

        found_tag = None
        while rclpy.ok() and not spin_future.done():
            if detector.detections:
                found_tag = detector.detections[0]
                print(f"tag detected. stopping rotation")
                rover_driver.stop_rotation()
                break

            time.sleep(0.1) # Just making sure cpu does not gets fried

        if found_tag:
            x,y,_ = found_tag["position"]
            print(f"Mobing to tag at x:{x}, y:{y}")
            nav_future = rover_driver.send_goal(float(x), float(y))
            goal_handle =  wait_for_result(rover_driver, nav_future)

            if goal_handle:
                result_future = goal_handle.get_result_async()
                wait_for_result(rover_driver, result_future)
                print("first aruco reached")


        # Phase 2: Pentagon search
        penta = PentaGon(radius=1, h=0, k=0)
        points = penta.generate_points()

        for i, (px, py) in enumerate(points):
            detector.detections.clear() #clearing the dictionary before next search

            print(f"moving to pentagon point {i+1} at x:{px}, y:{py}")
            nav_future = rover_driver.send_goal(float(px), float(py))
            goal_handle = wait_for_result(rover_driver, nav_future)

            if goal_handle:
                result_future = goal_handle.get_result_async()
                wait_for_result(rover_driver, result_future)

            # arrived at point, check for aruco
            print("arrived at point, checking for aruco")
            spin_future = rover_driver.rotate_360()

            found_tag = None
            while rclpy.ok() and not spin_future.done():
                if detector.detections:
                    found_tag = detector.detections[0]
                    print(f"second tag detected. stopping rotation")
                    rover_driver.stop_rotation()
                    break

                time.sleep(0.1)

            if found_tag:
                x,y,_ = found_tag["position"]
                print(f"Mobing to tag at x:{x}, y:{y}")
                nav_future = rover_driver.send_goal(float(x), float(y))
                
                goal_handle = wait_for_result(rover_driver, nav_future)
                if goal_handle:
                    result_future = goal_handle.get_result_async()
                    wait_for_result(rover_driver, result_future)
                print("Aruco reached, ending search")
                break


    except Exception as e:
        print(f"Exception in main: {e}")
    finally:
        print("Shutting down...")
        rover_driver.destroy_node()
        detector.destroy_node()
        rclpy.shutdown()
        executor_thread.join()



if __name__ == '__main__':
    main()





    
