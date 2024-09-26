from django.http import HttpResponse
from rest_framework import viewsets, permissions

from rest_framework.decorators import api_view

# for Data Download
from rest_framework.views import APIView

from rest_framework import status, generics
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

from .dynamic_data import (dispatch, schema_prefix,
                           available_spectra_to_database, available_isotopologues_to_database)
from .models import spectra_models, isotopologue_models, \
    AvailableIsotopologues, \
    AvailableFloatParams, AvailableSpectrumParams, \
    AvailableStrParams, Curated, DjangoMigrations, \
    FluxCalibration, LineFluxesCo, \
    ObjectNameAliases, ObjectParamsFloat, ObjectParamsStr, Spectra, \
    StackedLineSpectra, AvailableParamsAndUnits, DefaultSpectrum, DefaultSpectrumInfo, \
    StatsTotal, StatsInstrument
from .serializers import spectra_serializers, isotopologue_serializers, \
    AvailableIsotopologuesSerializer, \
    AvailableFloatParamsSerializer, \
    AvailableSpectrumParamsSerializer, AvailableStrParamsSerializer, CuratedSerializer, \
    DjangoMigrationsSerializer, \
    FluxCalibrationSerializer, LineFluxesCoSerializer, \
    ObjectNameAliasesSerializer, ObjectParamsFloatSerializer, \
    ObjectParamsStrSerializer, SpectraSerializer, StackedLineSpectraSerializer, \
    AvailableParamsAndUnitsSerializer, DefaultSpectrumSerializer, DefaultSpectrumInfoSerializer, \
    UserCreateSerializer, UserSerializer, StatsTotalSerializer, StatsInstrumentSerializer, ChangePasswordSerializer
"""
Dynamic Views
"""
isotopologue_views = {}
for molecule in sorted(isotopologue_models.keys()):
    isotopologue_views[molecule] = {}
    for isotopologue in sorted(isotopologue_models[molecule].keys()):
        view_name = f'Isotopologue{isotopologue}ViewSet'
        database_this_isotopologue = available_isotopologues_to_database[molecule][isotopologue]
        queryset = isotopologue_models[molecule][isotopologue].objects.using(database_this_isotopologue).all()
        serializer_class = isotopologue_serializers[molecule][isotopologue]
        iso_view = type(view_name, (viewsets.ReadOnlyModelViewSet,), dict(__module__='views', queryset=queryset,
                                                                          serializer_class=serializer_class))
        isotopologue_views[molecule][isotopologue] = iso_view


spectrum_fields = ('wavelength_um', 'flux', 'flux_error')


spectra_views = {}
for spectrum_handle in sorted(spectra_models.keys()):
    def list(self, request):
        return Response(data={key: data_array for key, data_array in
                              zip(spectrum_fields, zip(*self.queryset.values_list(*spectrum_fields)))},
                        status=status.HTTP_200_OK)


    view_name = f'{spectrum_handle.lower()}ViewSet'
    database_this_handle = available_spectra_to_database[spectrum_handle]
    queryset = spectra_models[spectrum_handle].objects.using(database_this_handle).order_by('pk')
    spectra_views[spectrum_handle] = type(view_name,
                                          (viewsets.ReadOnlyModelViewSet,),
                                          dict(__module__='views',
                                               queryset=queryset,
                                               serializer_class=spectra_serializers[spectrum_handle],
                                               throttle_scope='spectra',
                                               list=list))

"""
Static Views
"""


class StatsTotalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatsTotal.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = StatsTotalSerializer


class StatsInstrumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatsInstrument.objects.using(f'{schema_prefix}spexodisks').order_by('order_index')
    serializer_class = StatsInstrumentSerializer


class AvailableParamsAndUnitsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableParamsAndUnits.objects.using(f'{schema_prefix}spexodisks').order_by('pk')
    serializer_class = AvailableParamsAndUnitsSerializer


class DefaultSpectrumViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultSpectrum.objects.using(f'{schema_prefix}spexodisks').order_by('pk')
    serializer_class = DefaultSpectrumSerializer

    def list(self, request):
        return Response(data={key: data_array for key, data_array in
                              zip(spectrum_fields, zip(*self.queryset.values_list(*spectrum_fields)))},
                        status=status.HTTP_200_OK)


class DefaultSpectrumInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultSpectrumInfo.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = DefaultSpectrumInfoSerializer


class AvailableIsotopologuesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableIsotopologues.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = AvailableIsotopologuesSerializer


class SpectraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Spectra.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = SpectraSerializer


class CuratedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Curated.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = CuratedSerializer


class ObjectNameAliasesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectNameAliases.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = ObjectNameAliasesSerializer




"""
Data Downloads
"""

@api_view(['GET'])
def download_spectra(request):
    """
    Get a list of strings from a user with the spectra they would like to download.
    Each spectra being seperated with a % character.
    """
    try:
        spectra_list = request.query_params.get('spectra').split('%')
    except:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    current_user = request.user
    if current_user:
        response = HttpResponse(dispatch.zip_upload(spectra_handles=spectra_list),
                                content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=spexodisks.zip'
        return response
    else:
        print(f'User {current_user}, is not authenticated')
        return Response(status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    """ Register a new user. """
    # User = get_user_model()
    def post(self, request):
        """
        overwrite the post method to create a new user.
        """
        data = request.data
        serializer = UserCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.create(serializer.validated_data)
        user = UserSerializer(user)

        return Response(user.data, status=status.HTTP_201_CREATED)


class RetrieveUserView(APIView):
    """ Retrieve a user. """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get the user's details.
        """
        user = request.user
        user = UserSerializer(user)

        return Response(user.data, status=status.HTTP_200_OK)


class ChangePasswordView(generics.UpdateAPIView):
    """
    An endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Used tables, but supported tables
class AvailableFloatParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableFloatParams.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = AvailableFloatParamsSerializer


class ObjectParamsStrViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectParamsStr.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = ObjectParamsStrSerializer


class ObjectParamsFloatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectParamsFloat.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = ObjectParamsFloatSerializer


class StackedLineSpectraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StackedLineSpectra.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = StackedLineSpectraSerializer

class FluxCalibrationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FluxCalibration.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = FluxCalibrationSerializer


class AvailableSpectrumParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableSpectrumParams.objects.using(f'{schema_prefix}spexodisks').order_by('pk')
    serializer_class = AvailableSpectrumParamsSerializer


class AvailableStrParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableStrParams.objects.using(f'{schema_prefix}spexodisks').order_by('pk')
    serializer_class = AvailableStrParamsSerializer


class DjangoMigrationsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoMigrations.objects.using('default').order_by('pk')
    serializer_class = DjangoMigrationsSerializer


class LineFluxesCoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineFluxesCo.objects.using(f'{schema_prefix}spexodisks').all()
    serializer_class = LineFluxesCoSerializer