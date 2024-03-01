import os
from ref.ref import ref_dir, conv, k_c, conv_cmk


def covert_hitran(hitran_file, output_file=None, lam_min=float("-inf"), lam_max=float("inf"), isotope_select=None,
                  as_csv=True):
    """
    Takes a Hitran .dat fail and converts it to a human readable csv file of reference and analysis.
    The output file is automatically added to the Git version control.

    :param hitran_file: str - The full path to the Hitran .dat file to read in and reprocess.
    :param output_file: str or None - When "None" a default output filename is configured the hitran_file.
                                      Otherwise, this variable should be a str that is the full path for
                                      location and filename. Do not include the extension ".csv" or ".txt",
                                      this is added automatically.
    :param lam_min: float - default value of float("-inf")
    :param lam_max: float - default value of float("-inf")
    :param isotope_select: int - default value of None selects all isotopes
    :param as_csv: bool - default True. When True the ".csv" extension is added to the output file and the
                                        and the data is delimited by commas ",". When False the ".txt"
                                        extension is added to the output file and the data is delimited by
                                        whitespace " ".
    :return:
    """
    # Choose an appropriate output filename.
    if output_file is None:
        output_file_base_name, *_ = os.path.basename(hitran_file).split(".")
        output_file_dir_name = os.path.dirname(hitran_file)
        if isotope_select is None:
            output_file = os.path.join(output_file_dir_name, output_file_base_name)
        else:
            output_file = os.path.join(output_file_dir_name,
                                       output_file_base_name + "_isotope" + str(isotope_select))
    if as_csv:
        output_file += ".csv"
    else:
        output_file += ".txt"
    # open and read the Hitran data file
    with open(hitran_file, "r") as f:
        raw_hitran_file = f.readlines()
    # configure the output data's header
    header = "row_number,upper_level,lower_level,wavelength_um,frequency_GHz,einstein_A," + \
             "upper_level_energy,lower_level_energy,g_statistical_weight_upper_level,g_statistical_weight_lower_level"
    if not as_csv:
        header = header.replace(",", " ")
    # creat the body of the output files text
    output_file_text = [header]
    for index, raw_hitran_line in list(enumerate(raw_hitran_file)):
        # extract information to see if this line from the Hitran file should be included in the output file
        isonumb = int(raw_hitran_line[2:3])
        wave = float(raw_hitran_line[3:15])
        freq = wave / conv  # frequency in GHz
        wave_mu = 1.0e6 * k_c / (1.0e9 * freq)  # wavelength in um
        if (isotope_select is None or isonumb == isotope_select) and lam_min < wave_mu < lam_max:
            # extracted remaining information for the output file text
            molnumber = int(raw_hitran_line[0:2])  # not currently used
            astein = float(raw_hitran_line[25:35])
            elo = float(raw_hitran_line[45:55])
            qqup = raw_hitran_line[81:82] + "_" + raw_hitran_line[117:118] + "_" + raw_hitran_line[119:121]
            qqlow = raw_hitran_line[96:97] + "_" + raw_hitran_line[117:118] + "_" + raw_hitran_line[119:121]
            g_up = float(raw_hitran_line[146:153])
            g_low = float(raw_hitran_line[153:160])
            elo = elo * conv_cmk
            eup = elo + conv_cmk * wave
            # formatting of output file if statement
            if as_csv:
                output_file_text.append(F"{index + 1}," +
                                        F"{qqup}," +
                                        F"{qqlow}," +
                                        F"{wave_mu}," +
                                        F"{freq}," +
                                        F"{astein}," +
                                        F"{eup}," +
                                        F"{elo}," +
                                        F"{g_up}," +
                                        F"{g_low}")
            else:
                output_file_text.append(F"{index + 1:6}" +
                                        F"{qqup:15}" +
                                        F"{qqlow:15}" +
                                        F"{wave_mu:11.6f}" +
                                        F"{freq:15.8f}" +
                                        F"{astein:13.4e}" +
                                        F"{eup:15.5f}" +
                                        F"{elo:15.5f}" +
                                        F"{g_up:9.1f}" +
                                        F"{g_low:9.1f}")
    # write out the collected isotope information
    with open(output_file, 'w') as f:
        for output_line in output_file_text:
            f.write(output_line + "\n")
    # add the output file to the git repository
    os.system("git add " + output_file)
    print("Wrote Hitran output file to:", output_file)


if __name__ == "__main__":
    covert_hitran(hitran_file=os.path.join(ref_dir, 'hitran', "hitran_c18o.dat"),
                  lam_min=float('-inf'),
                  lam_max=float("inf"),
                  isotope_select=None,
                  as_csv=True)
