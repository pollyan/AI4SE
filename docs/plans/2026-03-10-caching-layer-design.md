# Caching Layer Architecture Design

## Problem Statement

The API is experiencing degraded response times, particularly under high concurrency loads. Database queries are the suspected bottleneck, with repeated queries for the same data causing unnecessary load and latency. A caching layer is needed to reduce database pressure and improve response times.

## Goals & Success Criteria

- **Primary Goal**: Reduce API response time by at least 50% for cached data endpoints
- **Scalability Goal**: Support 3-5x current concurrent request load
- **Efficiency Goal**: Achieve 80%+ cache hit ratio for frequently accessed data
- **Latency Goal**: Sub-10ms cache response times (p99)

**Success Indicators**:
- Average API response time reduced from current baseline by 50%
- Database query count reduced by 60% for cached endpoints
- Cache hit ratio consistently above 80%
- System handles peak traffic without degradation

## Solution Overview

We recommend implementing a Redis-based caching layer using the Cache-Aside pattern. Redis was selected over Memcached due to its richer data structures, built-in persistence, native clustering support, and broader ecosystem. The Cache-Aside pattern provides a pragmatic starting point that can be implemented incrementally without major architectural changes.

The implementation will prioritize high-impact, low-risk data types first: session data, user profiles, configuration data, and rate limit counters. Each data type will have appropriate TTLs configured to balance freshness with cache efficiency. The caching layer will be deployed as a Redis Cluster to ensure high availability and horizontal scalability.

## Architecture

### System Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │  API Pod  │  │  API Pod  │  │  API Pod  │
        │           │  │           │  │           │
        │ ┌───────┐ │  │ ┌───────┐ │  │ ┌───────┐ │
        │ │Cache  │ │  │ │Cache  │ │  │ │Cache  │ │
        │ │Client │ │  │ │Client │ │  │ │Client │ │
        │ └───┬───┘ │  │ └───┬───┘ │  │ └───┬───┘ │
        └─────┼─────┘  └─────┼─────┘  └─────┼─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Redis Cluster  │
                    │  (3 masters +   │
                    │   3 replicas)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Database      │
                    │   (PostgreSQL)  │
                    └─────────────────┘
```

### Cache Flow Diagram

```
Request Flow (Cache-Aside Pattern):
─────────────────────────────────────

1. Read Request:
   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Client  │───▶│   API   │───▶│  Redis  │───▶│Return   │
   └─────────┘    └────┬────┘    └────┬────┘    │ Cached  │
                       │              │ Miss    │  Data   │
                       │              ▼         └─────────┘
                       │        ┌─────────┐
                       │        │  Query  │
                       └───────▶│   DB    │
                                └────┬────┘
                                     │
                                ┌────▼────┐
                                │  Cache  │
                                │ Result  │
                                └────┬────┘
                                     │
                                ┌────▼────┐
                                │ Return  │
                                │  Data   │
                                └─────────┘

2. Write Request:
   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Client  │───▶│   API   │───▶│  Write  │───▶│Invalidate│
   └─────────┘    └────┬────┘    │   DB    │    │  Cache  │
                       │         └─────────┘    └─────────┘
                       │              │
                       └──────────────┘
                          (Return Success)
```

## Implementation Details

### Technology Selection: Redis vs Memcached

**Decision**: Redis

**Rationale**:
1. **Rich Data Structures**: Supports strings, hashes, lists, sets, sorted sets - enabling flexible caching strategies beyond simple key-value
2. **Persistence**: RDB snapshots and AOF provide data durability across restarts, reducing cache warming overhead
3. **Native Clustering**: Built-in Redis Cluster for horizontal scaling without external tools
4. **Pub/Sub**: Enables real-time cache invalidation notifications across API pods
5. **Industry Adoption**: Larger ecosystem, more community support, better tooling

**Trade-offs Accepted**:
- Slightly higher memory overhead per key compared to Memcached
- More complex configuration for clustering
- Marginally lower raw throughput (acceptable given feature benefits)

### Caching Patterns

#### Primary Pattern: Cache-Aside (Lazy Loading)

```python
# Pseudo-code for cache-aside pattern
def get_user(user_id):
    cache_key = f"user:{user_id}"

    # 1. Check cache first
    cached = redis.get(cache_key)
    if cached:
        return deserialize(cached)

    # 2. Cache miss - load from database
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

    # 3. Populate cache with TTL
    redis.setex(cache_key, ttl=300, value=serialize(user))

    return user

def update_user(user_id, data):
    # 1. Update database
    db.update("UPDATE users SET ... WHERE id = ?", user_id, data)

    # 2. Invalidate cache
    redis.delete(f"user:{user_id}")
```

### Data Caching Strategy

| Data Type | Strategy | TTL | Cache Key Pattern | Priority |
|-----------|----------|-----|-------------------|----------|
| Session Data | Cache-Aside + TTL | 30 min | `session:{session_id}` | High |
| User Profiles | Cache-Aside | 5 min | `user:{user_id}` | High |
| Configuration | Cache-Aside | 1 hour | `config:{service}:{key}` | High |
| Rate Limit Counters | Counter + TTL | Per-window | `ratelimit:{user_id}:{endpoint}` | High |
| API Response Cache | Cache-Aside | 1-5 min | `api:{endpoint}:{params_hash}` | Medium |
| Computed Aggregations | Cache-Aside | 10 min | `agg:{type}:{params_hash}` | Medium |
| Reference Data | Cache-Aside | 1 hour | `ref:{table}:{id}` | Low |

## Alternatives Considered

### Alternative 1: Memcached
- Limited to string values only
- No built-in persistence
- No native clustering
- When to consider: Simple key-value caching only, team expertise in Memcached

### Alternative 2: Application-Level Caching (In-Memory)
- No cache sharing between pods
- Memory pressure on application servers
- When to consider: Extremely low latency for small datasets, read-only data

### Alternative 3: Database Query Cache
- Limited control over cache behavior
- Doesn't reduce connection pool pressure
- When to consider: Simple queries with predictable patterns

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache stampede on miss | Medium | High | Cache warming; stale-while-revalidate; mutex locks |
| Data inconsistency | Medium | Medium | Versioned keys; explicit invalidation; TTL safety net |
| Memory exhaustion | Medium | High | Set maxmemory; LRU eviction; monitor at 80% |
| Single point of failure | Low | High | Redis Cluster with replicas; sentinel failover |
| Thundering herd on expiration | Medium | Medium | TTL jitter; request coalescing |

## Testing Strategy

- **Unit Tests**: Cache hit/miss, TTL, invalidation, serialization
- **Integration Tests**: Connection handling, cluster failover
- **Performance Tests**: Baseline vs target (50% improvement), 3-5x load
- **Chaos Tests**: Node failure, network partition, memory pressure

## Rollout Plan

1. **Week 1**: Deploy Redis Cluster, configure monitoring
2. **Week 2**: Cache configuration and static data
3. **Week 3**: Cache user profiles and sessions
4. **Week 4**: API response caching, final validation

---

*Document created: 2026-03-10*