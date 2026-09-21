# ADR 0003: Prefer explicit reduction over maximum upstream compatibility

- Status: Accepted

## Context

Keeping unused Home Assistant code in-tree makes exploration and search noisy and preserves accidental architectural assumptions. Deleting it increases divergence from upstream and can make future merges harder.

## Decision

Prefer physically deleting clearly out-of-scope code once its dependencies have been checked.

Do not reorganize retained code merely for aesthetics during the initial reduction. Keeping paths and local structure recognizable reduces the cost of comparing and selectively porting upstream changes.

Upstream updates are expected to be curated rather than blindly merged.

## Consequences

The project needs a documented scope matrix and generated dependency maps. Deletion commits should be thematic and small enough that their rationale remains understandable.

An upstream update experiment should be performed after the first useful reduction to measure the actual maintenance cost. **Still open.** Five reduction waves have landed and the cost of a curated upstream update has not been measured once, so the central assumption of this record is untested.
