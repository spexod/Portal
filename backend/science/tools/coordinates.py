from operator import itemgetter
from numpy import dot, sqrt, pi, sin, cos, tan, arcsin, arccos, arctan2
import numpy

twopi = 2.0*pi
halfpi = pi/2.0
degToRad = pi/180.0
rad_to_deg = 180.0/pi


"""
Constants 
"""

# J2000 (the angle between Earth's axis of rotation and the line normal to the plane of the ecliptic)
axialTilt_J2000 = 23.0 + (26.0 / 60.0) + (21.448 / 3600.0)  # degrees
axialTilt_J2000_rad = axialTilt_J2000 * degToRad
sinAxilTilt = sin(axialTilt_J2000_rad)
cosAxilTilt = cos(axialTilt_J2000_rad)

# Inclination of the Galactic Plane to the celestial equator
iG = 62.6  # degrees for epoch B1950.0

# Right Ascension of the ascending Node of the galactic Plane (the right ascension point at which the galactic
# plane crosses the celestial equator, heading northwards in the direction of increasing galactic longitude)
aN = 282.25  # degrees at for epoch B1950.0

# the galactic longitude of the ascending node of the galactic plane
l0 = 33.0  # degrees at B1950.0

"""

Basic Tools

"""

"""
This function is designed to deal with phase wrapping that may happen with float errors, 
phi near a pole should stay near the pole.
Input: phi in degrees in the set (-inf, inf) Example: phi=80->80, phi=100->80, phi=260->-80
Output: pi in degrees in the set [-90, 90]
"""


def phi_between_minus90and90(phi):
    phi = float(phi)
    while phi < -90.0:
        phi += 360.0
    while 270.0 < phi:
        phi -= 360.0
    if 90.0 < phi:
        phi = 180.0 - phi
    return phi


def astro_phase_clip(theta_phi):
    (theta, phi) = theta_phi
    return theta % 360.0, phi_between_minus90and90(phi)


"""
This function is designed to deal with phase wrapping that may happen with float errors, phi near a pole should stay 
near the pole.
Input: phi in radians in the set (-inf, inf) Example: phi=halfpi->halfpi, phi=pi+delta->pi-delta (for positive delta)
Output: pi in radians in the set [0, pi]
"""


def phi_between0and_pi(phi):
    phi = float(phi)
    while phi < 0:
        phi += pi
    while twopi < phi:
        phi -= pi
    if pi < phi:
        phi = twopi - phi
    return phi


def sph_phase_clip(theta_phi):
    (theta, phi) = theta_phi
    return theta % twopi, phi_between0and_pi(phi)


# This is to deal with float errors when one float is divided by itself and gives a value greater than 1
def num_be_between_minus1and1(number):
    if 1.0 < number: 
        number = 1.0
    elif number < -1.0: 
        number = -1.0
    return number


"""
Input: list of lists [list1,list2, list3, ...]
Output: list of lists [list1,list2, list3, ...]
This needs to be updated to use tuples and not lists for faster sorting
"""


def make_monotonic(raw_matrix, verbose=False, reverse=False):
    # the first list in the list_of_list should be the one for which the other lists are to be sorted
    if verbose: print("Making data monotonic, reverse =", reverse)
    # pack the data into the correct format
    sort_matrix = [list(x) for x in zip(*raw_matrix)]
    # sort
    sorted_martix_lists = sorted(sort_matrix, key=itemgetter(0))
    if reverse:
        sorted_martix_lists.reverse()
    try:
        sorted_martix = numpy.array(sorted_martix_lists)
    except ValueError:
        sorted_martix = sorted_martix_lists
    # Unpack
    sorted_list_of_lists = [list(x) for x in zip(*sorted_martix)]
    return sorted_list_of_lists


# listOfValues = a list of floats, testValue = a float to sort by
def get_index_list_of_closest_values(list_of_values, test_value, return_ordered_values=False):
    len_of_list = len(list_of_values)
    value_indexes = range(len_of_list)
    ranked_list = [float(list_of_values[n]) - float(test_value) for n in value_indexes]
    [ordered_values, ordered_index_array] = make_monotonic(raw_matrix=[ranked_list, value_indexes])
    ordered_index_list = [int(numpy.round(ordered_index)) for ordered_index in ordered_index_array]
    if return_ordered_values:
        return ordered_index_list, ordered_values
    else:
        return ordered_index_list


"""

Rotations in a Cartesian Coordinate System

"""


def cartesian3_rotate_xy(xyz_array, theta_rad):
    sin_theta = sin(float(theta_rad))
    cos_theta = cos(float(theta_rad))
    rotation_matrix = numpy.array([[cos_theta, -sin_theta, 0.0],
                                  [sin_theta,  cos_theta, 0.0],
                                  [     0.0,       0.0, 1.0]])
    return dot(rotation_matrix, numpy.array(xyz_array))


def cartesian3_rotate_yz(xyz_array, theta_rad):
    sin_theta = sin(float(theta_rad))
    cos_theta = cos(float(theta_rad))
    rotation_matrix = numpy.array([[1.0,      0.0,       0.0],
                                  [0.0, cos_theta, -sin_theta],
                                  [0.0, sin_theta,  cos_theta]])
    return dot(rotation_matrix, numpy.array(xyz_array))


def cartesian3_rotate_zx(xyz_array, theta_rad):
    sin_theta = sin(float(theta_rad))
    cos_theta = cos(float(theta_rad))
    rotation_matrix = numpy.array([[ cos_theta, 0.0, sin_theta],
                                  [      0.0, 1.0,      0.0],
                                  [-sin_theta, 0.0, cos_theta]])
    return dot(rotation_matrix, numpy.array(xyz_array))


"""

Rotations in a spherical Coordinate System

"""


# theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi], radius [0, inf]
def sphere_rotate_theta(theta_phi_radius, delta_theta):
    (theta_rad, phi_rad, radius) = theta_phi_radius
    new_theta_rad = (theta_rad + delta_theta) % twopi
    new_phi_rad = phi_between0and_pi(phi_rad)
    return new_theta_rad, new_phi_rad, radius


"""

From Cartesian To ...

"""


# Output: theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi], radius [0, inf]
def cartesian_to_spherical(xyz):
    (x, y, z) = xyz
    x = float(x)
    y = float(y)
    z = float(z)
    radius = sqrt(x ** 2.0 + y ** 2.0 + z ** 2.0)
    theta_rad = arctan2(y, x)
    phi_rad = arccos(num_be_between_minus1and1(z/radius))
    (theta_rad, phi_rad) = sph_phase_clip((theta_rad, phi_rad))
    return theta_rad, phi_rad, radius


# Output: theta_deg = Azimuthal [0, 360), phi_deg = polar [-90, 90], radius [0, inf]
def cartesian_to_spherical_astronomy(xyz):
    (x, y, z) = xyz
    x = float(x)
    y = float(y)
    z = float(z)
    radius = sqrt(x**2.0 + y**2.0 + z**2.0)
    theta_deg = arctan2(y, x)*rad_to_deg
    phi_deg = arcsin(num_be_between_minus1and1(z/radius))*rad_to_deg
    (theta_deg, phi_deg) = sph_phase_clip((theta_deg, phi_deg))
    return theta_deg, phi_deg, radius


# Output: right_ascension = Azimuthal [0, 360), declination = polar [-90, 90]
def cartesian_to_equatorial(xyz):
    (x, y, z) = xyz
    (right_ascension, declination, radius) = cartesian_to_spherical_astronomy((x, y, z))
    (right_ascension, declination) = astro_phase_clip((right_ascension, declination))
    return right_ascension, declination


# Output: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
def cartesian_to_galactic(xyz):
    (x, y, z) = xyz
    (gal_lon, gal_lat, radius) = cartesian_to_spherical_astronomy((x, y, z))
    (gal_lon, gal_lat) = astro_phase_clip((gal_lon, gal_lat))
    return gal_lon, gal_lat


# Output: ecliptic_lon = Azimuthal [0, 360), ecliptic_lat = polar [-90, 90]
def cartesian_to_ecliptic(xyz):
    (x, y, z) = xyz
    (ecliptic_lon, ecliptic_lat, radius) = cartesian_to_spherical_astronomy((x, y, z))
    (ecliptic_lon, ecliptic_lat) = astro_phase_clip((ecliptic_lon, ecliptic_lat))
    return ecliptic_lon, ecliptic_lat


"""

From Spherical To ...

"""


# Input: theta = Azimuthal [0, 2pi), phi = polar [0, pi], radius [0, inf]
def spherical_to_cartesian(theta_phi_radius):
    (theta, phi, radius) = theta_phi_radius
    (theta, phi) = sph_phase_clip((float(theta), float(phi)))
    radius = float(radius)
    x = radius*cos(theta)*sin(phi)
    y = radius*sin(theta)*sin(phi)
    z = radius*cos(phi)
    return x, y, z


"""
# Input:  theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi], radius [0, inf]
# Output: theta_deg = Azimuthal [0, 360), phi_deg = polar [-90, 90], radius [0, inf]
"""


def spherical_to_spherical_astronomy(theta_phi_radius):
    (theta_rad, phi_rad, radius) = theta_phi_radius
    (theta_rad, phi_rad) = sph_phase_clip((float(theta_rad), float(phi_rad)))
    theta_deg = rad_to_deg * theta_rad
    phi_deg = (rad_to_deg * phi_rad) + 90.0
    (theta_deg, phi_deg) = astro_phase_clip((theta_deg, phi_deg))
    return theta_deg, phi_deg, radius


"""
# Input:  theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi), radius [0, inf]
# Output: right_ascension = Azimuthal [0, 360) , declination = polar [-90, 90]
"""


def spherical_to_equatorial(theta_phi_radius):
    (theta_rad, phi_rad, radius) = theta_phi_radius
    (right_ascension, declination, radius) = spherical_to_spherical_astronomy((theta_rad, phi_rad, radius))
    return right_ascension, declination


"""
# Input:  theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi), radius [0, inf]
# Output: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
"""


def spherical_go_galactic(theta_phi_radius):
    (theta_rad, phi_rad, radius) = theta_phi_radius
    (gal_lon, gal_lat, radius) = spherical_to_spherical_astronomy((theta_rad, phi_rad, radius))
    return gal_lon, gal_lat


"""
# Input:  theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi), radius [0, inf]
# Output: ecliptic_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
"""


def spherical_to_ecliptic(theta_phi_radius):
    (theta_rad, phi_rad, radius) = theta_phi_radius
    (ecliptic_lon, ecliptic_lat, radius) = spherical_to_spherical_astronomy((theta_rad, phi_rad, radius))
    return ecliptic_lon, ecliptic_lat


"""

From Spherical Astronomy To ...

"""


# Input: theta_deg = Azimuthal [0, 360), phi_deg = polar [-90, 90], radius [0, inf]
def spherical_astronomy_to_cartesian(theta_phi_radius):
    (theta_deg, phi_deg, radius) = theta_phi_radius
    (theta_deg, phi_deg) = astro_phase_clip((float(theta_deg), float(phi_deg)))
    theta_rad = theta_deg * degToRad
    phi_rad = phi_deg * degToRad
    radius = float(radius)
    x = radius * cos(theta_rad) * cos(phi_rad)
    y = radius * sin(theta_rad) * cos(phi_rad)
    z = radius * sin(phi_rad)
    return x, y, z


def spherical_astronomy_to_spherical(theta_phi_radius):
    (theta_deg, phi_deg, radius) = theta_phi_radius
    (theta_deg, phi_deg) = astro_phase_clip((float(theta_deg), float(phi_deg)))
    theta_rad = theta_deg * degToRad
    phi_rad = (phi_deg - 90.0) * degToRad
    radius = float(radius)
    (theta_rad, phi_rad) = sph_phase_clip((theta_rad, phi_rad))
    return theta_rad, phi_rad, radius


"""

From Galactic To ... 

"""


# Input: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
def galactic_to_cartesian(gal_lat_lon):
    (gal_lon, gal_lat) = gal_lat_lon
    (x, y, z) = spherical_astronomy_to_cartesian((gal_lon, gal_lat, 1.0))
    return x, y, z


"""
# Input: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
# Output theta_rad = Azimuthal [0, 2pi), phi_rad = polar [0, pi], radius [0, inf]
"""


def galactic_to_spherical(gal_lat_lon):
    (gal_lon, gal_lat) = gal_lat_lon
    (theta_rad, phi_rad, radius) = spherical_astronomy_to_spherical((gal_lon, gal_lat, 1.0))
    return theta_rad, phi_rad, radius


"""
# Input: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
# Output: right_ascension = Azimuthal [0, 360), declination = polar [-90, 90]
"""


def galactic_to_equatorial_b1950(gal_lat_lon):
    (gal_lon, gal_lat) = gal_lat_lon
    (gal_lon, gal_lat) = astro_phase_clip((float(gal_lon), float(gal_lat)))
    sin27point4 = sin(27.4 * degToRad)
    cos27point4 = cos(27.4 * degToRad)
    gal_lat_rad = gal_lat * degToRad
    gl_change_rad = (gal_lon - 123.0) * degToRad
    # For galactic Longitude
    numerator = sin(gl_change_rad)
    denominator = (cos(gl_change_rad) * sin27point4) - (tan(gal_lat_rad) * cos27point4)
    right_ascension = (arctan2(numerator, denominator) * rad_to_deg) + 12.25
    # For galactic Latitude
    input_for_arcsin = num_be_between_minus1and1((sin(gal_lat_rad) * sin27point4) + (cos(gal_lat_rad) * cos27point4
                                                                                     * cos(gl_change_rad)))
    declination = arcsin(input_for_arcsin) * rad_to_deg
    (right_ascension, declination) = astro_phase_clip((right_ascension, declination))
    return right_ascension, declination


"""

Equatorial To ...

"""

"""
Input: right_ascension = Azimuthal [0, 360), declination = polar [-90, 90]
Output: gal_lon = Azimuthal [0, 360), gal_lat = polar [-90, 90]
"""


def equatorial_to_galactic_b1950(ra_dec):
    (right_ascension, declination) = ra_dec
    (right_ascension, declination) = astro_phase_clip((float(right_ascension), float(declination)))
    sin27point4 = sin(27.4 * degToRad)
    cos27point4 = cos(27.4 * degToRad)
    declination_rad = declination * degToRad
    ra_change_rad = (192.25 - right_ascension) * degToRad
    # For galactic Longitude
    numerator = sin(ra_change_rad)
    denominator = (cos(ra_change_rad) * sin27point4) - (tan(declination_rad) * cos27point4)
    gal_lon = 303.0 - arctan2(numerator, denominator)*rad_to_deg
    # For galactic Latitude
    input_for_arcsin = num_be_between_minus1and1((sin(declination_rad * sin27point4) + 
                                                  (cos(declination_rad) * cos27point4) * cos(ra_change_rad)))
    gal_lat = arcsin(input_for_arcsin) * rad_to_deg
    return astro_phase_clip((gal_lon, gal_lat))


"""
Input: right_ascension = Azimuthal [0, 360), declination = polar [-90, 90]
Output: ecliptic_lon = Azimuthal [0, 360), ecliptic_lat = polar [-90, 90]
"""


def equatorial_to_ecliptic(ra_dec):
    (right_ascension, declination) = ra_dec
    (right_ascension, declination) = astro_phase_clip((right_ascension, declination))
    right_ascension_rad = right_ascension * degToRad
    declination_rad = declination * degToRad
    sin_ra = sin(right_ascension_rad)
    cos_ra = cos(right_ascension_rad)
    sin_dec = sin(declination_rad)
    cos_dec = cos(declination_rad)
    tan_dec = sin_dec / cos_dec
    # For ecliptic Longitude
    numerator = (sin_ra * cosAxilTilt) + (tan_dec * sinAxilTilt)
    ecliptic_lon = arctan2(numerator, cos_ra) * rad_to_deg
    # For ecliptic Latitude
    input_for_arcsin = num_be_between_minus1and1((sin_dec * cosAxilTilt) - (cos_dec * sinAxilTilt * sin_ra))
    ecliptic_lat = arcsin(input_for_arcsin) * rad_to_deg
    return astro_phase_clip((ecliptic_lon, ecliptic_lat))


"""

Ecliptic To ... 

"""


# Input: ecliptic_lon =  Azimuthal [0, 360) , ecliptic_lat = polar [-90, 90)
def ecliptic_to_cartesian(ecliptic_lon_lat):
    (ecliptic_lon, ecliptic_lat) = ecliptic_lon_lat
    (ecliptic_lon, ecliptic_lat) = astro_phase_clip((float(ecliptic_lon), float(ecliptic_lat)))
    ecliptic_lon = float(ecliptic_lon)
    ecliptic_lat = float(ecliptic_lat)
    x = cos(ecliptic_lon) * cos(ecliptic_lat)
    y = sin(ecliptic_lon) * cos(ecliptic_lat)
    z = sin(ecliptic_lat)
    return x, y, z


"""
Input:  ecliptic_lon = Azimuthal [0, 360), ecliptic_lat = polar [-90, 90]
Output: right_ascension = Azimuthal [0, 360), declination = polar [-90, 90]
"""


def ecliptic_to_equatorial(ecliptic_lon_lat):
    (ecliptic_lon, ecliptic_lat) = ecliptic_lon_lat
    (ecliptic_lon, ecliptic_lat) = astro_phase_clip((float(ecliptic_lon), float(ecliptic_lat)))
    ecliptic_lon_rad = ecliptic_lon * degToRad
    ecliptic_lat_rad = ecliptic_lat * degToRad
    sin_lon = sin(ecliptic_lon_rad)
    cos_lon = cos(ecliptic_lon_rad)
    sin_lat = sin(ecliptic_lat_rad)
    cos_lat = cos(ecliptic_lat_rad)
    tan_lat = sin_lat / cos_lat
    # For right_ascension Longitude
    numerator = (sin_lon * cosAxilTilt) - (tan_lat * sinAxilTilt)
    right_ascension = arctan2(numerator, cos_lon) * rad_to_deg
    # For declination Latitude
    input_for_arcsin = num_be_between_minus1and1((sin_lat * cosAxilTilt) + (cos_lat * sinAxilTilt * sin_lon))
    declination = arcsin(input_for_arcsin) * rad_to_deg
    return astro_phase_clip((right_ascension, declination))


"""

Sophisticated Tools

"""


def average_astronomy_coors(lon_lat_list):
    cartesian_list = [spherical_astronomy_to_cartesian(lon_lat) for lon_lat in lon_lat_list]
    x_sum = 0.0
    y_sum = 0.0
    z_sum = 0.0
    for (x, y, z) in cartesian_list:
        x_sum += x
        y_sum += y
        z_sum += z
    (lon, lat, radius) = cartesian_to_spherical_astronomy((x_sum, y_sum, z_sum))
    return lon, lat


def find_angle_for_astronomy_coors(lon_lat1, lon_lat2):
    (Lon1, Lat1) = lon_lat1
    (Lon2, Lat2) = lon_lat2
    a = numpy.array(spherical_astronomy_to_cartesian((Lon1, Lat1, 1.0)))
    b = numpy.array(spherical_astronomy_to_cartesian((Lon2, Lat2, 1.0)))
    ratio = num_be_between_minus1and1(numpy.dot(a, b))
    angle = arccos(ratio)
    angle_deg = angle * rad_to_deg
    return angle_deg


def average_gal_coors(lon_lat_list):
    cartesian_list = [spherical_to_cartesian(galactic_to_spherical(lon_lat)) for lon_lat in lon_lat_list]
    x_sum = 0.0
    y_sum = 0.0
    z_sum = 0.0
    for (x, y, z) in cartesian_list:
        x_sum += x
        y_sum += y
        z_sum += z
    return spherical_go_galactic(cartesian_to_spherical((x_sum, y_sum, z_sum)))


"""
lon_lats looks like [(12.,56.7), (330.0,0.8888), (12.84,-30), ...]
goal_lon_lat looks like (theta_deg, phi_deg) theta_deg = Azimuthal [0, 360), phi_deg = polar [-90, 90]
min_angle_deg is a float, anything that is 180 or greater returns all the data
"""


def natalies_function(lon_lats, goal_lon_lat, min_angle_deg = 180.0, return_ranked_distances=False, verbose=True):
    min_angle_deg = float(min_angle_deg)
    if lon_lats == []:
        if verbose: print("The Lon Lat List is an empty set, this make the code break.\n")
    # makes List of distance in degrees for each lon_lat in lon_lats
    distance_list = [find_angle_for_astronomy_coors(lon_lat, goal_lon_lat) for lon_lat in lon_lats]
    # This function returns a ranked list of the closest values to a goal, the goal for us is 0.
    # For this function, it ranks the distance_list and returns the ordered ranked indexes of lon_lats and the distances
    # to the goal
    rank_ordered_index_list, ordered_distances = \
        get_index_list_of_closest_values(distance_list, 0.0, return_ordered_values=True)
    # Since the list of distance is ordered, I just need to search until I find one that is bigger than min_angle_deg
    for one_index_too_far in range(len(lon_lats)):
        if min_angle_deg < ordered_distances[one_index_too_far]:
            break
    # test to see if any values were closer than min_angle_deg
    if one_index_too_far == 0:
        if verbose:
            print("There were no lon_lats found around an angle of", min_angle_deg)
            print("at the goal_lon_lat", goal_lon_lat, '\n')
        list_of_near_indexes = []
        list_of_near_distances = []
    else:
        if verbose:
            print("There were", one_index_too_far, " lon_lats found around an angle of", min_angle_deg)
            print("at the goal_lon_lat", goal_lon_lat, '\n')
        # Get the ranked values that are less than the minAngle
        list_of_near_indexes = rank_ordered_index_list[:one_index_too_far]
        if return_ranked_distances:
            list_of_near_distances = ordered_distances[:one_index_too_far]
    if return_ranked_distances:
        return list_of_near_indexes, list_of_near_distances
    else:
        return list_of_near_indexes


def find_closestlon_lat(lon_lat_list, goal):
    closest_lon_lat = None
    best_test = float("inf")
    for search_element in lon_lat_list:
        test_val = find_angle_for_astronomy_coors(search_element, goal)
        if test_val <= best_test:
            closest_lon_lat = search_element
            best_test = test_val
    return closest_lon_lat


def init_working_coor_transformation(rotation_in_theta, rotation_in_phi, current_lon, center_lat, verbose=False):
    
    if verbose: 
        print("center (Longitude, Latitude)=(" + str(current_lon) + ', ' + str(center_lat) + ')')
    (center_theta, center_phi, center_radius) = galactic_to_spherical((current_lon, center_lat))
    if verbose: 
        print("Transform from galactic to spherical (theta, phi, radius)=" +
              "(" + str(center_theta) + ', ' + str(center_phi) + ', ' + str(center_radius) + ')')
    (center_x, center_y, center_z) = spherical_to_cartesian((center_theta, center_phi, center_radius))
    if verbose: 
        print("Transform from spherical to cartesian (x, y, z)=" +
              "(" + str(center_x) + ', ' + str(center_y) + ', ' + str(center_z) + ')')
    (rot1_x, rot1_y, rot1_z) = cartesian3_rotate_xy((center_x, center_y, center_z), theta_rad=rotation_in_theta)
    if verbose: 
        print("Rotation of " + str(rotation_in_theta) + 
              " radians in Theta, aka the XY plane, aka a rotation around the z axis)")
    if verbose: 
        print("(rot1_x, rot1_y, rot1_z)=(" + str(rot1_x) + ', ' + str(rot1_y) + ', ' + str(rot1_z) + ')')
    (rot12_x, rot12_y, rot12_z) = cartesian3_rotate_zx((rot1_x, rot1_y, rot1_z), theta_rad=-rotation_in_phi)
    if verbose: 
        print("Rotation of " + str(rotation_in_phi) 
              + " radians in Phi, aka the ZX plane, aka a rotation around the y axis)")
    if verbose: 
        print("(rot12_x, rot12_y, rot12_z)=(" + str(rot12_x) + ', ' + str(rot12_y) + ', ' 
              + str(rot12_z) + ')')
    (working_theta, working_phi, working_radius) = cartesian_to_spherical((rot12_x, rot12_y, rot12_z))
    if verbose: 
        print("Transform from cartesian to spherical (theta, phi, radius)=" +
              "(" + str(working_theta) + ', ' + str(working_phi) + ', ' + str(working_radius) + ')')
    return working_theta, working_phi


def rotate_working_coor(theta_phi, rotation_rad):
    (theta, phi) = theta_phi
    new_theta, new_phi, radius = cartesian_to_spherical(cartesian3_rotate_yz(spherical_to_cartesian((theta, phi, 1.0)), 
                                                                             theta_rad=rotation_rad))
    return new_theta, new_phi


def haversine(lon_lat1, lon_lat2, radius=1.0):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    (lon1, lat1) = lon_lat1
    (lon2, lat2) = lon_lat2
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (sin(dlat/2)**2) + cos(lat1) * cos(lat2) * (sin(dlon/2)**2)
    c = 2 * arcsin(sqrt(a))
    dist = c * radius
    return dist


if __name__ == "__main__":
    verbose = False
    mesh = 12
    thetas = range(0, 360, mesh)
    phis = range(-90, 91, mesh)
    lon_lats = []
    for theta in thetas:
        for phi in phis:
            lon_lats.append((theta, phi))
            if verbose:
                print("theta, phi :", (theta, phi), '  test return:', 
                      ecliptic_to_equatorial(equatorial_to_ecliptic((theta, phi))))
                
    print("")
    goal_lon_lat = (300, -12.)
    min_angle_deg = 20
    list_of_near_indexes, list_of_near_distances =\
        natalies_function(lon_lats, goal_lon_lat, min_angle_deg=min_angle_deg, return_ranked_distances=True, 
                          verbose=True)

    for (indexNearDist, indexlon_lat) in list(enumerate(list_of_near_indexes)):
        print("(Lon, Lat)", lon_lats[indexlon_lat], 'is', list_of_near_distances[indexNearDist], 
              'from the goal of', goal_lon_lat, 'the min angle was', min_angle_deg)
