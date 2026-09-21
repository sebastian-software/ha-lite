# ADR 0013: English is the project language

- Status: Accepted

## Context

ha-lite is a fork of Home Assistant Core, whose code, tests, documentation and
issue history are entirely in English. The fork keeps upstream paths and local
structure recognizable so changes can be compared and selectively ported
(ADR 0003), which only works if the two read the same way.

The people working on ha-lite do not all share a first language, and neither do
the agents. Day-to-day conversation happens in whatever language suits the
people in it. What lands in the repository is a different question: it is read
later, by someone who was not in that conversation.

## Decision

Everything written into the repository is in English: source code, identifiers,
comments, docstrings, tests, documentation, ADRs, commit messages, pull request
titles and descriptions, and issues.

Spoken and written conversation about the project is not constrained. A
discussion in German that produces an English commit and an English ADR is
working as intended.

User-facing strings remain Home Assistant's translation mechanism
(`strings.json` and the generated `translations/en.json`), not free text in
code. English is the source language there as upstream.

## Consequences

A diff against upstream stays readable in both directions, which is what makes
the curated-update model in ADR 0003 affordable.

A decision reached in another language is not recorded until it exists in
English in the repository. Writing it down is part of making it, not a
translation step afterwards.
