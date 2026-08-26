"""WebSocket 进度推送测试（此前为零覆盖的盲区）。

覆盖：未认证拒绝、越权拒绝（IDOR）、合法连接确认帧、
广播转发与死连接清理。

说明：Starlette 测试传输层不回传服务端自定义关闭码
（客户端侧一律表现为 code=1000 的 WebSocketDisconnect），
因此这里断言"被拒且未收到任何帧"；4401/4403 由真实
浏览器/WS 客户端在 close 帧中接收。
"""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.models import Analysis


def _make_analysis(db_session, make_dataset, owner_id=None) -> Analysis:
    ds = make_dataset(owner_id=owner_id)
    analysis = Analysis(dataset_id=ds.id, question="q", status="running", owner_id=owner_id)
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def _expect_rejected(client: TestClient, url: str) -> None:
    """断言连接被服务端立即关闭且未收到任何业务帧。"""
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(url) as ws:
            ws.receive_json()
            # 若收到帧则视为未拒绝
            pytest.fail("不应收到任何消息")


class TestWSAuth:
    def test_missing_token_rejected(self, client):
        _expect_rejected(client, "/ws/analysis/1?token=")

    def test_garbage_token_rejected(self, client):
        _expect_rejected(client, "/ws/analysis/1?token=not-a-jwt")

    def test_forbidden_for_other_user(self, client, make_user, make_dataset, db_session):
        """用户 B 不能订阅用户 A 的分析进度（IDOR 回归）。"""
        from app.security import create_access_token

        owner = make_user(email="ws-owner@example.com")
        stranger = make_user(email="ws-stranger@example.com")
        analysis = _make_analysis(db_session, make_dataset, owner_id=owner.id)

        stranger_token = create_access_token(subject=stranger.id)
        _expect_rejected(client, f"/ws/analysis/{analysis.id}?token={stranger_token}")

    def test_connected_frame_and_clean_close(self, client, auth_token, make_dataset, db_session):
        """合法连接收到确认帧；断开后订阅被清理。"""
        from app.ws.manager import manager

        token, user = auth_token
        analysis = _make_analysis(db_session, make_dataset, owner_id=user.id)

        url = f"/ws/analysis/{analysis.id}?token={token}"
        with client.websocket_connect(url) as ws:
            first = ws.receive_json()
            assert first["stage"] == "connected"
            assert first["analysis_id"] == analysis.id

        # 断开后订阅表应清理干净
        assert analysis.id not in manager._subscriptions


class TestConnectionManagerBroadcast:
    async def test_broadcast_and_dead_socket_pruned(self):
        from app.ws.manager import ConnectionManager

        class FakeWS:
            def __init__(self, fail: bool = False) -> None:
                self.fail = fail
                self.sent: list[dict] = []

            async def send_json(self, message: dict) -> None:
                if self.fail:
                    raise RuntimeError("dead socket")
                self.sent.append(message)

        mgr = ConnectionManager()
        good, bad = FakeWS(), FakeWS(fail=True)
        mgr._subscriptions[42] = {good, bad}

        await mgr.send_to_subscribers(42, {"stage": "succeeded"})

        assert good.sent == [{"stage": "succeeded"}]
        # 死连接已被移除，活连接保留
        assert 42 in mgr._subscriptions
        assert good in mgr._subscriptions[42]
        assert bad not in mgr._subscriptions[42]

    async def test_disconnect_is_idempotent(self):
        from app.ws.manager import ConnectionManager

        class FakeWS:
            pass

        mgr = ConnectionManager()
        ws = FakeWS()
        mgr._subscriptions[7] = {ws}
        mgr.disconnect(ws, 7)
        mgr.disconnect(ws, 7)  # 重复调用不应抛错
        assert 7 not in mgr._subscriptions
