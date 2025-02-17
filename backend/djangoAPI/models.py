from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import send_mail
from rest_framework import serializers
from django.contrib.auth.models import User

from .dynamic_data import available_spectra_handles, available_isotopologues, available_params_and_units

"""
User authentication
Sign up/login verification.
"""


class UserAccountManager(BaseUserManager):
    """
    Override BaseUserManager and create a user with the given email and password.
    """

    def create_user(self, first_name, last_name, email, institution, password=None):
        """
        Creates a model with the given email and password and any other information.
        """
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        email = email.lower()

        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=email,
            institution=institution,
        )

        user.set_password(password)  # This will hash the password
        user.save(using=self._db)

        return user


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """
    User authentication
    """
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    institution = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'institution']

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        return self.first_name + ' ' + self.last_name

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name

    def get_institution(self):
        """
        Return the institution of the user.
        """
        return self.institution

    def __str__(self):
        """
        String representation of this Model object.
        """
        return self.email


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    email_plaintext_message = f"https://spexodisks.com/ResetPassword?token={reset_password_token.key}"
    send_mail(
        # title:
        "Password Reset for SpExoDisks".format(title="SpExoDisks"),
        # message:
        "Click the following link to reset your password " + email_plaintext_message,
        # from:
        "donotreplyspexodisks@gmail.com",
        # to:
        [reset_password_token.user.email]
    )


class ChangePasswordSerializer(serializers.Serializer):
    model = User

    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


"""
Dynamic Models
"""
co_field_and_data = [('index_co', models.BigAutoField(db_column='index_CO', primary_key=True)),
                     # Field name made lowercase.
                     ('wavelength_um', models.FloatField()),
                     ('isotopologue', models.CharField(max_length=20, blank=True, null=True)),
                     ('upper_level', models.CharField(max_length=30, blank=True, null=True)),
                     ('lower_level', models.CharField(max_length=30, blank=True, null=True)),
                     ('transition', models.CharField(max_length=30, blank=True, null=True)),
                     ('einstein_a', models.FloatField(db_column='einstein_A')),  # Field name made lowercase.
                     ('upper_level_energy', models.FloatField()),
                     ('lower_level_energy', models.FloatField()),
                     ('g_statistical_weight_upper_level', models.FloatField()),
                     ('g_statistical_weight_lower_level', models.FloatField()),
                     ('upper_vibrational', models.IntegerField(blank=True, null=True)),
                     ('upper_rotational', models.IntegerField(blank=True, null=True)),
                     ('branch', models.CharField(max_length=1, blank=True, null=True)),
                     ('lower_vibrational', models.IntegerField(blank=True, null=True)),
                     ('lower_rotational', models.IntegerField(blank=True, null=True))]

h2o_field_and_data = [('index_h2o', models.BigAutoField(db_column='index_H2O', primary_key=True)),
                      # Field name made lowercase.
                      ('wavelength_um', models.FloatField()),
                      ('isotopologue', models.CharField(max_length=20, blank=True, null=True)),
                      ('upper_level', models.CharField(max_length=30, blank=True, null=True)),
                      ('lower_level', models.CharField(max_length=30, blank=True, null=True)),
                      ('transition', models.CharField(max_length=65, blank=True, null=True)),
                      ('einstein_a', models.FloatField(db_column='einstein_A')),  # Field name made lowercase.
                      ('upper_level_energy', models.FloatField()),
                      ('lower_level_energy', models.FloatField()),
                      ('g_statistical_weight_upper_level', models.FloatField()),
                      ('g_statistical_weight_lower_level', models.FloatField()),
                      ('upper_vibrational1', models.IntegerField(blank=True, null=True)),
                      ('upper_vibrational2', models.IntegerField(blank=True, null=True)),
                      ('upper_vibrational3', models.IntegerField(blank=True, null=True)),
                      ('upper_rotational', models.IntegerField(blank=True, null=True)),
                      ('upper_ka', models.IntegerField(blank=True, null=True)),
                      ('upper_kc', models.IntegerField(blank=True, null=True)),
                      ('lower_vibrational1', models.IntegerField(blank=True, null=True)),
                      ('lower_vibrational2', models.IntegerField(blank=True, null=True)),
                      ('lower_vibrational3', models.IntegerField(blank=True, null=True)),
                      ('lower_rotational', models.IntegerField(blank=True, null=True)),
                      ('lower_ka', models.IntegerField(blank=True, null=True)),
                      ('lower_kc', models.IntegerField(blank=True, null=True))]

oh_field_and_data = [
    ('index_oh', models.BigAutoField(db_column='index_OH', primary_key=True)),
    ('wavelength_um', models.FloatField()),
    ('isotopologue', models.CharField(max_length=20, blank=True, null=True)),
    ('upper_level', models.CharField(max_length=50, blank=True, null=True)),
    ('lower_level', models.CharField(max_length=100, blank=True, null=True)),
    ('transition', models.CharField(max_length=150, blank=True, null=True)),
    ('einstein_a', models.FloatField(db_column='einstein_A')),
    ('upper_level_energy', models.FloatField()),
    ('lower_level_energy', models.FloatField()),
    ('g_statistical_weight_upper_level', models.FloatField()),
    ('g_statistical_weight_lower_level', models.FloatField()),
    ('upper_electrical_state', models.CharField(max_length=2, blank=True, null=True)),
    ('upper_f_prime', models.IntegerField(blank=True, null=True)),
    ('upper_total_angular_momentum', models.CharField(max_length=5, blank=True, null=True)),
    ('upper_vibrational', models.IntegerField(blank=True, null=True)),
    ('lower_branch', models.CharField(max_length=2, blank=True, null=True)),
    ('lower_electrical_state', models.CharField(max_length=2, blank=True, null=True)),
    ('lower_f_double_prime', models.CharField(max_length=5, blank=True, null=True)),
    ('lower_j_double_prime', models.FloatField(blank=True, null=True)),
    ('lower_sym_double_prime', models.CharField(max_length=2, blank=True, null=True)),
    ('lower_total_angular_momentum', models.CharField(max_length=5, blank=True, null=True)),
    ('lower_vibrational', models.IntegerField(blank=True, null=True)),
    ]


# Dynamically create the isotopologue models
isotopologue_models = {}
for molecule in sorted(available_isotopologues.keys()):
    # Each molecule has different required fields
    if molecule == 'co':
        field_and_data = co_field_and_data
    elif molecule == 'h2o':
        field_and_data = h2o_field_and_data
    elif molecule == 'oh':
        field_and_data = oh_field_and_data
    else:
        raise KeyError(f'molecule type: {molecule} not recognized')
    # initialize the molecule dictionary
    if molecule not in isotopologue_models.keys():
        isotopologue_models[molecule] = {}
    # loop over the isotopologues for this molecule
    for isotopologue in sorted(available_isotopologues[molecule]):
        model_name = f'Isotopologue{isotopologue}'
        table_name = f'isotopologue_{isotopologue}'


        class Meta:
            managed = False
            db_table = table_name
            app_label = f'app_label_{model_name}'


        # Now construct the model class
        class_vars = {field_name: field_model for field_name, field_model in field_and_data}
        iso_model = type(model_name, (models.Model,), dict(Meta=Meta, __module__='models', **class_vars))
        # save the model to dictionary with the same shape as available_isotopologues
        isotopologue_models[molecule][isotopologue] = iso_model

# Dynamically create the spectra models
spectra_fields_and_data = [('wavelength_um', models.FloatField(primary_key=True)),
                           ('flux', models.FloatField(blank=True, null=True)),
                           ('flux_error', models.FloatField(blank=True, null=True))]

spectra_models = {}
for spectrum_handle in sorted(available_spectra_handles):
    model_name = f'Spectrum{spectrum_handle.lower()}'


    class Meta:
        managed = False
        db_table = spectrum_handle
        app_label = f'app_label_{model_name}'


    # Now construct the model class
    class_vars = {field_name: field_model for field_name, field_model in spectra_fields_and_data}
    spectrum_model = type(model_name, (models.Model,), dict(Meta=Meta, __module__='models', **class_vars))
    spectra_models[spectrum_handle] = spectrum_model


# Dynamically create curated parameters models
class Meta:
    managed = False
    db_table = 'curated'
    app_label = 'app_label_curated'


curated_class_vars = dict(spexodisks_handle=models.CharField(primary_key=True, max_length=50),
                          pop_name=models.CharField(max_length=50),
                          preferred_simbad_name=models.CharField(max_length=50),
                          simbad_link=models.CharField(max_length=122, blank=True, null=True),
                          ra_dec=models.CharField(max_length=35, blank=True, null=True),
                          ra=models.CharField(max_length=18, blank=True, null=True),
                          dec=models.CharField(max_length=18, blank=True, null=True),
                          esa_sky=models.CharField(max_length=200, blank=True, null=True),
                          has_spectra=models.IntegerField())
for param_name, unit in available_params_and_units:
    if unit == 'string':
        curated_class_vars[f'{param_name}_value'] = models.CharField(max_length=100, blank=True, null=True)
        curated_class_vars[f'{param_name}_err_low'] = models.CharField(max_length=100, blank=True, null=True)
        curated_class_vars[f'{param_name}_err_high'] = models.CharField(max_length=100, blank=True, null=True)
        curated_class_vars[f'{param_name}_ref'] = models.CharField(max_length=50, blank=True, null=True)
    else:
        curated_class_vars[f'{param_name}_value'] = models.FloatField(blank=True, null=True)
        curated_class_vars[f'{param_name}_err_low'] = models.FloatField(blank=True, null=True)
        curated_class_vars[f'{param_name}_err_high'] = models.FloatField(blank=True, null=True)
        curated_class_vars[f'{param_name}_ref'] = models.CharField(max_length=50, blank=True, null=True)

Curated = type("Curated", (models.Model,), dict(Meta=Meta, __module__='models', **curated_class_vars))

"""
Static Models
"""


# Overall statistics about the data for the website
class StatsTotal(models.Model):
    total_stars = models.IntegerField(primary_key=True)
    total_spectra = models.IntegerField(blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'stats_total'


# Overall statistics about the spectra per-instrument for the website
class StatsInstrument(models.Model):
    order_index = models.IntegerField(primary_key=True)
    inst_handle = models.CharField(max_length=100, blank=False, null=False)
    inst_name = models.CharField(max_length=100, blank=False, null=True)
    inst_name_short = models.CharField(max_length=100, blank=False, null=True)
    show_by_default = models.BooleanField(blank=False, null=False)
    spectra_count = models.CharField(max_length=100, blank=False, null=True)

    class Meta:
        managed = False
        db_table = 'stats_instrument'


class DefaultSpectrum(models.Model):
    wavelength_um = models.FloatField(primary_key=True)
    flux = models.FloatField(blank=True, null=True)
    flux_error = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'default_spectrum'


class AvailableFloatParams(models.Model):
    float_params = models.CharField(max_length=20, primary_key=True)

    class Meta:
        managed = False
        db_table = 'available_float_params'


class AvailableSpectrumParams(models.Model):
    spectrum_params = models.CharField(max_length=64, primary_key=True)

    class Meta:
        managed = False
        db_table = 'available_spectrum_params'


class AvailableStrParams(models.Model):
    str_params = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'available_str_params'


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class FluxCalibration(models.Model):
    index_flux_cal = models.BigAutoField(primary_key=True)
    spectrum_handle = models.CharField(max_length=100)
    flux_cal = models.FloatField()
    flux_cal_error = models.FloatField(blank=True, null=True)
    wavelength_um = models.FloatField()
    ref = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'flux_calibration'


class LineFluxesCo(models.Model):
    index_co = models.BigAutoField(db_column='index_CO', primary_key=True)  # Field name made lowercase.
    flux = models.FloatField()
    flux_error = models.FloatField(blank=True, null=True)
    match_wavelength_um = models.FloatField()
    wavelength_um = models.FloatField()
    spectrum_handle = models.CharField(max_length=100)
    isotopologue = models.CharField(max_length=20, blank=True, null=True)
    upper_level = models.CharField(max_length=30, blank=True, null=True)
    lower_level = models.CharField(max_length=30, blank=True, null=True)
    transition = models.CharField(max_length=30, blank=True, null=True)
    einstein_a = models.FloatField(db_column='einstein_A')  # Field name made lowercase.
    upper_level_energy = models.FloatField()
    lower_level_energy = models.FloatField()
    g_statistical_weight_upper_level = models.FloatField()
    g_statistical_weight_lower_level = models.FloatField()
    upper_vibrational = models.IntegerField(blank=True, null=True)
    upper_rotational = models.IntegerField(blank=True, null=True)
    branch = models.CharField(max_length=1, blank=True, null=True)
    lower_vibrational = models.IntegerField(blank=True, null=True)
    lower_rotational = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'line_fluxes_co'


class ObjectNameAliases(models.Model):
    alias = models.CharField(primary_key=True, max_length=50)
    spexodisks_handle = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'object_name_aliases'


class ObjectParamsFloat(models.Model):
    float_index_params = models.BigAutoField(primary_key=True)
    spexodisks_handle = models.CharField(max_length=50)
    float_param_type = models.CharField(max_length=20)
    float_value = models.CharField(max_length=100)
    float_error_low = models.CharField(max_length=100, blank=True, null=True)
    float_error_high = models.CharField(max_length=100, blank=True, null=True)
    float_ref = models.CharField(max_length=50, blank=True, null=True)
    float_units = models.CharField(max_length=10, blank=True, null=True)
    float_notes = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'object_params_float'


class ObjectParamsStr(models.Model):
    str_index_params = models.BigAutoField(primary_key=True)
    spexodisks_handle = models.CharField(max_length=50)
    str_param_type = models.CharField(max_length=20)
    str_value = models.CharField(max_length=100)
    str_error = models.CharField(max_length=100, blank=True, null=True)
    str_ref = models.CharField(max_length=50, blank=True, null=True)
    str_units = models.CharField(max_length=10, blank=True, null=True)
    str_notes = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'object_params_str'


class spectra_handle_name(models.CharField):
    def get_prep_value(self, value):
        return str(value).lower()


class Spectra(models.Model):
    spectrum_handle = spectra_handle_name(primary_key=True, max_length=100)
    spectrum_display_name = models.CharField(max_length=50)
    spexodisks_handle = models.CharField(max_length=50)
    spectrum_set_type = models.CharField(max_length=20, blank=True, null=True)
    spectrum_observation_date = models.DateTimeField(blank=True, null=True)
    spectrum_pi = models.CharField(max_length=50, blank=True, null=True)
    spectrum_reference = models.CharField(max_length=50, blank=True, null=True)
    spectrum_downloadable = models.IntegerField(blank=True, null=True)
    spectrum_data_reduction_by = models.CharField(max_length=50, blank=True, null=True)
    spectrum_aor_key = models.IntegerField(blank=True, null=True)
    spectrum_flux_is_calibrated = models.IntegerField(blank=True, null=True)
    spectrum_ref_frame = models.CharField(max_length=20, blank=True, null=True)
    spectrum_min_wavelength_um = models.FloatField(blank=True, null=True)
    spectrum_max_wavelength_um = models.FloatField(blank=True, null=True)
    spectrum_resolution_um = models.FloatField(blank=True, null=True)
    spectrum_output_filename = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'spectra'


class DefaultSpectrumInfo(models.Model):
    spectrum_handle = models.CharField(primary_key=True, max_length=100)
    spectrum_display_name = models.CharField(max_length=50)
    spexodisks_handle = models.CharField(max_length=50)
    spectrum_set_type = models.CharField(max_length=20, blank=True, null=True)
    spectrum_observation_date = models.DateTimeField(blank=True, null=True)
    spectrum_pi = models.CharField(max_length=50, blank=True, null=True)
    spectrum_reference = models.CharField(max_length=50, blank=True, null=True)
    spectrum_downloadable = models.IntegerField(blank=True, null=True)
    spectrum_data_reduction_by = models.CharField(max_length=50, blank=True, null=True)
    spectrum_aor_key = models.IntegerField(blank=True, null=True)
    spectrum_flux_is_calibrated = models.IntegerField(blank=True, null=True)
    spectrum_ref_frame = models.CharField(max_length=20, blank=True, null=True)
    spectrum_min_wavelength_um = models.FloatField(blank=True, null=True)
    spectrum_max_wavelength_um = models.FloatField(blank=True, null=True)
    spectrum_resolution_um = models.FloatField(blank=True, null=True)
    spectrum_output_filename = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'default_spectrum_info'


class StackedLineSpectra(models.Model):
    stack_line_handle = models.CharField(primary_key=True, max_length=130)
    spectrum_handle = models.CharField(max_length=100)
    spexodisks_handle = models.CharField(max_length=50)
    transition = models.CharField(max_length=30)
    isotopologue = models.CharField(max_length=20)
    molecule = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'stacked_line_spectra'


class AvailableIsotopologues(models.Model):
    name = models.CharField(max_length=20, blank=True, null=False, primary_key=True)
    label = models.CharField(max_length=100, blank=True, null=True)
    molecule = models.CharField(max_length=20, blank=True, null=True)
    mol_label = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    dash = models.CharField(max_length=20, blank=True, null=True)
    min_wavelength_um = models.FloatField()
    max_wavelength_um = models.FloatField()
    total_lines = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'available_isotopologues'


class AvailableParamsAndUnits(models.Model):
    order_index = models.IntegerField(primary_key=True)
    param_handle = models.CharField(max_length=100, blank=False, null=False)
    units = models.CharField(max_length=50, blank=True, null=True)
    short_label = models.CharField(max_length=50, blank=True, null=True)
    plot_axis_label = models.CharField(max_length=100, blank=True, null=True)
    for_display = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'available_params_and_units'
