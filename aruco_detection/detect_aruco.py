import cv2 as cv
import numpy as np
import cv2.aruco as aruco


def detect_aruco(frame, 
                camera_matrix,
                dist_coeffs,
                aruco_dict_type=cv.aruco.DICT_4X4_250,
                marker_length=0.05):
    
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    aruco_dict = aruco.getPredefinedDictionary(aruco_dict_type)
    parameters = aruco.DetectorParameters()

    #marker dection
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)


    detections = []
    if ids is not None:
        rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(corners, marker_length, camera_matrix, dist_coeffs)

        #draw markers
        cv.aruco.drawDetectedMarkers(frame, corners, ids)

        for i in range(len(ids)):
            tvec = tvecs[i][0]
            rvec = rvecs[i][0]
            x, y, z = tvec[0], tvec[1], tvec[2]
            

            detections.append({
                "id": int(ids[i][0]),
                "position": (x, y, z),
                "rvec": rvec,
                "tvec": tvec
            })

            cv.drawFrameAxes(
                frame, camera_matrix, dist_coeffs, rvec, tvec, 0.03
            )
    
    return detections, frame



cap = cv.VideoCapture(0)
camera_matrix = None
dist_coeffs = None

if cap.isOpened() == False:
    print("Could not open camera")
    exit()



# ---------- FAKE CAMERA PARAMETERS ----------
ret, frame = cap.read()
if not ret:
    print("Failed to grab frame")
    exit()
h, w = frame.shape[:2]

fx = w            # good first guess
fy = w            # assume square pixels
cx = w / 2
cy = h / 2

camera_matrix = np.array([
    [fx, 0,  cx],
    [0,  fy, cy],
    [0,   0,  1]
], dtype=np.float32)

dist_coeffs = np.zeros((5, 1), dtype=np.float32)
# -------------------------------------------

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    detections, frame = detect_aruco(frame, camera_matrix, dist_coeffs)
    for d in detections:
        print(f"ID {d['id']} → x={d['position'][0]:.2f}, "
        f"y={d['position'][1]:.2f}, z={d['position'][2]:.2f}")

    cv.imshow("Camera Feed", frame)
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv.destroyAllWindows()