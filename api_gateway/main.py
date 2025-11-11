#!/usr/bin/env python3
"""
API Gateway - Silhouette Enterprise Framework
Maneja el enrutamiento y balanceo de carga de equipos
"""

import asyncio
import logging
import json
import aiohttp
from aiohttp import web
from typing import Dict, List, Any
from datetime import datetime
import aiohttp_cors

class APIGateway:
    """Gateway principal para el framework"""
    
    def __init__(self, host="0.0.0.0", port=3000):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("silhouette.api_gateway")
        self.teams_registry = {}
        self.load_balancer = RoundRobinBalancer()
        
    async def route_request(self, request):
        """Enruta peticiones a los equipos apropiados"""
        try:
            path = request.path
            method = request.method
            
            if path.startswith('/api/teams/'):
                team_id = path.split('/api/teams/')[1].split('/')[0]
                return await self.route_to_team(team_id, request)
            elif path == '/api/status':
                return await self.get_gateway_status(request)
            elif path == '/api/teams':
                return await self.list_teams(request)
            else:
                return web.json_response({
                    "error": "Endpoint no encontrado",
                    "path": path
                }, status=404)
                
        except Exception as e:
            self.logger.error(f"Error en enrutamiento: {e}")
            return web.json_response({
                "error": "Error interno del gateway",
                "details": str(e)
            }, status=500)
    
    async def route_to_team(self, team_id, request):
        """Enruta petición a un equipo específico"""
        try:
            # Determinar puerto del equipo (equipo 1 = puerto 8000, etc.)
            team_port = 8000 + int(team_id) - 1
            
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:{team_port}/process"
                
                # Crear payload para el equipo
                if request.method == 'POST':
                    data = await request.json()
                else:
                    data = {"method": request.method, "path": request.path}
                
                async with session.post(url, json=data) as resp:
                    result = await resp.json()
                    return web.json_response(result, status=resp.status)
                    
        except Exception as e:
            self.logger.error(f"Error enrutando a equipo {team_id}: {e}")
            return web.json_response({
                "error": f"Equipo {team_id} no disponible",
                "details": str(e)
            }, status=503)
    
    async def get_gateway_status(self, request):
        """Estado del API Gateway"""
        return web.json_response({
            "service": "Silhouette API Gateway",
            "status": "operational",
            "teams_count": len(self.teams_registry),
            "timestamp": datetime.now().isoformat(),
            "endpoints": [
                "/api/status",
                "/api/teams",
                "/api/teams/{id}/process"
            ]
        })
    
    async def list_teams(self, request):
        """Lista todos los equipos disponibles"""
        teams = []
        for team_id in range(1, 79):  # 78 equipos
            teams.append({
                "id": team_id,
                "port": 8000 + team_id - 1,
                "status": await self.check_team_status(team_id)
            })
        
        return web.json_response({
            "teams": teams,
            "total": len(teams),
            "timestamp": datetime.now().isoformat()
        })
    
    async def check_team_status(self, team_id):
        """Verifica el estado de un equipo"""
        try:
            team_port = 8000 + team_id - 1
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{team_port}/status", timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('status', 'unknown')
                    else:
                        return 'unavailable'
                        
        except Exception:
            return 'offline'
    
    async def load_balance_request(self, team_ids, request):
        """Balanceador de carga para múltiples equipos"""
        # Seleccionar equipo con menor carga
        best_team = await self.load_balancer.select_team(team_ids)
        return await self.route_to_team(best_team, request)
    
    async def create_app(self):
        """Crea la aplicación aiohttp"""
        app = web.Application()
        
        # Configurar CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Agregar rutas
        app.router.add_route('*', '/api/*', self.route_request)
        
        # Aplicar CORS
        for route in list(app.router.routes()):
            cors.add(route)
        
        return app
    
    async def start_gateway(self):
        """Inicia el API Gateway"""
        app = await self.create_app()
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"API Gateway iniciado en {self.host}:{self.port}")
        
        # Mantener el gateway ejecutándose
        while True:
            await asyncio.sleep(1)

class RoundRobinBalancer:
    """Balanceador Round Robin simple"""
    
    def __init__(self):
        self.current_index = 0
    
    async def select_team(self, team_ids):
        """Selecciona un equipo usando Round Robin"""
        if not team_ids:
            return None
        
        selected = team_ids[self.current_index % len(team_ids)]
        self.current_index += 1
        return selected

async def main():
    """Función principal del API Gateway"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        gateway = APIGateway()
        await gateway.start_gateway()
    except Exception as e:
        logging.error(f"Error iniciando API Gateway: {e}")

if __name__ == "__main__":
    asyncio.run(main())