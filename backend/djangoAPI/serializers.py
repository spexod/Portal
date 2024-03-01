from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import (spectra_models, isotopologue_models,
                     AvailableIsotopologues, AvailableFloatParams, AvailableSpectrumParams, AvailableStrParams, Curated,
                     DjangoMigrations, FluxCalibration, LineFluxesCo, ObjectNameAliases, ObjectParamsFloat,
                     ObjectParamsStr, Spectra, StackedLineSpectra, AvailableParamsAndUnits,
                     DefaultSpectrum, DefaultSpectrumInfo, StatsTotal, StatsInstrument)

"""
User authentication
"""
User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model
    """

    class Meta:
        """
        Meta data for User
        """
        model = User
        fields = ('first_name', 'last_name', 'email', 'institution', 'password')

    def validate(self, data):
        """
        Validate the given data. Raises ValidationError if an error occurs.
        """
        user = User(**data)
        password = data.get('password')

        try:
            validate_password(password, user)
        except exceptions.ValidationError as e:
            serializer_errors = serializers.as_serializer_error(e)
            raise exceptions.ValidationError(
                {'password': serializer_errors['non_field_errors']}
            )

        return data

    def create(self, validated_data):
        """
        Create and return a new `User` instance, given the validated data.
        """
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            institution=validated_data['institution'],
            password=validated_data['password'],
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user without containing password information.
    """

    class Meta:
        """
        Metaclass for UserCreateSerializer
        """
        model = User
        fields = ('first_name', 'last_name', 'email', 'institution')


class ChangePasswordSerializer(serializers.Serializer):
    model = User

    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


"""
Dynamic ModelSerializers
"""
isotopologue_serializers = {}
for molecule in sorted(isotopologue_models.keys()):
    isotopologue_serializers[molecule] = {}
    for isotopologue in sorted(isotopologue_models[molecule].keys()):
        class Meta:
            model = isotopologue_models[molecule][isotopologue]
            fields = '__all__'


        # Now construct the serializer class
        serializer_name = f'Isotopologue{isotopologue}Serializer'
        iso_serializer = type(serializer_name, (ModelSerializer,), dict(Meta=Meta, __module__='serializers'))
        isotopologue_serializers[molecule][isotopologue] = iso_serializer

spectra_serializers = {}
for spectrum_handle in sorted(spectra_models.keys()):
    class Meta:
        model = spectra_models[spectrum_handle]
        fields = '__all__'


    # Now construct the serializer class
    serializer_name = f'{spectrum_handle.title()}Serializer'
    spectrum_serializer = type(serializer_name, (ModelSerializer,), dict(Meta=Meta, __module__='serializers'))
    spectra_serializers[spectrum_handle] = spectrum_serializer

"""
Static ModelSerializers
"""


class StatsTotalSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsTotal
        fields = '__all__'


class StatsInstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsInstrument
        fields = '__all__'


class AvailableParamsAndUnitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableParamsAndUnits
        fields = '__all__'


class DefaultSpectrumSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultSpectrum
        fields = '__all__'


class DefaultSpectrumInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultSpectrumInfo
        fields = '__all__'


class AvailableIsotopologuesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableIsotopologues
        fields = '__all__'


class AvailableFloatParamsSerializer(ModelSerializer):
    class Meta:
        model = AvailableFloatParams
        fields = '__all__'


class AvailableSpectrumParamsSerializer(ModelSerializer):
    class Meta:
        model = AvailableSpectrumParams
        fields = '__all__'


class AvailableStrParamsSerializer(ModelSerializer):
    class Meta:
        model = AvailableStrParams
        fields = '__all__'


class CuratedSerializer(ModelSerializer):
    class Meta:
        model = Curated
        fields = '__all__'


class DjangoMigrationsSerializer(ModelSerializer):
    class Meta:
        model = DjangoMigrations
        fields = '__all__'


class FluxCalibrationSerializer(ModelSerializer):
    class Meta:
        model = FluxCalibration
        fields = '__all__'


class LineFluxesCoSerializer(ModelSerializer):
    class Meta:
        model = LineFluxesCo
        fields = '__all__'


class ObjectNameAliasesSerializer(ModelSerializer):
    class Meta:
        model = ObjectNameAliases
        fields = '__all__'


class ObjectParamsFloatSerializer(ModelSerializer):
    class Meta:
        model = ObjectParamsFloat
        fields = '__all__'


class ObjectParamsStrSerializer(ModelSerializer):
    class Meta:
        model = ObjectParamsStr
        fields = '__all__'


class SpectraSerializer(ModelSerializer):
    class Meta:
        model = Spectra
        fields = '__all__'


class StackedLineSpectraSerializer(ModelSerializer):
    class Meta:
        model = StackedLineSpectra
        fields = '__all__'
