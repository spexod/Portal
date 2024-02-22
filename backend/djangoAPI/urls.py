from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


from . import views

# define the router
router = routers.DefaultRouter()

"""
Static API URLs
"""
# metadata tables currently used by the FrontEnd
router.register(r'spectra', views.SpectraViewSet)
router.register(r'curated', views.CuratedViewSet)
router.register(r'objectnamealiases', views.ObjectNameAliasesViewSet)
router.register(r'stats_total', views.StatsTotalViewSet)
router.register(r'stats_instrument', views.StatsInstrumentViewSet)
router.register(r'available_isotopologues', views.AvailableIsotopologuesViewSet)
router.register(r'available_params_and_units', views.AvailableParamsAndUnitsViewSet)
router.register(r'default_spectrum', views.DefaultSpectrumViewSet)
router.register(r'default_spectrum_info', views.DefaultSpectrumInfoViewSet)

"""
Dynamic API URLs
"""
# isotopologue
for molecule in sorted(views.isotopologue_views.keys()):
    for isotopologue in sorted(views.isotopologue_views[molecule].keys()):
        router.register(f'isotopologue_{isotopologue.lower()}', views.isotopologue_views[molecule][isotopologue])

# spectra
for spectrum_handle in sorted(views.spectra_views.keys()):
    router.register(f'{spectrum_handle.lower()}', views.spectra_views[spectrum_handle])


"""
Tables with duplicated information in other tables, these are raw versions of the available data
"""

# router.register(r'objectparamsfloat', views.ObjectParamsFloatViewSet)
# router.register(r'objectparamsstr', views.ObjectParamsStrViewSet)
# router.register(r'co', views.CoViewSet)
# router.register(r'h2o', views.H2OViewSet)
# router.register(r'availablefloatparams', views.AvailableFloatParamsViewSet)
# router.register(r'availablespectrumparams', views.AvailableSpectrumParamsViewSet)
# router.register(r'availablestrparams', views.AvailableStrParamsViewSet)


"""
URL Patterns
"""
urlpatterns = [path('', include(router.urls)),
               path('datadownload/', views.download_spectra),
               path('users/token/', TokenObtainPairView.as_view()),
               path('users/token/refresh/', TokenRefreshView.as_view()),
               path('users/token/verify/', TokenVerifyView.as_view()),
               path('users/register', views.RegisterView.as_view()),
               path('users/me', views.RetrieveUserView.as_view()),
               path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
               path('password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
               ]
