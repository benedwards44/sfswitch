from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView, RedirectView
from django.contrib import admin
admin.autodiscover() 

urlpatterns = patterns('',
    url(r'^$', 'enable_disable.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^oauth_response/$', 'enable_disable.views.oauth_response', name='oauth_response'),
    url(r'^logout/$', 'enable_disable.views.logout', name='logout'),
    url(r'^loading/(?P<job_id>[0-9A-Za-z_\-]+)/$', 'enable_disable.views.loading'),
    url(r'^job_status/(?P<job_id>[0-9A-Za-z_\-]+)/$', 'enable_disable.views.job_status'),
    url(r'^job/(?P<job_id>[0-9A-Za-z_\-]+)/$', 'enable_disable.views.job'),
    url(r'^update_metadata/(?P<job_id>[0-9A-Za-z_\-]+)/(?P<metadata_type>[0-9A-Za-z_\-]+)/$', 'enable_disable.views.update_metadata'),
    url(r'^check_deploy_status/(?P<deploy_job_id>\d+)/$', 'enable_disable.views.check_deploy_status'),
    url(r'^auth_details/$', 'enable_disable.views.auth_details'),
)
