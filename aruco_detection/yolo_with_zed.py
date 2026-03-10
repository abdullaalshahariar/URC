import pyzed.sl as sl
import cv2
import numpy as np

def main():
    # 1. Initialize ZED Camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.NEURAL # High accuracy
    init_params.coordinate_units = sl.UNIT.METER  # Use meters for ROS/Robotics
    
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open ZED camera.")
        return

    # 2. Enable Positional Tracking (REQUIRED for Object Tracking)
    print("Enabling Positional Tracking...")
    positional_tracking_params = sl.PositionalTrackingParameters()
    zed.enable_positional_tracking(positional_tracking_params)

    # 3. Configure Native Object Detection
    print("Initializing Native YOLO Inference (Optimization may take minutes)...")
    obj_param = sl.ObjectDetectionParameters()
    
    # Use the "Native" mode where ZED runs the ONNX
    obj_param.detection_model = sl.OBJECT_DETECTION_MODEL.CUSTOM_YOLOLIKE_BOX_OBJECTS
    obj_param.enable_tracking = True
    
    # POINT TO YOUR ONNX FILE HERE
    obj_param.custom_onnx_file = "yolov8s-worldv2.onnx" 
    
    # For YOLOv8, usually the SDK can infer these, but setting them is safer:
    # obj_param.custom_onnx_input_size = 640 

    # This call is where the optimization (ONNX -> TensorRT) happens
    status = zed.enable_object_detection(obj_param)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to enable Object Detection: {status}")
        zed.close()
        return

    # 4. Main Loop
    objects = sl.Objects()
    image_left = sl.Mat()
    obj_runtime_params = sl.ObjectDetectionRuntimeParameters()
    obj_runtime_params.detection_confidence_threshold = 40 # Set your confidence here

    print("Setup complete. Starting loop...")
    try:
        while True:
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                # Retrieve the image (ZED handles the BGR conversion internally for its AI)
                zed.retrieve_image(image_left, sl.VIEW.LEFT)
                frame = image_left.get_data() # This is for display only

                # Retrieve the objects (The SDK ran the YOLO model for you!)
                zed.retrieve_objects(objects, obj_runtime_params)

                for obj in objects.object_list:
                    # 3D Position
                    pos = obj.position 
                    # 2D Bounding Box (Top-Left point)
                    x1, y1 = int(obj.bounding_box_2d[0][0]), int(obj.bounding_box_2d[0][1])
                    
                    # Print info
                    print(f"ID: {obj.id} | Class: {obj.raw_label} | Dist: {pos[2]:.2f}m")

                    # Draw on frame
                    color = (0, 255, 0)
                    cv2.putText(frame, f"ID {obj.id}: {pos[2]:.2f}m", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                cv2.imshow("Native ZED-YOLO", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        zed.disable_object_detection()
        zed.disable_positional_tracking()
        zed.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()