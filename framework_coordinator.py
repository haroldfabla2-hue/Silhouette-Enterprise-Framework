#!/usr/bin/env python3
"""
Silhouette Enterprise Framework V4.0 - Coordinador Principal
Inicia y coordina todos los servicios del framework
"""

import asyncio
import logging
import os
import signal
import sys
import json
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Service:
    """Definición de un servicio del framework"""
    name: str
    module_path: str
    port: int
    process: asyncio.subprocess.Process = None
    status: str = "stopped"

class SilhouetteCoordinator:
    """Coordinador principal del framework"""
    
    def __init__(self):
        self.logger = logging.getLogger("silhouette.coordinator")
        self.services: List[Service] = []
        self.teams: List[Service] = []
        self.is_running = False
        
        # Configurar servicios principales
        self.setup_services()
        
        # Configurar señales para cierre graceful
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def setup_services(self):
        """Configura los servicios del framework"""
        
        # Servicios principales
        self.services = [
            Service("mcp_server", "/workspace/mcp_server/main.py", 8080),
            Service("api_gateway", "/workspace/api_gateway/main.py", 3000),
            Service("planner", "/workspace/planner/main.py", 8090),
        ]
        
        # Equipos (78 equipos en puertos 8000-8077)
        for i in range(1, 79):
            self.teams.append(Service(
                name=f"team_{i}",
                module_path=f"/workspace/team_{i}/main.py" if i <= 22 else f"/workspace/{self.get_team_name(i)}/main.py",
                port=8000 + i - 1
            ))
    
    def get_team_name(self, team_id: int) -> str:
        """Obtiene el nombre del equipo basado en su ID"""
        team_names = [
            'business_development_team', 'cloud_services_team', 'communications_team',
            'customer_service_team', 'design_creative_team', 'finance_team', 'hr_team',
            'legal_team', 'machine_learning_ai_team', 'manufacturing_team', 'marketing_team',
            'notifications_communication_team', 'product_management_team', 'quality_assurance_team',
            'research_team', 'risk_management_team', 'sales_team', 'security_team', 'strategy_team',
            'supply_chain_team', 'support_team', 'testing_team'
        ]
        
        # Equipos regenerados
        generated_teams = [
            'data_analytics_team', 'data_science_team', 'database_team', 'devops_team',
            'document_management_team', 'email_marketing_team', 'engineering_team',
            'event_management_team', 'fleet_management_team', 'gaming_team',
            'healthcare_team', 'hospitality_team', 'hr_analytics_team', 'industrial_team',
            'insurance_team', 'inventory_management_team', 'iot_team', 'knowledge_management_team',
            'legal_tech_team', 'logistics_team', 'maintenance_team', 'media_production_team',
            'mobile_app_team', 'network_infrastructure_team', 'operational_efficiency_team',
            'paralegal_team', 'performance_optimization_team', 'personal_assistant_team',
            'predictive_analytics_team', 'procurement_team', 'project_management_team',
            'real_estate_team', 'recruitment_team', 'regulatory_compliance_team',
            'renewable_energy_team', 'retail_team', 'revenue_optimization_team',
            'software_development_team', 'solar_energy_team', 'sustainability_team',
            'system_administration_team', 'technical_support_team', 'telecommunications_team',
            'training_team', 'transportation_team', 'travel_team', 'user_experience_team',
            'venture_capital_team', 'video_production_team', 'virtual_assistant_team',
            'voice_assistant_team', 'waste_management_team', 'web_development_team',
            'wholesale_team', 'cloud_computing_team'
        ]
        
        if team_id <= 22:
            return team_names[team_id - 1]
        else:
            return generated_teams[team_id - 23]
    
    async def start_service(self, service: Service) -> bool:
        """Inicia un servicio específico"""
        try:
            self.logger.info(f"Iniciando servicio: {service.name} en puerto {service.port}")
            
            # Cambiar al directorio del servicio
            os.chdir(os.path.dirname(service.module_path))
            
            # Iniciar proceso
            process = await asyncio.create_subprocess_exec(
                sys.executable, service.module_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            service.process = process
            service.status = "running"
            
            self.logger.info(f"Servicio iniciado: {service.name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando {service.name}: {e}")
            service.status = "error"
            return False
    
    async def stop_service(self, service: Service) -> bool:
        """Detiene un servicio específico"""
        try:
            if service.process and service.process.stdin.is_closing():
                service.process.terminate()
                await service.process.wait()
                service.status = "stopped"
                self.logger.info(f"Servicio detenido: {service.name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deteniendo {service.name}: {e}")
            return False
    
    async def start_framework(self):
        """Inicia todo el framework"""
        self.is_running = True
        
        try:
            self.logger.info("🚀 Iniciando Silhouette Enterprise Framework V4.0")
            self.logger.info("=" * 60)
            
            # Iniciar servicios principales primero
            self.logger.info("🔧 Iniciando servicios principales...")
            for service in self.services:
                await self.start_service(service)
                await asyncio.sleep(2)  # Delay entre servicios
            
            # Dar tiempo a los servicios principales para inicializar
            await asyncio.sleep(5)
            
            # Iniciar equipos
            self.logger.info(f"👥 Iniciando {len(self.teams)} equipos...")
            startup_tasks = []
            
            for team in self.teams:
                startup_tasks.append(self.start_service(team))
            
            # Ejecutar inicio de equipos con limitación de concurrencia
            batch_size = 10
            for i in range(0, len(startup_tasks), batch_size):
                batch = startup_tasks[i:i + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                await asyncio.sleep(1)  # Delay entre batches
            
            self.logger.info("✅ Framework iniciado exitosamente")
            self.logger.info("=" * 60)
            self.logger.info(f"🎯 MCP Server: Puerto 8080")
            self.logger.info(f"🎯 API Gateway: Puerto 3000")
            self.logger.info(f"🎯 Planner: Puerto 8090")
            self.logger.info(f"🎯 Equipos: Puertos 8000-8077 ({len(self.teams)} equipos)")
            self.logger.info("=" * 60)
            
            # Mantener el framework ejecutándose
            await self.monitor_framework()
            
        except Exception as e:
            self.logger.error(f"Error iniciando framework: {e}")
            await self.shutdown()
    
    async def monitor_framework(self):
        """Monitorea el estado del framework"""
        try:
            while self.is_running:
                # Verificar estado de servicios principales
                for service in self.services:
                    if service.process and service.process.stdin.is_closing():
                        self.logger.warning(f"Servicio {service.name} se detuvo inesperadamente")
                        await self.start_service(service)
                
                # Verificar estado de equipos (cada 30 segundos)
                await asyncio.sleep(30)
                
                # Log de estado cada 5 minutos
                running_services = len([s for s in self.services if s.status == "running"])
                running_teams = len([t for t in self.teams if t.status == "running"])
                
                self.logger.info(f"Estado: {running_services}/{len(self.services)} servicios activos, "
                               f"{running_teams}/{len(self.teams)} equipos activos")
                
        except Exception as e:
            self.logger.error(f"Error en monitoreo: {e}")
    
    async def get_framework_status(self) -> Dict[str, Any]:
        """Estado completo del framework"""
        return {
            "framework": "Silhouette Enterprise Framework V4.0",
            "status": "operational" if self.is_running else "stopped",
            "version": "4.0.0",
            "services": {
                "total": len(self.services),
                "running": len([s for s in self.services if s.status == "running"]),
                "stopped": len([s for s in self.services if s.status == "stopped"])
            },
            "teams": {
                "total": len(self.teams),
                "running": len([t for t in self.teams if t.status == "running"]),
                "stopped": len([t for t in self.teams if t.status == "stopped"])
            },
            "ports": {
                "mcp_server": 8080,
                "api_gateway": 3000,
                "planner": 8090,
                "teams_range": "8000-8077"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_shutdown(self, signum, frame):
        """Maneja señales de cierre"""
        self.logger.info(f"Señal de cierre recibida: {signum}")
        asyncio.create_task(self.shutdown())
    
    async def shutdown(self):
        """Cierre graceful del framework"""
        self.is_running = False
        self.logger.info("🛑 Cerrando Silhouette Enterprise Framework...")
        
        try:
            # Detener equipos primero
            for team in self.teams:
                if team.status == "running":
                    await self.stop_service(team)
            
            # Detener servicios principales
            for service in self.services:
                if service.status == "running":
                    await self.stop_service(service)
            
            self.logger.info("✅ Framework cerrado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error durante el cierre: {e}")
        finally:
            sys.exit(0)

async def main():
    """Función principal del coordinador"""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/workspace/framework.log')
        ]
    )
    
    try:
        coordinator = SilhouetteCoordinator()
        await coordinator.start_framework()
    except KeyboardInterrupt:
        logging.info("Interrupción del usuario")
    except Exception as e:
        logging.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())