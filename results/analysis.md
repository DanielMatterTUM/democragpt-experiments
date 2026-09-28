# Reactance coding on TikTok comments — results digest

- Sample: **201 comments** (12 accounts, 9 parties, 67 videos).
- Matrix: Codebook A, B × Conditions A, B × models deepseek-v4.1-flash, glm-5.3-flash, gpt-6-luna, jev-1.13.

## Prevalence of reactance (share of parsed comments coded `ja` / non-`keine_reaktanz`)

| codebook | cond | model | parse% | n_reactant | prevalence% | mean latency s | total $ |
|---|---|---|---|---|---|---|---|
| A | A | deepseek-v4.1-flash | 100.0 | 7 | 3.48 | 3.355 | 0.041048 |
| A | A | glm-5.3-flash | 100.0 | 16 | 7.96 | 5.959 | 0.039149 |
| A | A | gpt-6-luna | 100.0 | 5 | 2.49 | 1.785 | 0.025257 |
| A | A | jev-1.13 | 100.0 | 4 | 1.99 | 0.375 | 0.010977 |
| A | B | deepseek-v4.1-flash | 100.0 | 3 | 1.49 | 3.073 | 0.028392 |
| A | B | glm-5.3-flash | 100.0 | 13 | 6.47 | 5.869 | 0.029972 |
| A | B | gpt-6-luna | 100.0 | 6 | 2.99 | 1.552 | 0.01953 |
| A | B | jev-1.13 | 100.0 | 2 | 1.0 | 0.351 | 0.009077 |
| B | A | deepseek-v4.1-flash | 100.0 | 86 | 42.79 | 7.256 | 0.061965 |
| B | A | glm-5.3-flash | 100.0 | 96 | 47.76 | 6.104 | 0.035271 |
| B | A | gpt-6-luna | 100.0 | 58 | 28.86 | 2.204 | 0.041278 |
| B | A | jev-1.13 | 100.0 | 90 | 44.78 | 0.372 | 0.017481 |
| B | B | deepseek-v4.1-flash | 100.0 | 112 | 55.72 | 6.649 | 0.059781 |
| B | B | glm-5.3-flash | 100.0 | 110 | 54.73 | 3.714 | 0.017146 |
| B | B | gpt-6-luna | 100.0 | 58 | 28.86 | 2.237 | 0.032209 |
| B | B | jev-1.13 | 100.0 | 75 | 37.31 | 0.346 | 0.015712 |

## Inter-model agreement (same codebook + condition)

| codebook | cond | model A | model B | n | % agree | Cohen's κ |
|---|---|---|---|---|---|---|
| A | A | deepseek-v4.1-flash | glm-5.3-flash | 201 | 90.55 | 0.1318 |
| A | A | deepseek-v4.1-flash | gpt-6-luna | 201 | 97.01 | 0.4851 |
| A | A | deepseek-v4.1-flash | jev-1.13 | 201 | 95.52 | 0.1606 |
| A | A | glm-5.3-flash | gpt-6-luna | 201 | 91.54 | 0.1586 |
| A | A | glm-5.3-flash | jev-1.13 | 201 | 93.03 | 0.277 |
| A | A | gpt-6-luna | jev-1.13 | 201 | 96.52 | 0.2046 |
| A | B | deepseek-v4.1-flash | glm-5.3-flash | 201 | 94.03 | 0.2314 |
| A | B | deepseek-v4.1-flash | gpt-6-luna | 201 | 97.51 | 0.4332 |
| A | B | deepseek-v4.1-flash | jev-1.13 | 201 | 97.51 | -0.0121 |
| A | B | glm-5.3-flash | gpt-6-luna | 201 | 94.53 | 0.3964 |
| A | B | glm-5.3-flash | jev-1.13 | 201 | 94.53 | 0.2538 |
| A | B | gpt-6-luna | jev-1.13 | 201 | 97.01 | 0.2386 |
| B | A | deepseek-v4.1-flash | glm-5.3-flash | 201 | 75.62 | 0.5909 |
| B | A | deepseek-v4.1-flash | gpt-6-luna | 201 | 77.61 | 0.5685 |
| B | A | deepseek-v4.1-flash | jev-1.13 | 201 | 68.66 | 0.4568 |
| B | A | glm-5.3-flash | gpt-6-luna | 201 | 67.66 | 0.4155 |
| B | A | glm-5.3-flash | jev-1.13 | 201 | 62.19 | 0.3726 |
| B | A | gpt-6-luna | jev-1.13 | 201 | 68.16 | 0.399 |
| B | B | deepseek-v4.1-flash | glm-5.3-flash | 201 | 71.64 | 0.5537 |
| B | B | deepseek-v4.1-flash | gpt-6-luna | 201 | 71.14 | 0.499 |
| B | B | deepseek-v4.1-flash | jev-1.13 | 201 | 67.66 | 0.4597 |
| B | B | glm-5.3-flash | gpt-6-luna | 201 | 68.66 | 0.4696 |
| B | B | glm-5.3-flash | jev-1.13 | 201 | 64.68 | 0.4265 |
| B | B | gpt-6-luna | jev-1.13 | 201 | 77.11 | 0.531 |

## Codebook B label distribution

| codebook | cond | model | n_konfrontation_ | n_ablenkung_what | n_delegierung_hi | n_vermeidung_rue | n_reflektierte_r | n_konstruktive_k | n_keine_reaktanz |
|---|---|---|---|---|---|---|---|---|---|
| B | A | deepseek-v4.1-flash | 63 | 9 | 2 | 2 | 0 | 10 | 115 |
| B | A | glm-5.3-flash | 63 | 10 | 3 | 2 | 0 | 18 | 105 |
| B | A | gpt-6-luna | 46 | 6 | 1 | 1 | 0 | 4 | 143 |
| B | A | jev-1.13 | 66 | 8 | 1 | 6 | 1 | 8 | 111 |
| B | B | deepseek-v4.1-flash | 90 | 9 | 1 | 1 | 1 | 10 | 89 |
| B | B | glm-5.3-flash | 70 | 16 | 3 | 3 | 0 | 18 | 91 |
| B | B | gpt-6-luna | 48 | 6 | 0 | 1 | 0 | 3 | 143 |
| B | B | jev-1.13 | 54 | 9 | 1 | 5 | 0 | 6 | 126 |

## Cost

Total spend across all live calls: **$0.4842**.

| model | codebook | cond | calls | total $ | $/1k rows | mean lat s | p90 lat s |
|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | A | A | 198 | 0.041048 | 0.2042 | 3.355 | 5.471 |
| glm-5.3-flash | A | A | 197 | 0.039149 | 0.1948 | 5.959 | 13.949 |
| gpt-6-luna | A | A | 197 | 0.025257 | 0.1257 | 1.785 | 2.504 |
| jev-1.13 | A | A | 197 | 0.010977 | 0.0546 | 0.375 | 0.429 |
| deepseek-v4.1-flash | A | B | 201 | 0.028392 | 0.1413 | 3.073 | 5.795 |
| glm-5.3-flash | A | B | 201 | 0.029972 | 0.1491 | 5.869 | 11.553 |
| gpt-6-luna | A | B | 201 | 0.01953 | 0.0972 | 1.552 | 2.197 |
| jev-1.13 | A | B | 201 | 0.009077 | 0.0452 | 0.351 | 0.393 |
| deepseek-v4.1-flash | B | A | 198 | 0.061965 | 0.3083 | 7.256 | 11.99 |
| glm-5.3-flash | B | A | 197 | 0.035271 | 0.1755 | 6.104 | 14.803 |
| gpt-6-luna | B | A | 197 | 0.041278 | 0.2054 | 2.204 | 3.317 |
| jev-1.13 | B | A | 197 | 0.017481 | 0.087 | 0.372 | 0.467 |
| deepseek-v4.1-flash | B | B | 201 | 0.059781 | 0.2974 | 6.649 | 12.7 |
| glm-5.3-flash | B | B | 201 | 0.017146 | 0.0853 | 3.714 | 9.405 |
| gpt-6-luna | B | B | 201 | 0.032209 | 0.1602 | 2.237 | 3.308 |
| jev-1.13 | B | B | 201 | 0.015712 | 0.0782 | 0.346 | 0.376 |