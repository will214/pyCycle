import numpy as np
import unittest
import os

from openmdao.api import Problem, Group, IndepVarComp
from openmdao.utils.assert_utils import assert_rel_error

from pycycle.cea.species_data import janaf
from pycycle.elements.turbine import Turbine
from pycycle.elements.combustor import Combustor
from pycycle.connect_flow import connect_flow
from pycycle.constants import AIR_FUEL_MIX, AIR_MIX
from pycycle.elements.flow_start import FlowStart
from pycycle.maps.lpt2269 import LPT2269

fpath = os.path.dirname(os.path.realpath(__file__))
ref_data = np.loadtxt(fpath + "/reg_data/turbineOD1.csv",
                      delimiter=",", skiprows=1)

header = [
    'turb.PRdes',
    'turb.effDes',
    'shaft.Nmech',
    'burn.FAR',
    'burn.Fl_I.W',
    'burn.Fl_I.Pt',
    'burn.Fl_I.Tt',
    'burn.Fl_I.ht',
    'burn.Fl_I.s',
    'burn.Fl_I.MN',
    'burn.Fl_I.V',
    'burn.Fl_I.A',
    'burn.Fl_I.Ps',
    'burn.Fl_I.Ts',
    'burn.Fl_I.hs',
    'turb.Fl_I.W',
    'turb.Fl_I.Pt',
    'turb.Fl_I.Tt',
    'turb.Fl_I.ht',
    'turb.Fl_I.s',
    'turb.Fl_I.MN',
    'turb.Fl_I.V',
    'turb.Fl_I.A',
    'turb.Fl_I.Ps',
    'turb.Fl_I.Ts',
    'turb.Fl_I.hs',
    'turb.Fl_O.W',
    'turb.Fl_O.Pt',
    'turb.Fl_O.Tt',
    'turb.Fl_O.ht',
    'turb.Fl_O.s',
    'turb.Fl_O.MN',
    'turb.Fl_O.V',
    'turb.Fl_O.A',
    'turb.Fl_O.Ps',
    'turb.Fl_O.Ts',
    'turb.Fl_O.hs',
    'turb.PR',
    'turb.eff',
    'turb.Np',
    'turb.Wp',
    'turb.pwr',
    'turb.PRmap',
    'turb.effMap',
    'turb.NpMap',
    'turb.WpMap',
    'turb.s_WpDes',
    'turb.s_PRdes',
    'turb.s_effDes',
    'turb.s_NpDes']

h_map = dict(((v_name, i) for i, v_name in enumerate(header)))


class TurbineODTestCase(unittest.TestCase):

    def setUp(self):
        self.prob = Problem()

        des_vars = self.prob.model.add_subsystem('des_vars', IndepVarComp(), promotes=['*'])
        des_vars.add_output('P', 17., units='psi'),
        des_vars.add_output('T', 500.0, units='degR'),
        des_vars.add_output('W', 0., units='lbm/s'),
        des_vars.add_output('Nmech', 1000., units='rpm'),
        des_vars.add_output('area_targ', 150., units='inch**2')
        des_vars.add_output('burner_MN', .01, units=None)
        des_vars.add_output('burner_FAR', .01, units=None)

        self.prob.model.add_subsystem('flow_start', FlowStart(thermo_data=janaf, elements=AIR_MIX))
        self.prob.model.add_subsystem('burner', Combustor(thermo_data=janaf,
                                                          inflow_elements=AIR_MIX,
                                                          air_fuel_elements=AIR_FUEL_MIX,
                                                          fuel_type="JP-7"))
        self.prob.model.add_subsystem(
            'turbine',
            Turbine(
                map_data=LPT2269,
                design=False,
                elements=AIR_FUEL_MIX))

        connect_flow(self.prob.model, "flow_start.Fl_O", "burner.Fl_I")
        connect_flow(self.prob.model, "burner.Fl_O", "turbine.Fl_I")

        self.prob.model.connect("P", "flow_start.P")
        self.prob.model.connect("T", "flow_start.T")
        self.prob.model.connect("W", "flow_start.W")
        self.prob.model.connect("Nmech", "turbine.Nmech")
        self.prob.model.connect("area_targ", "turbine.area")
        self.prob.model.connect("burner_MN", "burner.MN")
        self.prob.model.connect("burner_FAR", "burner.Fl_I:FAR")

        self.prob.set_solver_print(level=-1)
        self.prob.setup(check=False)
        # self.prob.print_all_convergence(1)

        # from openmdao.api import view_model
        # view_model(self.prob)
        # exit()

    def test_case1(self):

        # np.seterr(all='raise')
        # 6 cases to check against
        for i, data in enumerate(ref_data):
            # input turbine variables
            self.prob['turbine.s_Wp'] = data[h_map['turb.s_WpDes']]
            self.prob['turbine.s_eff'] = data[h_map['turb.s_effDes']]
            self.prob['turbine.s_PR'] = data[h_map['turb.s_PRdes']]
            self.prob['turbine.s_Np'] = data[h_map['turb.s_NpDes']]

            self.prob['turbine.map.NpMap']= data[h_map['turb.NpMap']]
            self.prob['turbine.map.PRmap']= data[h_map['turb.PRmap']]

            # input flowstation variables
            self.prob['P'] = data[h_map['burn.Fl_I.Pt']]
            self.prob['T'] = data[h_map['burn.Fl_I.Tt']]
            self.prob['W'] = data[h_map['burn.Fl_I.W']]
            self.prob['burner_MN'] = data[h_map['burn.Fl_I.MN']]
            self.prob['turbine.PR'] = data[h_map['turb.PR']]

            # input shaft variable
            self.prob['Nmech'] = data[h_map['shaft.Nmech']]

            # input burner variable
            self.prob['burner_FAR'] = data[h_map['burn.FAR']]
            # cu(data[h_map['turb.Fl_O.A']],"inch**2", "m**2")
            self.prob['area_targ'] = data[h_map['turb.Fl_O.A']]

            self.prob.run_model()
            # print("n ", self.prob['flow_start.Fl_O:stat:n'])

            print('---- Test Case', i, ' ----')

            print("corrParams --")
            print("Wp", self.prob['turbine.Wp'][0], data[h_map['turb.Wp']])
            print("Np", self.prob['turbine.Np'][0], data[h_map['turb.Np']])

            print("flowConv---")
            print("PR ", self.prob['turbine.PR'][0], data[h_map['turb.PR']])

            print("mapInputs---")
            print("NpMap", self.prob['turbine.map.readMap.NpMap'][0], data[h_map['turb.NpMap']])
            print("PRmap", self.prob['turbine.map.readMap.PRmap'][0], data[h_map['turb.PRmap']])

            print("readMap --")
            print(
                "effMap",
                self.prob['turbine.map.scaledOutput.effMap'][0],
                data[
                    h_map['turb.effMap']])
            print(
                "WpMap",
                self.prob['turbine.map.scaledOutput.WpMap'][0],
                data[
                    h_map['turb.WpMap']])

            print("Scaled output --")
            print("eff", self.prob['turbine.eff'][0], data[h_map['turb.eff']])

            tol = 1.0e-3

            print()
            npss = data[h_map['burn.Fl_I.Pt']]
            pyc = self.prob['flow_start.Fl_O:tot:P'][0]
            print('Pt in:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['burn.Fl_I.s']]
            pyc = self.prob['flow_start.Fl_O:tot:S'][0]
            print('S in:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_O.W']]
            pyc = self.prob['turbine.Fl_O:stat:W'][0]
            print('W in:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_O.ht']] - data[h_map['turb.Fl_I.ht']]
            pyc = self.prob['turbine.Fl_O:tot:h'][0] - self.prob['burner.Fl_O:tot:h'][0]
            print('delta h:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_I.s']]
            pyc = self.prob['burner.Fl_O:tot:S'][0]
            print('S in:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_O.s']]
            pyc = self.prob['turbine.Fl_O:tot:S'][0]
            print('S out:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.pwr']]
            pyc = self.prob['turbine.power'][0]
            print('Power:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_O.Pt']]
            pyc = self.prob['turbine.Fl_O:tot:P'][0]
            print('Pt out:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            # these fail downstream of combustor
            npss = data[h_map['turb.Fl_O.Ps']]
            pyc = self.prob['turbine.Fl_O:stat:P'][0]
            print('Ps out:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)

            npss = data[h_map['turb.Fl_O.Ts']]
            pyc = self.prob['turbine.Fl_O:stat:T'][0]
            print('Ts out:', npss, pyc)
            assert_rel_error(self, pyc, npss, tol)
            # print("")

            # break
            print()


if __name__ == "__main__":
    unittest.main()
