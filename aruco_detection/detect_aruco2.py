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