"""Application bootstrap for wiring the LMS MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lms_engine.application.kpi_studio import KPIStudioService
from lms_engine.ai import AIContentGenerator
from lms_engine.application.mvp import LMSEngineService
from lms_engine.elevenlabs import ElevenLabsSpeechClient
from lms_engine.integrations.video import build_video_gateway
from lms_engine.storage import AssetStore, JsonStore


@dataclass
class AppContainer:
    engine: LMSEngineService
    kpi_studio: KPIStudioService


def build_container() -> AppContainer:
    data_path = Path(__file__).resolve().parent / "data" / "state.json"
    asset_path = Path(__file__).resolve().parent / "data" / "assets"
    store = JsonStore(str(data_path))
    asset_store = AssetStore(str(asset_path))
    engine = LMSEngineService(
        store=store,
        asset_store=asset_store,
        generator=AIContentGenerator(),
        speech_client=ElevenLabsSpeechClient(),
    )
    kpi_studio = KPIStudioService(video_gateway=build_video_gateway())
    return AppContainer(engine=engine, kpi_studio=kpi_studio)
