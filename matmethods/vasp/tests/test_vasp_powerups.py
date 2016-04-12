# coding: utf-8

from __future__ import division, print_function, unicode_literals, \
    absolute_import

import unittest

from fireworks import Firework, ScriptTask, Workflow
from matmethods.vasp.input_sets import StructureOptimizationVaspInputSet
from matmethods.vasp.vasp_powerups import decorate_priority, use_custodian, add_trackers, \
    add_modify_incar, add_small_gap_multiplier, use_scratch_dir
from matmethods.vasp.workflows.base.band_structure import get_wf_bandstructure_Vasp
from pymatgen import IStructure
from pymatgen import Lattice

__author__ = 'Anubhav Jain'
__email__ = 'ajain@lbl.gov'


class TestVaspPowerups(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        lattice = Lattice([[3.8401979337, 0.00, 0.00],
                           [1.9200989668, 3.3257101909, 0.00],
                           [0.00, -2.2171384943, 3.1355090603]])
        coords = [[0, 0, 0], [0.75, 0.5, 0.75]]
        struct_si = IStructure(lattice, ["Si"] * 2, coords)
        vis = StructureOptimizationVaspInputSet()
        cls.bs_wf = get_wf_bandstructure_Vasp(struct_si, vis, vasp_cmd="test_VASP")

    def _copy_wf(self, wf):
        return Workflow.from_dict(wf.to_dict())

    def test_decorate_priority(self):
        fw1 = Firework([ScriptTask(script=None)], fw_id=-1)
        fw2 = Firework([ScriptTask(script=None)], parents=[fw1], fw_id=-2)
        fw3 = Firework([ScriptTask(script=None)], parents=[fw1], fw_id=-3)

        wf = Workflow([fw1, fw2, fw3])

        wf = decorate_priority(wf, 4, 8)
        self.assertEqual(wf.id_fw[-1].spec["_priority"], 4)
        self.assertEqual(wf.id_fw[-2].spec["_priority"], 8)
        self.assertEqual(wf.id_fw[-3].spec["_priority"], 8)

    def test_use_custodian(self):
        my_wf = use_custodian(self._copy_wf(self.bs_wf))

        for fw in my_wf.fws:
            task_idx = 1 if "structure optimization" in fw.name else 2
            self.assertTrue(
                "RunVaspCustodian" in fw.to_dict()["spec"]["_tasks"][task_idx]["_fw_name"])
            self.assertEqual(
                fw.to_dict()["spec"]["_tasks"][task_idx]["vasp_cmd"], "test_VASP")

        my_wf_double_relax = use_custodian(self._copy_wf(self.bs_wf),
                                           fw_name_constraint="structure optimization",
                                           custodian_params={"job_type": "double_relaxation_run"})

        for fw in my_wf_double_relax.fws:
            if "structure optimization" in fw.name:
                self.assertTrue("RunVaspCustodian" in fw.to_dict()["spec"]["_tasks"][1]["_fw_name"])
                self.assertEqual(fw.to_dict()["spec"]["_tasks"][1]["job_type"],
                                 "double_relaxation_run")
            else:
                self.assertTrue("RunVaspDirect" in fw.to_dict()["spec"]["_tasks"][2]["_fw_name"])
                self.assertFalse("job_type" in fw.to_dict()["spec"]["_tasks"][2])

    def test_modify_incar(self):
        my_wf = add_modify_incar(self._copy_wf(self.bs_wf), {"key_update": {"NCORE": 1}},
                                 fw_name_constraint="structure optimization")

        for fw in my_wf.fws:
            if "structure optimization" in fw.name:
                self.assertTrue("ModifyIncar" in fw.to_dict()["spec"]["_tasks"][0]["_fw_name"])
                self.assertEqual(fw.to_dict()["spec"]["_tasks"][0]["key_update"], {"NCORE": 1})
            else:
                for t in fw.to_dict()["spec"]["_tasks"]:
                    self.assertFalse("ModifyIncar" in t["_fw_name"])

    def test_add_trackers(self):
        my_wf = add_trackers(self._copy_wf(self.bs_wf))

        for fw in my_wf.fws:
            self.assertEqual(len(fw.spec["_trackers"]), 2)

    def test_add_small_gap_multiplier(self):
        my_wf = self._copy_wf(self.bs_wf)
        my_wf = add_small_gap_multiplier(my_wf, 0.5, 1.5, "static")
        found=False

        for fw in my_wf.fws:
            if "static" in fw.name:
                for t in fw.tasks:
                    if 'WriteVasp' in str(t):
                        self.assertEqual(t["small_gap_multiplier"], [0.5, 1.5])
                        found=True

        self.assertEqual(found, True)

    def test_use_scratch_dir(self):
        my_wf = self._copy_wf(self.bs_wf)
        my_wf = use_custodian(my_wf)
        my_wf = use_scratch_dir(my_wf, ">>scratch_dir<<")
        found = 0

        for fw in my_wf.fws:
            for t in fw.tasks:
                if 'RunVaspCustodian' in str(t):
                    self.assertEqual(t["scratch_dir"], ">>scratch_dir<<")
                    found += 1

        self.assertEqual(found, 4)



if __name__ == "__main__":
    unittest.main()