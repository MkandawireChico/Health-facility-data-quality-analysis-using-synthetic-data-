# Statistical monitoring methodology

## Purpose

The statistical monitoring layer is a review-prioritisation aid. It is separate
from deterministic validation rules and does not establish that a report is
wrong, that a facility is underperforming, or that a patient is at risk.

All records and measurements in this portfolio are synthetic. No
`Ground_Truth_*` column is used by peer anomaly detection, monthly issue-rate
monitoring, district comparisons or facility rankings.

## Peer-group anomaly detection

Reported values are compared within the same District, Programme and Indicator
cohort. The detector requires at least eight non-null peer observations by
default.

1. Calculate the peer median and median absolute deviation (MAD).
2. When MAD is positive, calculate the modified robust z-score:
   `0.67448975 × (value − median) / MAD`.
3. Flag absolute robust z-scores greater than 3.5.
4. When MAD is zero, use the 1.5 × IQR fences. If IQR is also zero, use a
   scale-aware tolerance of the larger of 5% of the median's absolute value or
   one unit.

The output retains peer-group size, method and score for review. Small groups
are labelled as insufficient rather than silently treated as normal. These
thresholds are demonstration defaults and require domain validation before
operational use.

## Monthly issue-rate monitoring

The monthly control-chart input aligns with the operational profile and
includes four signals:

- missing reported values;
- source discrepancies;
- reported values greater than 1.5 times a positive target;
- late submissions.

A record is counted once in the issue-record numerator even if it has multiple
signals. Separate monthly counts are also retained for each signal. The issue
rate is:

`Issue rate = records with at least one detected signal / all staged records`

At least six distinct reporting months are required before descriptive limits
are calculated. The centre line is the mean of monthly issue rates; limits are
the centre line plus or minus three population standard deviations, clipped
to the valid 0–1 range.

**Important:** the limits use the complete observed period. They are
retrospective descriptive limits, not prospective limits for future alerts.
With a short series, non-independent observations, changing reporting
coverage or small denominators, these limits can be unstable. They should be
interpreted alongside record volumes and the underlying issue counts.

## Interpretation and governance

- A peer anomaly is unusual relative to its selected synthetic peer group; it
  is not proof of an error.
- A monthly review signal indicates a rate outside retrospective descriptive
  limits; it is not a causal explanation.
- District and facility comparisons must be read with their reporting volumes.
- Detector precision/recall evaluation against injected synthetic labels is
  kept separate from operational anomaly scoring.
- Thresholds, peer definitions, denominator rules and alert handling require
  review by data owners and health programme specialists before any real-world
  deployment.
