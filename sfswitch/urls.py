from django.urls import path
from django.views.generic import TemplateView
from django.contrib import admin

from enable_disable import views

urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', admin.site.urls),
    path('oauth_response/', views.oauth_response, name='oauth_response'),
    path('logout/', views.logout, name='logout'),
    path('loading/<str:job_id>/', views.loading),
    path('job_status/<str:job_id>/', views.job_status),
    path('job/<str:job_id>/', views.job),
    path('update_metadata/<str:job_id>/<str:metadata_type>/', views.update_metadata),
    path('check_deploy_status/<str:deploy_job_id>/', views.check_deploy_status),
    path('auth_details/', views.auth_details),
]
