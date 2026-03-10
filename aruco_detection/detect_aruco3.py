import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from rclpy.qos import qos_profile_sensor_data
import numpy as np
from cv_bridge import CvBridge
from ultralytics import YOLOWorld
import cv2
from ultralytics import YOLO

class ArucoDetector(Node):
    def __init__(self):
        super().__init__('aruco_detector')

        self.bridge = CvBridge() #required to convert between ROS and OpenCV images
        
        #initializing yolo world model
        self.get_logger().info('DEBUG: Initializing YOLO world model...')
        self.model = YOLOWorld('yolov8s-world.pt') 
        self.model.set_classes(["hand", "black and white square marker", "aruco marker"]) #using Open-Vocabulary


        #subscriber for camera_matrix and dist_coeffs
        self.camera_info_topic_name = '/zed/zed_node/rgb/color/rect/camera_info'
        self.camera_info_subscriber = self.create_subscription(
            msg_type=CameraInfo,
            topic=self.camera_info_topic_name,
            callback=self.camera_info_callback,
            qos_profile=qos_profile_sensor_data
        )
        self.get_logger().info(f'Subscribed to {self.camera_info_topic_name}')
        #information from camera info topic
        self.camera_matrix = None # value comes from callback function
        self.dist_coeffs = None


        #subscriber for image from zed cam
        self.image_topic_name = '/zed/zed_node/rgb/color/rect/image'
        self.image_subscriber = self.create_subscription(
            msg_type=Image,
            topic=self.image_topic_name,
            callback=self.image_callback,
            qos_profile=qos_profile_sensor_data
        )
        self.get_logger().info(f'Subscribed to {self.image_topic_name}')
        


    def camera_info_callback(self, msg):
        try:
            self.camera_matrix = np.array(msg.k, dtype=np.float32).reshape((3, 3))
            self.dist_coeffs = np.array(msg.d, dtype=np.float32)
            self.get_logger().info('Camera parameters received.')

            self.destroy_subscription(self.camera_info_subscriber)
        except Exception as e:
            self.get_logger().error(f'Error processing camera info: {e}')
    
    def image_callback(self, msg):
        if self.camera_matrix is None or self.dist_coeffs is None:
            self.get_logger().warn('Waiting for camera parameters...', throttle_duration_sec=2.0)

            return

        # Convert ROS image to OpenCV
        try:
            #yolo expects BGR format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'CV Bridge Error: {e}')
            return
        
        #detection of aruco tag
        results = self.model(cv_image, conf=0.3, verbose=False)[0] #yolo returns result as list
        # print(results) #for debugging - check if results are being generated

        #processing after detection
        if (len(results.boxes) > 0):
            for box in results.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                conf = float(box.conf[0])

                #drawing the bounding box
                cv2.rectangle(cv_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                label = f"Marker: {conf:.2f}"
                cv2.putText(cv_image, label, (int(x1), int(y1 - 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
        
        cv2.imshow("YOLO-World Detection", cv_image)
        cv2.waitKey(1)


def main():
    rclpy.init()
    node = ArucoDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()