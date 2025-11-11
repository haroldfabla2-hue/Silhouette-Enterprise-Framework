/**
 * Silhouette Enterprise Framework V4.0
 * Auto-Scaling Framework Controller
 * Dual Mode: Auto-Scaling & Manual Tier Management
 * 
 * @author MiniMax Agent
 * @version 4.0.0
 * @date 2025-11-12
 */

const { Pool } = require('pg');
const Redis = require('redis');
const EventEmitter = require('events');

class AutoScaleFrameworkController extends EventEmitter {
    constructor() {
        super();
        
        // Database Configuration
        this.dbConfig = {
            user: process.env.POSTGRES_USER || 'silhouette',
            host: process.env.DB_HOST || 'localhost',
            database: process.env.POSTGRES_DB || 'silhouette_db',
            password: process.env.POSTGRES_PASSWORD || 'silhouette2024',
            port: process.env.DB_PORT || 5432,
            ssl: process.env.DB_SSL === 'true'
        };

        // Redis Configuration
        this.redisConfig = {
            host: process.env.REDIS_HOST || 'localhost',
            port: process.env.REDIS_PORT || 6379,
            password: process.env.REDIS_PASSWORD || 'silhouette2024',
            db: process.env.REDIS_DB || 0
        };

        // Framework Configuration
        this.frameworkConfig = require('./config/framework-config.json');
        
        // Current State
        this.currentState = {
            mode: 'auto', // 'auto' or 'manual'
            activeTier: 'free',
            metrics: {
                currentTokens: 0,
                maxTokens: this.frameworkConfig.tiers.free.maxTokens,
                requestsToday: 0,
                errorRate: 0,
                uptime: 0,
                lastScaleTime: null
            },
            scalingHistory: [],
            isScaling: false
        };

        // Initialize connections
        this.initializeConnections();
        
        // Start monitoring
        this.startMonitoring();
    }

    /**
     * Initialize database and Redis connections
     */
    async initializeConnections() {
        try {
            // Initialize PostgreSQL connection
            this.dbPool = new Pool(this.dbConfig);
            await this.dbPool.query('SELECT NOW()');
            console.log('✅ PostgreSQL connection established');

            // Initialize Redis connection
            this.redisClient = Redis.createClient({
                socket: {
                    host: this.redisConfig.host,
                    port: this.redisConfig.port
                },
                password: this.redisConfig.password
            });
            
            await this.redisClient.connect();
            console.log('✅ Redis connection established');

            // Create tables if not exist
            await this.createTables();
            
        } catch (error) {
            console.error('❌ Connection initialization failed:', error);
            throw error;
        }
    }

    /**
     * Create necessary database tables
     */
    async createTables() {
        const createTablesQuery = `
            -- Framework events table
            CREATE TABLE IF NOT EXISTS framework_events (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                event_data JSONB NOT NULL,
                tier_before VARCHAR(20),
                tier_after VARCHAR(20),
                mode VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Usage metrics table
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0,
                requests_count INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                active_tier VARCHAR(20),
                response_time_ms INTEGER DEFAULT 0
            );

            -- Tier limits table
            CREATE TABLE IF NOT EXISTS tier_limits (
                tier_name VARCHAR(20) PRIMARY KEY,
                max_tokens INTEGER NOT NULL,
                max_teams INTEGER NOT NULL,
                cost_per_month DECIMAL(10,2),
                capabilities JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `;

        try {
            await this.dbPool.query(createTablesQuery);
            console.log('✅ Database tables created/verified');
        } catch (error) {
            console.error('❌ Table creation failed:', error);
            throw error;
        }
    }

    /**
     * Set scaling mode: 'auto' or 'manual'
     */
    async setScalingMode(mode) {
        try {
            if (!['auto', 'manual'].includes(mode)) {
                throw new Error('Mode must be either "auto" or "manual"');
            }

            const oldMode = this.currentState.mode;
            this.currentState.mode = mode;

            // Log the mode change
            await this.logEvent('MODE_CHANGE', {
                oldMode,
                newMode: mode,
                timestamp: new Date().toISOString()
            });

            console.log(`🔄 Scaling mode changed: ${oldMode} → ${mode}`);

            // Emit event
            this.emit('modeChanged', { 
                oldMode, 
                newMode: mode,
                timestamp: new Date().toISOString()
            });

            return { 
                success: true, 
                mode,
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('❌ Mode change failed:', error);
            await this.logEvent('MODE_CHANGE_ERROR', { error: error.message });
            throw error;
        }
    }

    /**
     * Manually select a tier (only works in manual mode)
     */
    async selectTierManually(tierName) {
        try {
            // Check if manual mode is active
            if (this.currentState.mode !== 'manual') {
                throw new Error('Manual tier selection is only available in manual mode');
            }

            // Validate tier exists
            if (!this.frameworkConfig.tiers[tierName]) {
                throw new Error(`Tier "${tierName}" does not exist`);
            }

            const oldTier = this.currentState.activeTier;
            const newTier = tierName;

            // Update current tier
            this.currentState.activeTier = newTier;
            this.currentState.metrics.maxTokens = this.frameworkConfig.tiers[newTier].maxTokens;

            // Log the tier change
            await this.logEvent('MANUAL_TIER_CHANGE', {
                oldTier,
                newTier,
                mode: 'manual',
                timestamp: new Date().toISOString()
            });

            console.log(`🎯 Manual tier changed: ${oldTier} → ${newTier}`);

            // Emit event
            this.emit('tierChanged', { 
                oldTier, 
                newTier, 
                mode: 'manual',
                timestamp: new Date().toISOString()
            });

            return { 
                success: true, 
                tier: newTier,
                mode: 'manual',
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('❌ Manual tier selection failed:', error);
            await this.logEvent('MANUAL_TIER_CHANGE_ERROR', { error: error.message });
            throw error;
        }
    }

    /**
     * Get current active tier
     */
    getActiveTier() {
        return {
            tier: this.currentState.activeTier,
            mode: this.currentState.mode,
            maxTokens: this.currentState.metrics.maxTokens,
            capabilities: this.frameworkConfig.tiers[this.currentState.activeTier].capabilities,
            cost: this.frameworkConfig.tiers[this.currentState.activeTier].cost,
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Check if scaling is needed (Auto mode only)
     */
    async checkScalingNeeds() {
        try {
            // Only check in auto mode
            if (this.currentState.mode !== 'auto') {
                return { 
                    scalingNeeded: false, 
                    reason: 'Manual mode active',
                    currentTier: this.currentState.activeTier
                };
            }

            const metrics = this.getCurrentMetrics();
            const activeTier = this.currentState.activeTier;
            const tierConfig = this.frameworkConfig.tiers[activeTier];

            // Scaling thresholds
            const tokenUsageThreshold = 0.8; // 80% token usage
            const errorRateThreshold = 0.05; // 5% error rate
            const responseTimeThreshold = 5000; // 5 seconds

            // Calculate usage percentage
            const tokenUsagePercent = metrics.currentTokens / tierConfig.maxTokens;
            
            // Check scaling conditions
            const scalingReasons = [];

            // Scale up conditions
            if (tokenUsagePercent >= tokenUsageThreshold) {
                scalingReasons.push(`Token usage ${(tokenUsagePercent * 100).toFixed(1)}% exceeds ${tokenUsageThreshold * 100}% threshold`);
            }

            if (metrics.errorRate >= errorRateThreshold) {
                scalingReasons.push(`Error rate ${(metrics.errorRate * 100).toFixed(1)}% exceeds ${errorRateThreshold * 100}% threshold`);
            }

            if (metrics.responseTime >= responseTimeThreshold) {
                scalingReasons.push(`Response time ${metrics.responseTime}ms exceeds ${responseTimeThreshold}ms threshold`);
            }

            // Determine scaling direction
            let scalingNeeded = false;
            let scalingDirection = null;

            if (scalingReasons.length > 0) {
                scalingNeeded = true;
                scalingDirection = 'up';
                
                // Check if we can scale up
                const nextTier = this.getNextTier(activeTier);
                if (!nextTier) {
                    scalingNeeded = false;
                    scalingReasons.push('Already at highest tier');
                }
            } else {
                // Check for scale down (only if not at minimum tier)
                if (activeTier !== 'free') {
                    const lowerTier = this.getLowerTier(activeTier);
                    if (lowerTier) {
                        // Check if we can scale down based on sustained low usage
                        const canScaleDown = await this.canScaleDown(activeTier, lowerTier);
                        if (canScaleDown) {
                            scalingNeeded = true;
                            scalingDirection = 'down';
                            scalingReasons.push('Sustained low usage allows scale down');
                        }
                    }
                }
            }

            return {
                scalingNeeded,
                scalingDirection,
                currentTier: activeTier,
                targetTier: scalingDirection === 'up' ? this.getNextTier(activeTier) : 
                           scalingDirection === 'down' ? this.getLowerTier(activeTier) : null,
                reasons: scalingReasons,
                metrics: metrics,
                tokenUsagePercent: tokenUsagePercent * 100,
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('❌ Scaling check failed:', error);
            await this.logEvent('SCALING_CHECK_ERROR', { error: error.message });
            throw error;
        }
    }

    /**
     * Execute automatic scaling
     */
    async executeAutoScaling() {
        try {
            if (this.currentState.isScaling) {
                return { success: false, message: 'Scaling operation already in progress' };
            }

            const scalingCheck = await this.checkScalingNeeds();
            
            if (!scalingCheck.scalingNeeded) {
                return { 
                    success: true, 
                    scaled: false, 
                    reason: 'No scaling needed',
                    ...scalingCheck
                };
            }

            this.currentState.isScaling = true;

            const oldTier = this.currentState.activeTier;
            const newTier = scalingCheck.targetTier;

            console.log(`⚡ Auto-scaling: ${oldTier} → ${newTier}`);

            // Perform the scaling
            await this.performScaling(oldTier, newTier, 'auto');

            return {
                success: true,
                scaled: true,
                oldTier,
                newTier,
                mode: 'auto',
                timestamp: new Date().toISOString(),
                ...scalingCheck
            };

        } catch (error) {
            console.error('❌ Auto-scaling failed:', error);
            await this.logEvent('AUTO_SCALING_ERROR', { error: error.message });
            throw error;
        } finally {
            this.currentState.isScaling = false;
        }
    }

    /**
     * Perform the actual scaling operation
     */
    async performScaling(oldTier, newTier, mode) {
        try {
            // Update current state
            this.currentState.activeTier = newTier;
            this.currentState.metrics.maxTokens = this.frameworkConfig.tiers[newTier].maxTokens;
            this.currentState.metrics.lastScaleTime = new Date().toISOString();

            // Add to scaling history
            this.currentState.scalingHistory.push({
                timestamp: new Date().toISOString(),
                oldTier,
                newTier,
                mode,
                reason: mode === 'auto' ? 'Automatic scaling' : 'Manual tier selection'
            });

            // Keep only last 100 scaling events
            if (this.currentState.scalingHistory.length > 100) {
                this.currentState.scalingHistory = this.currentState.scalingHistory.slice(-100);
            }

            // Log the scaling event
            await this.logEvent('TIER_SCALING', {
                oldTier,
                newTier,
                mode,
                timestamp: new Date().toISOString(),
                scalingDirection: this.frameworkConfig.tiers[newTier].cost > this.frameworkConfig.tiers[oldTier].cost ? 'up' : 'down'
            });

            // Update tier limits in database
            await this.updateTierLimits(newTier);

            // Update Redis cache
            await this.updateRedisCache();

            console.log(`✅ Scaling completed: ${oldTier} → ${newTier} (${mode})`);

            // Emit scaling event
            this.emit('tierChanged', { 
                oldTier, 
                newTier, 
                mode,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('❌ Scaling operation failed:', error);
            await this.logEvent('SCALING_OPERATION_ERROR', { 
                oldTier, 
                newTier, 
                error: error.message 
            });
            throw error;
        }
    }

    /**
     * Get current system metrics
     */
    getCurrentMetrics() {
        return {
            ...this.currentState.metrics,
            mode: this.currentState.mode,
            activeTier: this.currentState.activeTier,
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Update metrics from various sources
     */
    async updateMetrics(metricsData) {
        try {
            // Validate metrics data
            const { tokensUsed, requestsCount, errorsCount, responseTime } = metricsData;
            
            if (tokensUsed !== undefined) {
                this.currentState.metrics.currentTokens = tokensUsed;
            }
            
            if (requestsCount !== undefined) {
                this.currentState.metrics.requestsToday = requestsCount;
            }
            
            if (errorsCount !== undefined) {
                this.currentState.metrics.errorRate = errorsCount / Math.max(requestsCount || 1, 1);
            }
            
            if (responseTime !== undefined) {
                this.currentState.metrics.responseTime = responseTime;
            }

            // Store metrics in database
            await this.storeMetrics();

            // Emit metrics update event
            this.emit('metricsUpdated', this.getCurrentMetrics());

        } catch (error) {
            console.error('❌ Metrics update failed:', error);
            await this.logEvent('METRICS_UPDATE_ERROR', { error: error.message });
            throw error;
        }
    }

    /**
     * Get next tier in the hierarchy
     */
    getNextTier(currentTier) {
        const tierOrder = ['free', 'pyme', 'mediana', 'enterprise'];
        const currentIndex = tierOrder.indexOf(currentTier);
        
        if (currentIndex === -1 || currentIndex === tierOrder.length - 1) {
            return null; // Already at highest tier or invalid tier
        }
        
        return tierOrder[currentIndex + 1];
    }

    /**
     * Get lower tier in the hierarchy
     */
    getLowerTier(currentTier) {
        const tierOrder = ['free', 'pyme', 'mediana', 'enterprise'];
        const currentIndex = tierOrder.indexOf(currentTier);
        
        if (currentIndex <= 0) {
            return null; // Already at lowest tier or invalid tier
        }
        
        return tierOrder[currentIndex - 1];
    }

    /**
     * Check if can scale down based on usage patterns
     */
    async canScaleDown(currentTier, targetTier) {
        try {
            // Get historical usage data for the last 7 days
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            
            const usageQuery = `
                SELECT 
                    AVG(tokens_used) as avg_tokens,
                    AVG(requests_count) as avg_requests,
                    AVG(errors_count) as avg_errors
                FROM usage_metrics 
                WHERE created_at >= $1 AND active_tier = $2
            `;
            
            const result = await this.dbPool.query(usageQuery, [sevenDaysAgo, currentTier]);
            const avgUsage = result.rows[0];
            
            if (!avgUsage || !avgUsage.avg_tokens) {
                return false; // No historical data
            }

            // Check if usage supports scaling down
            const targetTierConfig = this.frameworkConfig.tiers[targetTier];
            const tokenUsagePercent = (avgUsage.avg_tokens || 0) / targetTierConfig.maxTokens;
            
            return tokenUsagePercent < 0.6; // Scale down if using less than 60% of target tier

        } catch (error) {
            console.error('❌ Scale down check failed:', error);
            return false;
        }
    }

    /**
     * Store metrics in database
     */
    async storeMetrics() {
        try {
            const query = `
                INSERT INTO usage_metrics 
                (tokens_used, requests_count, errors_count, active_tier, response_time_ms)
                VALUES ($1, $2, $3, $4, $5)
            `;
            
            await this.dbPool.query(query, [
                this.currentState.metrics.currentTokens,
                this.currentState.metrics.requestsToday,
                Math.floor(this.currentState.metrics.errorRate * this.currentState.metrics.requestsToday),
                this.currentState.activeTier,
                this.currentState.metrics.responseTime
            ]);
            
        } catch (error) {
            console.error('❌ Metrics storage failed:', error);
            throw error;
        }
    }

    /**
     * Update tier limits in database
     */
    async updateTierLimits(tierName) {
        try {
            const tierConfig = this.frameworkConfig.tiers[tierName];
            
            const query = `
                INSERT INTO tier_limits 
                (tier_name, max_tokens, max_teams, cost_per_month, capabilities)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tier_name) 
                DO UPDATE SET 
                    max_tokens = EXCLUDED.max_tokens,
                    max_teams = EXCLUDED.max_teams,
                    cost_per_month = EXCLUDED.cost_per_month,
                    capabilities = EXCLUDED.capabilities,
                    updated_at = CURRENT_TIMESTAMP
            `;
            
            await this.dbPool.query(query, [
                tierName,
                tierConfig.maxTokens,
                tierConfig.maxTeams,
                tierConfig.cost,
                JSON.stringify(tierConfig.capabilities)
            ]);
            
        } catch (error) {
            console.error('❌ Tier limits update failed:', error);
            throw error;
        }
    }

    /**
     * Update Redis cache
     */
    async updateRedisCache() {
        try {
            const cacheKey = 'silhouette:current_tier';
            const cacheData = {
                tier: this.currentState.activeTier,
                mode: this.currentState.mode,
                maxTokens: this.currentState.metrics.maxTokens,
                timestamp: new Date().toISOString()
            };
            
            await this.redisClient.setEx(cacheKey, 3600, JSON.stringify(cacheData)); // 1 hour expiry
            
        } catch (error) {
            console.error('❌ Redis cache update failed:', error);
            // Don't throw error for cache failures
        }
    }

    /**
     * Log framework events for audit trail
     */
    async logEvent(eventType, eventData) {
        try {
            const query = `
                INSERT INTO framework_events 
                (event_type, event_data, tier_before, tier_after, mode)
                VALUES ($1, $2, $3, $4, $5)
            `;
            
            await this.dbPool.query(query, [
                eventType,
                JSON.stringify(eventData),
                eventData.oldTier || null,
                eventData.newTier || null,
                eventData.mode || null
            ]);
            
        } catch (error) {
            console.error('❌ Event logging failed:', error);
            // Don't throw error for logging failures
        }
    }

    /**
     * Get scaling history
     */
    getScalingHistory(limit = 50) {
        return this.currentState.scalingHistory.slice(-limit);
    }

    /**
     * Get framework status
     */
    getStatus() {
        return {
            mode: this.currentState.mode,
            activeTier: this.currentState.activeTier,
            isScaling: this.currentState.isScaling,
            metrics: this.getCurrentMetrics(),
            scalingHistory: this.getScalingHistory(10),
            frameworkVersion: '4.0.0',
            uptime: process.uptime(),
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Start monitoring and auto-scaling
     */
    startMonitoring() {
        // Monitor metrics every 30 seconds
        this.monitoringInterval = setInterval(async () => {
            try {
                if (this.currentState.mode === 'auto' && !this.currentState.isScaling) {
                    await this.executeAutoScaling();
                }
            } catch (error) {
                console.error('❌ Monitoring cycle failed:', error);
            }
        }, 30000);

        console.log('🔍 Monitoring started (30-second intervals)');
    }

    /**
     * Stop monitoring
     */
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            console.log('⏹️ Monitoring stopped');
        }
    }

    /**
     * Graceful shutdown
     */
    async shutdown() {
        try {
            console.log('🛑 Shutting down AutoScale Framework Controller...');
            
            // Stop monitoring
            this.stopMonitoring();
            
            // Close database connections
            if (this.dbPool) {
                await this.dbPool.end();
            }
            
            // Close Redis connection
            if (this.redisClient) {
                await this.redisClient.quit();
            }
            
            console.log('✅ Shutdown completed');
            
        } catch (error) {
            console.error('❌ Shutdown error:', error);
        }
    }

    /**
     * Health check
     */
    async healthCheck() {
        try {
            // Test database connection
            await this.dbPool.query('SELECT 1');
            
            // Test Redis connection
            await this.redisClient.ping();
            
            return {
                status: 'healthy',
                database: 'connected',
                redis: 'connected',
                timestamp: new Date().toISOString()
            };
            
        } catch (error) {
            return {
                status: 'unhealthy',
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Get available tiers
     */
    getAvailableTiers() {
        return Object.keys(this.frameworkConfig.tiers).map(tierName => ({
            name: tierName,
            ...this.frameworkConfig.tiers[tierName]
        }));
    }

    /**
     * Get tier information
     */
    getTierInfo(tierName) {
        if (!this.frameworkConfig.tiers[tierName]) {
            throw new Error(`Tier "${tierName}" does not exist`);
        }
        
        return {
            name: tierName,
            ...this.frameworkConfig.tiers[tierName],
            isActive: tierName === this.currentState.activeTier
        };
    }
}

// Export for use in other modules
module.exports = AutoScaleFrameworkController;

// Example usage and demonstration
if (require.main === module) {
    async function demonstrateFramework() {
        console.log('🚀 Silhouette Enterprise Framework V4.0 - Demo Mode');
        console.log('=' * 60);
        
        const controller = new AutoScaleFrameworkController();
        
        try {
            // Demo scenarios
            console.log('\n📊 Demo Scenario 1: Auto-scaling mode');
            await controller.setScalingMode('auto');
            console.log('Status:', controller.getStatus());
            
            console.log('\n📊 Demo Scenario 2: Manual mode with tier selection');
            await controller.setScalingMode('manual');
            await controller.selectTierManually('pyme');
            console.log('Active tier:', controller.getActiveTier());
            
            console.log('\n📊 Demo Scenario 3: Update metrics');
            await controller.updateMetrics({
                tokensUsed: 150000,
                requestsCount: 1000,
                errorsCount: 10,
                responseTime: 3000
            });
            
            console.log('\n📊 Demo Scenario 4: Scaling check');
            const scalingCheck = await controller.checkScalingNeeds();
            console.log('Scaling needed:', scalingCheck);
            
            console.log('\n📊 Demo Scenario 5: Framework health');
            const health = await controller.healthCheck();
            console.log('Health status:', health);
            
            console.log('\n✅ Demo completed successfully!');
            
        } catch (error) {
            console.error('❌ Demo failed:', error);
        } finally {
            await controller.shutdown();
        }
    }
    
    // Run demo if this file is executed directly
    demonstrateFramework();
}

// Graceful shutdown on process termination
process.on('SIGTERM', async () => {
    if (global.frameworkController) {
        await global.frameworkController.shutdown();
    }
});

process.on('SIGINT', async () => {
    if (global.frameworkController) {
        await global.frameworkController.shutdown();
    }
    process.exit(0);
});
