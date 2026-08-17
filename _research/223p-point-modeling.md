# ASHRAE 223P Point Modeling — Grounding Notes

Verified 2026-08-17 against the published ontology `223p.ttl` from open223.info
(ontology IRI `http://data.ashrae.org/standard223/1.0/model/all`,
`owl:versionInfo "v1.0.0-2026"`), which bundles a **Guideline 36 extension**
(`http://data.ashrae.org/standard223/1.0/extensions/g36#`), plus Brick 1.4.4 and
QUDT 3.1.4. Every term below was grep-verified in the TTL — nothing from memory.
Pending: confirmation against the formal ASHRAE 223 standard text (not yet in
hand). Point-by-point mappings live in `points/ahu.points.json`.

## The pattern: 223P has no "Point" class

A Brick point decomposes into two or three 223P nodes:

1. **The property is the point.** `s223:Property` splits on two axes —
   observable vs. actuatable, quantifiable vs. enumerable — giving four leaf
   classes: `QuantifiableObservableProperty` (analog sensor),
   `QuantifiableActuatableProperty` (analog command/setpoint),
   `EnumeratedObservableProperty` (binary/multi-state status),
   `EnumeratedActuatableProperty` (binary command).
2. **Quantifiable properties carry QUDT directly**: `qudt:hasQuantityKind`,
   `qudt:hasUnit` (plain QUDT predicates). Values via `s223:hasValue`
   (`qudt:value` is forbidden by shape). `qudt:isDeltaQuantity true` marks
   difference quantities.
3. **Enumerated properties carry `s223:hasEnumerationKind`**: `Binary-OnOff`
   (`OnOff-On/Off`), `Binary-Logical` (`Logical-True/False`),
   `Binary-Position` (`Position-Open/Closed`), `Occupancy-Occupied`
   (`Occupied-True/False`).
4. **Attachment**: `s223:hasProperty` from the owning concept. Reference models
   attach *medium* properties (air temps, duct pressure) to the
   **ConnectionPoint/Connection** where measured; *equipment* properties
   (valve/damper/fan commands, status) to the **Equipment**. An optional
   `s223:Sensor` node `s223:observes` the property with
   `s223:hasObservationLocation` (auto-inferred by SHACL when unambiguous);
   `s223:Actuator` is `actuatedByProperty` the command and `actuates` the
   equipment.
5. **Aspects double as roles**: `s223:hasAspect` takes any EnumerationKind —
   both true aspects (`Aspect-Setpoint`, `Aspect-OperatingStatus`,
   `Aspect-OperatingMode`, `Aspect-Alarm`, `Aspect-Fault`, limits…) and role
   members (`Role-Supply` asserted directly on the supply-air temperature
   property). `s223:hasRole` is the equipment/connection-level parallel
   (`Role-Economizer` on the OA damper, `Role-Heating`/`Role-Cooling` on
   coils). `EnumerationKind-Role` has exactly 21 members.
6. **Setpoints**: `QuantifiableActuatableProperty` + `s223:hasSetpoint` from
   the controlled property; `Aspect-Setpoint` is then SHACL-inferred.
7. **Medium**: `s223:hasMedium` on Connection/ConnectionPoint
   (`s223:Fluid-Air`); property-level `s223:ofMedium` is rare in the reference
   models (used with `ofSubstance` for CO₂).

## Notable gaps found (v1.0.0-2026 ontology)

- **No mixed-air role or aspect** — mixed air is identified purely
  topologically (observation location downstream of the mixing junction).
- **No schedule concept** (one incidental comment hit) and **no override
  vocabulary** at all. Our `occ_schedule` / `override_active` 223P mappings are
  constructions from verified primitives, unattested in reference models.
- Duct static pressure quantity kind is contested: reference model says
  `quantitykind:Pressure`; `s223:GaugePressureSensor`'s shape wants
  `GaugePressure` + `isDeltaQuantity true`.

## Key artifacts

- **Official G36 reference models**: github.com/open223/models.open223.info —
  `guideline36-2021-A-9.ttl` is the multi-zone VAV AHU and attests 12 of our
  14 AHU points verbatim (instances like `MultipleZoneAhu-sa-temp`,
  `MultipleZoneAhu-clg-coil-valve-command`); A-2/3/4/7 are single-zone and
  terminal-unit variants.
- The g36 extension ships SHACL shapes per G36 equipment archetype
  (`g36:HotWaterValveOrShape1`, `g36:ChilledWaterValveOrShape1`,
  `g36:DamperOrShape1`, `g36:Zone`…) — a ready-made conformance target if we
  later emit 223P models of the equipment our fault rules bind to.
- Ontology downloads: Brick releases (github brickschema/Brick; note
  brickschema.org/schema/Brick.ttl currently serves 1.4.1), 223P at
  https://open223.info/223p.ttl.
