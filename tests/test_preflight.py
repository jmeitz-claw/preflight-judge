"""stdlib unittest suite for the pre-flight panel."""
import unittest

from preflight import screen, screen_candidate, survivors, PanelConfig


def series(values, start_ts=0, prefix="s"):
    return [{"value": v, "ts": start_ts + i, "id": f"{prefix}{i}"} for i, v in enumerate(values)]


class TestPanel(unittest.TestCase):
    def setUp(self):
        self.cfg = PanelConfig.default()

    def test_genuine_survives(self):
        c = {"id": "g", "observations": series([1.0] * 40)}
        r = screen_candidate(c, [c], self.cfg)
        self.assertTrue(r.survived)
        self.assertGreater(r.effect, 0)

    def test_null_refuted_by_bootstrap(self):
        c = {"id": "n", "observations": series([1.0, -1.0] * 30)}
        r = screen_candidate(c, [c], self.cfg)
        self.assertFalse(r.survived)
        self.assertIn("bootstrap_stability", r.refuted_lenses())

    def test_regime_refuted_by_temporal(self):
        c = {"id": "r",
             "observations": series([1.0] * 20, 0, "a") + series([-1.0] * 20, 100, "b")}
        r = screen_candidate(c, [c], self.cfg)
        self.assertFalse(r.survived)
        self.assertIn("temporal_robustness", r.refuted_lenses())

    def test_redundancy(self):
        parent = {"id": "parent", "observations": series([1.0] * 60, prefix="p")}
        child = {"id": "child", "observations": parent["observations"][:40]}
        res = {x.candidate_id: x for x in screen([parent, child], self.cfg)}
        self.assertFalse(res["child"].survived)
        self.assertIn("redundancy", res["child"].refuted_lenses())
        self.assertTrue(res["parent"].survived)

    def test_practical_haircut_is_advisory(self):
        cfg = PanelConfig(effect_haircut=0.02, practical_floor=0.03)
        c = {"id": "thin", "observations": series([0.03] * 200)}
        r = screen_candidate(c, [c], cfg)
        self.assertIn("practical_haircut", r.refuted_lenses())
        self.assertTrue(r.survived)  # advisory cannot kill alone

    def test_deterministic(self):
        c = {"id": "g", "observations": series([1.0] * 40)}
        self.assertEqual(screen_candidate(c, [c], self.cfg).to_dict(),
                         screen_candidate(c, [c], self.cfg).to_dict())

    def test_survivors_filter(self):
        genuine = {"id": "g", "observations": series([1.0] * 40)}
        null = {"id": "n", "observations": series([1.0, -1.0] * 30, prefix="n")}
        kept = {c["id"] for c in survivors([genuine, null], self.cfg)}
        self.assertEqual(kept, {"g"})

    def test_thin_data_never_refuted(self):
        c = {"id": "tiny", "observations": [{"value": 1.0, "id": "z"}]}
        self.assertTrue(screen_candidate(c, [c], self.cfg).survived)


if __name__ == "__main__":
    unittest.main()
