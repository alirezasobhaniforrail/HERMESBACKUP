# Realistic Monte Carlo Implementation

## Why Basic MC is Insufficient
Basic MC only shuffles trade sequence. It assumes:
- All trades execute perfectly
- No slippage variation
- No correlated losses
- No funding spikes
- No execution failures

## Enhanced MC Model

### 1. Slippage Perturbation
```python
noise = random.uniform(-0.001, 0.001) * abs(pnl)
perturbed_pnl = pnl + noise
```

### 2. Execution Failures
```python
# 2% chance of trade not executing
if random.random() < 0.02:
    continue  # Skip this trade
```

### 3. Correlated Crash Events
```python
# 5% chance of 3-5 consecutive large losses
if random.random() < 0.05:
    cluster_size = random.randint(3, 5)
    avg_loss = calculate_average_loss(pnls)
    for _ in range(cluster_size):
        idx = random.randint(0, len(pnls)-1)
        pnls[idx] = avg_loss * random.uniform(1.5, 3.0)
```

### 4. Funding Rate Spikes
```python
# 10% chance per trade of 5% funding cost
for i in range(len(pnls)):
    if random.random() < 0.10:
        pnls[i] *= 0.95
```

## Results Comparison
| Metric | Basic MC | Realistic MC | Change |
|--------|----------|--------------|--------|
| 5th %ile | $11,556 | $11,183 | -3.2% |
| Median | $11,572 | $11,270 | -2.6% |
| Worst DD | 4.6% | 2.2% | -52% |
| Profitable | 100% | 100% | 0% |
| Kill Switch | 0% | 0% | 0% |

## Key Finding
Even with realistic perturbations, strategy remains 100% profitable.
Returns drop ~2.6% — acceptable degradation.

## When to Use Realistic MC
- Before paper trading (mandatory)
- Before live deployment (mandatory)
- After any parameter change
- When comparing strategies

## MC Parameters to Tune
- Slippage noise: ±0.05% to ±0.2% (depends on exchange/pair)
- Execution failure rate: 1-5% (depends on API reliability)
- Correlated crash probability: 3-10% (depends on market)
- Funding spike probability: 5-20% (depends on leverage)
