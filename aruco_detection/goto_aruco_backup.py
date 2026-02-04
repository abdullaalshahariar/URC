import rclpy
import threading
import time
from goto_goal import GoToGoalNode
from detect_aruco2 import ArucoDetector

def main():
    """
    Plan: detect aruco in a different thread.
    after detection get x,y,z and kill the thread
    run the rover_driver to go to that location
    """

    rclpy.init() #aruco detector depends on ros2

    detector = ArucoDetector()
    thread = threading.Thread(target=rclpy.spin,
                            args=(detector,),
                            daemon=True)
    thread.start()
    print("Started Aruco Detetor.")


    #main thread, just waiting for x,y,z to appear
    while rclpy.ok():
        if detector.detections is not None:
            tag_coord = detector.detections
            print(f"Found tag at {tag_coord}")
            break
        time.sleep(0.1) #just taking small break, so that cpu does not get fried
    
    #if reached this point, that means got the coords
    #will kill the detector
    detector.destroy_node()
    print("detector killled")



    #stating the driver
    x,y,z = detector[x], detector[y], detector[z]
    rover_driver = GoToGoalNode()
    rover_driver.send_goal(float(x), float(-y))

    rclpy.spin(rover_driver)
    rclpy.shutdown()


if __name__ == '__main__':
    main()





    