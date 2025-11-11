# 🚀 Silhouette Enterprise Framework V4.0

![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Node](https://img.shields.io/badge/node-%3E%3D16.0.0-brightgreen.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

Una plataforma enterprise de auto-scaling con modo dual (automático/manual) que permite gestionar tiers dinámicamente basándose en métricas de rendimiento en tiempo real.

## ✨ Características Principales

### 🎛️ Modo Dual de Operación
- **Modo Automático**: Escalado inteligente basado en métricas (tokens, requests, errors, response time)
- **Modo Manual**: Control total del tier con selección directa desde la interfaz
- **Transición fluida** entre modos sin interrumpir el servicio

### 📊 4-Tier Architecture
| Tier | Precio | Tokens | Equipos | Características |
|------|--------|--------|---------|----------------|
| **Free** | $0/mes | 10K | 5 | Auto-scaling básico, soporte comunidad |
| **PYME** | $250/mes | 100K | 25 | API completa, email support, webhooks |
| **Mediana** | $1,200/mes | 500K | 100 | Escalado predictivo, analytics avanzadas |
| **Enterprise** | $3,500/mes | 2M | 500 | Solución completa, soporte 24/7, white-label |

### 📈 Monitoreo en Tiempo Real
- **Dashboard integrado** con métricas live
- **Gráficos interactivos** usando Chart.js
- **Alertas automáticas** por umbrales críticos
- **Historial de escalado** con auditoría completa

### 🏗️ Arquitectura Técnica
- **Event Sourcing** con PostgreSQL
- **Caching inteligente** con Redis
- **Event-driven architecture**
- **Container orchestration** con Docker Compose
- **Load balancing** con Nginx

## 🛠️ Instalación Rápida

### Prerrequisitos
- Docker & Docker Compose
- Node.js 16+
- Git

### 1. Clonar el Repositorio
```bash
git clone https://github.com/haroldfabla2-hue/Silhouette-Enterprise-Framework.git
cd Silhouette-Enterprise-Framework
```

### 2. Configurar Variables de Entorno
```bash
cp .env.example .env
# Editar .env con tu configuración
```

### 3. Ejecutar con Docker Compose
```bash
docker-compose up -d
```

### 4. Acceder a las Interfaces
- **Dashboard**: http://localhost:8080
- **Config Manual**: http://localhost:8080/manual-tier-config.html
- **Métricas Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## 🚀 Uso

### Modo Automático (Recomendado)
```javascript
const controller = new AutoScaleFrameworkController();

// Activar modo automático
await controller.setScalingMode('auto');

// El sistema escalará automáticamente basado en:
// - 80% uso de tokens → Scale up
// - <30% uso sostenido → Scale down  
// - >5% error rate → Scale up
// - <1% error rate → Scale down
```

### Modo Manual
```javascript
// Cambiar a modo manual
await controller.setScalingMode('manual');

// Seleccionar tier específico
await controller.selectTierManually('pyme');

// Verificar estado actual
const status = controller.getActiveTier();
console.log(`Tier activo: ${status.tier}, Modo: ${status.mode}`);
```

### Actualizar Métricas
```javascript
// Simular métricas de uso
await controller.updateMetrics({
    tokensUsed: 85000,
    requestsCount: 1500,
    errorsCount: 15,
    responseTime: 2500
});
```

## 📊 Interfaces Web

### Dashboard Auto-Scale (`/dashboard-auto-scale.html`)
- Métricas en tiempo real
- Gráficos de uso de tokens
- Controles de modo (auto/manual)
- Historial de escalado
- Alertas del sistema

### Configuración Manual (`/manual-tier-config.html`)
- Selección visual de tiers
- Comparación detallada de características
- Modo toggle (auto/manual)
- Recomendaciones de tier

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │────│   API Gateway   │────│ AutoScale Controller│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │     Redis       │
                       │  (Event Store)  │    │    (Cache)      │
                       └─────────────────┘    └─────────────────┘
```

### Componentes Principales

1. **AutoScaleFrameworkController.cjs**
   - Controlador principal con lógica dual-mode
   - Gestión de tiers y métricas
   - Event sourcing y auditoría
   - Health checks y monitoring

2. **docker-compose.yml**
   - Orquestación completa de servicios
   - PostgreSQL + Redis + Nginx
   - Prometheus + Grafana monitoring
   - Elasticsearch + Kibana logging

3. **config/framework-config.json**
   - Configuración de tiers y límites
   - Thresholds de escalado
   - Capacidades por tier
   - Parámetros de monitoreo

## ⚙️ Configuración

### Variables de Entorno Principales

```bash
# Framework
FRAMEWORK_MODE=auto                    # auto | manual
SCALING_INTERVAL=30                    # segundos entre checks

# Database
POSTGRES_DB=silhouette_db
POSTGRES_USER=silhouette
POSTGRES_PASSWORD=silhouette2024

# Redis
REDIS_HOST=localhost
REDIS_PASSWORD=silhouette2024

# Tiers (override defaults)
FREE_TIER_MAX_TOKENS=10000
PYME_TIER_MAX_TOKENS=100000
MEDIANA_TIER_MAX_TOKENS=500000
ENTERPRISE_TIER_MAX_TOKENS=2000000
```

### Thresholds de Escalado
```json
{
  "scaling": {
    "thresholds": {
      "tokenUsage": { "scaleUp": 80, "scaleDown": 30 },
      "errorRate": { "scaleUp": 5, "scaleDown": 1 },
      "responseTime": { "scaleUp": 5000, "scaleDown": 1000 }
    },
    "cooldown": { "scaleUp": 300, "scaleDown": 900 }
  }
}
```

## 📈 Monitoreo y Alertas

### Métricas Clave
- **Uso de Tokens**: Porcentaje del límite actual
- **Solicitudes**: Count por día/hora
- **Tasa de Errores**: Porcentaje de requests fallidas
- **Tiempo de Respuesta**: Promedio en ms

### Alertas Automáticas
- **Warning**: 80% uso tokens, 3% error rate
- **Critical**: 90% uso tokens, 5% error rate
- **Scaling**: Eventos de escalado automático

### Dashboards
- **Grafana**: Métricas históricas y alertas
- **Kibana**: Logs y debugging
- **Prometheus**: Métricas raw y queries

## 🔒 Seguridad

### Autenticación y Autorización
- JWT tokens para API
- Rate limiting configurable
- Secure headers y CORS
- Database connection pooling

### Monitoreo de Seguridad
- Audit logs de todos los eventos
- Failed login attempts
- API abuse detection
- Health check endpoints

## 🧪 Testing

### Ejecutar Tests
```bash
# Unit tests
npm test

# Integration tests  
npm run test:integration

# E2E tests
npm run test:e2e

# Coverage report
npm run test:coverage
```

### Scenarios de Demo
```bash
# Ejecutar demo completo
node demo-manual-mode.cjs

# Casos de prueba:
# 1. Cambio de modo auto → manual
# 2. Selección manual de tier
# 3. Simulación de alto tráfico
# 4. Escalado automático
# 5. Rollback a tier menor
```

## 📚 API Reference

### Endpoints Principales

```javascript
GET  /health                    # Health check
GET  /status                    # Framework status
POST /mode                      # Set scaling mode
POST /tier                      # Manual tier selection
GET  /metrics                   # Current metrics
GET  /history                   # Scaling history
```

### Ejemplos de API

```bash
# Cambiar a modo manual
curl -X POST http://localhost:3000/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual"}'

# Seleccionar tier PYME
curl -X POST http://localhost:3000/tier \
  -H "Content-Type: application/json" \
  -d '{"tier": "pyme"}'

# Obtener estado actual
curl http://localhost:3000/status
```

## 🚀 Deployment

### Producción con Docker
```bash
# Build images
docker-compose build

# Deploy with production config
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale api-gateway=3
```

### Kubernetes
```bash
# Install with Helm
helm install silhouette ./k8s/helm-chart

# Update configuration
helm upgrade silhouette ./k8s/helm-chart \
  --set framework.mode=auto \
  --set database.host=prod-postgres
```

### Cloud Providers
- **AWS**: ECS/Fargate con RDS + ElastiCache
- **Azure**: Container Instances con Azure Database
- **GCP**: Cloud Run con Cloud SQL + Memorystore

## 🤝 Contribuir

1. Fork el proyecto
2. Crear branch de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

### Guidelines de Desarrollo
- Seguir ESLint configuration
- Unit tests requeridos para nuevas features
- Documentación actualizada
- Commits conConventional Commits

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👨‍💻 Autor

**MiniMax Agent** - Silhouette Enterprise Framework V4.0

- GitHub: [@haroldfabla2-hue](https://github.com/haroldfabla2-hue)
- Email: haroldfabla2@gmail.com

## 🙏 Agradecimientos

- Chart.js para visualizaciones
- Docker para containerización
- PostgreSQL & Redis por la infraestructura
- Nginx por load balancing
- Prometheus & Grafana por monitoring

## 📞 Soporte

### Canales de Soporte
- **Free**: Community support
- **PYME**: Email support (12h response)
- **Mediana**: Phone support (4h response)  
- **Enterprise**: Dedicated support (1h response)

### Documentación Adicional
- [Guía de Migración](docs/migration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [API Reference](docs/api.md)
- [Architecture Guide](docs/architecture.md)

---

<div align="center">

**🚀 Silhouette Enterprise Framework V4.0 - Powering the Future of Auto-Scaling**

[Website](https://silhouette.dev) • [Documentation](https://docs.silhouette.dev) • [Community](https://community.silhouette.dev)

</div>
