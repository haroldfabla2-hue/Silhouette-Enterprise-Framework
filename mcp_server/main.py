#!/usr/bin/env python3
"""
MCP Server - Silhouette Enterprise Framework
Maneja las conexiones NCP y herramientas del sistema
"""

import asyncio
import logging
import json
import aiohttp
from aiohttp import web, WSMsgType
from typing import Dict, List, Any
from datetime import datetime

class MCPServer:
    """Servidor MCP principal del framework"""
    
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("silhouette.mcp_server")
        self.connected_clients = set()
        self.tools_registry = {}
        
    async def handle_ws_connection(self, request):
        """Maneja conexiones WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        client_id = f"client_{len(self.connected_clients)}"
        self.connected_clients.add(ws)
        self.logger.info(f"Cliente conectado: {client_id}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(ws, msg.data, client_id)
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f"Error WebSocket: {ws.exception()}")
                    
        except Exception as e:
            self.logger.error(f"Error en conexión WebSocket: {e}")
        finally:
            self.connected_clients.discard(ws)
            self.logger.info(f"Cliente desconectado: {client_id}")
            
        return ws
    
    async def handle_message(self, ws, message, client_id):
        """Procesa mensajes del cliente"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "tool_call":
                result = await self.execute_tool(data)
                await ws.send_str(json.dumps(result))
            elif message_type == "status_request":
                result = await self.get_system_status()
                await ws.send_str(json.dumps(result))
            else:
                await ws.send_str(json.dumps({
                    "error": "Tipo de mensaje no reconocido",
                    "received_type": message_type
                }))
                
        except Exception as e:
            await ws.send_str(json.dumps({
                "error": f"Error procesando mensaje: {str(e)}"
            }))
    
    async def execute_tool(self, data):
        """Ejecuta herramientas NCP"""
        try:
            tool_name = data.get("tool")
            parameters = data.get("parameters", {})
            
            if tool_name in self.tools_registry:
                tool_func = self.tools_registry[tool_name]
                result = await tool_func(parameters)
                return {
                    "success": True,
                    "tool": tool_name,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Herramienta {tool_name} no encontrada",
                    "available_tools": list(self.tools_registry.keys())
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error ejecutando herramienta: {str(e)}"
            }
    
    async def get_system_status(self):
        """Obtiene el estado del sistema"""
        return {
            "status": "operational",
            "connected_clients": len(self.connected_clients),
            "registered_tools": len(self.tools_registry),
            "mcp_server": "active",
            "timestamp": datetime.now().isoformat()
        }
    
    def register_tool(self, tool_name, tool_function):
        """Registra una nueva herramienta"""
        self.tools_registry[tool_name] = tool_function
        self.logger.info(f"Herramienta registrada: {tool_name}")
    
    async def start_server(self):
        """Inicia el servidor MCP"""
        app = web.Application()
        app.router.add_get('/ws', self.handle_ws_connection)
        app.router.add_get('/status', self.handle_status_request)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"MCP Server iniciado en {self.host}:{self.port}")
        
        # Mantener el servidor ejecutándose
        while True:
            await asyncio.sleep(1)
    
    async def handle_status_request(self, request):
        """Maneja solicitudes de estado HTTP"""
        return web.json_response(await self.get_system_status())

async def main():
    """Función principal del MCP Server"""
    logging.basicConfig(level=logging.INFO)
    
    # Cargar herramientas NCP
    try:
        import sys
        sys.path.append('/workspace/external_api')
        from data_sources.client import get_data_sources_client
        mcp_tools_client = get_data_sources_client()
        
        # Registrar herramientas
        server = MCPServer()
        # Aquí se registrarían las herramientas NCP específicas
        
        await server.start_server()
        
    except Exception as e:
        logging.error(f"Error iniciando MCP Server: {e}")

if __name__ == "__main__":
    asyncio.run(main())