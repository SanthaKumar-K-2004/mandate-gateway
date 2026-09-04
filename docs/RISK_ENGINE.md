# RAZORPAY — Combined Risk Intelligence Engine Specification

## Overview

The **Razorpay Combined Risk Intelligence Engine** aggregates outputs from supervised statistical models, deep neural network autoencoders, and rule-based prompt defense engines to assign risk scores to agentic payment requests.

---

## 1. Risk Model Components

| Model Component | Type | Framework | Output Metric | Primary Target |
| :--- | :--- | :--- | :--- | :--- |
| **Prompt Defense** | Structural Heuristics | Pure Python Regex | Boolean `is_injection` | System prompt override & financial jailbreaks |
| **ML Risk Classifier** | Supervised Logistic Regression | Pure NumPy | Probability `risk_score` [0.0 - 1.0] | Transaction anomaly & budget violation probability |
| **Neural Anomaly Detector** | 3-Layer Autoencoder Neural Net | Pure NumPy | Reconstruction `MSE` & `anomaly_score` | Out-of-distribution behavioral anomalies |
| **Combined Risk Aggregator** | Weighted Intelligence Fusion | Pure Python | Aggregated `risk_level` | Integrated risk input for Policy Engine |

---

## 2. Feature Extraction Vector (10-Dimensional)

The `FeatureExtractor` builds a 10D normalized float array:

$$\mathbf{x} = [x_0, x_1, x_2, x_3, x_4, x_5, x_6, x_7, x_8, x_9]^T$$

1. $x_0$: `normalized_amount` $\min(\text{amount\_paise} / 100000, 1.0)$
2. $x_1$: `amount_budget_ratio` $\min(\text{amount} / \text{budget}, 2.0)$
3. $x_2$: `unverified_product_flag` ($1.0$ if unverified, else $0.0$)
4. $x_3$: `merchant_risk_score` ($0.0$ trusted to $1.0$ unknown)
5. $x_4$: `velocity_attempt_count` $\text{attempts} / 10$
6. $x_5$: `confirmation_timing_sec` $\text{seconds} / 60$
7. $x_6$: `cart_item_count` $\text{items} / 10$
8. $x_7$: `prompt_injection_flag` ($1.0$ if signal present, else $0.0$)
9. $x_8$: `protocol_risk_weight` ($0.1$ Razorpay test, $0.3$ x402, $0.2$ UAP)
10. $x_9$: `retry_failure_count` $\text{retries} / 5$

---

## 3. Supervised ML Logistic Model Formulation

$$z = \mathbf{w}^T \mathbf{x} + b$$
$$P(\text{Risk}) = \sigma(z) = \frac{1}{1 + e^{-z}}$$

Where calibrated weights $\mathbf{w} = [0.8, 1.2, 2.5, 1.5, 1.0, 0.4, 0.3, 3.5, 0.5, 2.0]$ and $b = -3.2$.

---

## 4. Autoencoder Neural Network Anomaly Detection

- **Encoder Architecture**: $\mathbf{h} = \text{ReLU}(\mathbf{W}_{\text{enc}} \mathbf{x} + \mathbf{b}_{\text{enc}})$ (Input 10 $\rightarrow$ Hidden 4)
- **Decoder Architecture**: $\hat{\mathbf{x}} = \text{ReLU}(\mathbf{W}_{\text{dec}} \mathbf{h} + \mathbf{b}_{\text{dec}})$ (Hidden 4 $\rightarrow$ Output 10)
- **Reconstruction Error**: $\text{MSE} = \frac{1}{10} \sum_{i=0}^{9} (x_i - \hat{x}_i)^2$

---

## 5. Decision Hierarchy & Risk Thresholds

```text
Score Range         Risk Classification     Policy Engine Action
-----------------------------------------------------------------------
0.00 - 0.29         LOW                     Allowed (with Human Auth)
0.30 - 0.59         MEDIUM                  Allowed (Strict Spending Cap)
0.60 - 0.79         HIGH                    Referred to Step-Up Gate
0.80 - 1.00         CRITICAL / BLOCKED      Fail-Closed Rejection
```
