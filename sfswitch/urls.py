from django.conf.urls import url, include
from django.views.generic import TemplateView, RedirectView
from django.contrib import admin

from enable_disable import views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index, name='index'),
    url(r'^oauth_response/$', views.oauth_response, name='oauth_response'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^loading/(?P<job_id>[0-9A-Za-z_\-]+)/$', views.loading),
    url(r'^job_status/(?P<job_id>[0-9A-Za-z_\-]+)/$', views.job_status),
    url(r'^job/(?P<job_id>[0-9A-Za-z_\-]+)/$', views.job),
    url(r'^update_metadata/(?P<job_id>[0-9A-Za-z_\-]+)/(?P<metadata_type>[0-9A-Za-z_\-]+)/$', views.update_metadata),
    url(r'^check_deploy_status/(?P<deploy_job_id>\d+)/$', views.check_deploy_status),
    url(r'^auth_details/$', views.auth_details),
]
