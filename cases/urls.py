from django.urls import path
from cases import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('add_visit/', views.addVisitRecordView.as_view(), name="add_visit_record"),
    path('save_geodata/', views.saveGeoData, name='save_geodata'),
    path('query_locdb/', views.queryLocationDB, name='query_locdb'),
    path('save_visit/', views.saveVisit, name="save_visit"),
    path('', views.casesView.as_view(), name="view_cases"),
    path('case/<int:case>/', views.caseDetails.as_view(), name='case_details'),
    path('login/', views.LoginView, name='login'),
    path('logout/', views.LogoutView, name='logout'),
    path('view_clusters/', views.clustersView.as_view(), name="view_clusters"),
]
