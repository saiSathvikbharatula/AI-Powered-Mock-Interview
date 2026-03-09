from __future__ import annotations
from dataclasses import dataclass
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional
from collections import deque

import numpy as np
import av
import mediapipe as mp
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration


# --------------------------------------------------
# PATCH SHUTDOWN BUG (CRITICAL)
# --------------------------------------------------
try:
    from streamlit_webrtc import shutdown as _shutdown
    _orig_stop = _shutdown.SessionShutdownObserver.stop

    def _safe_stop(self):
        t = getattr(self, "_polling_thread", None)
        if t is None:
            return
        return _orig_stop(self)

    _shutdown.SessionShutdownObserver.stop = _safe_stop
except Exception:
    pass


def rtc_config():
    return RTCConfiguration(
        iceServers=[{"urls": "stun:stun.l.google.com:19302"}]
    )


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


def _ensure_model(local_path: Path):
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if not local_path.exists():
        urllib.request.urlretrieve(MODEL_URL, str(local_path))
    return local_path


@dataclass
class FaceScoreBuffer:
    lock = threading.Lock()
    frames_total: int = 0
    frames_face_found: int = 0
    cx = deque(maxlen=30)
    cy = deque(maxlen=30)
    motion = deque(maxlen=30)
    last_center: Optional[tuple] = None
    conf_sum: float = 0.0
    nerv_sum: float = 0.0
    scored_frames: int = 0

    def update_no_face(self):
        with self.lock:
            self.frames_total += 1

    def update_with_landmarks(self, lms):
        xs = np.array([p.x for p in lms])
        ys = np.array([p.y for p in lms])
        cx = float(xs.mean())
        cy = float(ys.mean())

        with self.lock:
            self.frames_total += 1
            self.frames_face_found += 1

            motion = 0 if self.last_center is None else abs(cx - self.last_center[0]) + abs(cy - self.last_center[1])
            self.last_center = (cx, cy)

            self.cx.append(cx)
            self.cy.append(cy)
            self.motion.append(motion)

            jitter = np.std(self.cx) + np.std(self.cy)
            nervous = min(100, jitter * 800)
            confidence = max(0, 100 - nervous)

            self.conf_sum += confidence
            self.nerv_sum += nervous
            self.scored_frames += 1

    def snapshot(self):
        with self.lock:
            return {
                "visual_confidence": round(self.conf_sum / self.scored_frames, 2) if self.scored_frames else 0,
                "visual_nervousness": round(self.nerv_sum / self.scored_frames, 2) if self.scored_frames else 0,
                "frames_total": self.frames_total,
                "frames_scored": self.scored_frames,
                "face_found_ratio": round(self.frames_face_found / self.frames_total, 3) if self.frames_total else 0,
            }


class MediaPipeFaceLandmarkerProcessor:
    def __init__(self, face_buffer: FaceScoreBuffer):
        self.face_buffer = face_buffer
        self.t0 = time.time()

        model_path = _ensure_model(Path(".cache/mediapipe/face_landmarker.task"))

        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(
            mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=1,
            )
        )

    def recv(self, frame: av.VideoFrame):
        img = frame.to_ndarray(format="rgb24")
        ts = int((time.time() - self.t0) * 1000)
        result = self.landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=img), ts
        )

        if result.face_landmarks:
            self.face_buffer.update_with_landmarks(result.face_landmarks[0])
        else:
            self.face_buffer.update_no_face()

        return frame


def start_realtime_capture(*, key, face_buffer, playing, frame_rate=15, show_camera=True):
    return webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=rtc_config(),
        desired_playing_state=playing,
        media_stream_constraints={
            "video": {"frameRate": {"ideal": frame_rate}},
            "audio": False,
        },
        video_processor_factory=lambda: MediaPipeFaceLandmarkerProcessor(face_buffer),
        async_processing=True,
    )
