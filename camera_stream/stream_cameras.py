
import sys
import socket
import json
import threading
import time
import gi
from typing import Dict, Any, List, Optional

# Require GStreamer 1.0 components
try:
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtsp', '1.0')
    gi.require_version('GstRtspServer', '1.0')
except ValueError as e:
    print(f"Error: {e}")
    print("Please ensure you have installed gstreamer1.0 and gir1.2-gst-rtsp-server-1.0")
    sys.exit(1)

from gi.repository import Gst, GstRtsp, GstRtspServer, GLib


class CameraStatusBroadcaster:
    def __init__(self, broadcast_port=5000, broadcast_interval=2.0):
        self.broadcast_port = broadcast_port
        self.broadcast_interval = broadcast_interval
        self.streams: List[Dict[str, Any]] = []
        self.server_ip = self._get_local_ip()
        self.rtsp_port = "8555"
        self.running = False
        self.thread = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def set_streams(self, streams: List[Dict[str, Any]], rtsp_port: str):
        self.streams = streams
        self.rtsp_port = rtsp_port

    def set_cameras(self, cameras, rtsp_port):
        if isinstance(cameras, dict):
            self.streams = [
                {
                    "route": route,
                    "device": device_path,
                    "profile": "default",
                    "codec": "H264",
                }
                for route, device_path in cameras.items()
            ]
        else:
            self.streams = cameras
        self.rtsp_port = rtsp_port

    def get_status_message(self):
        camera_list = []
        for stream in self.streams:
            route = stream.get("route")
            device_path = stream.get("device")
            rtsp_url = f"rtsp://{self.server_ip}:{self.rtsp_port}{route}"

            profile = stream.get("profile")
            width = stream.get("width")
            height = stream.get("height")
            fps = stream.get("fps")
            bitrate_kbps = stream.get("bitrate_kbps")
            codec = stream.get("codec", "H264")

            details = []
            if profile:
                details.append(str(profile))
            if width and height:
                details.append(f"{width}x{height}")
            if fps:
                details.append(f"{fps}fps")
            if bitrate_kbps:
                details.append(f"{bitrate_kbps}kbps")
            if codec:
                details.append(str(codec))

            label = f"{route}"
            if details:
                label = f"{route} [{', '.join(details)}]"

            camera_list.append({
                "route": route,
                "device": device_path,
                "rtsp_url": rtsp_url,
                "status": "active",
                "label": label,
                "profile": profile,
                "codec": codec,
                "width": width,
                "height": height,
                "fps": fps,
                "bitrate_kbps": bitrate_kbps,
            })

        message = {
            "type": "camera_status",
            "server_ip": self.server_ip,
            "rtsp_port": self.rtsp_port,
            "cameras": camera_list,
            "timestamp": time.time(),
            "formats": sorted(list({c.get("codec", "H264") for c in camera_list})),
            "resolutions": sorted(list({f"{c.get('width')}x{c.get('height')}" for c in camera_list if c.get('width') and c.get('height')}))
        }
        return json.dumps(message)

    def _broadcast_loop(self):
        while self.running:
            try:
                message = self.get_status_message()
                # Broadcast to all addresses on the network
                self.sock.sendto(
                    message.encode('utf-8'),
                    ('<broadcast>', self.broadcast_port)
                )
                print(
                    f"[Broadcast] Sent camera status to port {self.broadcast_port}")
            except Exception as e:
                print(f"[Broadcast] Error: {e}")

            time.sleep(self.broadcast_interval)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(
                target=self._broadcast_loop, daemon=True)
            self.thread.start()
            print(f"[Broadcast] Started on port {self.broadcast_port}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.sock.close()
        print("[Broadcast] Stopped")


def _profile_route(base_route: str, profile_name: str, codec: str, default_profile: str) -> str:
    codec_lower = codec.lower()
    if profile_name == default_profile:
        return base_route

    if profile_name.lower().startswith(codec_lower + "_"):
        return f"{base_route}_{profile_name}"

    return f"{base_route}_{codec_lower}_{profile_name}"


def build_h264_pipeline(
    device_path: str,
    width: int,
    height: int,
    fps: int,
    bitrate_kbps: int,
    key_int_max: int = 15,
    speed_preset: str = "ultrafast",
) -> str:
    source = f"v4l2src device={device_path}"
    caps = f"video/x-raw,width={width},height={height},framerate={fps}/1"
    processing = "videoconvert"
    encoder_options = (
        "x264enc "
        "tune=zerolatency "
        f"speed-preset={speed_preset} "
        f"bitrate={bitrate_kbps} "
        f"key-int-max={key_int_max}"
    )
    payloader = "rtph264pay name=pay0 pt=96 config-interval=1"
    return f"( {source} ! {caps} ! {processing} ! {encoder_options} ! {payloader} )"


def build_h265_pipeline(
    device_path: str,
    width: int,
    height: int,
    fps: int,
    bitrate_kbps: int,
    key_int_max: int = 15,
    speed_preset: str = "ultrafast",
    tune: str = "zerolatency",
) -> str:
    source = f"v4l2src device={device_path}"
    caps = f"video/x-raw,width={width},height={height},framerate={fps}/1"
    processing = "videoconvert"
    encoder_options = (
        "x265enc "
        f"speed-preset={speed_preset} "
        f"bitrate={bitrate_kbps} "
        f"key-int-max={key_int_max} "
        f"option-string=\"tune={tune}\""
    )
    payloader = "rtph265pay name=pay0 pt=96 config-interval=1"
    return f"( {source} ! {caps} ! {processing} ! {encoder_options} ! {payloader} )"


def build_mjpeg_pipeline(
    device_path: str,
    width: int,
    height: int,
    fps: int,
    quality: int = 85,
) -> str:
    source = f"v4l2src device={device_path}"
    caps = f"image/jpeg,width={width},height={height},framerate={fps}/1"
    payloader = "rtpjpegpay name=pay0 pt=26"
    return f"( {source} ! {caps} ! {payloader} )"


def build_vp8_pipeline(
    device_path: str,
    width: int,
    height: int,
    fps: int,
    bitrate_kbps: int,
    deadline: int = 1,
    cpu_used: int = 8,
) -> str:
    source = f"v4l2src device={device_path}"
    caps = f"video/x-raw,width={width},height={height},framerate={fps}/1"
    processing = "videoconvert"
    # vp8enc bitrate is in bits/sec.
    encoder = f"vp8enc deadline={deadline} cpu-used={cpu_used} target-bitrate={int(bitrate_kbps) * 1000}"
    payloader = "rtpvp8pay name=pay0 pt=96"
    return f"( {source} ! {caps} ! {processing} ! {encoder} ! {payloader} )"


def build_vp9_pipeline(
    device_path: str,
    width: int,
    height: int,
    fps: int,
    bitrate_kbps: int,
    deadline: int = 1,
    cpu_used: int = 8,
) -> str:
    source = f"v4l2src device={device_path}"
    caps = f"video/x-raw,width={width},height={height},framerate={fps}/1"
    processing = "videoconvert"
    encoder = f"vp9enc deadline={deadline} cpu-used={cpu_used} target-bitrate={int(bitrate_kbps) * 1000}"
    payloader = "rtpvp9pay name=pay0 pt=96"
    return f"( {source} ! {caps} ! {processing} ! {encoder} ! {payloader} )"


def build_pipeline_from_profile(device_path: str, profile: Dict[str, Any]) -> str:
    codec = str(profile.get("codec", "H264")).upper()
    width = int(profile["width"])
    height = int(profile["height"])
    fps = int(profile["fps"])

    if codec in {"H264", "AVC"}:
        return build_h264_pipeline(
            device_path=device_path,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=int(profile.get("bitrate_kbps", 2000)),
            key_int_max=int(profile.get("key_int_max", 15)),
            speed_preset=str(profile.get("speed_preset", "ultrafast")),
        )
    if codec in {"H265", "HEVC"}:
        return build_h265_pipeline(
            device_path=device_path,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=int(profile.get("bitrate_kbps", 1500)),
            key_int_max=int(profile.get("key_int_max", 15)),
            speed_preset=str(profile.get("speed_preset", "ultrafast")),
            tune=str(profile.get("tune", "zerolatency")),
        )
    if codec in {"MJPEG", "JPEG"}:
        return build_mjpeg_pipeline(
            device_path=device_path,
            width=width,
            height=height,
            fps=fps,
            quality=int(profile.get("quality", 85)),
        )
    if codec == "VP8":
        return build_vp8_pipeline(
            device_path=device_path,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=int(profile.get("bitrate_kbps", 800)),
            deadline=int(profile.get("deadline", 1)),
            cpu_used=int(profile.get("cpu_used", 8)),
        )
    if codec == "VP9":
        return build_vp9_pipeline(
            device_path=device_path,
            width=width,
            height=height,
            fps=fps,
            bitrate_kbps=int(profile.get("bitrate_kbps", 800)),
            deadline=int(profile.get("deadline", 1)),
            cpu_used=int(profile.get("cpu_used", 8)),
        )

    raise ValueError(f"Unsupported codec: {codec}")


class MultiCamRTSPServer:

    def __init__(
        self,
        port: str = "8555",
        cameras: Optional[Dict[str, Any]] = None,
        broadcast_port: int = 5000,
        profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        default_profile: str = "med",
    ):
        if cameras is None:
            cameras = {}

        if profiles is None:
            profiles = {}

        self.port = port
        self.cameras = cameras
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(port)

        self.broadcaster = CameraStatusBroadcaster(
            broadcast_port=broadcast_port)
        streams_for_broadcast: List[Dict[str, Any]] = []

        mounts = self.server.get_mount_points()

        for base_route, cam_value in cameras.items():
            if isinstance(cam_value, str):
                device_path = cam_value
            elif isinstance(cam_value, dict):
                device_path = cam_value.get("device")
            else:
                raise ValueError(
                    f"Invalid camera config for {base_route}: {cam_value!r}")

            if not profiles:
                profile = {"width": 640, "height": 480,
                           "fps": 30, "bitrate_kbps": 2000}
                route = base_route
                pipeline_str = build_pipeline_from_profile(
                    device_path, {**profile, "codec": "H264"})

                factory = GstRtspServer.RTSPMediaFactory()
                factory.set_protocols(GstRtsp.RTSPLowerTrans.UDP)
                factory.set_launch(pipeline_str)
                factory.set_shared(False)
                mounts.add_factory(route, factory)
                streams_for_broadcast.append(
                    {
                        "route": route,
                        "device": device_path,
                        "profile": "default",
                        "codec": "H264",
                        **profile,
                    }
                )
                print(f"Configuring {route} -> {device_path} (default)")
                continue

            for profile_name, profile in profiles.items():
                codec = str(profile.get("codec", "H264")).upper()
                route = _profile_route(
                    base_route, profile_name, codec, default_profile)
                pipeline_str = build_pipeline_from_profile(
                    device_path, profile)

                factory = GstRtspServer.RTSPMediaFactory()
                factory.set_protocols(GstRtsp.RTSPLowerTrans.UDP)
                factory.set_launch(pipeline_str)
                factory.set_shared(False)
                mounts.add_factory(route, factory)
                streams_for_broadcast.append(
                    {
                        "route": route,
                        "device": device_path,
                        "profile": profile_name,
                        "codec": str(profile.get("codec", "H264")).upper(),
                        **profile,
                    }
                )
                print(f"Configuring {route} -> {device_path} ({profile_name})")

        print(f"\n[RTSP Server] Running on port {port}")
        for stream in streams_for_broadcast:
            route = stream.get("route")
            print(
                f"  Stream available at: rtsp://{self.broadcaster.server_ip}:{port}{route}")

        self.server.attach(None)

        self.broadcaster.set_streams(streams_for_broadcast, port)
        self.broadcaster.start()

    def stop(self):
        """Stop the RTSP server and broadcaster"""
        self.broadcaster.stop()


if __name__ == '__main__':
    Gst.init(None)

    camera_config = {
        "/cam1": "/dev/video0",
    }

    # Stream URLs will be: /cam1 (default), /cam1_h264_low, /cam1_h264_high, /cam1_mjpeg_low, etc.
    # eta diye check kora jay -  v4l2-ctl --device=/dev/video0 --list-formats-ext
    STREAM_PROFILES = {
        # Lowest bandwidth / lowest decode cost
        "low": {"codec": "H264",  "width": 960, "height": 540, "fps": 15, "bitrate_kbps": 400},
        # Default balance
        "med": {"codec": "H264", "width": 640, "height": 480, "fps": 30, "bitrate_kbps": 1200},
        # Higher quality (more bandwidth)
        "high": {"codec": "H264", "width": 1280, "height": 720, "fps": 30, "bitrate_kbps": 2500},

        # MJPEG profiles (uses camera's native MJPEG - no re-encode, lower CPU)
        "mjpeg_low": {"codec": "MJPEG", "width": 960, "height": 540, "fps": 30, "quality": 75},
        "mjpeg_med": {"codec": "MJPEG", "width": 640, "height": 480, "fps": 30, "quality": 85},
        "mjpeg_high": {"codec": "MJPEG", "width": 1280, "height": 720, "fps": 30, "quality": 90},


    }

    DEFAULT_PROFILE = "med"

    BROADCAST_PORT = 5000
    RTSP_PORT = "8555"
    server = MultiCamRTSPServer(
        port=RTSP_PORT,
        cameras=camera_config,
        broadcast_port=BROADCAST_PORT,
        profiles=STREAM_PROFILES,
        default_profile=DEFAULT_PROFILE,
    )

    loop = GLib.MainLoop()
    try:
        print("\nPress Ctrl+C to stop the server...")
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()