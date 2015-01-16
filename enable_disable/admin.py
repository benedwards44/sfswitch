from django.contrib import admin
from enable_disable.models import Job, ValidationRule, WorkflowRule, ApexTrigger, DeployJob, DeployJobComponent

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
    list_display = ('created_date','finished_date','status','error')
    ordering = ['-created_date']
    inlines = [ValidationRuleInline, WorkflowRuleInline, ApexTriggerInline, DeployJobInline]

class DeployJobAdmin(admin.ModelAdmin):
	list_display = ('job','metadata_type','status','error')
	ordering = ['-id']
	inlines = [DeployJobComponentInline]


admin.site.register(Job, JobAdmin)
admin.site.register(DeployJob, DeployJobAdmin)
