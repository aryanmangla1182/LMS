"""Video generation gateways for KPI studio workflows."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from base64 import b64encode
from pathlib import Path
from typing import Dict, List, Mapping, Optional
from urllib import request
from urllib.error import HTTPError, URLError

from lms_engine.domain.models import VideoScenePlan, VideoVersionStatus
from lms_engine.integrations.local_video_assets import (
    ensure_directory,
    export_final_audio_track,
    render_mock_video_bundle,
    render_scene_clip,
    stitch_scene_clips,
)


DEFAULT_ELEVENLABS_VOICE_ID = "siw1N9V8LmYeEWKyWBxv"


class VideoGenerationGateway(ABC):
    provider_name = "unknown"

    @abstractmethod
    def generate_scene_clips(self, scene_plan: List[VideoScenePlan]) -> Dict[str, object]:
        """Start or simulate clip generation for each scene."""

    @abstractmethod
    def refresh_scene_clips(self, scene_plan: List[VideoScenePlan], external_job_ids: List[str]) -> Dict[str, object]:
        """Refresh clip status for the scene plan."""


class DemoVideoGateway(VideoGenerationGateway):
    provider_name = "demo"

    def generate_scene_clips(self, scene_plan: List[VideoScenePlan]) -> Dict[str, object]:
        job_ids: List[str] = []
        for scene in scene_plan:
            scene.job_id = "demo_job_{0}".format(scene.scene_number)
            scene.clip_url = None
            scene.status = VideoVersionStatus.COMPLETED
            job_ids.append(scene.job_id)
        return {
            "status": VideoVersionStatus.COMPLETED,
            "progress": 100,
            "job_ids": job_ids,
            "video_url": "",
            "error": "",
        }

    def refresh_scene_clips(self, scene_plan: List[VideoScenePlan], external_job_ids: List[str]) -> Dict[str, object]:
        return {
            "status": VideoVersionStatus.COMPLETED,
            "progress": 100,
            "job_ids": external_job_ids,
            "video_url": "",
            "error": "",
        }


class LocalStoryboardVideoGateway(VideoGenerationGateway):
    provider_name = "local_storyboard"

    def __init__(
        self,
        output_root: str,
        render_mode: str = "render",
        voice_provider: str = "system",
        local_voice_name: str = "Samantha",
        elevenlabs_api_key: str = "",
        elevenlabs_voice_id: str = "",
        elevenlabs_model_id: str = "eleven_multilingual_v2",
        openai_api_key: str = "",
        openai_base_url: str = "https://api.openai.com/v1",
        openai_tts_model: str = "gpt-4o-mini-tts",
        openai_tts_voice: str = "marin",
        openai_tts_instructions: str = "",
    ) -> None:
        self.output_root = ensure_directory(Path(output_root))
        self.render_mode = render_mode
        self.voice_provider = voice_provider
        self.local_voice_name = local_voice_name
        self.elevenlabs_api_key = elevenlabs_api_key
        self.elevenlabs_voice_id = elevenlabs_voice_id
        self.elevenlabs_model_id = elevenlabs_model_id
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url
        self.openai_tts_model = openai_tts_model
        self.openai_tts_voice = openai_tts_voice
        self.openai_tts_instructions = openai_tts_instructions
        self.asset_paths: Dict[str, Path] = {}

    def generate_scene_clips(self, scene_plan: List[VideoScenePlan]) -> Dict[str, object]:
        bundle_dir = ensure_directory(self.output_root / "bundle_{0}".format(os.urandom(6).hex()))
        if self.render_mode == "mock":
            scene_paths, final_path = render_mock_video_bundle(scene_plan, bundle_dir)
        else:
            scene_paths = [
                render_scene_clip(
                    scene,
                    bundle_dir,
                    index,
                    voice_provider=self.voice_provider,
                    voice_name=self.local_voice_name,
                    elevenlabs_api_key=self.elevenlabs_api_key,
                    elevenlabs_voice_id=self.elevenlabs_voice_id,
                    elevenlabs_model_id=self.elevenlabs_model_id,
                    openai_api_key=self.openai_api_key,
                    openai_tts_model=self.openai_tts_model,
                    openai_tts_voice=self.openai_tts_voice,
                    openai_tts_instructions=self.openai_tts_instructions,
                    openai_base_url=self.openai_base_url,
                )
                for index, scene in enumerate(scene_plan)
            ]
            final_path = stitch_scene_clips(scene_paths, bundle_dir)
            export_final_audio_track(final_path, bundle_dir)

        job_ids: List[str] = []
        for scene, scene_path in zip(scene_plan, scene_paths):
            job_id = "local_scene_{0}".format(os.urandom(6).hex())
            self.asset_paths[job_id] = scene_path
            scene.job_id = job_id
            scene.clip_url = str(scene_path)
            scene.status = VideoVersionStatus.COMPLETED
            job_ids.append(job_id)

        final_asset_id = "local_video_{0}".format(os.urandom(6).hex())
        self.asset_paths[final_asset_id] = final_path
        return {
            "status": VideoVersionStatus.COMPLETED,
            "progress": 100,
            "job_ids": job_ids,
            "video_url": str(final_path),
            "video_asset_id": final_asset_id,
            "error": "",
        }

    def refresh_scene_clips(self, scene_plan: List[VideoScenePlan], external_job_ids: List[str]) -> Dict[str, object]:
        return {
            "status": VideoVersionStatus.COMPLETED,
            "progress": 100,
            "job_ids": external_job_ids,
            "video_url": "",
            "error": "",
        }

    def fetch_clip_bytes(self, job_id: str) -> tuple[str, bytes]:
        path = self.asset_paths.get(job_id)
        if path is None or not path.exists():
            raise ValueError("Local video asset not found: {0}".format(job_id))
        return "video/mp4", path.read_bytes()


class OpenAISoraVideoGateway(VideoGenerationGateway):
    provider_name = "openai_sora"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "sora-2",
        size: str = "1280x720",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.size = size

    def generate_scene_clips(self, scene_plan: List[VideoScenePlan]) -> Dict[str, object]:
        job_ids: List[str] = []
        overall_status = VideoVersionStatus.COMPLETED
        progress = 0

        for scene in scene_plan:
            payload = {
                "prompt": scene.sora_prompt,
                "model": self.model,
                "seconds": str(scene.duration_seconds),
                "size": self.size,
            }
            response = self._request_json("POST", "/videos", payload)
            scene.job_id = str(response["id"])
            scene.status = VideoVersionStatus(response.get("status", VideoVersionStatus.QUEUED.value))
            scene.clip_url = self._content_url(scene.job_id)
            job_ids.append(scene.job_id)
            progress += int(response.get("progress", 0))
            if scene.status != VideoVersionStatus.COMPLETED:
                overall_status = VideoVersionStatus.IN_PROGRESS

        return {
            "status": overall_status,
            "progress": int(progress / len(scene_plan)) if scene_plan else 0,
            "job_ids": job_ids,
            "video_url": "",
            "error": "",
        }

    def refresh_scene_clips(self, scene_plan: List[VideoScenePlan], external_job_ids: List[str]) -> Dict[str, object]:
        progress = 0
        overall_status = VideoVersionStatus.COMPLETED
        error_message = ""

        for scene, job_id in zip(scene_plan, external_job_ids):
            response = self._request_json("GET", "/videos/{0}".format(job_id))
            scene.status = VideoVersionStatus(response.get("status", VideoVersionStatus.QUEUED.value))
            scene.clip_url = self._content_url(job_id) if scene.status == VideoVersionStatus.COMPLETED else None
            progress += int(response.get("progress", 0))
            error = response.get("error") or {}
            scene.error_message = error.get("message", "")
            if scene.status == VideoVersionStatus.FAILED:
                overall_status = VideoVersionStatus.FAILED
                error_message = scene.error_message
            elif scene.status != VideoVersionStatus.COMPLETED and overall_status != VideoVersionStatus.FAILED:
                overall_status = VideoVersionStatus.IN_PROGRESS

        return {
            "status": overall_status,
            "progress": int(progress / len(scene_plan)) if scene_plan else 0,
            "job_ids": external_job_ids,
            "video_url": "",
            "error": error_message,
        }

    def fetch_clip_bytes(self, job_id: str) -> tuple[str, bytes]:
        response = self._request_bytes("GET", "/videos/{0}/content".format(job_id))
        return "video/mp4", response

    def _content_url(self, job_id: str) -> str:
        return "{0}/videos/{1}/content".format(self.base_url, job_id)

    def _request_json(self, method: str, path: str, payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": "Bearer {0}".format(self.api_key),
            "Content-Type": "application/json",
        }
        req = request.Request("{0}{1}".format(self.base_url, path), data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise ValueError("OpenAI video request failed: {0}".format(body or exc.reason)) from exc
        except URLError as exc:
            raise ValueError("OpenAI video request failed: {0}".format(exc.reason)) from exc

    def _request_bytes(self, method: str, path: str) -> bytes:
        headers = {"Authorization": "Bearer {0}".format(self.api_key)}
        req = request.Request("{0}{1}".format(self.base_url, path), headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=60) as response:
                return response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise ValueError("OpenAI video content request failed: {0}".format(body or exc.reason)) from exc
        except URLError as exc:
            raise ValueError("OpenAI video content request failed: {0}".format(exc.reason)) from exc


def load_local_env(env_path: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    path = Path(env_path)
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_video_gateway(
    env: Optional[Mapping[str, str]] = None,
    env_path: Optional[str] = None,
) -> VideoGenerationGateway:
    runtime_env = dict(env or os.environ)
    local_env = load_local_env(env_path or ".env.local")

    def read_setting(name: str, default: str = "") -> str:
        return str(runtime_env.get(name) or local_env.get(name) or default).strip()

    provider = read_setting("LMS_VIDEO_PROVIDER", "local")
    if provider == "demo":
        return DemoVideoGateway()

    if provider == "local":
        default_voice_provider = "openai" if read_setting("OPENAI_API_KEY") else "system"
        return LocalStoryboardVideoGateway(
            output_root=read_setting("LMS_VIDEO_OUTPUT_ROOT", ".generated_videos"),
            render_mode=read_setting("LMS_VIDEO_RENDER_MODE", "render"),
            voice_provider=read_setting("LMS_VOICE_PROVIDER", default_voice_provider),
            local_voice_name=read_setting("LOCAL_VOICE_NAME", "Samantha"),
            elevenlabs_api_key=read_setting("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=DEFAULT_ELEVENLABS_VOICE_ID,
            elevenlabs_model_id=read_setting("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            openai_api_key=read_setting("OPENAI_API_KEY"),
            openai_base_url=read_setting("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_tts_model=read_setting("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=read_setting("OPENAI_TTS_VOICE", "marin"),
            openai_tts_instructions=read_setting(
                "OPENAI_TTS_INSTRUCTIONS",
                "Speak clearly, warmly, and at a measured pace for frontline retail training in India. Pronounce KPI terms carefully.",
            ),
        )

    api_key = read_setting("OPENAI_API_KEY")
    if not api_key:
        return DemoVideoGateway()

    return OpenAISoraVideoGateway(
        api_key=api_key,
        base_url=read_setting("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=read_setting("OPENAI_VIDEO_MODEL", "sora-2"),
        size=read_setting("OPENAI_VIDEO_SIZE", "1280x720"),
    )


def build_demo_clip_data_uri(title: str) -> str:
    payload = json.dumps({"title": title}).encode("utf-8")
    return "data:application/json;base64,{0}".format(b64encode(payload).decode("ascii"))
