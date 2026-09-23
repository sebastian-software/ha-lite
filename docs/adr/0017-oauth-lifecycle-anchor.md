# ADR 0017: Keep one OAuth integration as the anchor for authorization

- Status: Accepted

## Context

The retained integrations were chosen as compatibility anchors, and all six
are local: Shelly, MQTT, Matter, Hue, Fronius and Modbus talk to devices on
the network. None of them uses `application_credentials` or the OAuth2 flow
helper, so the generic authorization machinery — client credentials, the
authorize and callback round-trip, token refresh, reauthentication — was
retained without a single real consumer.

`tests/helpers/test_config_entry_oauth2_flow.py` and
`tests/components/application_credentials` test that machinery against mocks.
Neither shows that a real integration still completes the lifecycle once the
integration long tail, `my` and `cloud` are gone. And Wave 4 was about to delete
every OAuth integration in the tree by reachability, which would have left the
helpers with no consumer at all: nothing would fail, and nothing would prove
they still work.

## Decision

Retain **Miele** as the OAuth lifecycle anchor: a root of the closure, with
its full test directory in the retained-integration CI matrix.

It was picked by these criteria:

- it authenticates through `application_credentials` and the OAuth2 flow
  helper, with the credentials supplied by the user rather than a hosted
  account-linking service;
- its config flow implements reauth and reconfigure, and its tests drive the
  complete authorize → callback → token exchange, including the redirect to
  the instance's own `/auth/external/callback`;
- it is Platinum on the integration quality scale;
- rooting it adds nothing to the closure but itself: every platform it
  provides is retained entity-domain substrate;
- it controls physical devices — household appliances — which keeps it inside
  ha-lite's scope instead of stretching it.

Of the other Platinum candidates, Home Connect is larger for the same
coverage, Volvo and Yoto are narrower device classes, Google Health is a
service rather than a device, and the Google Drive and OneDrive integrations
are backup agents that pull in `backup`.

## Consequences

Miele is an anchor, not a promise to retain cloud integrations in general.
It is kept for what its tests exercise. If the generic OAuth machinery is ever
covered better by another retained integration, Miele can be replaced by
editing this record.

Being `cloud_push`, it is also the one retained integration whose device data
does not stay on the local network. That is acceptable for an anchor; it is
not a direction.

With `my` removed, OAuth integrations redirect to the instance's own callback
URL, which is the URL a user registers with the provider.
