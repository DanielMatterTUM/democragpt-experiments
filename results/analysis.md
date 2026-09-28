# Reactance coding on TikTok comments — results digest

- Sample: **1200 comments** (68 accounts, 16 parties, 400 videos).
- Matrix: Codebook A, B × Conditions A, B × models deepseek-v4.1-flash, gpt-6-luna, jev-1.13.

## Prevalence of reactance (share of parsed comments coded `ja` / non-`keine_reaktanz`)

| codebook | cond | model | parse% | n_reactant | prevalence% | mean latency s | total $ |
|---|---|---|---|---|---|---|---|
| A | A | deepseek-v4.1-flash | 100.0 | 74 | 6.17 | 4.085 | 0.398841 |
| A | A | gpt-6-luna | 100.0 | 79 | 6.58 | 2.114 | 0.176779 |
| A | A | jev-1.13 | 100.0 | 46 | 3.83 | 0.464 | 0.07334 |
| A | B | deepseek-v4.1-flash | 100.0 | 65 | 5.42 | 3.63 | 0.291836 |
| A | B | gpt-6-luna | 100.0 | 65 | 5.42 | 1.898 | 0.135713 |
| A | B | jev-1.13 | 100.0 | 33 | 2.75 | 0.349 | 0.062368 |
| B | A | deepseek-v4.1-flash | 100.0 | 41 | 3.42 | 3.976 | 0.364296 |
| B | A | gpt-6-luna | 100.0 | 21 | 1.75 | 2.073 | 0.129569 |
| B | A | jev-1.13 | 100.0 | 29 | 2.42 | 0.348 | 0.134038 |
| B | B | deepseek-v4.1-flash | 100.0 | 45 | 3.75 | 3.924 | 0.285713 |
| B | B | gpt-6-luna | 100.0 | 22 | 1.83 | 2.096 | 0.087817 |
| B | B | jev-1.13 | 100.0 | 27 | 2.25 | 0.35 | 0.126091 |

## Inter-model agreement (same codebook + condition)

| codebook | cond | model A | model B | n | % agree | Cohen's κ |
|---|---|---|---|---|---|---|
| A | A | deepseek-v4.1-flash | gpt-6-luna | 1200 | 95.08 | 0.5882 |
| A | A | deepseek-v4.1-flash | jev-1.13 | 1200 | 95.0 | 0.4752 |
| A | A | gpt-6-luna | jev-1.13 | 1200 | 94.58 | 0.4535 |
| A | B | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.0 | 0.7072 |
| A | B | deepseek-v4.1-flash | jev-1.13 | 1200 | 95.83 | 0.4705 |
| A | B | gpt-6-luna | jev-1.13 | 1200 | 95.67 | 0.4493 |
| B | A | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.0 | 0.4075 |
| B | A | deepseek-v4.1-flash | jev-1.13 | 1200 | 96.58 | 0.4003 |
| B | A | gpt-6-luna | jev-1.13 | 1200 | 97.58 | 0.41 |
| B | B | deepseek-v4.1-flash | gpt-6-luna | 1200 | 97.25 | 0.4962 |
| B | B | deepseek-v4.1-flash | jev-1.13 | 1200 | 96.92 | 0.4737 |
| B | B | gpt-6-luna | jev-1.13 | 1200 | 97.58 | 0.3971 |

## Codebook B label distribution

| codebook | cond | model | n_konfrontation_ | n_ablenkung_what | n_delegierung_hi | n_vermeidung_rue | n_reflektierte_r | n_konstruktive_k | n_keine_reaktanz |
|---|---|---|---|---|---|---|---|---|---|
| B | A | deepseek-v4.1-flash | 35 | 5 | 1 | 0 | 0 | 0 | 1159 |
| B | A | gpt-6-luna | 18 | 0 | 0 | 0 | 0 | 3 | 1179 |
| B | A | jev-1.13 | 22 | 0 | 1 | 0 | 3 | 3 | 1171 |
| B | B | deepseek-v4.1-flash | 37 | 3 | 1 | 0 | 1 | 3 | 1155 |
| B | B | gpt-6-luna | 22 | 0 | 0 | 0 | 0 | 0 | 1178 |
| B | B | jev-1.13 | 22 | 0 | 0 | 0 | 1 | 4 | 1173 |

## Cost

Total spend across all live calls: **$2.2664**.

| model | codebook | cond | calls | total $ | $/1k rows | mean lat s | p90 lat s |
|---|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | A | A | 1382 | 0.398841 | 0.3324 | 4.085 | 7.481 |
| gpt-6-luna | A | A | 1381 | 0.176779 | 0.1473 | 2.114 | 3.098 |
| jev-1.13 | A | A | 1321 | 0.07334 | 0.0611 | 0.464 | 0.406 |
| deepseek-v4.1-flash | A | B | 1385 | 0.291836 | 0.2432 | 3.63 | 6.203 |
| gpt-6-luna | A | B | 1385 | 0.135713 | 0.1131 | 1.898 | 2.799 |
| jev-1.13 | A | B | 1385 | 0.062368 | 0.052 | 0.349 | 0.39 |
| deepseek-v4.1-flash | B | A | 1382 | 0.364296 | 0.3036 | 3.976 | 6.484 |
| gpt-6-luna | B | A | 1381 | 0.129569 | 0.108 | 2.073 | 2.955 |
| jev-1.13 | B | A | 1321 | 0.134038 | 0.1117 | 0.348 | 0.395 |
| deepseek-v4.1-flash | B | B | 1385 | 0.285713 | 0.2381 | 3.924 | 6.505 |
| gpt-6-luna | B | B | 1385 | 0.087817 | 0.0732 | 2.096 | 3.129 |
| jev-1.13 | B | B | 1385 | 0.126091 | 0.1051 | 0.35 | 0.39 |