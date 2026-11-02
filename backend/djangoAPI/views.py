import os
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions

from rest_framework.decorators import api_view, permission_classes

# for Data Download
from rest_framework.views import APIView

from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django_rest_passwordreset.views import ResetPasswordRequestToken, ResetPasswordConfirm

from . import accounts
from .dynamic_data import (dispatch, schema_prefix,
                           available_spectra_to_database, available_isotopologues_to_database)
from .models import spectra_models, isotopologue_models, \
    AvailableIsotopologues, Curated, ObjectNameAliases, Spectra, \
    AvailableParamsAndUnits, DefaultSpectrum, DefaultSpectrumInfo, \
    StatsTotal, StatsInstrument
from .serializers import spectra_serializers, isotopologue_serializers, \
    AvailableIsotopologuesSerializer, CuratedSerializer, ObjectNameAliasesSerializer, SpectraSerializer, \
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


def list_spectrum(self, request):
    """ The "list" action of every per-spectrum view set: one array per column instead of one row per point.
    (Defined at module level under its own name: a module-level "def list" shadowed the built-in list().) """
    return Response(data={key: data_array for key, data_array in
                          zip(spectrum_fields, zip(*self.queryset.values_list(*spectrum_fields)))},
                    status=status.HTTP_200_OK)


spectra_views = {}
for spectrum_handle in sorted(spectra_models.keys()):
    view_name = f'{spectrum_handle.lower()}ViewSet'
    database_this_handle = available_spectra_to_database[spectrum_handle]
    queryset = spectra_models[spectrum_handle].objects.using(database_this_handle).order_by('pk')
    spectra_views[spectrum_handle] = type(view_name,
                                          (viewsets.ReadOnlyModelViewSet,),
                                          dict(__module__='views',
                                               queryset=queryset,
                                               serializer_class=spectra_serializers[spectrum_handle],
                                               throttle_scope='spectra',
                                               list=list_spectrum))

"""
Static Views
"""


User = get_user_model()

# limits per download request, see download_spectra
DOWNLOAD_MAX_SPECTRA = int(os.environ.get('DOWNLOAD_MAX_SPECTRA', '200'))
DOWNLOAD_MAX_BYTES = int(os.environ.get('DOWNLOAD_MAX_BYTES', str(2 * 1024 ** 3)))


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
@permission_classes([IsAuthenticated])
def download_spectra(request):
    """
    Get a list of strings from a user with the spectra they would like to download.
    Each spectra being seperated with a % character.

    The zip (uncompressed) is written to a temporary file and streamed, so a request holds at most a small
    part of it in memory; the number of spectra and the total size per request are limited.
    """
    # drop empty entries and duplicates, keeping the order
    spectra_list = list(dict.fromkeys(handle for handle in request.query_params.get('spectra', '').split('%') if handle))
    if not spectra_list:
        return Response({'detail': 'No spectra requested.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(spectra_list) > DOWNLOAD_MAX_SPECTRA:
        return Response({'detail': f'At most {DOWNLOAD_MAX_SPECTRA} spectra per download.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        zip_file, size = dispatch.zip_upload(spectra_handles=spectra_list, max_bytes=DOWNLOAD_MAX_BYTES)
    except dispatch.TooLarge as too_large:
        return Response({'detail': f'The requested spectra are {too_large.total_bytes / 1024 ** 2:.0f} MB, at most '
                                   f'{DOWNLOAD_MAX_BYTES / 1024 ** 2:.0f} MB per download: request fewer spectra.'},
                        status=status.HTTP_400_BAD_REQUEST)
    response = FileResponse(zip_file, as_attachment=True, filename='spexodisks.zip', content_type='application/zip')
    response['Content-Length'] = str(size)
    return response


def revoke_all_tokens(user):
    """ Blacklist every refresh token issued to a user (after a password change or reset). """
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


# the 'auth' throttle scope (core/settings.py) limits password guessing and reset-email floods
class LoginView(TokenObtainPairView):
    throttle_scope = 'auth'


class RefreshView(TokenRefreshView):
    # every logged-in browser refreshes about every five minutes, so this scope is separate from the
    # password-guessing limit, which users behind one shared address would otherwise exhaust together
    throttle_scope = 'refresh'


class PasswordResetRequestView(ResetPasswordRequestToken):
    throttle_scope = 'auth'


class PasswordResetConfirmView(ResetPasswordConfirm):
    throttle_scope = 'auth'


class LogoutView(APIView):
    """ Revoke the refresh token, so a logout also ends the session on the server. """
    # the refresh token in the body is the credential: an expired access token must not prevent the logout
    # (the frontend sends its Authorization header anyway, and logs out exactly when that token was refused,
    # so the default JWT authentication would answer 401 before this view runs)
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        try:
            RefreshToken(request.data.get('refresh', '')).blacklist()
        except TokenError:
            # already revoked, expired or missing: the client is logged out either way
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class RegisterView(APIView):
    """
    Register a new user.

    The answer is the same whether or not the address already has an account (the address's owner gets a mail
    either way: the confirmation link, or a note that the account exists), so the endpoint does not reveal who
    is registered. With REQUIRE_EMAIL_VERIFICATION the new account is inactive until the link is used.
    """
    throttle_scope = 'auth'

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if settings.REQUIRE_EMAIL_VERIFICATION:
            detail = ('If the address is new, the account was created: open the link in the mail we sent to '
                      'confirm the address, then log in.')
        else:
            detail = 'If the address is new, the account was created: you can log in.'
        answer = Response({'detail': detail}, status=status.HTTP_201_CREATED)

        email = User.objects.normalize_email(serializer.validated_data['email']).lower()
        existing = User.objects.filter(email=email).first()
        if existing is None:
            try:
                with transaction.atomic():
                    user = serializer.create(serializer.validated_data)
            except IntegrityError:
                # registered twice at the same moment: the same answer as for an existing address
                existing = User.objects.filter(email=email).first()
            else:
                if settings.REQUIRE_EMAIL_VERIFICATION:
                    user.is_active = False
                    user.save(update_fields=['is_active'])
                    accounts.send_verification_mail(user)
                return answer
        if existing is not None:
            if existing.is_active or not settings.REQUIRE_EMAIL_VERIFICATION:
                accounts.send_existing_account_mail(existing)
            else:
                # registered before, the link was never used (or expired): a fresh link
                accounts.send_verification_mail(existing)
        return answer


class VerifyEmailView(APIView):
    """ Activate the account named by a confirmation token from the registration mail. """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        user = accounts.user_from_token(request.data.get('token', ''))
        if user is None:
            return Response({'detail': 'This confirmation link is not valid or has expired. Register again with the '
                                       'same address to receive a new one.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
        return Response({'detail': 'Your email address is confirmed: you can log in.'}, status=status.HTTP_200_OK)


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
            # other devices and browsers have to log in again with the new password
            revoke_all_tokens(self.object)
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
