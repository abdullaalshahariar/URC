import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from rclpy.qos import qos_profile_sensor_data
import numpy as np
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLOWorld

class ArucoDector(Node):
    def __init__(self):
        super().__init__('aruco_detector')
        self.bridge = CvBridge()
        
        # 1. Initialize YOLO26 World
        self.get_logger().info('DEBUG: Initializing YOLO26 World model...')
        # yolov26n is the Nano version - best for real-time ROS performance
        self.model = YOLOWorld('yolov26n-world.pt') 
        
        # Define specific prompts. 
        # Adding "square" and "black and white" helps the model's 'imagination'
        self.model.set_classes(["aruco marker", "black and white square QR code"])
        
        # ... (Your existing Camera Info Subscriptions) ...

    def image_callback(self, msg):
        # Convert ROS image to OpenCV
        try:
            # We use 'bgr8' because YOLO expects standard OpenCV colors
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'CV Bridge Error: {e}')
            return

        # 2. Run Inference
        # conf=0.3 is a good starting point; lower it to 0.1 if it sees nothing
        results = self.model.predict(cv_image, conf=0.3, verbose=False)[0]

        # 3. Process and Visualize
        if len(results.boxes) > 0:
            for box in results.boxes:
                # Get coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                
                # Draw on the image
                cv2.rectangle(cv_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Marker: {conf:.2f}"
                cv2.putText(cv_image, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                self.get_logger().info(f"Detected potential marker at [{x1}, {y1}]")

        # 4. Show the "Live View"
        cv2.imshow("YOLO-World Detection", cv_image)
        cv2.waitKey(1)