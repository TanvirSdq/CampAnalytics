# CampAnalytics Analytical & Methodological Framework

This document outlines the theoretical foundations, mathematical formulations, calibration procedures, and benchmark estimation techniques employed across the CampAnalytics platform.

---

## 1. Overview and Core Analytical Modules

CampAnalytics is an analytical suite designed for organizers, researchers, and grant committees within the Wikimedia ecosystem. The platform provides empirical visibility into contributor dynamics and content outcomes across annual photography competitions (Wiki Loves Monuments, Wiki Loves Earth, Wiki Loves Folklore, Wiki Loves Africa, and Wiki Loves Bangla).

The suite comprises five primary analytical tools:
1. **Evaluation (Tool 01)**: Multi-dimensional campaign evaluation combining volunteer continuity, newcomer recruitment, content utility, quality recognition, and participation equity into a standardized 0–100 index.
2. **Retention (Tool 02)**: Longitudinal participant continuity analysis across multi-year editions, directional cohort retention matrices, and geographic choropleth mappings.
3. **Influx (Tool 03)**: Year-over-Year (YoY) contributor segmentation distinguishing first-time participants from returning veterans to assess participant pipeline sustainability.
4. **Content Utility (Tool 04)**: Live encyclopedic reuse tracking across Wikimedia projects (`prop=globalusage`), article inclusion volume, cross-wiki project breadth, and photographer impact rankings.
5. **Quality Recognition (Tool 05)**: Movement-wide curatorial and technical honors tracking (Quality Images, Featured Pictures, Valued Images) with structured Commons category harvesting and contributor hall of fame.

---

## 2. Participant Retention Modeling

### 2.1 Cohort Identification and Directional Overlap

Let $U_A$ denote the set of unique Wikimedia Commons usernames who uploaded at least one eligible file during source campaign edition $A$, and let $U_B$ denote the set of unique uploaders during target edition $B$.

The **Directional Retention Rate** from edition $A$ to edition $B$ is defined as:

$$R(A \to B) = \frac{|U_A \cap U_B|}{|U_A|} \times 100\%$$

Where:
- $|U_A|$ is the baseline cohort size.
- $|U_A \cap U_B|$ represents the intersection of contributors who participated in both editions.
- Directionality is preserved: $R(A \to B) \neq R(B \to A)$ whenever $|U_A| \neq |U_B|$.

### 2.2 Forward Cohort Tracking vs. Backward Intersect

In multi-year comparative matrices, CampAnalytics distinguishes two temporal perspectives:
- **Forward Retention ($t_A < t_B$)**: Measures the survival rate of historic participants over subsequent campaign cycles, reflecting long-term community continuity.
- **Backward Intersect ($t_A > t_B$)**: Measures the proportion of a current cohort who had prior experience in earlier editions, indicating veteran reliance.

Self-retention along matrix diagonals is defined as:

$$R(A \to A) = 100.0\% \quad \text{for } |U_A| > 0$$

---

## 3. Contributor Influx and Lifecycle Segmentation

For an ordered chronological sequence of editions $E_1, E_2, \dots, E_T$, participant activity in edition $t$ is partitioned into two mutually exclusive subsets:
1. **Returning Veterans ($V_t$)**: Contributors who participated in at least one prior evaluated edition:
   $$V_t = U_t \cap \left( \bigcup_{k=1}^{t-1} U_k \right)$$
2. **First-Time Newcomers ($N_t$)**: Participants active in edition $t$ who had never previously contributed within the evaluated sequence:
   $$N_t = U_t \setminus \left( \bigcup_{k=1}^{t-1} U_k \right)$$

The **Newcomer Influx Share** ($\Gamma_t$) and **Cumulative Contributor Pool** ($C_t$) are computed as:

$$\Gamma_t = \frac{|N_t|}{|U_t|} \times 100\%$$

$$C_t = \left| \bigcup_{k=1}^t U_k \right| = C_{t-1} + |N_t|$$

---

## 4. Multi-Dimensional Campaign Evaluation Framework

The Campaign Evaluation module assesses overall campaign vitality across five core dimensions. Rather than evaluating campaigns against absolute, uncalibrated thresholds, metrics are normalized against contemporary regional peer benchmarks and regularized global baselines.

### 4.1 Evaluation Dimensions

| Dimension | Notation | Definition | Data Source |
| :--- | :---: | :--- | :--- |
| **Retention Index** | $S_{\text{ret}}$ | Continuity of baseline participants into target edition: $\frac{\|U_{\text{target}} \cap U_{\text{base}}\|}{\|U_{\text{base}}\|} \times 100\%$ | Commons Upload API Logs |
| **Growth Capacity** | $S_{\text{grow}}$ | Share of target participants who are newcomers: $\frac{\|U_{\text{target}} \setminus U_{\text{base}}\|}{\|U_{\text{target}}\|} \times 100\%$ | Commons Upload API Logs |
| **Content Utility** | $S_{\text{util}}$ | Percentage of uploaded files actively deployed in Wikimedia project articles | Commons API (`prop=globalusage`) |
| **Quality Recognition** | $S_{\text{qual}}$ | Percentage of uploaded files designated as Commons Quality Images (QI) or Featured Pictures (FP) | Commons Category Members API |
| **Contributor Diversity** | $S_{\text{div}}$ | Inverse upload concentration: share of total uploads contributed by the top 10% most active uploaders | Commons API uploader distributions |

### 4.2 Paired Weighting Model

Weights are assigned using a balanced paired-dimension architecture summing to 100%:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Composite Evaluation (100%)                       │
├──────────────────────────┬──────────────────────────┬──────────────────┤
│  Community Vitality Pair │   Mission & Content Pair │   Participation  │
│          (50%)           │          (35%)           │   Equity (15%)   │
├─────────────┬────────────┼─────────────┬────────────┼──────────────────┤
│  Retention  │   Growth   │   Utility   │  Quality   │    Diversity     │
│    (25%)    │   (25%)    │    (20%)    │   (15%)    │      (15%)       │
└─────────────┴────────────┴─────────────┴────────────┴──────────────────┘
```

The composite evaluation score is calculated as:

$$\text{Evaluation Index} = 0.25 S_{\text{ret}} + 0.25 S_{\text{grow}} + 0.20 S_{\text{util}} + 0.15 S_{\text{qual}} + 0.15 S_{\text{div}}$$

#### Rationale for Paired Weighting
- **Community Vitality Pair (50%)**: Balances volunteer retention ($25\%$) against newcomer recruitment ($25\%$). A campaign with high recruitment but zero retention represents an exhausting revolving door; conversely, a campaign with high retention but zero newcomers stagnates.
- **Mission & Content Impact Pair (35%)**: Balances practical encyclopedic utility ($20\%$) against formal artistic quality ($15\%$). File uploads that illustrate Wikipedia articles deliver direct mission value; recognized Quality Images reflect high photographic execution.
- **Participation Equity (15%)**: Assesses contributor distribution breadth, guarding against campaigns where aggregate numbers are heavily skewed by a single power uploader.

---

## 5. Non-Linear Relative Performance Scoring

Direct linear percentage ratios ($x / B$) suffer from two primary failure modes:
1. They create runaway scores (e.g. $200\%$) when small baseline numbers are exceeded.
2. They fail to reflect diminishing marginal returns to scale.

To resolve this, CampAnalytics maps observed metrics $x$ against regional reference thresholds $B$ using continuous, concave utility functions.

### 5.1 Positive Dimensions (Retention, Growth, Utility, Quality)

For dimensions where higher values represent stronger performance:

$$S(x, B) = \begin{cases} 
0.0 & \text{if } x \le 0 \\
70.0 \times \left( \frac{x}{B} \right)^{0.75} & \text{if } 0 < x \le B \\
70.0 + 30.0 \times \left( 1 - \exp\left( -1.2 \times \frac{x - B}{B} \right) \right) & \text{if } x > B 
\end{cases}$$

#### Key Mathematical Properties:
- **Zero-Floor Integrity**: $S(0, B) = 0.0$. An event with zero recorded quality images or zero encyclopedic usage receives 0 points for that dimension.
- **Benchmark Alignment**: $S(B, B) = 70.0$. Achieving the regional peer standard yields 70 points ("Meets Regional Standard").
- **Sub-Linear Growth Below Benchmark**: The exponent $0.75$ ensures that initial progress is recognized encouragingly without cliff-edge score collapses.
- **Diminishing Returns Above Benchmark**: Above the benchmark, the exponential saturation term asymptotically approaches 100.0, rewarding excellence without distorting the overall index.

### 5.2 Inverse Concentration Dimension (Contributor Diversity)

Contributor diversity measures the upload share accounted for by the top 10% most active uploaders ($c \in [10.0\%, 100.0\%]$). Lower concentration indicates a broader, healthier distribution of community effort:

$$S_{\text{div}}(c, B) = \begin{cases}
100.0 & \text{if } c \le 10.0 \\
70.0 + 30.0 \times \left( \frac{B - c}{B - 10.0} \right)^{0.85} & \text{if } 10.0 < c \le B \\
\max\left(15.0, \; 70.0 - 55.0 \times \left( \frac{c - B}{100.0 - B} \right)^{0.85}\right) & \text{if } c > B \\
15.0 & \text{if } c \ge 100.0
\end{cases}$$

---

## 6. Empirical Bayesian Shrinkage of Benchmarks

### 6.1 The Small-Sample Denominator Problem

In regions with few active national campaigns in a given year (e.g., Sub-Saharan Africa or Central Europe with $N \le 3$), raw empirical percentiles can become unstable:
- An edition where only one peer country participated might yield an empirical benchmark of $0\%$ quality images or $0\%$ retention, causing division-by-zero or score inflation.
- Conversely, a single outlier peer with an unusually small upload count can artificially elevate regional percentiles.

### 6.2 Empirical Bayes Formulation

To stabilize benchmarks against small-sample noise, regional observed values ($B_{\text{regional}}$) are regularized using Empirical Bayesian shrinkage toward global movement baselines ($B_{\text{global}}$):

$$B_{\text{effective}} = \lambda \cdot B_{\text{regional}} + (1 - \lambda) \cdot B_{\text{global}}$$

Where the shrinkage weight $\lambda \in [0, 1)$ is determined by the number of active peer campaigns $N$:

$$\lambda = \frac{N}{N + M}, \quad \text{with prior pseudo-count } M = 3.0$$

- When $N = 0$ (no regional peers active): $\lambda = 0$, $B_{\text{effective}} = B_{\text{global}}$.
- When $N = 3$ (sparse region): $\lambda = 0.50$, blending regional empirical data equally with global baselines.
- When $N \ge 10$ (data-dense region): $\lambda \ge 0.77$, allowing regional characteristics to drive the benchmark while remaining bounded against edge-case anomalies.

### 6.3 Global Movement Baseline Priors

Derived from multi-year aggregate distributions across 50+ national editions:

| Metric | Movement Baseline Prior ($B_{\text{global}}$) | Context |
| :--- | :---: | :--- |
| **Retention** | $20.0\%$ | Median cross-edition participant return rate |
| **Newcomer Growth** | $65.0\%$ | Typical new contributor share in annual photo drives |
| **Content Utility** | $2.5\%$ | Median encyclopedic reuse rate across Wikipedia projects |
| **Quality Recognition** | $1.5\%$ | Median Commons Quality Image / Featured Picture award rate |
| **Contributor Diversity** | $70.0\%$ | Typical top-10% uploader concentration under open collaboration power laws |

---

## 7. Categorical Rating Scale

Individual dimension scores and the composite overall score map to standard qualitative ratings:

| Score Range | Star Rating | Qualitative Classification | Operational Interpretation |
| :---: | :---: | :--- | :--- |
| $85.0 - 100.0$ | ★★★★★ | Outstanding | Exceptional performance surpassing regional and movement benchmarks. |
| $70.0 - 84.9$ | ★★★★☆ | Strong | Healthy execution meeting or slightly exceeding regional peer standards. |
| $50.0 - 69.9$ | ★★★☆☆ | Moderate | Baseline execution with solid fundamentals and identifiable growth areas. |
| $30.0 - 49.9$ | ★★☆☆☆ | Emerging | Developing initiative; early progress observed, requires targeted support. |
| $0.0 - 29.9$ | ★☆☆☆☆ | Critical / Low | Critical structural fragility or unindexed activity requiring intervention. |

---

---

## 8. Content Utility Modeling (`prop=globalusage`)

Content Utility evaluates the direct downstream encyclopedic impact of uploaded files. Media uploaded to Wikimedia Commons is evaluated against live deployment across global Wikimedia projects (Wikipedia language editions, Wikidata, Wikivoyage, Wikinews, etc.).

### 8.1 Utility Rate Formulation
Let $F$ denote the total set of verified files uploaded during campaign edition $C$. For each file $f \in F$, let $P(f)$ represent the set of distinct wiki pages in which file $f$ is actively embedded, obtained via `prop=globalusage`.

The subset of utilized files is defined as:
$$F_{\text{in-use}} = \{ f \in F \mid |P(f)| > 0 \}$$

The **Campaign File Utility Rate** ($U_r$) is:
$$U_r = \frac{|F_{\text{in-use}}|}{|F|} \times 100\%$$

### 8.2 Global Inclusions & Cross-Wiki Footprint
1. **Total Article Inclusions ($I_{\text{total}}$)**: Cumulative instances of media deployment across all client wikis:
   $$I_{\text{total}} = \sum_{f \in F} |P(f)|$$
2. **Project Breadth Index ($B_{\text{proj}}$)**: Count of distinct Wikimedia domains (e.g. `en.wikipedia.org`, `de.wikipedia.org`, `wikidata.org`) hosting at least one campaign submission:
   $$B_{\text{proj}} = \left| \bigcup_{f \in F} \{ \text{domain}(p) \mid p \in P(f) \} \right|$$
3. **Photographer Impact Contribution**: For uploader $u$, the aggregate usage volume of their portfolio is evaluated to construct the campaign contributor utility leaderboard.

---

## 9. Quality Recognition Modeling (Commons Curatorial Standards)

Quality Recognition quantifies formal artistic, technical, and canonical achievements awarded by established Wikimedia Commons peer review processes.

### 9.1 Community Designation Types
Submissions are evaluated against three formal Commons award categories:
1. **Quality Images (QI)**: Images meeting rigorous technical standards (composition, exposure, sharpness, lighting), evaluated and ratified by the Commons Quality Images committee.
2. **Featured Pictures (FP)**: The movement's premier visual content, selected by community consensus via strict multi-day candidacy votes.
3. **Valued Images (VI)**: Images recognized as the most valuable of their kind for depicting particular encyclopedic subjects or concepts.

### 9.2 Quality Rate Formulation
Let $F_{\text{honored}} \subseteq F$ denote the set of campaign files awarded at least one formal designation ($QI \cup FP \cup VI$), discovered via structured Commons category trees (`Quality images from [Campaign]`, `Featured pictures from [Campaign]`, or `Valued images from [Campaign]`):

The **Quality Distinction Rate** ($Q_r$) is:
$$Q_r = \frac{|F_{\text{honored}}|}{|F|} \times 100\%$$

The **Honored Photographers Count** ($H$) quantifies distinct uploaders who created at least one recognized work:
$$H = |\{ \text{uploader}(f) \mid f \in F_{\text{honored}} \}|$$

---

## 10. References and Literature

1. **OECD / European Commission JRC (2008)**. *Handbook on Constructing Composite Indicators: Methodology and User Guide*. OECD Publishing, Paris.
2. **Halfaker, A., Geiger, R. S., Morgan, J. T., & Riedl, J. (2013)**. The Rise and Decline of an Open Collaboration System: How Wikipedia’s reaction to popularity is causing its decline. *American Behavioral Scientist*, 57(5), 664–688.
3. **Morgan, J. T., & Halfaker, A. (2018)**. Evaluating the Impact of Wikimedia Community Health Interventions: Methodological Frameworks and Quantitative Models. *Proceedings of the ACM on Human-Computer Interaction (CSCW)*.
4. **Kittur, A., Chi, E., Pendleton, B. A., Suh, B., & Mytkowicz, T. (2007)**. Power of the Few vs. Wisdom of the Crowd: Wikipedia and the Rise of the Bourgeoisie. *ACM Conference on Human Factors in Computing Systems (CHI)*.
5. **Wikimedia Foundation Research & Grants Committee (2020–2024)**. *Community Metrics and Impact Reporting Guidelines for Movement Organizers*. Wikimedia Meta-Wiki.
