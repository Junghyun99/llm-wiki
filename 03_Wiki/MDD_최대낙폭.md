---
aliases: [최대 낙폭, Maximum Drawdown, MDD]
tags: [permanent, 퀀트, 성과지표, 리스크]
date_created: 2026-05-23
date_updated: 2026-05-24
source: "https://blog.intelliquant.ai/post/max-drawdown"
---
# MDD_최대낙폭

## 핵심 개념
MDD(Maximum Drawdown, 최대낙폭)는 특정 기간 동안 포트폴리오 또는 자산이 **고점(Peak)에서 저점(Trough)까지 하락한 최대 폭**을 백분율로 표현한 **하방 리스크 지표**다. 퀀트 전략 평가 시 [[CAGR]]과 함께 가장 핵심적으로 확인하는 두 축 중 하나로, 수익률보다 얼마나 버틸 수 있는가를 측정한다.

## 계산 공식

$$
MDD = \frac{Trough - Peak}{Peak} \times 100
$$

- **Peak**: 해당 기간의 최고 누적 자산가치 (기준점)
- **Trough**: Peak 이후 발생한 최저 누적 자산가치

> **주의:** 시작 가격이 아니라 **구간 내 최고점**이 기준이다.

### 계산 예시
| 시점 | 자산가치 | 비고 |
|------|---------|------|
| T1   | 100     | 시작 |
| T2   | 150     | 고점(Peak) |
| T3   | 90      | 저점(Trough) |

$$MDD = \frac{90 - 150}{150} \times 100 = -40\%$$

## Python 구현

```python
import pandas as pd
import numpy as np

def calculate_mdd(prices: pd.Series) -> float:
    """누적 수익률 기준 MDD 계산"""
    cumulative = (1 + prices.pct_change()).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return drawdown.min()  # 음수값 반환 (예: -0.40)
```

## 해석 기준
| MDD 범위 | 리스크 수준 |
|---------|------------|
| 0 ~ -10% | 낮음 — 안정적 전략 |
| -10% ~ -20% | 보통 — 주요 지수 수준 |
| -20% ~ -40% | 높음 — 적극적 모멘텀 전략 |
| -40% 이하 | 매우 높음 — 레버리지·집중 투자 |

## 한계 및 보완 지표
- **시간 정보 부재:** MDD는 낙폭의 크기만 보여줄 뿐, 얼마나 오래 지속됐는지(회복 기간)는 알 수 없다.
- **단일 이벤트 편향:** 과거 최악의 한 번만 반영하여, 반복되는 소규모 낙폭은 과소평가될 수 있다.
- **보완 지표:** [[샤프지수]], Calmar Ratio(`CAGR / |MDD|`), Ulcer Index

## 퀀트 전략 평가에서의 활용
- **Calmar Ratio** = CAGR / |MDD| — 수익 대비 최대손실 효율. 값이 클수록 리스크 대비 수익 우수
- MDD가 **-20% 이하**인 전략은 일반적으로 개인 투자자가 심리적으로 버티기 어려운 구간으로 간주
- 백테스트 결과의 MDD는 실제 운용 시 **과소 추정**될 가능성이 높으므로 보수적 해석 필요

## 연결 노트
- [[MOC_퀀트트레이딩]]
- [[샤프지수]]
- [[CAGR]]
