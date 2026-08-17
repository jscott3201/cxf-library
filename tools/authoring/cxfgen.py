"""Helpers for generating fault-rule CXF documents and vectors (SCHEMA.md contracts).

Used by per-fault authoring scripts:

    from cxfgen import Doc, square, write_json
    d = Doc("ahu-fc-059", "ahu_fc_059")
    d.block("htgOpen", "Reals.GreaterThreshold", params={"t": "5.0"}, ins=["u"], outs=["y"])
    ...

The generated JSON matches the engine's composite-subset dialect exactly
(flat @graph, full IRIs, S231 prefix, typed literals).
"""

import json

XSD_D = "http://www.w3.org/2001/XMLSchema#double"
XSD_B = "http://www.w3.org/2001/XMLSchema#boolean"
XSD_I = "http://www.w3.org/2001/XMLSchema#integer"

PORT_TYPES = {
    "real_in": ("S231:RealInput", "S231:Real"),
    "real_out": ("S231:RealOutput", "S231:Real"),
    "bool_in": ("S231:BooleanInput", "S231:Boolean"),
    "bool_out": ("S231:BooleanOutput", "S231:Boolean"),
    "int_in": ("S231:IntegerInput", "S231:Integer"),
    "int_out": ("S231:IntegerOutput", "S231:Integer"),
}


class Doc:
    """One fault-rule CXF document under `urn:cxf-library:<fault-id>#<root_label>`."""

    def __init__(self, fault_id_lower, root_label):
        self.ns = f"urn:cxf-library:{fault_id_lower}#"
        self.root_id = self.ns + root_label
        self.root_label = root_label
        self.contains = []
        self.inputs = []
        self.outputs = []
        self.nodes = []

    def _iri(self, local):
        return {"@id": f"{self.root_id}.{local}"}

    def _one_or_many(self, refs):
        return refs[0] if len(refs) == 1 else refs

    def block(self, label, cls, params=None, ins=None, outs=None):
        """A contained elementary-block instance; params maps name -> (value, xsd) or value str."""
        self.contains.append(label)
        node = {
            "@id": f"{self.root_id}.{label}",
            "@type": f"{self.ns}Buildings.Controls.OBC.CDL.{cls}",
            "S231:label": label,
        }
        if params:
            node["S231:hasParameter"] = self._one_or_many(
                [self._iri(f"{label}.{p}") for p in params]
            )
        if ins:
            node["S231:hasInput"] = self._one_or_many([self._iri(f"{label}.{p}") for p in ins])
        if outs:
            node["S231:hasOutput"] = self._one_or_many([self._iri(f"{label}.{p}") for p in outs])
        self.nodes.append(node)
        for p, spec in (params or {}).items():
            value, xsd = spec if isinstance(spec, tuple) else (spec, XSD_D)
            self.nodes.append(
                {
                    "@id": f"{self.root_id}.{label}.{p}",
                    "S231:value": {"@value": value, "@type": xsd},
                }
            )

    def port(self, local, kind, to=None):
        """A connector node; `to` lists local names of destination inputs."""
        t, dt = PORT_TYPES[kind]
        node = {"@id": f"{self.root_id}.{local}", "@type": t, "S231:isOfDataType": {"@id": dt}}
        if to:
            node["S231:isConnectedTo"] = self._one_or_many([self._iri(d) for d in to])
        self.nodes.append(node)

    def boundary_input(self, name, kind, to):
        self.inputs.append(name)
        self.port(name, kind, to)

    def boundary_output(self, name, kind="bool_out"):
        self.outputs.append(name)
        self.port(name, kind)

    def tdelay(self, label, delay, to, delay_on_init=True):
        """Convenience: a Logical.TrueDelay with the library's startup-conservatism default."""
        self.block(
            label,
            "Logical.TrueDelay",
            params={
                "delayTime": (delay, XSD_D),
                "delayOnInit": ("true" if delay_on_init else "false", XSD_B),
            },
            ins=["u"],
            outs=["y"],
        )
        self.port(f"{label}.u", "bool_in")
        self.port(f"{label}.y", "bool_out", to)

    def finish(self):
        root = {
            "@id": self.root_id,
            "@type": "S231:Block",
            "S231:label": self.root_label,
            "S231:containsBlock": [self._iri(b) for b in self.contains],
            "S231:hasInput": [self._iri(i) for i in self.inputs],
            "S231:hasOutput": [self._iri(o) for o in self.outputs],
        }
        return {
            "@context": {"S231": "http://data.ashrae.org/S231P#", "base": self.ns},
            "@graph": [root] + self.nodes,
        }

    def write(self, path):
        write_json(path, self.finish())


def square(t0, period, a, b, horizon):
    """Piecewise-constant square wave as a vectors.json step list."""
    steps, t, v = [], t0, a
    while t <= horizon:
        steps.append({"t": t, "value": v})
        v = b if v == a else a
        t += period
    return steps


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    print("wrote", path)
