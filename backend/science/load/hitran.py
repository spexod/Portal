import os

from typing import NamedTuple, Optional, Tuple
from bisect import bisect_left, bisect_right
from operator import attrgetter

from ref.ref import hitran_dir, data_pro_dir, k_h, k_c, k_k, conv, conv_cmk

molecule_key = {1: "H2O", 2: "CO2", 3: "O3", 4: "N2O", 5: "CO", 6: "CH4", 7: "O2", 13: "OH"}
molecule_to_label = {"H2O": 'H<sub>2</sub>O',
                     "CO2": 'CO<sub>2</sub>',
                     'OH': 'OH',
                     "O3": 'O<sub>3</sub>',
                     "N2O": 'N<sub>2</sub>O',
                     "CO": 'CO',
                     "CH4": 'CH<sub>4</sub>',
                     "O2": 'O<sub>2</sub>'}

isotopologue_key = {"H2O": {1: "H216O", 2: "H218O", 3: "H217O", 4: "HD16O", 5: "HD18O", 6: "HD17O", 7: "D216O"},
                    "CO": {1: "12C16O", 2: "13C16O", 3: "12C18O", 4: "12C17O", 5: "13C18O", 6: "13C17O"},
                    "OH": {1: "16OH", 2: "18OH", 3: "16OD"},
                    }

isotopologue_to_color = {"H216O": 'mediumblue', "H218O": "royalblue", "H217O": "midnightblue",
                         "HD16O": 'cornflowerblue', 'HD18O': "deepskyblue", 'HD17O': "slateblue", "D216O": 'steelblue',
                         "12C16O": 'forestgreen', "13C16O": "limegreen", "12C18O": "seagreen",
                         "12C17O": 'chartreuse', '13C18O': "olivedrab", '13C17O': "springgreen",
                         "16OH": 'firebrick', "18OH": "crimson", "16OD": "salmon"}

isotopologue_to_label = {"H216O": 'H<sub>2</sub><sup>16</sup>O',
                         "H218O": "H<sub>2</sub><sup>18</sup>O",
                         "H217O": "H<sub>2</sub><sup>17</sup>O",
                         "HD16O": 'HD<sup>16</sup>O',
                         'HD18O': "HD<sup>18</sup>O",
                         'HD17O': "HD<sup>17</sup>O",
                         "D216O": 'D<sub>2</sub><sup>16</sup>O',
                         "12C16O": '<sup>12</sup>C<sup>16</sup>O',
                         "13C16O": "<sup>13</sup>C<sup>16</sup>O",
                         "12C18O": "<sup>12</sup>C<sup>18</sup>O",
                         "12C17O": "<sup>12</sup>C<sup>17</sup>O",
                         '13C18O': "<sup>13</sup>C<sup>18</sup>O",
                         '13C17O': "<sup>13</sup>C<sup>17</sup>O",
                         "16OH": '<sup>16</sup>OH',
                         "18OH": "<sup>18</sup>OH",
                         "16OD": "<sup>16</sup>OD",
                         }

# possible styles {"solid", "dot", "dash", "longdash", "dashdot", "longdashdot"}
plotly_dash_value = {"H216O": 'dot', "H218O": "dot", "H217O": "dot",
                     "HD16O": 'dot', 'HD18O': "dot", 'HD17O': "dot", "D216O": 'dot',
                     "12C16O": 'dash', "13C16O": "dash", "12C18O": "dash",
                     "12C17O": 'dash', '13C18O': "dash", '13C17O': "dash",
                     "16OH": 'longdash', "18OH": "longdash", "16OD": "longdash",
                     }

columns_CO = ['wavelength_um', 'isotopologue', 'upper_level', 'lower_level', 'transition', 'einstein_A',
              'upper_level_energy', 'lower_level_energy', 'g_statistical_weight_upper_level',
              'g_statistical_weight_lower_level', 'upper_vibrational', 'upper_rotational', 'branch',
              'lower_vibrational', 'lower_rotational']
columns_H2O = ['wavelength_um', 'isotopologue', 'upper_level', 'lower_level', 'transition', 'einstein_A',
               'upper_level_energy', 'lower_level_energy', 'g_statistical_weight_upper_level',
               'g_statistical_weight_lower_level', 'upper_vibrational1', 'upper_vibrational2',
               'upper_vibrational3', 'upper_rotational', 'upper_ka', 'upper_kc', 'lower_vibrational1',
               'lower_vibrational2', 'lower_vibrational3', 'lower_rotational', 'lower_ka', 'lower_kc']
columns_OH = ['wavelength_um', 'isotopologue', 'upper_level', 'lower_level', 'transition', 'einstein_A',
              'upper_level_energy', 'lower_level_energy',
              'g_statistical_weight_upper_level', 'g_statistical_weight_lower_level',
              'upper_electrical_state', 'upper_f_prime', 'upper_total_angular_momentum', 'upper_vibrational',
              'lower_branch', 'lower_electrical_state', 'lower_f_double_prime', 'lower_j_double_prime',
              'lower_sym_double_prime', 'lower_total_angular_momentum', 'lower_vibrational']


def make_hl_dict(hitran_line):
    hl_data = {
        'wavelength_um': hitran_line.wavelength_um,
        'isotopologue': hitran_line.isotopologue,
        'upper_level': str(hitran_line.upper_level),
        'lower_level': str(hitran_line.lower_level),
        'transition': hitran_line.transition,
        'einstein_A': hitran_line.einstein_A,
        'upper_level_energy': hitran_line.upper_level_energy,
        'lower_level_energy': hitran_line.lower_level_energy,
        'g_statistical_weight_upper_level': hitran_line.g_statistical_weight_upper_level,
        'g_statistical_weight_lower_level': hitran_line.g_statistical_weight_lower_level,
    }
    if hitran_line.molecule == 'CO':
        hl_data.update({
            'upper_vibrational': hitran_line.upper_level.vibrational,
            'upper_rotational': hitran_line.upper_level.rotational,
            'branch': hitran_line.upper_level.branch,
            'lower_vibrational': hitran_line.lower_level.vibrational,
            'lower_rotational': hitran_line.lower_level.rotational,
        })
    elif hitran_line.molecule == 'H2O':
        hl_data.update({
            'upper_vibrational1': hitran_line.upper_level.vibrational[0],
            'upper_vibrational2': hitran_line.upper_level.vibrational[1],
            'upper_vibrational3': hitran_line.upper_level.vibrational[2],
            'upper_rotational': hitran_line.upper_level.rotational,
            'upper_ka': hitran_line.upper_level.ka,
            'upper_kc': hitran_line.upper_level.kc,
            'lower_vibrational1': hitran_line.lower_level.vibrational[0],
            'lower_vibrational2': hitran_line.lower_level.vibrational[1],
            'lower_vibrational3': hitran_line.lower_level.vibrational[2],
            'lower_rotational': hitran_line.lower_level.rotational,
            'lower_ka': hitran_line.lower_level.ka,
            'lower_kc': hitran_line.lower_level.kc,
        })
    elif hitran_line.molecule == 'OH':
        hl_data.update({
            'upper_electrical_state': hitran_line.upper_level.electrical_state,
            'upper_total_angular_momentum': hitran_line.upper_level.total_angular_momentum,
            'upper_vibrational': hitran_line.upper_level.vibrational,
            'upper_f_prime': hitran_line.upper_level.f_prime,
            'lower_electrical_state': hitran_line.lower_level.electrical_state,
            'lower_total_angular_momentum': hitran_line.lower_level.total_angular_momentum,
            'lower_vibrational': hitran_line.lower_level.vibrational,
            'lower_branch': hitran_line.lower_level.branch,
            'lower_j_double_prime': hitran_line.lower_level.j_double_prime,
            'lower_sym_double_prime': hitran_line.lower_level.sym_double_prime,
            'lower_f_double_prime': hitran_line.lower_level.f_double_prime,
        })
    return hl_data


isotopologue_to_molecule = {}
for molecule in isotopologue_key.keys():
    for key in isotopologue_key[molecule].keys():
        isotopologue = isotopologue_key[molecule][key]
        isotopologue_to_molecule[isotopologue] = molecule

global_quanta_function_keys = {frozenset({"CO", "HF", "HCl"}): "diatomic_a",
                               frozenset({"O2", "NO", "OH", "ClO", "SO"}): "diatomic_b",
                               frozenset({"H2O", "O3", "SO2"}): "non_linear_triatomic"}
local_quanta_function_keys = {frozenset({"CO", "CO2", "N2O"}): "diatomic_and_linear",
                              frozenset({"H2O", "O2", "SO2"}): "asymmetric_rotors",
                              frozenset({"OH"}): "open_shell_diatomics_with_2pi_ground_electronic_states_b",
                              }

global_quanta_functions = {}


def global_quanta(func):
    name_type = func.__name__
    global_quanta_functions[name_type] = func
    return func


@global_quanta
def diatomic_a(upper_global_quanta, lower_global_quanta):
    global_quanta_dict = {"upper_vibrational1": int(upper_global_quanta[-2:].strip()),
                          "lower_vibrational1": int(lower_global_quanta[-2:].strip())}
    return global_quanta_dict


def diatomic_b_either_state(global_quanta: str) -> Tuple[str, str, int]:
    electrical_state = global_quanta[6:8].strip()
    total_angular_momentum = global_quanta[8:11].strip()
    vibrational = int(global_quanta[13:].strip())
    return electrical_state, total_angular_momentum, vibrational


@global_quanta
def diatomic_b(upper_global_quanta, lower_global_quanta):
    upper_electrical_state, upper_total_angular_momentum, upper_vibrational = \
        diatomic_b_either_state(upper_global_quanta)
    lower_electrical_state, lower_total_angular_momentum, lower_vibrational = \
        diatomic_b_either_state(lower_global_quanta)
    return {'upper_electrical_state': upper_electrical_state,
            'upper_total_angular_momentum': upper_total_angular_momentum,
            'upper_vibrational': upper_vibrational,
            'lower_electrical_state': lower_electrical_state,
            'lower_total_angular_momentum': lower_total_angular_momentum,
            'lower_vibrational': lower_vibrational}


def non_linear_triatomic_either_state(global_quanta_str):
    info_str = global_quanta_str[-6:]
    vibrational1 = int(info_str[:2].strip())
    vibrational2 = int(info_str[2:4].strip())
    vibrational3 = int(info_str[4:].strip())
    return vibrational1, vibrational2, vibrational3


@global_quanta
def non_linear_triatomic(upper_global_quanta, lower_global_quanta):
    global_quanta_dict = {"upper_vibrational1": non_linear_triatomic_either_state(upper_global_quanta)[0],
                          "upper_vibrational2": non_linear_triatomic_either_state(upper_global_quanta)[1],
                          "upper_vibrational3": non_linear_triatomic_either_state(upper_global_quanta)[2],
                          "lower_vibrational1": non_linear_triatomic_either_state(lower_global_quanta)[0],
                          "lower_vibrational2": non_linear_triatomic_either_state(lower_global_quanta)[1],
                          "lower_vibrational3": non_linear_triatomic_either_state(lower_global_quanta)[2]}
    return global_quanta_dict


local_quanta_functions = {}


def local_quanta(func):
    name_type = func.__name__
    local_quanta_functions[name_type] = func
    return func


@local_quanta
def diatomic_and_linear(upper_local_quanta, lower_local_quanta):
    local_quanta_dict = {"f_prime": upper_local_quanta[-5:].strip(),
                         "branch": lower_local_quanta[5:6].strip(),
                         "j_double_prime": int(lower_local_quanta[6:9].strip()),
                         "sym_double_prime": lower_local_quanta[9:10].strip(),
                         "f_double_prime": lower_local_quanta[10:15].strip()}
    return local_quanta_dict


def asymmetric_rotors_either_state(local_quanta):
    local_quanta_dict = {"j": int(local_quanta[:3].strip()),
                         "ka": int(local_quanta[3:6].strip()),
                         "kc": int(local_quanta[6:9].strip()),
                         "f": local_quanta[9:14].strip(),
                         "sym": local_quanta[14:].strip()}
    return local_quanta_dict


@local_quanta
def asymmetric_rotors(upper_local_quanta, lower_local_quanta):
    local_quanta_dict = {}
    upper_local_quanta_dict = asymmetric_rotors_either_state(upper_local_quanta)
    for quantum_name in upper_local_quanta_dict.keys():
        local_quanta_dict["upper_" + quantum_name] = upper_local_quanta_dict[quantum_name]
    lower_local_quanta_dict = asymmetric_rotors_either_state(lower_local_quanta)
    for quantum_name in lower_local_quanta_dict.keys():
        local_quanta_dict["lower_" + quantum_name] = lower_local_quanta_dict[quantum_name]
    return local_quanta_dict


@local_quanta
def open_shell_diatomics_with_2pi_ground_electronic_states_b(upper_local_quanta, lower_local_quanta):
    local_quanta_dict = {"f_prime": upper_local_quanta[-5:].strip(),
                         "branch": lower_local_quanta[1:3].strip(),
                         "j_double_prime": float(lower_local_quanta[3:8].strip()),
                         "sym_double_prime": lower_local_quanta[8:10].strip(),
                         "f_double_prime": lower_local_quanta[10:].strip()}
    return local_quanta_dict


def parse_quanta(molecule, upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta):
    for molecule_set in global_quanta_function_keys:
        if molecule in molecule_set:
            global_quanta_function_name = global_quanta_function_keys[molecule_set]
            break
    else:
        raise KeyError("molecule " + str(molecule) + " not defined in global_quanta_function_keys")
    for molecule_set in local_quanta_function_keys:
        if molecule in molecule_set:
            local_quanta_function_name = local_quanta_function_keys[molecule_set]
            break
    else:
        raise KeyError("molecule " + str(molecule) + " not defined in global_quanta_function_keys")
    quanta_dict = {}
    quanta_dict.update(global_quanta_functions[global_quanta_function_name](upper_global_quanta, lower_global_quanta))
    quanta_dict.update(local_quanta_functions[local_quanta_function_name](upper_local_quanta, lower_local_quanta))
    for quantum in list(quanta_dict.keys()):
        if quanta_dict[quantum] == "":
            del quanta_dict[quantum]
    return quanta_dict


class QuantaCO(NamedTuple):
    vibrational: int
    branch: str
    rotational: int

    def __str__(self):
        return "(v=" + str(self.vibrational) + ") " + self.branch + "-branch (J=" + str(self.rotational) + ")"


class QuantaH2O(NamedTuple):
    vibrational: tuple
    rotational: int
    ka: int
    kc: int

    def __str__(self):
        return "v=(" + str(self.vibrational[0]) + " " + str(self.vibrational[1]) + " " + \
               str(self.vibrational[2]) + ") J=" + str(self.rotational) + " Ka=" + str(self.ka) + " Kc=" + str(self.kc)


class QuantaUpperOH(NamedTuple):
    electrical_state: str
    total_angular_momentum: str
    vibrational: int
    f_prime: Optional[str] = None

    def __str__(self):
        if self.f_prime is None:
            return f'X omega V ({self.electrical_state} {self.total_angular_momentum} {self.vibrational})'
        else:
            return f'X omega V F ({self.electrical_state} {self.total_angular_momentum} {self.vibrational} ' + \
                f'{self.f_prime})'



class QuantaLowerOH(NamedTuple):
    electrical_state: str
    total_angular_momentum: str
    vibrational: int
    branch: str
    j_double_prime: float
    sym_double_prime: str
    f_double_prime: Optional[str] = None

    def __str__(self):
        if self.f_double_prime is None:
            return f'({self.electrical_state} {self.total_angular_momentum} {self.vibrational}) ' + \
                         f'{self.branch} {self.j_double_prime} {self.sym_double_prime}'
        else:
            return f'({self.electrical_state} {self.total_angular_momentum} ' + \
                   f'{self.vibrational} {self.f_double_prime}) {self.branch} {self.j_double_prime} ' + \
                   f'{self.sym_double_prime}'


quanta_summary_functions = {}


def quanta_summary(func):
    name_type = func.__name__.lower()
    quanta_summary_functions[name_type] = func
    return func


@quanta_summary
def co(upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta):
    quanta = parse_quanta("CO", upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta)
    qqup = QuantaCO(vibrational=quanta["upper_vibrational1"],
                    branch=quanta["branch"],
                    rotational=quanta['j_double_prime'])
    qqlow = QuantaCO(vibrational=quanta["lower_vibrational1"],
                     branch=quanta["branch"],
                     rotational=quanta['j_double_prime'])
    transition = "v" + str(qqup.vibrational) + "-" + str(qqlow.vibrational) + " " + \
                 qqup.branch + "-" + str(qqup.rotational)
    return qqup, qqlow, transition


@quanta_summary
def h2o(upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta):
    quanta = parse_quanta("H2O", upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta)
    qqup = QuantaH2O(vibrational=(quanta["upper_vibrational1"],
                                  quanta["upper_vibrational2"],
                                  quanta["upper_vibrational3"]),
                     rotational=quanta['upper_j'],
                     ka=quanta['upper_ka'],
                     kc=quanta['upper_kc'])
    qqlow = QuantaH2O(vibrational=(quanta["lower_vibrational1"],
                                   quanta["lower_vibrational2"],
                                   quanta["lower_vibrational3"]),
                      rotational=quanta['lower_j'],
                      ka=quanta['lower_ka'],
                      kc=quanta['lower_kc'])
    if qqup.vibrational == qqlow.vibrational:
        transition = "J Ka Kc (" + str(qqup.rotational) + " " + str(qqup.ka) + " " + str(qqup.kc) + ")->(" + \
                     str(qqlow.rotational) + " " + str(qqlow.ka) + " " + str(qqlow.kc) + ")"
    else:
        transition = "v1 v2 v3 J Ka Kc (" + str(qqup.vibrational[0]) + " " + str(qqup.vibrational[1]) + " " + \
                     str(qqup.vibrational[2]) + " " + str(qqup.rotational) + " " + str(qqup.ka) + " " + str(qqup.kc) + \
                     ")->(" + str(qqlow.vibrational[0]) + " " + str(qqlow.vibrational[1]) + " " + \
                     str(qqlow.vibrational[2]) + " " + str(qqlow.rotational) + " " + str(qqlow.ka) + " " + str(
            qqlow.kc) + ")"
    return qqup, qqlow, transition


@quanta_summary
def oh(upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta):
    quanta = parse_quanta('OH', upper_global_quanta, lower_global_quanta, upper_local_quanta, lower_local_quanta)
    if "f_prime" in quanta.keys():
        f_prime = quanta['f_prime']
    else:
        f_prime = None
    if "f_double_prime" in quanta.keys():
        f_double_prime = quanta['f_double_prime']
    else:
        f_double_prime = None
    qqup = QuantaUpperOH(electrical_state=quanta['upper_electrical_state'],
                         total_angular_momentum=quanta['upper_total_angular_momentum'],
                         vibrational=quanta['upper_vibrational'],
                         f_prime=f_prime)
    qqlow = QuantaLowerOH(electrical_state=quanta['lower_electrical_state'],
                          total_angular_momentum=quanta['lower_total_angular_momentum'],
                          vibrational=quanta['lower_vibrational'],
                          branch=quanta['branch'],
                          j_double_prime=quanta['j_double_prime'],
                          sym_double_prime=quanta['sym_double_prime'],
                          f_double_prime=f_double_prime)
    if (f_prime is None and f_double_prime is None) or (f_prime is not None and f_double_prime is not None):
        transition = f'{qqlow}->{qqup}'
    else:
        raise ValueError('OH must have both f_prime and f_double_prime to be None or both not None')
    return qqup, qqlow, transition


class HitranLine(NamedTuple):
    molecule: str
    isotopologue: str
    wavelength_um: float
    frequency_GHz: float
    einstein_A: float
    upper_level_energy: float
    lower_level_energy: float
    g_statistical_weight_upper_level: float
    g_statistical_weight_lower_level: float
    transition: Optional[str] = None
    upper_level: Optional[NamedTuple] = None
    lower_level: Optional[NamedTuple] = None

    def __str__(self):
        string_line = str(self.wavelength_um) + "," + self.molecule + "," + self.isotopologue + "," + \
                      str(self.transition) + "," + str(self.upper_level) + "," + str(self.lower_level) + "," + \
                      str(self.frequency_GHz) + "," + str(self.einstein_A) + "," + \
                      str(self.upper_level_energy) + "," + str(self.lower_level_energy) + "," + \
                      str(self.g_statistical_weight_upper_level) + "," + str(self.g_statistical_weight_lower_level)
        return string_line


hitran_line_header = "wavelength_um,molecule,isotopologue,transition,upper_level,lower_level,frequency_GHz,einstein_A," + \
                     "upper_level_energy,lower_level_energy," + \
                     "g_statistical_weight_upper_level,g_statistical_weight_lower_level"


def translate_line(raw_line):
    molnumber = int(raw_line[0:2])
    molecule = molecule_key[molnumber]
    isotopologue_number = int(raw_line[2:3])
    isotopologue = isotopologue_key[molecule][isotopologue_number]
    wave = float(raw_line[3:15])
    freq = wave / conv  # frequency in GHz
    wave_mu = 1.0e6 * k_c / (1.0e9 * freq)  # wavelength in um
    # line_intensity = float(raw_line[15:25])
    astein = float(raw_line[25:35])
    # air_broadened_width = float(raw_line[35:40])
    # self_broadened_width = float(raw_line[40:45])
    elo = float(raw_line[45:55])
    temp_dependence = float(raw_line[55:59])
    pressure_shift = float(raw_line[59:67])
    upper_global_quanta = raw_line[67:82]
    lower_global_quanta = raw_line[82:97]
    upper_local_quanta = raw_line[97:112]
    lower_local_quanta = raw_line[112:127]
    qqup, qqlow, transition = quanta_summary_functions[molecule.lower()](upper_global_quanta, lower_global_quanta,
                                                                         upper_local_quanta, lower_local_quanta)
    # error_codes = tuple([int(num) for num in raw_line[127:133]])
    # reference_codes = tuple([int(raw_line[index:index + 2]) for index in range(133, 145, 2)])
    # if raw_line[145:146] == " ":
    #     line_mixing_flag = False
    # else:
    #     line_mixing_flag = True
    g_up = float(raw_line[146:153])
    g_low = float(raw_line[153:160])
    elo = elo * conv_cmk
    eup = elo + conv_cmk * wave
    hl = HitranLine(molecule=molecule, isotopologue=isotopologue, upper_level=qqup, lower_level=qqlow,
                    wavelength_um=wave_mu, frequency_GHz=freq, einstein_A=astein,
                    upper_level_energy=eup, lower_level_energy=elo,
                    g_statistical_weight_upper_level=g_up, g_statistical_weight_lower_level=g_low,
                    transition=transition)
    return hl


def reductive_filter(things_to_filter, single_thing, thing_to_check, value_key, desired_keys):
    if thing_to_check.__getattribute__(value_key) in desired_keys:
        return True
    else:
        things_to_filter.remove(single_thing)
        return False


def reductive_set_filter(things_to_filter, value_key, desired_keys):
    if desired_keys is not None:
        for hitran_line in list(things_to_filter):
            reductive_filter(things_to_filter, hitran_line, hitran_line, value_key, desired_keys)


def level_reductive_filter_co(things_to_filter, level, vibrational_levels, branches, rotational_levels):
    if any((vibrational_levels is not None, branches is not None, rotational_levels is not None)):
        for hitran_line in list(things_to_filter):
            if hitran_line.molecule == "CO":
                keep_flag = True
                if vibrational_levels is not None and \
                        hitran_line.__getattribute__(level).vibrational not in vibrational_levels:
                    keep_flag = False
                if keep_flag and branches is not None and \
                        hitran_line.__getattribute__(level).branch not in branches:
                    keep_flag = False
                if keep_flag and rotational_levels is not None and \
                        hitran_line.__getattribute__(level).rotational not in rotational_levels:
                    keep_flag = False
                if not keep_flag:
                    things_to_filter.remove(hitran_line)


def level_reductive_filter_h2o(things_to_filter, level, allowed_vibrational_quanta,
                               allowed_rotational, allowed_ka, allowed_kc):
    if any((allowed_vibrational_quanta is not None, local_quanta is not None, allowed_rotational is not None,
            allowed_ka is not None, allowed_kc)):
        for hitran_line in list(things_to_filter):
            if hitran_line.molecule == "H2O":
                removed_flag = False
                level_this_line = hitran_line.__getattribute__(level)
                if allowed_vibrational_quanta is not None:
                    removed_flag = reductive_filter(things_to_filter, hitran_line, level_this_line,
                                                    "vibrational", allowed_vibrational_quanta)
                if not removed_flag and allowed_rotational is not None:
                    removed_flag = reductive_filter(things_to_filter, hitran_line, level_this_line,
                                                    "rotational", allowed_rotational)
                if not removed_flag and allowed_ka is not None:
                    removed_flag = reductive_filter(things_to_filter, hitran_line, level_this_line, "ka", allowed_ka)
                if not removed_flag and allowed_ka is not None:
                    reductive_filter(things_to_filter, hitran_line, level_this_line, "kc", allowed_ka)


class Hitran:
    def __init__(self, auto_load=True, data=None, verbose=False):
        self.verbose = verbose
        self.full_paths = []
        for f in os.listdir(hitran_dir):
            test_file_name = os.path.join(hitran_dir, f)
            if os.path.isfile(test_file_name):
                _prefix, extension = test_file_name.rsplit(".", 1)
                if extension == "par":
                    self.full_paths.append(test_file_name)

        self.data = set()
        self.ordered_data = None
        self.wavelength_list = None
        self.ref_dic_molecule = None
        self.ref_dic_isotopologue = None
        if data is None:
            if auto_load:
                self.load()
        else:
            self.receive(data=data)

    def wavelength_sort(self):
        self.ordered_data = sorted(self.data, key=attrgetter('wavelength_um'))
        self.wavelength_list = [hitran_line.wavelength_um for hitran_line in self.ordered_data]

    def load(self):
        for path in self.full_paths:
            if self.verbose:
                print(f"    Loading: {path}")
            with open(path, 'r') as f:
                for raw_line in f:
                    self.data.add(translate_line(raw_line))
        self.wavelength_sort()

    def receive(self, data):
        self.data = set(data)
        self.wavelength_sort()

    def get_wavelength_range(self, min_wavelength_um=float("-inf"), max_wavelength_um=float("inf")):
        start_index = bisect_left(self.wavelength_list, min_wavelength_um)
        end_index = bisect_right(self.wavelength_list, max_wavelength_um)
        return self.ordered_data[start_index:end_index]

    def find_closest(self, target_wavelength, n=1):
        target_index = bisect_right(self.wavelength_list, target_wavelength)

        start_index = max(0, target_index - n)
        end_index = min(len(self.wavelength_list), target_index + n)
        if end_index - start_index < n:
            raise IndexError("Not enough elements in self.ordered_data to return " + str(n) + " elements")
        diff_list = [abs(wavelength - target_wavelength)
                     for wavelength in self.wavelength_list[start_index: end_index]]
        data_list = self.ordered_data[start_index: end_index]
        sorted_data_list = [hitran_line for _, hitran_line in sorted(zip(diff_list, data_list))]
        return sorted_data_list[0: n]

    def get_lines(self, min_wavelength_um=None, max_wavelength_um=None,
                  molecules=None, isotopologues=None,
                  upper_vibrational_levels_co=None, branch_co=None, upper_rotational_levels_co=None,
                  lower_vibrational_levels_co=None, lower_rotational_levels_co=None,
                  upper_vibrational_quanta_h20=None, upper_rotational_h2o=None, upper_ka_h2o=None, upper_kc_h2o=None,
                  lower_vibrational_quanta_h20=None, lower_rotational_h2o=None, lower_ka_h2o=None, lower_kc_h2o=None):
        if min_wavelength_um is None:
            min_wavelength_um = float("-inf")
        if max_wavelength_um is None:
            max_wavelength_um = float("inf")
        filtered = set(self.get_wavelength_range(min_wavelength_um, max_wavelength_um))

        reductive_set_filter(filtered, 'molecule', molecules)
        reductive_set_filter(filtered, 'isotopologue', isotopologues)
        level_reductive_filter_co(filtered, "upper_level",
                                  upper_vibrational_levels_co, branch_co, upper_rotational_levels_co)
        level_reductive_filter_co(filtered, "lower_level",
                                  lower_vibrational_levels_co, branch_co, lower_rotational_levels_co)
        level_reductive_filter_h2o(filtered, "upper_level", upper_vibrational_quanta_h20, upper_rotational_h2o,
                                   upper_ka_h2o, upper_kc_h2o)
        level_reductive_filter_h2o(filtered, "lower_level", lower_vibrational_quanta_h20, lower_rotational_h2o,
                                   lower_ka_h2o, lower_kc_h2o)
        from_filter = Hitran(auto_load=False)
        from_filter.receive(data=filtered)
        return from_filter

    def write(self, file_name=None):
        if file_name is None:
            file_name = "hitran_output.csv"
        parent_dir = os.path.join(data_pro_dir, 'hitran')
        if not os.path.isdir(parent_dir):
            os.mkdir(parent_dir)
        path = os.path.join(parent_dir, file_name)
        with open(path, 'w') as f:
            f.write(hitran_line_header + "\n")
            for hitran_line in self.ordered_data:
                f.write(str(hitran_line) + "\n")
        print("Hitran output file written to:", path)


class HitranRef(Hitran):
    def ref_iso(self, isotopologue, filter_dict=None):
        mol_found = False
        for molecule in isotopologue_key.keys():
            for dict_key in isotopologue_key[molecule].keys():
                if isotopologue_key[molecule][dict_key] == isotopologue:
                    mol_found = True
                    break
            if mol_found:
                break
        else:
            raise KeyError("isotopologue not found")
        molecule_data = self.ref_mol(molecule)
        if self.ref_dic_isotopologue is None:
            self.ref_dic_isotopologue = {}
        if isotopologue not in self.ref_dic_isotopologue.keys():
            if filter_dict is None:
                self.ref_dic_isotopologue[isotopologue] = molecule_data.get_lines(isotopologues={isotopologue})
            else:
                self.ref_dic_isotopologue[isotopologue] = molecule_data.get_lines(isotopologues={isotopologue},
                                                                                  **filter_dict)
        return self.ref_dic_isotopologue[isotopologue]

    def ref_mol(self, molecule):
        if self.ref_dic_molecule is None:
            self.ref_dic_molecule = {}
        if molecule not in self.ref_dic_molecule.keys():
            self.ref_dic_molecule[molecule] = self.get_lines(molecules={molecule})
        return self.ref_dic_molecule[molecule]


if __name__ == "__main__":
    # style for looking of line fluxes super fast
    h = HitranRef()
    iso_data = h.ref_iso("12C16O")
    iso_closest_lines = iso_data.find_closest(target_wavelength=4.7545000, n=2)

    # style for getting all lines based on filter tools
    h_CO = h.get_lines(molecules={'CO'}, isotopologues=None)
    wave_list = h_CO.get_wavelength_range(min_wavelength_um=float("-inf"), max_wavelength_um=3)
    closest_lines = h_CO.find_closest(target_wavelength=4.7545000, n=20)

    # use set notation  {"3", "2", "R"} or None
    general_filter = h.get_lines(min_wavelength_um=None, max_wavelength_um=None,
                                 molecules={"H2O"}, isotopologues={'H216O'},
                                 upper_vibrational_levels_co=None, branch_co=None, upper_rotational_levels_co=None,
                                 lower_vibrational_levels_co=None, lower_rotational_levels_co=None,
                                 upper_vibrational_quanta_h20={(0, 0, 0)},
                                 upper_rotational_h2o=None, upper_ka_h2o=None, upper_kc_h2o=None,
                                 lower_vibrational_quanta_h20={(0, 0, 0)},
                                 lower_rotational_h2o=None, lower_ka_h2o=None, lower_kc_h2o=None)
    general_filter.write()
