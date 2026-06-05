"""Sui seam: tools absent without config; calls error cleanly without config."""

from __future__ import annotations

import pytest

from suiswarm_agent.config.settings import SuiServiceSettings
from suiswarm_agent.core.exceptions import ConfigError
from suiswarm_agent.tools.registry import sui_tools
from suiswarm_agent.tools.sui.client import SuiServiceClient
from suiswarm_agent.tools.sui.service import SuiService


def test_sui_tools_absent_without_config(make_settings) -> None:
    assert sui_tools(make_settings()) == []


async def test_sui_call_raises_without_config(make_settings) -> None:
    service = SuiService(SuiServiceClient(make_settings(sui_service=SuiServiceSettings())))
    with pytest.raises(ConfigError):
        await service.call("GET", "/accounts/0x1/balances")


async def test_sui_write_blocked_when_allow_writes_false(make_settings) -> None:
    settings = make_settings(
        sui_service=SuiServiceSettings(base_url="http://nest:3000", allow_writes=False)
    )
    service = SuiService(SuiServiceClient(settings))
    with pytest.raises(ConfigError):
        await service.call("POST", "/tx", body={"kind": "transfer"})
