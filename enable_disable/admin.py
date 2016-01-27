from django.contrib import admin
from enable_disable.models import Job, ValidationRule, WorkflowRule, ApexTrigger, Flow, DeployJob, DeployJobComponent
from import_export.admin import ImportExportModelAdmin

"""
	INLINES/RELATED LISTS 
"""
class ValidationRuleInline(admin.TabularInline):
	fields = ['object_name','name','active']
	ordering = ['object_name', 'name']
	model = ValidationRule
	extra = 0

class WorkflowRuleInline(admin.TabularInline):
	fields = ['object_name','name','active']
	ordering = ['object_name', 'name']
	model = WorkflowRule
	extra = 0

class ApexTriggerInline(admin.TabularInline):
	fields = ['name','active', 'content', 'meta_content']
	ordering = ['name']
	model = ApexTrigger
	extra = 0

class FlowInline(admin.TabularInline):
	fields = ['flow_id','name','active', 'active_version', 'latest_version']
	ordering = ['name']
	model = Flow
	extra = 0

class DeployJobInline(admin.TabularInline):
	fields = ['metadata_type','status','error']
	ordering = ['id']
	model = DeployJob
	extra = 0

class DeployJobComponentInline(admin.TabularInline):
	fields = ['validation_rule','workflow_rule','trigger','enable', 'status', 'error']
	ordering = ['id']
	model = DeployJobComponent
	extra = 0


"""
	ADMIN CLASSES
"""
class JobAdmin(admin.ModelAdmin):
    list_display = ('created_date','finished_date','username','status','error')
    ordering = ['-created_date']
    inlines = [ValidationRuleInline, WorkflowRuleInline, ApexTriggerInline, FlowInline, DeployJobInline]

class DeployJobAdmin(admin.ModelAdmin):
	list_display = ('job','metadata_type','status','error')
	ordering = ['-id']
	inlines = [DeployJobComponentInline]


class ValidationRuleAdmin(ImportExportModelAdmin):
    resource_class = ValidationRule
    pass


admin.site.register(Job, JobAdmin)
admin.site.register(DeployJob, DeployJobAdmin)
admin.site.register(ValidationRule, ValidationRuleAdmin)
