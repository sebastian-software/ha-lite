# ADR 0012: Retain the device-class trigger and condition vocabulary

- Status: Accepted

## Context

The capability report introduced by ADR 0011 surfaced fifteen components that
sit outside the closure and exist almost entirely to provide `trigger.py` and
`condition.py`: `air_quality`, `battery`, `door`, `doorbell`, `garage_door`,
`gate`, `humidity`, `illuminance`, `moisture`, `motion`, `occupancy`, `power`,
`temperature`, `vibration` and `window`.

They are easy to misread in both directions.

They do **not** define entity states or device classes.
`BinarySensorDeviceClass.MOTION` lives in `binary_sensor`,
`SensorDeviceClass.TEMPERATURE` in `sensor` — both retained roots. Deleting
`motion/` would not affect a single motion sensor.

What they define is the **named trigger and condition vocabulary** over those
device classes. `motion/trigger.py` is a table mapping `motion.detected` to
"binary_sensor with device class motion, state on". `air_quality/trigger.py`
maps `smoke_detected`, `co_detected` and `gas_detected` the same way.

The decisive fact is what `binary_sensor` and `sensor` ship themselves:

```
homeassistant/components/binary_sensor/ -> device_condition.py, device_trigger.py
homeassistant/components/sensor/        -> device_condition.py, device_trigger.py
```

Only the legacy device-automation platforms, no modern `trigger.py` or
`condition.py`. The entire semantic trigger vocabulary for the two most
important sensor domains comes from these fifteen components. Without them,
sensors are addressable only through the generic `homeassistant.state` and
`homeassistant.numeric_state` triggers — "entity X became 'on'" instead of
"motion was detected".

ADR 0002 places automation outside the core, which invites the reading that this
vocabulary is automation and should go. It is not. These components evaluate
nothing and schedule nothing; they describe what an entity can report. Their
consumer is retained and machine-facing: `websocket_api` exposes
`triggers/target`, `conditions/target`, `subscribe_trigger` and `test_condition`
— the surface an external decision engine uses to discover what it may react to,
which ADR 0002 requires the core to make first-class and ADR 0009 assumes for
agent-driven control.

## Decision

Retain all fifteen as roots, in a `device_class_semantics` category in
`script/ha_lite_closure_config.json`, with a matching `device-class-semantics`
job matrix in CI. Wave 4 may not delete them by reachability.

Add `doorbell` to `DEFAULT_INTEGRATIONS` in `homeassistant/bootstrap.py`. It is
the only one of the fifteen that upstream never registered, and platforms are
collected only from integrations that have been set up, so `doorbell.rang` was
present in the tree but unreachable at runtime. Keeping the component without
registering it would retain dead code.

## Consequences

The closure grows from 73 to 89 domains and deletion candidates fall from 1,415
to 1,399, and CI grows by fifteen jobs. The first version of this decision added
the roots without the jobs, which left the capability protected from deletion
but not from breakage; ADR 0010 now names that as the failure mode to watch. The retained cost is 7,797 lines across 134 files, of which only 1,825
are Python; the remainder is YAML specs, `strings.json`, `icons.json` and one
`en.json` each. No external requirements, no config flow, no setup cost beyond
bootstrap registration.

Adding `doorbell` to bootstrap is a divergence from upstream that adds a
capability rather than removing one. It is justified by ha-lite's scope — a
doorbell is a physical device and `event` is a retained entity domain — but it
is the first such case and should stay an exception.

Making `temperature` and `humidity` roots pulls `weather` into the closure:
both declare a `DomainSpec` over weather entities. No retained integration
provides the weather platform, so that spec can never match in ha-lite and the
domain is genuinely removable. It is recorded as `patch_required` against #27
rather than patched here, because the upstream trigger and condition tests
reference weather in 99 places and that change deserves its own review.

This decision widens the class of things ha-lite protects: not only what the
runtime needs in order to work, but the vocabulary it offers an external agent
for describing what it wants to observe. Future waves must weigh capability loss
for agents, not only import breakage.
