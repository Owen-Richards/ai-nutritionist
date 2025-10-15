"""
Redis configuration and setup for the caching system.
"""

import os
from typing import Dict, Any, Optional


def get_redis_config() -> Dict[str, Any]:
    """Get Redis configuration from environment variables."""
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": os.getenv("REDIS_PASSWORD"),
        "db": int(os.getenv("REDIS_DB", "0")),
        "cluster_mode": os.getenv("REDIS_CLUSTER_MODE", "false").lower() == "true",
        "connection_pool_size": int(os.getenv("REDIS_POOL_SIZE", "20")),
        "timeout": float(os.getenv("REDIS_TIMEOUT", "1.0")),
        "retry_on_timeout": True,
        "health_check_interval": 30,
        "socket_keepalive": True,
        "socket_keepalive_options": {}
    }


def get_cache_config() -> Dict[str, Any]:
    """Get comprehensive cache configuration."""
    return {
        # Basic cache settings
        "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600")),  # 1 hour
        "max_size": int(os.getenv("CACHE_MAX_SIZE", "10000")),
        "compression_enabled": os.getenv("CACHE_COMPRESSION", "true").lower() == "true",
        
        # Memory cache settings
        "memory_cache_size": int(os.getenv("MEMORY_CACHE_SIZE", "1000")),
        "memory_cache_ttl": int(os.getenv("MEMORY_CACHE_TTL", "300")),  # 5 minutes
        
        # Redis settings
        **get_redis_config(),
        
        # CDN settings
        "cdn_enabled": os.getenv("CDN_ENABLED", "false").lower() == "true",
        "cdn_base_url": os.getenv("CDN_BASE_URL", ""),
        "cdn_cache_control": os.getenv("CDN_CACHE_CONTROL", "public, max-age=3600"),
        
        # Performance settings
        "enable_background_refresh": os.getenv("CACHE_BACKGROUND_REFRESH", "true").lower() == "true",
        "refresh_threshold": float(os.getenv("CACHE_REFRESH_THRESHOLD", "0.8")),
        "batch_size": int(os.getenv("CACHE_BATCH_SIZE", "100")),
        "timeout_seconds": float(os.getenv("CACHE_TIMEOUT", "1.0")),
        
        # Monitoring
        "enable_metrics": os.getenv("CACHE_METRICS", "true").lower() == "true",
        "metrics_interval": int(os.getenv("CACHE_METRICS_INTERVAL", "60")),
        
        # Database cache settings
        "db_cache_table": os.getenv("DB_CACHE_TABLE", "ai_nutritionist_cache"),
        "db_cache_ttl": int(os.getenv("DB_CACHE_TTL", "86400")),  # 24 hours
    }


# Docker Compose Redis configuration
REDIS_DOCKER_COMPOSE = """
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: ai-nutritionist-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD:-}
    networks:
      - ai-nutritionist-network

  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: ai-nutritionist-redis-ui
    ports:
      - "8081:8081"
    environment:
      - REDIS_HOSTS=local:redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD:-}
    depends_on:
      - redis
    networks:
      - ai-nutritionist-network

volumes:
  redis_data:

networks:
  ai-nutritionist-network:
    driver: bridge
"""

# Redis configuration file
REDIS_CONFIG = """
# AI Nutritionist Redis Configuration

# Network
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300

# General
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""
databases 16

# Security
# requirepass your_password_here

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence
save 900 1
save 300 10
save 60 10000

stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir ./

# Replication
replica-serve-stale-data yes
replica-read-only yes
repl-diskless-sync no
repl-diskless-sync-delay 5
repl-ping-replica-period 10
repl-timeout 60
repl-disable-tcp-nodelay no
repl-backlog-size 1mb
repl-backlog-ttl 3600

# Clients
maxclients 10000

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Latency monitor
latency-monitor-threshold 100

# Event notification
notify-keyspace-events ""

# Advanced config
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
stream-node-max-bytes 4096
stream-node-max-entries 100
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
hz 10
dynamic-hz yes
aof-rewrite-incremental-fsync yes
rdb-save-incremental-fsync yes
"""


def save_redis_configs(base_path: str = "."):
    """Save Redis configuration files to the specified path."""
    import os
    
    # Create docker-compose.redis.yml
    docker_compose_path = os.path.join(base_path, "docker-compose.redis.yml")
    with open(docker_compose_path, "w") as f:
        f.write(REDIS_DOCKER_COMPOSE)
    
    # Create redis.conf
    redis_conf_path = os.path.join(base_path, "redis.conf")
    with open(redis_conf_path, "w") as f:
        f.write(REDIS_CONFIG)
    
    # Create .env.example for cache configuration
    env_example_path = os.path.join(base_path, ".env.cache.example")
    with open(env_example_path, "w") as f:
        f.write("""# Cache Configuration
CACHE_DEFAULT_TTL=3600
CACHE_MAX_SIZE=10000
CACHE_COMPRESSION=true

# Memory Cache
MEMORY_CACHE_SIZE=1000
MEMORY_CACHE_TTL=300

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_CLUSTER_MODE=false
REDIS_POOL_SIZE=20
REDIS_TIMEOUT=1.0

# CDN Configuration
CDN_ENABLED=false
CDN_BASE_URL=
CDN_CACHE_CONTROL=public, max-age=3600

# Performance
CACHE_BACKGROUND_REFRESH=true
CACHE_REFRESH_THRESHOLD=0.8
CACHE_BATCH_SIZE=100
CACHE_TIMEOUT=1.0

# Monitoring
CACHE_METRICS=true
CACHE_METRICS_INTERVAL=60

# Database Cache
DB_CACHE_TABLE=ai_nutritionist_cache
DB_CACHE_TTL=86400
""")
    
    print(f"Redis configuration files saved to {base_path}")
    print("Files created:")
    print(f"  - {docker_compose_path}")
    print(f"  - {redis_conf_path}")
    print(f"  - {env_example_path}")
    print()
    print("To start Redis:")
    print(f"  cd {base_path}")
    print("  docker-compose -f docker-compose.redis.yml up -d")
    print()
    print("To access Redis Commander UI:")
    print("  http://localhost:8081")


if __name__ == "__main__":
    save_redis_configs()
