from __future__ import annotations

import unittest

from mva_solver.vcf import parse_query_line


class VcfQueryTest(unittest.TestCase):
    def test_parse_biallelic_call(self) -> None:
        parsed = parse_query_line(
            "15\t100\trs1\ta\tg\t99\tPASS\t0/1\t12,8\t20\t45\t.\t.\n"
        )
        self.assertEqual(parsed.key, ("15", 100, "A", "G"))
        self.assertAlmostEqual(parsed.allele_balance or 0.0, 8 / 20)
        self.assertIsNone(parsed.phase_set)

    def test_rejects_unexpected_shape(self) -> None:
        with self.assertRaises(ValueError):
            parse_query_line("too\tfew\tfields\n")


if __name__ == "__main__":
    unittest.main()
