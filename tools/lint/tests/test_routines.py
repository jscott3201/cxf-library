import contextlib
import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.lint import routines as routine_lint


PRODUCT_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_PATH = "g36/generic/air-economizer-high-limits/ashrae-differential-dry-bulb"
PINS = {
    "routines/g36/SOURCE_PIN": "a131864e4c4df22ebcd52bb8da439de0087ac365\n",
    "routines/g36/DONOR_PIN": "41e997fd130c5e454446b40bcc3ba576429876b4\n",
}
UNKNOWN_COMPLETENESS = {
    "donor_configuration": "unknown",
    "canonical_class": "unknown",
    "family_package": "unknown",
    "guideline_profile": "unknown",
}


def valid_row(class_id="G36-GEN-EXAMPLE", variant_id="default", path=None):
    return {
        "id": f"{class_id}__{variant_id}",
        "class_id": class_id,
        "variant_id": variant_id,
        "name": "Example",
        "family": "generic",
        "level": "leaf",
        "status": "draft",
        "path": path if path is not None else f"g36/{class_id.lower()}/{variant_id}",
        "canonical_class": "Buildings.Controls.OBC.ASHRAE.G36.Generic.Example",
        "evidence_tier": "E0",
        "completeness": copy.deepcopy(UNKNOWN_COMPLETENESS),
    }


class RoutineLintTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.write_text("ENGINE_PIN", "e2ff2f84577d9be65a49e6cb5440c223f6126817\n")
        self.write_registry([])
        self.write_coverage()
        for relative_path, value in PINS.items():
            self.write_text(relative_path, value)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_text(self, relative_path, value):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_json(self, relative_path, value):
        self.write_text(relative_path, json.dumps(value) + "\n")

    def write_registry(self, rows, **extra):
        value = {
            "schema": "cxf-library/routine-registry/v1",
            "routines": rows,
        }
        value.update(extra)
        self.write_json("routines/registry.json", value)

    def write_coverage(self, **changes):
        value = {
            "schema": "cxf-library/g36-coverage/v1",
            "profile": "G36-2021-private-audit",
            "completeness": copy.deepcopy(UNKNOWN_COMPLETENESS),
            "areas": [],
            "claims": [],
        }
        value.update(changes)
        self.write_json("routines/g36/coverage.json", value)

    def assert_error(self, expected):
        errors = routine_lint.validate(self.root)
        self.assertTrue(
            any(expected in error for error in errors),
            f"{expected!r} not found in {errors!r}",
        )
        return errors

    def read_json(self, relative_path):
        return json.loads((self.root / relative_path).read_text(encoding="utf-8"))

    def install_production_bundle(self):
        registry = json.loads(
            (PRODUCT_ROOT / "routines/registry.json").read_text(encoding="utf-8")
        )
        for row in registry["routines"]:
            source = PRODUCT_ROOT / "routines" / row["path"]
            destination = self.root / "routines" / row["path"]
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            elif destination.exists():
                shutil.rmtree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
        self.write_json("routines/registry.json", registry)
        self.write_json(
            "routines/g36/coverage.json",
            json.loads(
                (PRODUCT_ROOT / "routines/g36/coverage.json").read_text(encoding="utf-8")
            ),
        )
        return self.root / "routines" / BUNDLE_PATH

    def make_matching_donor(self):
        donor = self.root / "donor"
        if donor.is_symlink() or donor.is_file():
            donor.unlink()
        elif donor.exists():
            shutil.rmtree(donor)
        registry = self.read_json("routines/registry.json")
        for row in registry["routines"]:
            bundle = self.root / "routines" / row["path"]
            provenance = json.loads((bundle / "provenance.json").read_text(encoding="utf-8"))
            for artifact in provenance["artifacts"]:
                source = bundle / artifact["local_path"]
                destination = donor / artifact["donor_path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        return donor

    def install_alternate_scalar_bundle(self):
        path = "g36/example/alternate-scalar"
        bundle = self.root / "routines" / path
        bundle.mkdir(parents=True)
        routine_id = "G36-EXAMPLE-SCALAR__alternate"
        canonical_class = "Example.Controls.AlternateScalar"
        root_id = "http://example.org#alternate.scalar"
        block_id = f"{root_id}.offset"
        graph = {
            "@context": {
                "S231": "http://data.ashrae.org/S231P#",
                "base": "http://example.org#",
            },
            "@graph": [
                {
                    "@id": root_id,
                    "@type": f"http://example.org#{canonical_class}",
                    "S231:hasParameter": {"@id": f"{root_id}.mode"},
                    "S231:hasInput": {"@id": f"{root_id}.uAlt"},
                    "S231:hasOutput": {"@id": f"{root_id}.yAlt"},
                    "S231:containsBlock": {"@id": block_id},
                },
                {
                    "@id": f"{root_id}.mode",
                    "@type": "S231:Parameter",
                    "S231:value": "alternate",
                },
                {
                    "@id": f"{root_id}.uAlt",
                    "@type": "S231:RealInput",
                    "S231:isOfDataType": {"@id": "S231:Real"},
                    "S231:unit": "K",
                    "S231:quantity": "ThermodynamicTemperature",
                },
                {
                    "@id": f"{root_id}.yAlt",
                    "@type": "S231:RealOutput",
                    "S231:isOfDataType": {"@id": "S231:Real"},
                    "S231:unit": "K",
                    "S231:quantity": "ThermodynamicTemperature",
                },
                {
                    "@id": block_id,
                    "@type": "http://example.org#Example.Blocks.Offset",
                    "S231:hasParameter": {"@id": f"{block_id}.delta"},
                },
                {
                    "@id": f"{block_id}.delta",
                    "@type": "S231:Parameter",
                    "S231:value": 0.0,
                },
            ],
        }
        interface = {
            "schema": "cxf-library/routine-interface/v1",
            "routine_id": routine_id,
            "tick_profile": "HostTick-v1",
            "connectors": [
                {
                    "id": "uAlt",
                    "direction": "input",
                    "value_type": "real",
                    "unit": "K",
                    "quantity": "ThermodynamicTemperature",
                    "shape": "scalar",
                },
                {
                    "id": "yAlt",
                    "direction": "output",
                    "value_type": "real",
                    "unit": "K",
                    "quantity": "ThermodynamicTemperature",
                    "shape": "scalar",
                },
            ],
        }
        vectors = {
            "schema": "cxf-library/routine-vectors/v1",
            "routine_id": routine_id,
            "clock": {"step_s": 1.0, "horizon_s": 1.0},
            "scenarios": [
                {
                    "name": "alternate_reference",
                    "inputs": {
                        "uAlt": [
                            {"t": 0.0, "value": 280.0},
                            {"t": 1.0, "value": 281.5},
                        ]
                    },
                    "expect": [
                        {
                            "output": "yAlt",
                            "from_s": 0.0,
                            "to_s": 0.0,
                            "equals": 280.0,
                            "tolerance": 0.0,
                        },
                        {
                            "output": "yAlt",
                            "from_s": 1.0,
                            "to_s": 1.0,
                            "equals": 281.5,
                            "tolerance": 0.0,
                        },
                    ],
                }
            ],
        }
        self.write_json(f"routines/{path}/routine.cxf.jsonld", graph)
        self.write_json(f"routines/{path}/interface.json", interface)
        self.write_json(f"routines/{path}/vectors.json", vectors)
        self.write_text(f"routines/{path}/card.md", "# Alternate scalar\n\n![Flow](diagram.svg)\n")
        self.write_text(
            f"routines/{path}/diagram.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>\n',
        )
        self.write_text(f"routines/{path}/LICENSE-BUILDINGS.html", "test license\n")
        self.write_text(f"routines/{path}/THIRD_PARTY_NOTICES.md", "test notice\n")
        self.write_text(f"routines/{path}/evidence/structure.txt", "alternate structure\n")
        self.write_text(
            f"routines/{path}/evidence/reference.dat",
            "# columns: time source_value result_value\n"
            "double alternate_reference(2,3)\n"
            "0.0 280.0 280.0\n"
            "1.0 281.5 281.5\n",
        )
        self.write_json(f"routines/{path}/evidence/reference.prov.json", {"source": "test"})
        artifact_specs = [
            ("graph", "routine.cxf.jsonld", "fixtures/alternate.jsonld"),
            ("structural_oracle", "evidence/structure.txt", "fixtures/alternate.txt"),
            ("donor_reference", "evidence/reference.dat", "goldens/alternate/reference.dat"),
            (
                "reference_provenance",
                "evidence/reference.prov.json",
                "goldens/alternate/reference.prov.json",
            ),
        ]
        artifacts = [
            {
                "role": role,
                "local_path": local_path,
                "donor_path": donor_path,
                "sha256": hashlib.sha256((bundle / local_path).read_bytes()).hexdigest(),
            }
            for role, local_path, donor_path in artifact_specs
        ]
        provenance = {
            "schema": "cxf-library/routine-provenance/v1",
            "routine_id": routine_id,
            "runtime": {
                "repository": "https://github.com/jscott3201/open-control-engine",
                "commit": "e2ff2f84577d9be65a49e6cb5440c223f6126817",
                "tick_profile": "HostTick-v1",
                "content_id": f"cxf:fnv1a128:{'1' * 32}",
            },
            "donor": {
                "repository": "https://github.com/jscott3201/open-control-engine",
                "commit": "41e997fd130c5e454446b40bcc3ba576429876b4",
            },
            "upstream": {
                "repository": "https://github.com/lbl-srg/modelica-buildings",
                "commit": "a131864e4c4df22ebcd52bb8da439de0087ac365",
                "canonical_class": canonical_class,
                "source_file": "Buildings/Controls/Example/AlternateScalar.mo",
            },
            "fixed_parameters": {"mode": "alternate"},
            "implementation": {
                "selected_branch": "alternate scalar branch",
                "block_class": "Example.Blocks.Offset",
                "parameters": {"delta": 0.0},
            },
            "donor_columns": {
                "time": "time",
                "connectors": {"uAlt": "source_value", "yAlt": "result_value"},
            },
            "artifacts": artifacts,
            "evidence": [
                {"tier": "E0", "status": "complete", "artifact": "interface.json"},
                {"tier": "E1", "status": "complete", "artifact": "vectors.json"},
                {"tier": "E2", "status": "complete", "artifact": "evidence/reference.dat"},
                {
                    "tier": "E3",
                    "status": "complete",
                    "artifact": "evidence/reference.prov.json",
                },
            ],
            "private_reference": {
                "profile": "G36-2021-private-audit",
                "audit_status": "not_used",
                "sections": [],
            },
        }
        self.write_json(f"routines/{path}/provenance.json", provenance)
        row = {
            "id": routine_id,
            "class_id": "G36-EXAMPLE-SCALAR",
            "variant_id": "alternate",
            "name": "Alternate scalar",
            "family": "example",
            "level": "leaf",
            "status": "source_evidenced",
            "path": path,
            "canonical_class": canonical_class,
            "evidence_tier": "E3",
            "completeness": {
                "donor_configuration": "complete",
                "canonical_class": "partial",
                "family_package": "not_applicable",
                "guideline_profile": "partial",
            },
        }
        registry = self.read_json("routines/registry.json")
        rows = registry["routines"] + [row]
        self.write_registry(sorted(rows, key=lambda item: item["id"]))
        self.write_coverage(
            completeness={
                "donor_configuration": "partial",
                "canonical_class": "partial",
                "family_package": "unknown",
                "guideline_profile": "partial",
            }
        )
        return bundle

    def install_output_only_scalar_bundle(self):
        path = "g36/example/output-only-scalar"
        bundle = self.root / "routines" / path
        bundle.mkdir(parents=True)
        routine_id = "G36-EXAMPLE-SCALAR__output-only"
        canonical_class = (
            "Buildings.Controls.OBC.ASHRAE.G36.Generic.AirEconomizerHighLimits"
        )
        root_id = "http://example.org#g36.source.output_only_scalar"
        block_id = f"{root_id}.con"
        fixed_parameters = {
            "eneStd": (
                "Buildings.Controls.OBC.ASHRAE.G36.Types."
                "EnergyStandard.ASHRAE90_1"
            ),
            "ecoHigLimCon": (
                "Buildings.Controls.OBC.ASHRAE.G36.Types."
                "ControlEconomizer.FixedDryBulb"
            ),
            "ashCliZon": (
                "Buildings.Controls.OBC.ASHRAE.G36.Types."
                "ASHRAEClimateZone.Zone_1B"
            ),
        }
        graph = {
            "@context": {
                "S231": "http://data.ashrae.org/S231P#",
                "base": "http://example.org#",
            },
            "@graph": [
                {
                    "@id": root_id,
                    "@type": f"http://example.org#{canonical_class}",
                    "S231:hasParameter": [
                        {"@id": f"{root_id}.{name}"} for name in fixed_parameters
                    ],
                    "S231:hasOutput": {"@id": f"{root_id}.TCut"},
                    "S231:containsBlock": {"@id": block_id},
                },
                *[
                    {
                        "@id": f"{root_id}.{name}",
                        "@type": "S231:Parameter",
                        "S231:value": value,
                    }
                    for name, value in fixed_parameters.items()
                ],
                {
                    "@id": f"{root_id}.TCut",
                    "@type": "S231:RealOutput",
                    "S231:isOfDataType": {"@id": "S231:Real"},
                    "S231:unit": "K",
                    "S231:quantity": "ThermodynamicTemperature",
                },
                {
                    "@id": block_id,
                    "@type": (
                        "http://example.org#Buildings.Controls.OBC.CDL."
                        "Reals.Sources.Constant"
                    ),
                    "S231:hasParameter": {"@id": f"{block_id}.k"},
                    "S231:hasOutput": {"@id": f"{block_id}.y"},
                },
                {
                    "@id": f"{block_id}.k",
                    "@type": "S231:Parameter",
                    "S231:value": 297.15,
                },
                {
                    "@id": f"{block_id}.y",
                    "@type": "S231:RealOutput",
                    "S231:isOfDataType": {"@id": "S231:Real"},
                    "S231:isConnectedTo": {"@id": f"{root_id}.TCut"},
                },
            ],
        }
        interface = {
            "schema": "cxf-library/routine-interface/v1",
            "routine_id": routine_id,
            "tick_profile": "HostTick-v1",
            "connectors": [
                {
                    "id": "TCut",
                    "direction": "output",
                    "value_type": "real",
                    "unit": "K",
                    "quantity": "ThermodynamicTemperature",
                    "shape": "scalar",
                }
            ],
        }
        vectors = {
            "schema": "cxf-library/routine-vectors/v1",
            "routine_id": routine_id,
            "clock": {"step_s": 1.0, "horizon_s": 0.0},
            "scenarios": [
                {
                    "name": "fixed_dry_bulb_reference",
                    "inputs": {},
                    "expect": [
                        {
                            "output": "TCut",
                            "from_s": 0.0,
                            "to_s": 0.0,
                            "equals": 297.15,
                            "tolerance": 0.0,
                        }
                    ],
                }
            ],
        }
        self.write_json(f"routines/{path}/routine.cxf.jsonld", graph)
        self.write_json(f"routines/{path}/interface.json", interface)
        self.write_json(f"routines/{path}/vectors.json", vectors)
        self.write_text(
            f"routines/{path}/card.md",
            "# Output-only scalar\n\n![Flow](diagram.svg)\n",
        )
        self.write_text(
            f"routines/{path}/diagram.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>\n',
        )
        self.write_text(f"routines/{path}/LICENSE-BUILDINGS.html", "test license\n")
        self.write_text(f"routines/{path}/THIRD_PARTY_NOTICES.md", "test notice\n")
        self.write_text(f"routines/{path}/evidence/structure.txt", "constant output\n")
        self.write_text(
            f"routines/{path}/evidence/reference.dat",
            "# columns: time temperature_cutoff\n"
            "double output_only_reference(1,2)\n"
            "0.0 297.15\n",
        )
        self.write_json(f"routines/{path}/evidence/reference.prov.json", {"source": "test"})
        artifact_specs = [
            ("graph", "routine.cxf.jsonld", "fixtures/output_only.jsonld"),
            ("structural_oracle", "evidence/structure.txt", "fixtures/output_only.txt"),
            (
                "donor_reference",
                "evidence/reference.dat",
                "goldens/output_only/reference.dat",
            ),
            (
                "reference_provenance",
                "evidence/reference.prov.json",
                "goldens/output_only/reference.prov.json",
            ),
        ]
        artifacts = [
            {
                "role": role,
                "local_path": local_path,
                "donor_path": donor_path,
                "sha256": hashlib.sha256((bundle / local_path).read_bytes()).hexdigest(),
            }
            for role, local_path, donor_path in artifact_specs
        ]
        provenance = {
            "schema": "cxf-library/routine-provenance/v1",
            "routine_id": routine_id,
            "runtime": {
                "repository": "https://github.com/jscott3201/open-control-engine",
                "commit": "e2ff2f84577d9be65a49e6cb5440c223f6126817",
                "tick_profile": "HostTick-v1",
                "content_id": f"cxf:fnv1a128:{'2' * 32}",
            },
            "donor": {
                "repository": "https://github.com/jscott3201/open-control-engine",
                "commit": "41e997fd130c5e454446b40bcc3ba576429876b4",
            },
            "upstream": {
                "repository": "https://github.com/lbl-srg/modelica-buildings",
                "commit": "a131864e4c4df22ebcd52bb8da439de0087ac365",
                "canonical_class": canonical_class,
                "source_file": (
                    "Buildings/Controls/OBC/ASHRAE/G36/Generic/"
                    "AirEconomizerHighLimits.mo"
                ),
            },
            "fixed_parameters": fixed_parameters,
            "implementation": {
                "selected_branch": "fixed dry-bulb constant cutoff",
                "block_class": "Buildings.Controls.OBC.CDL.Reals.Sources.Constant",
                "parameters": {"k": 297.15},
            },
            "donor_columns": {
                "time": "time",
                "connectors": {"TCut": "temperature_cutoff"},
            },
            "artifacts": artifacts,
            "evidence": [
                {"tier": "E0", "status": "complete", "artifact": "interface.json"},
                {"tier": "E1", "status": "complete", "artifact": "vectors.json"},
                {"tier": "E2", "status": "complete", "artifact": "evidence/reference.dat"},
                {
                    "tier": "E3",
                    "status": "complete",
                    "artifact": "evidence/reference.prov.json",
                },
            ],
            "private_reference": {
                "profile": "G36-2021-private-audit",
                "audit_status": "not_used",
                "sections": [],
            },
        }
        self.write_json(f"routines/{path}/provenance.json", provenance)
        row = {
            "id": routine_id,
            "class_id": "G36-EXAMPLE-SCALAR",
            "variant_id": "output-only",
            "name": "Output-only scalar",
            "family": "example",
            "level": "leaf",
            "status": "source_evidenced",
            "path": path,
            "canonical_class": canonical_class,
            "evidence_tier": "E3",
            "completeness": {
                "donor_configuration": "complete",
                "canonical_class": "partial",
                "family_package": "not_applicable",
                "guideline_profile": "partial",
            },
        }
        registry = self.read_json("routines/registry.json")
        self.write_registry(sorted(registry["routines"] + [row], key=lambda item: item["id"]))
        self.write_coverage(
            completeness={
                "donor_configuration": "partial",
                "canonical_class": "partial",
                "family_package": "unknown",
                "guideline_profile": "partial",
            }
        )
        return bundle

    def test_valid_zero_state(self):
        self.assertEqual(routine_lint.validate(self.root), [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = routine_lint.main(self.root)
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "routine catalog lint: 0 routines OK\n")

    def test_missing_source_and_donor_pins(self):
        for relative_path in PINS:
            with self.subTest(relative_path=relative_path):
                (self.root / relative_path).unlink()
                self.assert_error(f"{relative_path}: file is missing")
                self.write_text(relative_path, PINS[relative_path])

    def test_malformed_source_and_donor_pins(self):
        for relative_path in PINS:
            with self.subTest(relative_path=relative_path):
                self.write_text(relative_path, "ABCDEF\n")
                self.assert_error(
                    f"{relative_path}: must contain one lowercase 40-hex Git commit"
                )
                self.write_text(relative_path, PINS[relative_path])

        self.write_text(
            "routines/g36/SOURCE_PIN",
            " a131864e4c4df22ebcd52bb8da439de0087ac365 \n",
        )
        self.assert_error(
            "routines/g36/SOURCE_PIN: must contain one lowercase 40-hex Git commit"
        )

    def test_wrong_registry_and_coverage_schema_ids(self):
        self.write_registry([])
        registry = json.loads((self.root / "routines/registry.json").read_text())
        registry["schema"] = "wrong"
        self.write_json("routines/registry.json", registry)
        self.assert_error("registry.json: schema must be 'cxf-library/routine-registry/v1'")

        self.write_registry([])
        self.write_coverage(schema="wrong")
        self.assert_error("coverage.json: schema must be 'cxf-library/g36-coverage/v1'")

    def test_missing_malformed_and_non_object_json(self):
        registry_path = self.root / "routines/registry.json"
        registry_path.unlink()
        self.assert_error("routines/registry.json: file is missing")

        self.write_text("routines/registry.json", "{")
        self.assert_error("routines/registry.json: invalid JSON at line 1, column 2")

        self.write_json("routines/registry.json", [])
        self.assert_error("routines/registry.json: must contain a JSON object")

    def test_registry_and_coverage_top_level_keys_are_exact(self):
        self.write_registry([], runtime_pin="deadbeef")
        self.assert_error("unexpected runtime_pin")

        for key in ("donor_pin", "source_pin", "implemented_variants"):
            with self.subTest(key=key):
                self.write_coverage(**{key: "duplicate"})
                self.assert_error(f"unexpected {key}")

        self.write_coverage()
        coverage = json.loads((self.root / "routines/g36/coverage.json").read_text())
        del coverage["claims"]
        self.write_json("routines/g36/coverage.json", coverage)
        self.assert_error("missing claims")

    def test_registry_must_be_an_array(self):
        self.write_registry({})
        self.assert_error("routines/registry.json: routines must be an array")

    def test_registry_row_keys_and_types_are_exact(self):
        row = valid_row()
        del row["family"]
        row["extra"] = True
        self.write_registry([row])
        errors = self.assert_error("missing family; unexpected extra")
        self.assertFalse(any("Traceback" in error for error in errors))

        row = valid_row()
        row["name"] = 3
        self.write_registry([row])
        self.assert_error("routines[0].name: must be a string")

    def test_duplicate_routine_ids_and_paths(self):
        first = valid_row()
        duplicate_id = valid_row(path="g36/generic/other")
        self.write_registry([first, duplicate_id])
        self.assert_error("routines[1].id: duplicate 'G36-GEN-EXAMPLE__default'")

        second = valid_row("G36-GEN-SECOND", path=first["path"])
        self.write_registry([first, second])
        self.assert_error(f"routines[1].path: duplicate {first['path']!r}")

    def test_registry_rows_must_be_sorted_by_id(self):
        second = valid_row("G36-GEN-SECOND")
        first = valid_row("G36-GEN-EXAMPLE")
        self.write_registry([second, first])
        self.assert_error("routines/registry.json: routines must be sorted by id")

    def test_routine_identity_must_match_class_and_variant(self):
        row = valid_row()
        row["id"] = "G36-GEN-OTHER__default"
        self.write_registry([row])
        self.assert_error("routines[0].id: must equal 'G36-GEN-EXAMPLE__default'")

    def test_class_variant_and_routine_id_grammar(self):
        row = valid_row(class_id="g36-GEN-EXAMPLE")
        self.write_registry([row])
        self.assert_error("routines[0].class_id: does not match G36-<DOMAIN>-<SLUG>")

        row = valid_row(variant_id="Not_Kebab")
        self.write_registry([row])
        self.assert_error("routines[0].variant_id: must be lowercase kebab case")

        row = valid_row()
        row["id"] = "not-a-routine-id"
        self.write_registry([row])
        self.assert_error(
            "routines[0].id: does not match G36-<DOMAIN>-<SLUG>__<variant-id>"
        )

    def test_unsafe_paths_are_rejected(self):
        cases = {
            "/g36/example": "absolute paths are forbidden",
            "g36\\example": "backslashes are forbidden",
            "g36/example/../other": "parent traversal is forbidden",
            "../g36/example": "parent traversal is forbidden",
            "g36//example": "empty path segments are forbidden",
            "g36/./example": "dot path segments are forbidden",
            "": "empty path segments are forbidden",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.write_registry([valid_row(path=path)])
                self.assert_error(f"routines[0].path: {expected}")

    def test_invalid_level_status_and_evidence_tier(self):
        cases = {
            "level": ("package", "routines[0].level: must be one of"),
            "status": ("verified", "routines[0].status: must be one of"),
            "evidence_tier": ("E6", "routines[0].evidence_tier: must be one of"),
        }
        for key, (value, expected) in cases.items():
            with self.subTest(key=key):
                row = valid_row()
                row[key] = value
                self.write_registry([row])
                self.assert_error(expected)

    def test_registry_completeness_keys_and_values(self):
        row = valid_row()
        del row["completeness"]["family_package"]
        self.write_registry([row])
        self.assert_error("routines[0].completeness: keys must be exactly")

        row = valid_row()
        row["completeness"]["guideline_profile"] = "done"
        self.write_registry([row])
        self.assert_error("completeness.guideline_profile: must be one of")

    def test_canonical_class_rule(self):
        for level in ("leaf", "controller"):
            with self.subTest(level=level):
                row = valid_row()
                row["level"] = level
                row["canonical_class"] = None
                self.write_registry([row])
                self.assert_error("canonical_class: non-fragments require a nonempty string")

        row = valid_row()
        row["level"] = "fragment"
        self.write_registry([row])
        self.assert_error("canonical_class: fragments must use null")

        row["canonical_class"] = None
        self.write_registry([row])
        errors = routine_lint.validate(self.root)
        self.assertFalse(any("routines[0].canonical_class" in error for error in errors))

    def test_coverage_profile_and_completeness_contract(self):
        self.write_coverage(profile=" ")
        self.assert_error("coverage.json: profile must be a nonempty string")

        completeness = copy.deepcopy(UNKNOWN_COMPLETENESS)
        del completeness["donor_configuration"]
        self.write_coverage(completeness=completeness)
        self.assert_error("coverage.json: completeness: keys must be exactly")

        completeness = copy.deepcopy(UNKNOWN_COMPLETENESS)
        completeness["canonical_class"] = "complete"
        self.write_coverage(completeness=completeness)
        self.assert_error("must be 'unknown' while the registry is empty")

        self.install_production_bundle()
        coverage = self.read_json("routines/g36/coverage.json")
        coverage["completeness"]["canonical_class"] = "complete"
        self.write_json("routines/g36/coverage.json", coverage)
        self.assert_error("unless every applicable registry row is complete")

        registry = self.read_json("routines/registry.json")
        for row in registry["routines"]:
            if row["completeness"]["canonical_class"] != "not_applicable":
                row["completeness"]["canonical_class"] = "complete"
        self.write_json("routines/registry.json", registry)
        self.assertFalse(
            any(
                "coverage.json: completeness.canonical_class" in error
                for error in routine_lint.validate(self.root)
            )
        )

    def test_nonempty_areas_and_claims_are_rejected(self):
        for key in ("areas", "claims"):
            with self.subTest(key=key):
                self.write_coverage(**{key: ["claim"]})
                self.assert_error(f"coverage.json: {key} must be empty in v1")

        self.write_coverage(areas={})
        self.assert_error("coverage.json: areas must be an array")

    def test_expected_failures_have_deterministic_output_without_traceback(self):
        self.write_text("routines/g36/SOURCE_PIN", "bad\n")
        self.write_text("routines/g36/DONOR_PIN", "bad\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = routine_lint.main(self.root)
        self.assertEqual(result, 1)
        lines = output.getvalue().splitlines()
        self.assertEqual(lines, sorted(lines))
        self.assertEqual(
            lines,
            [
                "routines/g36/DONOR_PIN: must contain one lowercase 40-hex Git commit",
                "routines/g36/SOURCE_PIN: must contain one lowercase 40-hex Git commit",
            ],
        )
        self.assertNotIn("Traceback", output.getvalue())

    def test_production_shaped_bundle_and_donor_parity(self):
        self.install_production_bundle()
        donor = self.make_matching_donor()
        self.assertEqual(routine_lint.validate(self.root), [])
        self.assertEqual(routine_lint.validate(self.root, donor), [])

    def test_alternate_scalar_bundle_uses_manifest_contracts(self):
        self.install_production_bundle()
        self.install_alternate_scalar_bundle()
        donor = self.make_matching_donor()
        self.assertEqual(routine_lint.validate(self.root), [])
        self.assertEqual(routine_lint.validate(self.root, donor), [])

    def test_output_only_scalar_bundle_and_donor_parity(self):
        bundle = self.install_output_only_scalar_bundle()
        graph = self.read_json(
            "routines/g36/example/output-only-scalar/routine.cxf.jsonld"
        )
        root = next(node for node in graph["@graph"] if node["@id"].endswith("output_only_scalar"))
        interface = self.read_json("routines/g36/example/output-only-scalar/interface.json")
        vectors = self.read_json("routines/g36/example/output-only-scalar/vectors.json")
        reference = (bundle / "evidence/reference.dat").read_text(encoding="utf-8")

        self.assertNotIn("S231:hasInput", root)
        self.assertIn("S231:hasOutput", root)
        self.assertEqual(
            [(connector["id"], connector["direction"]) for connector in interface["connectors"]],
            [("TCut", "output")],
        )
        self.assertEqual(vectors["scenarios"][0]["inputs"], {})
        self.assertTrue(vectors["scenarios"][0]["expect"])
        self.assertEqual(
            next(line for line in reference.splitlines() if line.startswith("# columns:")).split()[2:],
            ["time", "temperature_cutoff"],
        )

        donor = self.make_matching_donor()
        self.assertEqual(routine_lint.validate(self.root), [])
        self.assertEqual(routine_lint.validate(self.root, donor), [])

    def test_output_connector_and_nonempty_array_remain_required(self):
        self.install_output_only_scalar_bundle()
        relative = "routines/g36/example/output-only-scalar/interface.json"
        interface = self.read_json(relative)
        interface["connectors"] = [
            {
                "id": "uOnly",
                "direction": "input",
                "value_type": "real",
                "unit": "K",
                "quantity": "ThermodynamicTemperature",
                "shape": "scalar",
            }
        ]
        self.write_json(relative, interface)
        self.assert_error("at least one output connector is required")

        interface["connectors"] = []
        self.write_json(relative, interface)
        self.assert_error("connectors must be a nonempty array")

    def test_output_only_scenario_rejects_undeclared_input(self):
        self.install_output_only_scalar_bundle()
        relative = "routines/g36/example/output-only-scalar/vectors.json"
        vectors = self.read_json(relative)
        vectors["scenarios"][0]["inputs"] = {"uUnexpected": 1.0}
        self.write_json(relative, vectors)
        self.assert_error("'uUnexpected' is not a declared input")

    def test_registry_bundle_bijection_and_required_files(self):
        bundle = self.install_production_bundle()
        (bundle / "interface.json").unlink()
        self.assert_error("interface.json: required bundle file is missing")

        self.install_production_bundle_after_cleanup(bundle)
        (bundle / "LICENSE-BUILDINGS.html").unlink()
        self.assert_error("required Modelica attribution file is missing")

        self.write_registry([])
        self.write_coverage()
        self.assert_error("bundle has no registry row")

    def test_bundle_identity_and_strict_shapes(self):
        bundle = self.install_production_bundle()
        interface = self.read_json(f"routines/{BUNDLE_PATH}/interface.json")
        interface["routine_id"] = "G36-GEN-AEHL__wrong"
        interface["extra"] = True
        self.write_json(f"routines/{BUNDLE_PATH}/interface.json", interface)
        errors = self.assert_error("interface.json: routine_id must equal")
        self.assertTrue(any("unexpected extra" in error for error in errors))

        self.install_production_bundle_after_cleanup(bundle)
        vectors = self.read_json(f"routines/{BUNDLE_PATH}/vectors.json")
        vectors["routine_id"] = "G36-GEN-AEHL__wrong"
        self.write_json(f"routines/{BUNDLE_PATH}/vectors.json", vectors)
        self.assert_error("vectors.json: routine_id must equal")

        self.install_production_bundle_after_cleanup(bundle)
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["routine_id"] = "G36-GEN-AEHL__wrong"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        self.assert_error("provenance.json: routine_id must equal")

    def install_production_bundle_after_cleanup(self, bundle):
        shutil.rmtree(bundle)
        return self.install_production_bundle()

    def test_graph_connector_and_fixed_parameter_mismatch(self):
        bundle = self.install_production_bundle()
        interface = self.read_json(f"routines/{BUNDLE_PATH}/interface.json")
        interface["connectors"][0]["unit"] = "Cel"
        self.write_json(f"routines/{BUNDLE_PATH}/interface.json", interface)
        self.assert_error("connector 'TRet' unit disagrees with interface.json")

        self.install_production_bundle_after_cleanup(bundle)
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["fixed_parameters"]["ashCliZon"] = "wrong"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        self.assert_error("fixed parameter 'ashCliZon' disagrees with provenance.json")

    def test_provenance_source_and_implementation_are_strict(self):
        self.install_production_bundle()
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["upstream"]["source_file"] = "../private.mo"
        provenance["fixed_parameters"] = {}
        provenance["implementation"]["selected_branch"] = ""
        provenance["implementation"]["parameters"]["p"] = "zero"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        errors = self.assert_error("upstream.source_file: parent traversal is forbidden")
        self.assertTrue(any("fixed_parameters must be a nonempty object" in error for error in errors))
        self.assertTrue(any("selected_branch must be a safe nonempty string" in error for error in errors))
        self.assertTrue(any("implementation.parameters.p must be a finite number" in error for error in errors))

    def test_vectors_reject_undeclared_connectors_and_incomplete_donor_coverage(self):
        self.install_production_bundle()
        vectors = self.read_json(f"routines/{BUNDLE_PATH}/vectors.json")
        vectors["scenarios"][0]["inputs"]["unknown"] = 1.0
        vectors["scenarios"][0]["expect"].pop()
        self.write_json(f"routines/{BUNDLE_PATH}/vectors.json", vectors)
        errors = self.assert_error("'unknown' is not a declared input")
        self.assertTrue(
            any("TCut zero-tolerance output expectations must cover" in error for error in errors)
        )

        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["donor_columns"]["connectors"]["TCut"] = "missing_output"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        self.assert_error("mapped columns are missing: missing_output")

    def test_artifact_hash_path_and_donor_drift(self):
        bundle = self.install_production_bundle()
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["artifacts"][0]["sha256"] = "f" * 63
        provenance["artifacts"][1]["local_path"] = "../oracle.txt"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        errors = self.assert_error("sha256: must be lowercase 64-hex")
        self.assertTrue(any("parent traversal is forbidden" in error for error in errors))

        self.install_production_bundle_after_cleanup(bundle)
        donor = self.make_matching_donor()
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        donor_graph = donor / provenance["artifacts"][0]["donor_path"]
        donor_graph.write_bytes(donor_graph.read_bytes() + b"\n")
        errors = routine_lint.validate(self.root, donor)
        self.assertTrue(any("donor bytes differ" in error for error in errors), errors)

        self.install_production_bundle_after_cleanup(bundle)
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["artifacts"] = [
            artifact
            for artifact in provenance["artifacts"]
            if artifact["role"] != "structural_oracle"
        ]
        provenance["artifacts"][-1]["role"] = "donor_metadata"
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        errors = self.assert_error("artifacts missing required roles structural_oracle")
        self.assertTrue(any("require at least one provenance role" in error for error in errors))

    def test_stale_local_artifact_and_private_path_leakage(self):
        bundle = self.install_production_bundle()
        reference = bundle / "golden/reference.csv"
        reference.write_bytes(reference.read_bytes() + b"\n")
        self.assert_error("sha256: does not match golden/reference.csv")

        self.install_production_bundle_after_cleanup(bundle)
        card = bundle / "card.md"
        card.write_text(card.read_text(encoding="utf-8") + "\n/Users/name/private.pdf\n")
        self.assert_error("private document, image, or local path leakage")

    def test_registry_claims_cannot_exceed_provenance(self):
        bundle = self.install_production_bundle()
        provenance = self.read_json(f"routines/{BUNDLE_PATH}/provenance.json")
        provenance["evidence"].pop()
        self.write_json(f"routines/{BUNDLE_PATH}/provenance.json", provenance)
        errors = self.assert_error("registry evidence_tier exceeds completed provenance evidence")
        self.assertTrue(any("registry status exceeds" in error for error in errors))

        self.install_production_bundle_after_cleanup(bundle)
        registry = self.read_json("routines/registry.json")
        registry["routines"][0]["completeness"]["guideline_profile"] = "complete"
        self.write_json("routines/registry.json", registry)
        self.assert_error("completeness.guideline_profile requires E5 evidence")


if __name__ == "__main__":
    unittest.main()
