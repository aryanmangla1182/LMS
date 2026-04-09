"""Application bootstrap for wiring the LMS MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lms_engine.ai import AIContentGenerator
from lms_engine.application.mvp import LMSEngineService
from lms_engine.storage import AssetStore, JsonStore


@dataclass
class AppContainer:
    engine: LMSEngineService


def build_container() -> AppContainer:
    data_path = Path(__file__).resolve().parent / "data" / "state.json"
    asset_path = Path(__file__).resolve().parent / "data" / "assets"
    store = JsonStore(str(data_path))
    asset_store = AssetStore(str(asset_path))
    engine = LMSEngineService(store=store, asset_store=asset_store, generator=AIContentGenerator())
    return AppContainer(engine=engine)
