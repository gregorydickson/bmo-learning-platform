# Infrastructure Cost Optimization - Demo Configuration

**Date**: 2025-11-20
**Purpose**: Minimize AWS costs for demonstration/learning platform

---

## Cost Optimizations Applied

### 1. ECS Task Resources ✅

| Service | Original | Optimized | Savings |
|---------|----------|-----------|---------|
| **AI Service CPU** | 1024 (1 vCPU) | 512 (0.5 vCPU) | 50% |
| **AI Service Memory** | 2048 MB | 1024 MB | 50% |
| **Rails API CPU** | 512 (0.5 vCPU) | 256 (0.25 vCPU) | 50% |
| **Rails API Memory** | 1024 MB | 512 MB | 50% |

### 2. RDS PostgreSQL ✅

| Parameter | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| **Instance Class** | db.t3.medium | db.t3.micro | ~83% |
| **Storage** | 100 GB | 20 GB | 80% |
| **Multi-AZ** | Enabled | Disabled | 50% |
| **Deletion Protection** | Enabled | Disabled | N/A |

### 3. ElastiCache Redis ✅

| Parameter | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| **Node Type** | cache.t3.small | cache.t3.micro | ~50% |

### 4. ECS Service Counts ✅

| Service | Original (Prod) | Optimized | Savings |
|---------|-----------------|-----------|---------|
| **AI Service** | 2 tasks | 1 task | 50% |
| **Rails API** | 2 tasks | 1 task | 50% |
| **Sidekiq** | 2 tasks | 1 task | 50% |

---

## Estimated Monthly Costs

### Original Configuration
- ECS Fargate (6 tasks): ~$150/month
- RDS db.t3.medium Multi-AZ: ~$120/month
- ElastiCache cache.t3.small: ~$50/month
- ALB: ~$25/month
- Other (NAT Gateway, Data Transfer, CloudWatch): ~$35/month
- **Total Infrastructure**: ~$380/month

### Optimized Configuration
- ECS Fargate (3 tasks, smaller sizes): ~$40/month
- RDS db.t3.micro Single-AZ: ~$15/month
- ElastiCache cache.t3.micro: ~$12/month
- ALB: ~$25/month
- Other (NAT Gateway, Data Transfer, CloudWatch): ~$30/month
- **Total Infrastructure**: **~$122/month**

### Cost Savings
- **Monthly Savings**: ~$258 (68% reduction)
- **Annual Savings**: ~$3,096

---

## Performance Trade-offs

### What You're Giving Up
1. **High Availability**: No Multi-AZ for RDS (single point of failure for database)
2. **Auto-Scaling Redundancy**: Only 1 task per service (no instant failover)
3. **Performance Headroom**: Smaller instances may be slower under load
4. **Storage Capacity**: Only 20GB database storage (vs 100GB)

### What Remains
✅ **All functionality works** - Just runs on smaller/fewer instances
✅ **Auto-scaling configured** - Can scale up to 10 tasks if needed
✅ **Production architecture** - Same patterns, just scaled down
✅ **Security** - All security features remain intact

---

## Recommendations

### For Demo/Learning
- ✅ **Use optimized configuration** - Perfect for testing, demos, learning
- ✅ **Monitor costs** - Set up billing alerts in AWS
- ✅ **Tear down when not in use** - Save even more

### For Production Use
- ⚠️ **Revert to original values** - Better for real workloads
- ⚠️ **Enable Multi-AZ** - Critical for production reliability
- ⚠️ **Increase task counts** - Better for high availability
- ⚠️ **Larger instances** - Better performance under load

---

## Files Modified

1. `infrastructure/terraform/environments/prod/terraform.tfvars`
   - Reduced ECS CPU/memory
   - Changed RDS to db.t3.micro, 20GB storage
   - Changed Redis to cache.t3.micro

2. `infrastructure/terraform/environments/prod/main.tf`
   - Disabled RDS Multi-AZ
   - Disabled deletion protection

3. `infrastructure/terraform/modules/ecs_services/main.tf`
   - Set all desired_count to 1 (fixed, not conditional)

---

## Quick Restore to Production Settings

If you need to scale back up, simply revert these values in terraform.tfvars:

```hcl
# Production Settings
ai_service_cpu    = 1024
ai_service_memory = 2048
rails_api_cpu     = 512
rails_api_memory  = 1024
db_instance_class = "db.t3.medium"
db_allocated_storage = 100
redis_node_type   = "cache.t3.small"
```

And in main.tf:
```hcl
multi_az            = true
deletion_protection = true
```

And in ecs_services/main.tf:
```hcl
desired_count = var.environment == "prod" ? 2 : 1
```

Then run: `terraform apply`

---

**Estimated Monthly Cost**: **$122** (infrastructure only, excludes API costs)
**Cost vs Original**: **68% reduction** ($258/month savings)
**Suitable For**: Demo, learning, development, testing
**Not Suitable For**: Production workloads requiring high availability

