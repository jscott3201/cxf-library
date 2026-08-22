# Routine catalog

Status: **zero executable routines**. Nothing in this namespace is implemented
or verified yet.

`registry.json` is the executable routine inventory. It contains an empty
`routines` array. `g36/coverage.json` records the non-claiming G36 profile
zero-state; it is not a second inventory.

Revision ownership is explicit:

- Root `ENGINE_PIN` selects the runtime evaluator.
- `g36/DONOR_PIN` selects the open-control-engine donor fixture and golden
  revision.
- `g36/SOURCE_PIN` selects the upstream Modelica Buildings source revision.

The pin files are authoritative. See the routine catalog section in
[`SCHEMA.md`](../SCHEMA.md) for row identities, allowed values, and path rules.
Run `python3 tools/lint/routines.py` from the repository root to validate the
catalog.

Interface ABI, vectors, cards or frontmatter, provenance bundles, package
acceptance, member-list or array support, and executable verification remain
deferred.
