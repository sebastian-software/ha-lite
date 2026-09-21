# Security Policy

## Supported versions

Security fixes are provided for the latest state of the default branch. ha-lite
publishes no releases yet, so there is nothing older to patch — build from the
default branch to receive a fix.

## Reporting a vulnerability

Report suspected vulnerabilities privately. Do not open a public issue, pull
request, or discussion for a vulnerability that has not been fixed yet.

Two private channels are available:

- **GitHub private vulnerability reporting** — open this repository's
  **Security** tab and choose **Report a vulnerability**.
- **Email** — security@sebastian-software.de.

Include a concise description, the affected version or commit, reproduction
steps, the impact you expect, and any suggested fix. Leave out credentials and
data you are not allowed to share.

## Response expectations

Maintainers aim to:

- Acknowledge a private report within 7 days.
- Assess severity and affected versions within 14 days.
- Coordinate a fix and a disclosure timeline with the reporter.
- Credit the reporter when desired and appropriate.

Timing can vary for low-impact reports and for reports that depend on a fix in
an upstream dependency.

## Scope

In scope: anything in this repository that lets someone read, modify, or execute
something they should not — including the build and CI automation, and the
changes ha-lite makes to the Home Assistant code it carries.

ha-lite is a reduction of Home Assistant Core, so a defect that reproduces on
upstream Home Assistant belongs to `home-assistant/core` and should be reported
through its own security policy. A defect this project introduced by removing or
rewiring something is ours; when in doubt, report it here and say so.

Usually out of scope: reports without a concrete impact path, vulnerabilities in
third-party dependencies used as documented, and problems that require an
already-compromised machine or a deliberately corrupted local state.
