import json
import socket
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_api_key, encrypt_api_key
from app.models.mcp_server import McpServer
from app.models.mcp_tool import McpTool
from app.schema.mcp import McpServerPayload, McpServerUpdatePayload


def _is_ip_private_or_local(hostname: str) -> bool:
    """
    基础 SSRF 防护：阻止 localhost/私网/链路本地地址。

    注意：该防护是 best-effort，无法完全防御 DNS rebinding。
    """
    import ipaddress

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except Exception:
        # DNS 解析失败时不直接放行，交由上层连接失败处理
        return True

    for family, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True

        # 常见云元数据地址
        if str(ip) == "169.254.169.254":
            return True

        # IPv6 特殊
        if str(ip) in {"::1"}:
            return True

    return False


def _validate_mcp_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("仅支持 http/https 的 MCP Server URL")
    if not parsed.hostname:
        raise ValueError("MCP Server URL 缺少 hostname")
    if _is_ip_private_or_local(parsed.hostname):
        raise ValueError("出于安全考虑，禁止连接本地/内网/保留地址的 MCP Server")


class McpService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_servers(self, user_id: int) -> list[McpServer]:
        stmt = select(McpServer).where(McpServer.user_id == user_id).order_by(
            McpServer.create_time.desc()
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_server(self, user_id: int, server_id: int) -> McpServer | None:
        stmt = select(McpServer).where(McpServer.id == server_id, McpServer.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_server(self, user_id: int, payload: McpServerPayload) -> McpServer:
        _validate_mcp_http_url(payload.url)

        headers_encrypted = None
        if payload.headers:
            headers_json = json.dumps(payload.headers, ensure_ascii=False)
            headers_encrypted = encrypt_api_key(headers_json)

        server = McpServer(
            user_id=user_id,
            name=payload.name,
            url=payload.url,
            headers_encrypted=headers_encrypted,
            status=payload.status,
        )
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def update_server(
        self, user_id: int, server_id: int, payload: McpServerUpdatePayload
    ) -> McpServer | None:
        server = await self.get_server(user_id, server_id)
        if not server:
            return None

        if payload.url is not None:
            _validate_mcp_http_url(payload.url)
            server.url = payload.url
        if payload.name is not None:
            server.name = payload.name
        if payload.status is not None:
            server.status = payload.status
        if payload.headers is not None:
            headers_json = json.dumps(payload.headers, ensure_ascii=False)
            server.headers_encrypted = encrypt_api_key(headers_json)

        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def delete_server(self, user_id: int, server_id: int) -> bool:
        server = await self.get_server(user_id, server_id)
        if not server:
            return False

        # 删除 server 下的 tools
        await self.db.execute(delete(McpTool).where(McpTool.server_id == server_id))
        await self.db.delete(server)
        await self.db.commit()
        return True

    async def _get_headers(self, server: McpServer) -> dict[str, str] | None:
        if not server.headers_encrypted:
            return None
        try:
            headers_json = decrypt_api_key(server.headers_encrypted)
            headers = json.loads(headers_json)
            if isinstance(headers, dict):
                return {str(k): str(v) for k, v in headers.items()}
        except Exception as exc:
            logger.warning(f"Failed to decrypt MCP headers: {exc}")
        return None

    async def sync_tools(self, user_id: int, server_id: int) -> int:
        server = await self.get_server(user_id, server_id)
        if not server:
            raise ValueError("MCP Server 不存在或无权限")
        if server.status != 1:
            raise ValueError("MCP Server 已禁用")

        headers = await self._get_headers(server)

        try:
            from fastmcp import Client
            from fastmcp.client.transports import StreamableHttpTransport
        except Exception as exc:
            raise RuntimeError("缺少 fastmcp 依赖，请先安装 fastmcp") from exc

        transport = StreamableHttpTransport(server.url, headers=headers)
        async with Client(transport=transport, timeout=30.0) as client:
            tools = await client.list_tools()

        tool_names = {t.name for t in tools}

        # 标记已不存在的工具为禁用
        existing_stmt = select(McpTool).where(McpTool.server_id == server_id)
        existing_tools = list((await self.db.execute(existing_stmt)).scalars().all())
        for existing in existing_tools:
            if existing.name not in tool_names:
                existing.enabled = False

        # upsert tools
        upserted = 0
        for tool in tools:
            name = tool.name
            description = getattr(tool, "description", None)
            input_schema = getattr(tool, "inputSchema", None)

            stmt = select(McpTool).where(McpTool.server_id == server_id, McpTool.name == name)
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.description = description
                existing.input_schema = input_schema
                # 不自动重置 enabled，保留用户选择；若之前因缺失禁用，可重新启用
                if existing.enabled is False:
                    existing.enabled = True
            else:
                self.db.add(
                    McpTool(
                        server_id=server_id,
                        name=name,
                        description=description,
                        input_schema=input_schema,
                        enabled=True,
                    )
                )
            upserted += 1

        await self.db.commit()
        return upserted

