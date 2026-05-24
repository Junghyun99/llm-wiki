---
aliases: [연평균 복리 수익률, Compound Annual Growth Rate]
tags: [permanent, 퀀트, 성과지표]
date_created: 2026-05-23
source: ""
---
# CAGR (연평균 복리 수익률)

## 정의
CAGR(Compound Annual Growth Rate)은 일정 기간 동안 투자 자산이 **매년 복리로 얼마나 성장했는가**를 나타내는 기하평균 수익률이다. 단순 산술 평균이 아닌 복리 효과를 반영하므로, 변동성이 있는 장기 투자 성과를 비교할 때 표준 지표로 사용된다.

## 공식

$$
\text{CAGR} = \left(\frac{V_{끝}}{V_{시작}}\right)^{\frac{1}{n}} - 1
$$

- $V_{끝}$: 기간 말 자산 가치
- $V_{시작}$: 기간 초 자산 가치
- $n$: 기간(연 단위)

## 계산 예시
1,000만 원 → 10년 후 1억 원:

$$
\text{CAGR} = \left(\frac{100,000,000}{10,000,000}\right)^{1/10} - 1 \approx 25.9\%
$$

## Python 구현

```python
def cagr(initial_value: float, final_value: float, years: float) -> float:
    """연평균 복리 수익률 계산"""
    return (final_value / initial_value) ** (1 / years) - 1

# pandas 포트폴리오 수익률에서 계산
def portfolio_cagr(portfolio_values: pd.Series) -> float:
    n_years = len(portfolio_values) / 252  # 영업일 기준
    return (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) ** (1 / n_years) - 1
```

## 산술 평균 수익률과의 차이
| 구분 | 산술 평균 | CAGR (기하 평균) |
|------|----------|----------------|
| 계산 방식 | 연간 수익률 단순 합산 ÷ 연수 | 복리 효과 반영 기하 평균 |
| 변동성 반영 | 반영 안 됨 | 반영됨 |
| 장기 성과 표현 | 과대 추정 경향 | 실제 최종 자산 가치에 부합 |

> 변동성이 클수록 산술 평균 > CAGR이 성립한다. (Variance Drain)

## 한계
- 복리 성장을 가정하므로 **중간 손실이 얼마나 컸는지**(낙폭 깊이)를 알 수 없다.
- 최대낙폭([[MDD]])이나 [[소르티노지수]] 등과 함께 사용해야 전략의 리스크 조정 성과를 평가할 수 있다.
- 기간 선택에 따라 크게 달라지므로, **동일한 기간** 기준으로 전략 간 비교해야 한다.

## 연관 개념
- [[MDD]] — 최대 낙폭; CAGR과 함께 리스크 대비 수익을 평가한다
- [[소르티노지수]] — 하방 리스크 대비 초과 수익률
- [[샤프지수]] — 전체 변동성 대비 초과 수익률
- [[MOC_퀀트트레이딩]]
