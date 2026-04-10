"""Helpers for rendering local instructional KPI videos."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Iterable, List, Tuple
from urllib import request
from urllib.error import HTTPError, URLError
from xml.sax.saxutils import escape

from lms_engine.domain.models import VideoScenePlan


CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1280
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
BACKGROUND_COLORS = ["#f7f1e8", "#efe7dc", "#f3eadf", "#f1ebe1", "#efe1cf", "#f6efe6"]
ACCENT_COLORS = ["#be5a2f", "#1f6f68", "#8f3f1f", "#1d4d4f", "#b86a3d", "#356d64"]
TEXT_COLOR = "#1f1b17"
MUTED_TEXT_COLOR = "#695e54"


def slugify(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in value).strip("_")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_command(args: List[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def audio_duration_seconds(audio_path: Path, narration_text: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if output and output != "N/A":
        return max(float(output), 1.0)
    estimated_seconds = max(len(narration_text.split()) / 2.8, 1.0)
    return round(estimated_seconds, 2)


def render_voiceover(text: str, output_path: Path, voice_name: str = "Samantha") -> None:
    run_command(
        [
            "say",
            "-v",
            voice_name,
            "-o",
            str(output_path),
            text,
        ]
    )


def render_elevenlabs_voiceover(
    text: str,
    output_path: Path,
    api_key: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    base_url: str = "https://api.elevenlabs.io",
) -> None:
    payload = {
        "text": text,
        "model_id": model_id,
    }
    req = request.Request(
        "{0}/v1/text-to-speech/{1}".format(base_url.rstrip("/"), voice_id),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            output_path.write_bytes(response.read())
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ValueError("ElevenLabs voice request failed: {0}".format(body or exc.reason)) from exc
    except URLError as exc:
        raise ValueError("ElevenLabs voice request failed: {0}".format(exc.reason)) from exc

def render_openai_voiceover(
    text: str,
    output_path: Path,
    api_key: str,
    model: str = "gpt-4o-mini-tts",
    voice: str = "marin",
    instructions: str = "",
    base_url: str = "https://api.openai.com/v1",
) -> None:
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
    }
    if instructions:
        payload["instructions"] = instructions
    req = request.Request(
        "{0}/audio/speech".format(base_url.rstrip("/")),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer {0}".format(api_key),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            output_path.write_bytes(response.read())
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ValueError("OpenAI voice request failed: {0}".format(body or exc.reason)) from exc
    except URLError as exc:
        raise ValueError("OpenAI voice request failed: {0}".format(exc.reason)) from exc
def render_voice_track(
    text: str,
    output_path: Path,
    voice_provider: str = "system",
    voice_name: str = "Samantha",
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "",
    elevenlabs_model_id: str = "eleven_multilingual_v2",
    openai_api_key: str = "",
    openai_tts_model: str = "gpt-4o-mini-tts",
    openai_tts_voice: str = "marin",
    openai_tts_instructions: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
) -> None:
    if voice_provider == "elevenlabs":
        if not elevenlabs_api_key:
            raise ValueError("ElevenLabs voice is selected but ELEVENLABS_API_KEY is missing")
        if not elevenlabs_voice_id:
            raise ValueError("ElevenLabs voice is selected but ELEVENLABS_VOICE_ID is missing")
        render_elevenlabs_voiceover(
            text=text,
            output_path=output_path,
            api_key=elevenlabs_api_key,
            voice_id=elevenlabs_voice_id,
            model_id=elevenlabs_model_id,
        )
        return
    if voice_provider == "openai":
        if not openai_api_key:
            raise ValueError("OpenAI voice is selected but OPENAI_API_KEY is missing")
        render_openai_voiceover(
            text=text,
            output_path=output_path,
            api_key=openai_api_key,
            model=openai_tts_model,
            voice=openai_tts_voice,
            instructions=openai_tts_instructions,
            base_url=openai_base_url,
        )
        return
    render_voiceover(text, output_path, voice_name=voice_name)


def wrap_svg_text(value: str, width: int, max_lines: int) -> List[str]:
    lines = textwrap.wrap(value.strip(), width=width) or [""]
    if len(lines) <= max_lines:
        return lines
    visible = lines[: max_lines - 1]
    remainder = " ".join(lines[max_lines - 1 :]).strip()
    visible.append(textwrap.shorten(remainder, width=width, placeholder="..."))
    return visible


def infer_scene_context(scene: VideoScenePlan) -> Tuple[str, str]:
    pattern = re.compile(r"^(?P<kpi>.+?) for (?P<role>.+?)\. Scene \d+:", re.DOTALL)
    match = pattern.search(scene.narration)
    if match:
        return match.group("role").strip(), match.group("kpi").strip()
    return "Store Leader", "KPI Focus"


def narration_body(scene: VideoScenePlan) -> str:
    marker = "Scene {0}: {1}.".format(scene.scene_number, scene.title)
    if marker in scene.narration:
        return scene.narration.split(marker, 1)[1].strip()
    sentences = [part.strip() for part in scene.narration.split(".") if part.strip()]
    if len(sentences) > 2:
        return ". ".join(sentences[2:]).strip() + "."
    return scene.narration.strip()


def svg_lines(lines: List[str], x: int, y: int, font_size: int, line_height: int, color: str, weight: str = "400") -> str:
    content = []
    for index, line in enumerate(lines):
        content.append(
            '<text x="{x}" y="{y}" font-size="{font_size}" font-weight="{weight}" '
            'fill="{color}" font-family="Georgia">{text}</text>'.format(
                x=x,
                y=y + (index * line_height),
                font_size=font_size,
                weight=weight,
                color=color,
                text=escape(line),
            )
        )
    return "\n".join(content)


def build_scene_svg(scene: VideoScenePlan, role_name: str, kpi_name: str, scene_index: int) -> str:
    background = BACKGROUND_COLORS[scene_index % len(BACKGROUND_COLORS)]
    accent = ACCENT_COLORS[scene_index % len(ACCENT_COLORS)]
    body_lines = wrap_svg_text(narration_body(scene), width=43, max_lines=5)
    subtitle_lines = wrap_svg_text(scene.narration, width=58, max_lines=3)
    cue_lines = wrap_svg_text(scene.visual_direction, width=24, max_lines=4)
    kpi_badge = "".join(word[0] for word in kpi_name.split() if word[:1]).upper()[:4] or "KPI"

    return """<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}">
  <rect width="{canvas_width}" height="{canvas_height}" fill="{background}"/>
  <rect x="40" y="40" width="1200" height="640" rx="30" fill="#ffffff" fill-opacity="0.90"/>
  <rect x="40" y="40" width="18" height="640" fill="{accent}"/>
  <rect x="92" y="96" width="128" height="42" rx="21" fill="{accent}" fill-opacity="0.14"/>
  <text x="120" y="124" font-size="24" font-weight="700" fill="{accent}" font-family="Georgia">KPI Studio</text>
  <text x="92" y="186" font-size="54" font-weight="700" fill="{text_color}" font-family="Georgia">{title}</text>
  <g aria-label="icon badge">
    <circle cx="994" cy="130" r="54" fill="{accent}" fill-opacity="0.14"/>
    <circle cx="994" cy="130" r="42" fill="{accent}" fill-opacity="0.22"/>
    <text x="959" y="142" font-size="28" font-weight="700" fill="{accent}" font-family="Georgia">{kpi_badge}</text>
  </g>
  <rect x="1056" y="88" width="132" height="42" rx="21" fill="{accent}" fill-opacity="0.12"/>
  <text x="1090" y="116" font-size="23" font-weight="700" fill="{accent}" font-family="Georgia">V{scene_number}</text>
  <rect x="820" y="164" width="340" height="54" rx="18" fill="{accent}" fill-opacity="0.10"/>
  <text x="848" y="198" font-size="25" font-weight="700" fill="{accent}" font-family="Georgia">{kpi_name}</text>
  <rect x="92" y="232" width="656" height="214" rx="22" fill="{background}"/>
  <rect x="780" y="232" width="380" height="214" rx="22" fill="{accent}" fill-opacity="0.08"/>
  <text x="92" y="224" font-size="22" font-weight="700" fill="{muted_text}" font-family="Georgia">Instructional focus</text>
  {body_copy}
  <text x="808" y="274" font-size="24" font-weight="700" fill="{accent}" font-family="Georgia">Scene cues</text>
  {cue_copy}
  <rect x="92" y="476" width="1068" height="128" rx="24" fill="{accent}" fill-opacity="0.10"/>
  <text x="124" y="522" font-size="24" font-weight="700" fill="{accent}" font-family="Georgia">Role: {role_name}</text>
  <text x="124" y="558" font-size="24" font-weight="700" fill="{muted_text}" font-family="Georgia">Target length: {duration}s instructional scene</text>
  <g id="subtitle">
    <rect x="92" y="618" width="1068" height="86" rx="20" fill="#1f1b17" fill-opacity="0.94"/>
    <text x="124" y="650" font-size="18" font-weight="700" fill="#f6efe6" font-family="Georgia">subtitle</text>
    {subtitle_copy}
  </g>
  <g aria-label="icon badge cluster">
    <rect x="842" y="310" width="28" height="70" rx="8" fill="{accent}" fill-opacity="0.55"/>
    <rect x="886" y="284" width="28" height="96" rx="8" fill="{accent}" fill-opacity="0.72"/>
    <rect x="930" y="254" width="28" height="126" rx="8" fill="{accent}"/>
    <circle cx="1032" cy="294" r="18" fill="{accent}" fill-opacity="0.28"/>
    <path d="M1016 294 L1028 306 L1052 278" fill="none" stroke="{accent}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
""".format(
        canvas_width=CANVAS_WIDTH,
        canvas_height=CANVAS_HEIGHT,
        background=background,
        accent=accent,
        text_color=TEXT_COLOR,
        muted_text=MUTED_TEXT_COLOR,
        title=escape(scene.title),
        kpi_badge=escape(kpi_badge),
        scene_number=scene.scene_number,
        kpi_name=escape(kpi_name),
        role_name=escape(role_name),
        duration=scene.duration_seconds,
        body_copy=svg_lines(body_lines, 124, 286, 30, 42, TEXT_COLOR, "400"),
        cue_copy=svg_lines(cue_lines, 808, 320, 24, 34, MUTED_TEXT_COLOR, "400"),
        subtitle_copy=svg_lines(subtitle_lines, 124, 680, 24, 28, "#f6efe6", "400"),
    )


def render_scene_card(scene: VideoScenePlan, output_dir: Path, scene_index: int) -> Path:
    role_name, kpi_name = infer_scene_context(scene)
    svg_path = output_dir / "scene_{0:02d}.svg".format(scene.scene_number)
    svg_path.write_text(build_scene_svg(scene, role_name, kpi_name, scene_index), encoding="utf-8")
    run_command(["qlmanage", "-t", "-s", str(FRAME_WIDTH), "-o", str(output_dir), str(svg_path)])
    png_path = output_dir / "{0}.png".format(svg_path.name)
    if not png_path.exists():
        raise FileNotFoundError("Quick Look did not produce a PNG preview for {0}".format(svg_path.name))
    return png_path


def render_scene_clip(
    scene: VideoScenePlan,
    output_dir: Path,
    scene_index: int,
    voice_provider: str = "system",
    voice_name: str = "Samantha",
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "",
    elevenlabs_model_id: str = "eleven_multilingual_v2",
    openai_api_key: str = "",
    openai_tts_model: str = "gpt-4o-mini-tts",
    openai_tts_voice: str = "marin",
    openai_tts_instructions: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
) -> Path:
    audio_extension = (
        "mp3"
        if (
            (voice_provider == "elevenlabs" and elevenlabs_api_key and elevenlabs_voice_id)
            or (voice_provider == "openai" and openai_api_key)
        )
        else "aiff"
    )
    audio_path = output_dir / "scene_{0:02d}.{1}".format(scene.scene_number, audio_extension)
    output_path = output_dir / "scene_{0:02d}.mp4".format(scene.scene_number)

    render_voice_track(
        scene.narration,
        audio_path,
        voice_provider=voice_provider,
        voice_name=voice_name,
        elevenlabs_api_key=elevenlabs_api_key,
        elevenlabs_voice_id=elevenlabs_voice_id,
        elevenlabs_model_id=elevenlabs_model_id,
        openai_api_key=openai_api_key,
        openai_tts_model=openai_tts_model,
        openai_tts_voice=openai_tts_voice,
        openai_tts_instructions=openai_tts_instructions,
        openai_base_url=openai_base_url,
    )
    duration = audio_duration_seconds(audio_path, scene.narration) + 0.5
    card_path = render_scene_card(scene, output_dir, scene_index)

    run_command(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(card_path),
            "-i",
            str(audio_path),
            "-filter:v",
            "crop={0}:{1}:0:0,scale={0}:{1},format=yuv420p".format(FRAME_WIDTH, FRAME_HEIGHT),
            "-t",
            "{0:.2f}".format(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
    )
    return output_path


def write_concat_file(scene_paths: Iterable[Path], concat_path: Path) -> None:
    lines = []
    for path in scene_paths:
        resolved = str(path.resolve()).replace("'", "'\\''")
        lines.append("file '{0}'".format(resolved))
    concat_path.write_text("\n".join(lines), encoding="utf-8")


def stitch_scene_clips(scene_paths: Iterable[Path], output_dir: Path) -> Path:
    concat_path = output_dir / "scenes.txt"
    final_path = output_dir / "final_video.mp4"
    write_concat_file(scene_paths, concat_path)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(final_path),
        ]
    )
    return final_path


def export_final_audio_track(final_video_path: Path, output_dir: Path) -> Path:
    audio_path = output_dir / "final_voiceover.m4a"
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(final_video_path),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(audio_path),
        ]
    )
    return audio_path


def render_mock_video_bundle(scene_plan: List[VideoScenePlan], output_dir: Path) -> Tuple[List[Path], Path]:
    scene_paths: List[Path] = []
    for scene in scene_plan:
        scene_path = output_dir / "scene_{0:02d}.mp4".format(scene.scene_number)
        scene_path.write_bytes(
            "mock local video for {0}".format(scene.title).encode("utf-8")
        )
        scene_paths.append(scene_path)

    final_path = output_dir / "final_video.mp4"
    final_path.write_bytes(b"mock final instructional video")
    return scene_paths, final_path
