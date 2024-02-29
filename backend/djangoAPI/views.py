from django.http import HttpResponse
from rest_framework import status, viewsets, permissions, generics
from rest_framework.permissions import IsAuthenticated

from rest_framework.decorators import api_view
from rest_framework.response import Response

# for Data Download
from rest_framework.views import APIView

from rest_framework import status, generics
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

from .dynamic_data import write_upload_zip, del_upload_zip
from .models import spectra_models, isotopologue_models, \
    AvailableIsotopologues, Co, H2O, \
    AvailableFloatParams, AvailableSpectrumParams, \
    AvailableStrParams, ContactContact, Curated, DjangoContentType, DjangoMigrations, \
    DjangoPlotlyDashDashapp, DjangoPlotlyDashStatelessapp, DjangoSession, FluxCalibration, LineFluxesCo, \
    MainStatelessapp, ObjectNameAliases, ObjectParamsFloat, ObjectParamsStr, Spectra, \
    StackedLineSpectra, Stars, AvailableParamsAndUnits, DefaultSpectrum, DefaultSpectrumInfo, \
    StatsTotal, StatsInstrument
from .serializers import spectra_serializers, isotopologue_serializers, \
    AvailableIsotopologuesSerializer, CoSerializer, H2OSerializer, \
    AvailableFloatParamsSerializer, \
    AvailableSpectrumParamsSerializer, AvailableStrParamsSerializer, ContactContactSerializer, CuratedSerializer, \
    DjangoContentTypeSerializer, DjangoMigrationsSerializer, \
    DjangoPlotlyDashDashappSerializer, DjangoPlotlyDashStatelessappSerializer, DjangoSessionSerializer, \
    FluxCalibrationSerializer, LineFluxesCoSerializer, \
    MainStatelessappSerializer, ObjectNameAliasesSerializer, ObjectParamsFloatSerializer, \
    ObjectParamsStrSerializer, SpectraSerializer, StackedLineSpectraSerializer, StarsSerializer, \
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
        queryset = isotopologue_models[molecule][isotopologue].objects.using('spexo').all()
        serializer_class = isotopologue_serializers[molecule][isotopologue]
        iso_view = type(view_name, (viewsets.ReadOnlyModelViewSet,), dict(__module__='views', queryset=queryset,
                                                                          serializer_class=serializer_class))
        isotopologue_views[molecule][isotopologue] = iso_view

spectra_views_base = {}
for spectrum_handle in sorted(spectra_models.keys()):
    view_name = f'{spectrum_handle.lower()}ViewSet'
    queryset = spectra_models[spectrum_handle].objects.order_by('pk')
    serializer_class = spectra_serializers[spectrum_handle]
    spectrum_view = type(view_name, (viewsets.ReadOnlyModelViewSet,), dict(__module__='views', queryset=queryset,
                                                                           serializer_class=serializer_class))
    spectra_views_base[spectrum_handle] = spectrum_view


spectrum_fields = ('wavelength_um', 'flux', 'flux_error')


spectra_views = {}
for spectrum_handle in sorted(spectra_models.keys()):
    def list(self, request):
        return Response(data={key: data_array for key, data_array in
                              zip(spectrum_fields, zip(*self.queryset.values_list(*spectrum_fields)))},
                        status=status.HTTP_200_OK)


    view_name = f'{spectrum_handle.lower()}ViewSet'

    spectra_views[spectrum_handle] = type(view_name,
                                          (viewsets.ReadOnlyModelViewSet,),
                                          dict(__module__='views',
                                               queryset=spectra_models[spectrum_handle].objects.order_by('pk'),
                                               serializer_class=spectra_serializers[spectrum_handle],
                                               list=list
                                               ))

"""
Static Views
"""


class StatsTotalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatsTotal.objects.using('spexo').all()
    serializer_class = StatsTotalSerializer


class StatsInstrumentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatsInstrument.objects.using('spexo').order_by('order_index')
    serializer_class = StatsInstrumentSerializer


class AvailableParamsAndUnitsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableParamsAndUnits.objects.using('spexo').order_by('order_index')
    serializer_class = AvailableParamsAndUnitsSerializer


class DefaultSpectrumViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultSpectrum.objects.using('spexo').order_by('pk')
    serializer_class = DefaultSpectrumSerializer

    def list(self, request):
        return Response(data={key: data_array for key, data_array in
                              zip(spectrum_fields, zip(*self.queryset.values_list(*spectrum_fields)))},
                        status=status.HTTP_200_OK)


class DefaultSpectrumInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultSpectrumInfo.objects.using('spexo').all()
    serializer_class = DefaultSpectrumInfoSerializer


class AvailableIsotopologuesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableIsotopologues.objects.using('spexo').all()
    print(queryset)
    serializer_class = AvailableIsotopologuesSerializer


class StarsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stars.objects.using('spexo').all().order_by('spexodisks_handle')
    serializer_class = StarsSerializer


class SpectraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Spectra.objects.using('spexo').all()
    serializer_class = SpectraSerializer


class CuratedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Curated.objects.using('spexo').all()
    serializer_class = CuratedSerializer


class H2OViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = H2O.objects.using('spexo').all()
    serializer_class = H2OSerializer


class CoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Co.objects.using('spexo').all()
    serializer_class = CoSerializer


class SortedIso(viewsets.ReadOnlyModelViewSet):
    queryset = Co.objects.using('spexo').all()


class AvailableFloatParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableFloatParams.objects.using('spexo').all()
    serializer_class = AvailableFloatParamsSerializer


class StackedLineSpectraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StackedLineSpectra.objects.using('spexo').all()
    serializer_class = StackedLineSpectraSerializer


class ObjectParamsStrViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectParamsStr.objects.using('spexo').all()
    serializer_class = ObjectParamsStrSerializer


class ObjectNameAliasesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectNameAliases.objects.using('spexo').all()
    serializer_class = ObjectNameAliasesSerializer


class LineFluxesCoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineFluxesCo.objects.using('spexo').all()
    serializer_class = LineFluxesCoSerializer


class MainStatelessappViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainStatelessapp.objects.using('spexo').all()
    serializer_class = MainStatelessappSerializer


class ObjectParamsFloatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ObjectParamsFloat.objects.using('spexo').all()
    serializer_class = ObjectParamsFloatSerializer


class FluxCalibrationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FluxCalibration.objects.using('spexo').all()
    serializer_class = FluxCalibrationSerializer


class AvailableSpectrumParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableSpectrumParams.objects.order_by('pk')
    serializer_class = AvailableSpectrumParamsSerializer


class AvailableStrParamsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AvailableStrParams.objects.order_by('pk')
    serializer_class = AvailableStrParamsSerializer


class ContactContactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ContactContact.objects.order_by('pk')
    serializer_class = ContactContactSerializer


class DjangoContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoContentType.objects.order_by('pk')
    serializer_class = DjangoContentTypeSerializer


class DjangoMigrationsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoMigrations.objects.order_by('pk')
    serializer_class = DjangoMigrationsSerializer


class DjangoPlotlyDashDashappViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoPlotlyDashDashapp.objects.order_by('pk')
    serializer_class = DjangoPlotlyDashDashappSerializer


class DjangoPlotlyDashStatelessappViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoPlotlyDashStatelessapp.objects.order_by('pk')
    serializer_class = DjangoPlotlyDashStatelessappSerializer


class DjangoSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoSession.objects.order_by('pk')
    serializer_class = DjangoSessionSerializer


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
    user_username = current_user.email.replace('@', '_at_').replace('.', '_dot_')
    print(user_username)
    if current_user:
        zipfile_path = write_upload_zip(username=user_username, spectra_handles=spectra_list)
        with open(zipfile_path[0], 'rb') as file_zip:
            response = HttpResponse(file_zip, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename={user_username}.zip'
            return response
    else:
        print('User is not authenticated')
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
