#!/usr/bin/env python3
"""
Planner - Silhouette Enterprise Framework
Coordinador principal y planificador de tareas del sistema
"""

import asyncio
import logging
import json
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """Definición de una tarea en el sistema"""
    id: str
    type: str
    description: str
    priority: int
    assigned_team: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters: Dict[str, Any] = None
    dependencies: List[str] = None
    result: Any = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.parameters is None:
            self.parameters = {}
        if self.dependencies is None:
            self.dependencies = []

class Planner:
    """Planificador principal del framework"""
    
    def __init__(self, gateway_url="http://localhost:3000"):
        self.gateway_url = gateway_url
        self.logger = logging.getLogger("silhouette.planner")
        self.tasks: Dict[str, Task] = {}
        self.teams_load: Dict[str, int] = {}
        self.task_queue: List[str] = []
        self.is_running = False
        
        # Especialización por tipo de tarea
        self.task_specializations = {
            "data_analysis": "data_analytics_team",
            "data_science": "data_science_team", 
            "development": "software_development_team",
            "devops": "devops_team",
            "mobile": "mobile_app_team",
            "web": "web_development_team",
            "cloud": "cloud_computing_team",
            "database": "database_team",
            "security": "security_team",
            "marketing": "marketing_team",
            "finance": "finance_team",
            "hr": "hr_team",
            "legal": "legal_team",
            "logistics": "logistics_team",
            "maintenance": "maintenance_team",
            "healthcare": "healthcare_team",
            "retail": "retail_team",
            "real_estate": "real_estate_team",
            "manufacturing": "manufacturing_team"
        }
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Crea una nueva tarea"""
        try:
            task_id = task_data.get("id", f"task_{len(self.tasks)}")
            
            task = Task(
                id=task_id,
                type=task_data.get("type", "general"),
                description=task_data.get("description", "Sin descripción"),
                priority=task_data.get("priority", 5),
                parameters=task_data.get("parameters", {})
            )
            
            # Determinar equipo asignado automáticamente
            task.assigned_team = self.determine_team_for_task(task)
            
            self.tasks[task_id] = task
            self.task_queue.append(task_id)
            
            self.logger.info(f"Tarea creada: {task_id} -> {task.assigned_team}")
            
            # Intentar procesar inmediatamente si no hay dependencias
            if not task.dependencies:
                await self.process_task(task_id)
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error creando tarea: {e}")
            raise
    
    def determine_team_for_task(self, task: Task) -> str:
        """Determina qué equipo debe procesar la tarea"""
        task_type = task.type.lower()
        
        # Buscar especialización directa
        for key, team in self.task_specializations.items():
            if key in task_type:
                return team
        
        # Si no hay especialización específica, usar equipo por defecto
        return "support_team"
    
    async def process_task(self, task_id: str) -> bool:
        """Procesa una tarea específica"""
        try:
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PENDING:
                self.logger.warning(f"Tarea {task_id} no está pendiente")
                return False
            
            # Verificar dependencias
            if not self.check_dependencies(task_id):
                self.logger.info(f"Tarea {task_id} esperando dependencias")
                return False
            
            # Actualizar estado
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()
            
            # Enviar tarea al equipo correspondiente
            success = await self.send_to_team(task)
            
            if success:
                self.logger.info(f"Tarea {task_id} enviada a {task.assigned_team}")
            else:
                task.status = TaskStatus.FAILED
                task.error = "Equipo no disponible"
                self.logger.error(f"Error enviando tarea {task_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error procesando tarea {task_id}: {e}")
            return False
    
    def check_dependencies(self, task_id: str) -> bool:
        """Verifica que todas las dependencias estén completadas"""
        task = self.tasks[task_id]
        
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                continue
                
            dep_task = self.tasks[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def send_to_team(self, task: Task) -> bool:
        """Envía tarea al equipo asignado"""
        try:
            # Determinar puerto del equipo
            team_name = task.assigned_team
            if "_team" in team_name:
                base_team_name = team_name.replace("_team", "")
                # Mapeo de nombres a IDs para demostración
                team_mapping = {
                    "business_development": 1, "cloud_services": 2, "communications": 3,
                    "customer_service": 4, "design_creative": 5, "finance": 6,
                    "hr": 7, "legal": 8, "machine_learning_ai": 9,
                    "manufacturing": 10, "marketing": 11, "notifications_communication": 12,
                    "product_management": 13, "quality_assurance": 14, "research": 15,
                    "risk_management": 16, "sales": 17, "security": 18,
                    "strategy": 19, "supply_chain": 20, "support": 21, "testing": 22
                }
                
                team_id = team_mapping.get(base_team_name, 21)  # Default to support team
            else:
                team_id = 21  # Default support team
            
            team_port = 8000 + team_id - 1
            
            # Enviar tarea vía API Gateway
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/api/teams/{team_id}/process"
                
                payload = {
                    "task_id": task.id,
                    "task_type": task.type,
                    "description": task.description,
                    "parameters": task.parameters,
                    "priority": task.priority
                }
                
                async with session.post(url, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.now()
                        return True
                    else:
                        self.logger.error(f"Equipo respondió con error {resp.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error enviando a equipo: {e}")
            return False
    
    async def complete_task(self, task_id: str, result: Any):
        """Marca una tarea como completada"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            
            self.logger.info(f"Tarea {task_id} completada")
            
            # Verificar si hay tareas que esperaban esta dependencia
            await self.check_dependent_tasks(task_id)
    
    async def check_dependent_tasks(self, completed_task_id: str):
        """Verifica tareas que dependían de la tarea completada"""
        for task_id, task in self.tasks.items():
            if (task.status == TaskStatus.PENDING and 
                completed_task_id in task.dependencies):
                if self.check_dependencies(task_id):
                    await self.process_task(task_id)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Estado completo del planificador"""
        status_counts = {
            TaskStatus.PENDING: 0,
            TaskStatus.IN_PROGRESS: 0, 
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.CANCELLED: 0
        }
        
        for task in self.tasks.values():
            status_counts[task.status] += 1
        
        return {
            "service": "Silhouette Planner",
            "status": "operational" if self.is_running else "stopped",
            "tasks_total": len(self.tasks),
            "tasks_by_status": status_counts,
            "queue_size": len(self.task_queue),
            "teams_registered": len(self.teams_load),
            "timestamp": datetime.now().isoformat()
        }
    
    async def start_planner(self):
        """Inicia el servicio del planificador"""
        self.is_running = True
        self.logger.info("Planificador iniciado")
        
        # Mantener ejecutándose y procesar cola de tareas
        while self.is_running:
            try:
                # Procesar tareas pendientes
                if self.task_queue:
                    task_id = self.task_queue.pop(0)
                    await self.process_task(task_id)
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error en bucle del planificador: {e}")
                await asyncio.sleep(5)

async def main():
    """Función principal del Planner"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        planner = Planner()
        
        # Crear tarea de prueba
        await planner.create_task({
            "id": "test_task_001",
            "type": "data_analysis",
            "description": "Análisis de datos de prueba",
            "priority": 3,
            "parameters": {"source": "test_data"}
        })
        
        # Iniciar planificador
        await planner.start_planner()
        
    except Exception as e:
        logging.error(f"Error iniciando Planner: {e}")

if __name__ == "__main__":
    asyncio.run(main())