---
aliases: [칼마비율, Calmar Ratio, 칼마 비율]
tags: [permanent, 퀀트, 성과지표, 리스크]
date_created: 2026-05-24
date_updated: 2026-06-02
source: ""
---
# 칼마비율(Calmar Ratio)

## 핵심 개념

칼마비율은 연간 수익률(CAGR)을 최대낙폭(MDD)으로 나눈 **리스크 조정 성과지표**로, 동일한 수익률이라면 낙폭이 작을수록 우수한 전략임을 정량화한다. 1991년 Terry W. Young이 자신의 회사 California Managed Account Reports(Calmar)의 이름을 따 개발했다.

## 공식

$$
\text{Calmar Ratio} = \frac{\text{CAGR}}{\left|\text{MDD}\right|}
$$

- **CAGR (연복리 수익률):** $\left(\frac{V_{end}}{V_{begin}}\right)^{1/n} - 1$, $n$은 연 단위 기간
- **MDD (최대낙폭):** $\frac{V_{trough} - V_{peak}}{V_{peak}}$, 음수값 (예: -0.25 = -25%)

> 관례상 **3년** 기간의 CAGR과 MDD를 사용한다.

## 해석 기준

| 칼마비율 | 평가 |
|----------|------|
| < 0.5 | 위험 대비 수익 불충분 |
| 0.5 ~ 1.0 | 보통 |
| > 1.0 | 양호 |
| > 2.0 | 우수 |
| > 3.0 | 탁월 |

비율이 높을수록 MDD 1%당 더 많은 연간 수익을 창출한다는 의미다.

## 계산 예시

- 전략 기간: 3년, 시작 $50,000 → 종료 $78,500
- CAGR = $(78500 / 50000)^{1/3} - 1 = 16.2\%$
- 고점 $82,000, 저점 $61,500 → MDD = $(61500 - 82000) / 82000 = -25\%$
- **칼마비율 = 16.2% / |-25%| = 0.65**

## 타 지표와의 비교

| 지표 | 위험 측정 기준 | 특징 |
|------|--------------|------|
| [[샤프지수]] | 전체 표준편차(상·하향 모두) | 가장 범용적 |
| [[소르티노지수]] | 하방 표준편차만 | 하락 리스크에 집중 |
| **칼마비율** | 최대낙폭(MDD) | 최악의 시나리오에 집중 |

칼마비율은 "전략이 겪은 최악의 손실 대비 얼마를 벌었는가"에 집중하므로, 헤지펀드·CTA(상품 트레이딩 어드바이저)·선물 전략처럼 **드로다운 통제**가 핵심인 전략 평가에 특히 적합하다.

## 한계

- MDD는 **과거 최대 낙폭**만 반영하며 미래 낙폭을 보장하지 않는다.
- 데이터 기간에 따라 MDD가 크게 달라져 **기간 의존성**이 존재한다.
- 동일 MDD라도 낙폭의 **지속 기간(duration)** 과 **회복 속도**는 반영하지 못한다.

## Python 구현

```python
import numpy as np
import pandas as pd

def calmar_ratio(returns: pd.Series, periods: int = 252) -> float:
    """
    returns: 일별 수익률 Series
    periods: 연간 거래일 수 (주식 252, 선물 365)
    """
    if returns.empty:
        return np.nan
    cagr = (1 + returns).prod() ** (periods / len(returns)) - 1
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    mdd = drawdown.min()  # 음수값
    return cagr / abs(mdd) if mdd != 0 else np.inf
```

> 라이브러리 활용: `quantstats.stats.calmar(returns)` 또는 `empyrical.calmar_ratio(returns)`

## 관련 개념

- [[MDD_최대낙폭]]
- [[샤프지수]]
- [[소르티노지수]]
- [[CAGR]]
- [[MOC_퀀트트레이딩]]
