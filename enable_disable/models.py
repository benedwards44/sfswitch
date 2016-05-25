from django.db import models

class Job(models.Model):
	random_id = models.CharField(db_index=True, max_length=255, blank=True, null=True)
	created_date = models.DateTimeField(null=True, blank=True)
	finished_date = models.DateTimeField(null=True, blank=True)
	org_id = models.CharField(max_length=255)
	org_name = models.CharField(max_length=255, blank=True, null=True)
	username = models.CharField(max_length=255, blank=True, null=True)
	access_token = models.CharField(max_length=255, blank=True, null=True)
	instance_url = models.CharField(max_length=255, blank=True, null=True)
	json_message = models.TextField(blank=True, null=True)
	is_sandbox = models.BooleanField(default=False)
	status = models.CharField(max_length=255, blank=True, null=True)
	error = models.TextField(blank=True, null=True)

	def validation_rules(self):
		return self.validationrule_set.order_by('object_name', 'name')

	def workflow_rules(self):
		return self.workflowrule_set.order_by('object_name', 'name')

	def triggers(self):
		return self.apextrigger_set.order_by('name')

	def flows(self):
		return self.flow_set.order_by('name')

	def __str__(self):
		return '%s' % (self.random_id)

class ValidationRule(models.Model):
	job = models.ForeignKey(Job)
	object_name = models.CharField(max_length=255, blank=True, null=True)
	name = models.CharField(max_length=255, blank=True, null=True)
	active = models.BooleanField()
	description = models.TextField(blank=True, null=True)
	errorConditionFormula = models.TextField(blank=True, null=True)
	errorDisplayField = models.CharField(max_length=255, blank=True, null=True)
	errorMessage = models.TextField(blank=True, null=True)
	fullName = models.CharField(max_length=255, blank=True, null=True)

	def __str__(self):
		return '%s' % (self.fullName)

class WorkflowRule(models.Model):
	job = models.ForeignKey(Job)
	object_name = models.CharField(max_length=255, blank=True, null=True)
	name = models.CharField(max_length=255, blank=True, null=True)
	active = models.BooleanField()
	actions = models.TextField(blank=True, null=True)
	booleanFilter = models.CharField(max_length=255, blank=True, null=True)
	criteriaItems = models.TextField(blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	formula = models.TextField(blank=True, null=True)
	fullName = models.CharField(max_length=255, blank=True, null=True)
	triggerType = models.CharField(max_length=255, blank=True, null=True)
	workflowTimeTriggers = models.TextField(blank=True, null=True)

	def __str__(self):
		return '%s' % (self.fullName)

class ApexTrigger(models.Model):
	job = models.ForeignKey(Job)
	active = models.BooleanField(default=False)
	content = models.TextField(blank=True, null=True)
	meta_content = models.TextField(blank=True, null=True)
	name = models.CharField(max_length=255, blank=True, null=True)

	def __str__(self):
		return '%s' % (self.name)

class Flow(models.Model):
	job = models.ForeignKey(Job)
	flow_id = models.CharField(max_length=255, blank=True, null=True)
	active = models.BooleanField(default=False)
	name = models.CharField(max_length=255, blank=True, null=True)
	latest_version = models.SmallIntegerField(blank=True, null=True)
	active_version = models.SmallIntegerField(blank=True, null=True)

	def __str__(self):
		return '%s' % (self.name)


class DeployJob(models.Model):
	job = models.ForeignKey(Job)
	metadata_type = models.CharField(max_length=255, blank=True, null=True)
	deploy_result = models.TextField(blank=True, null=True)
	status = models.CharField(max_length=255, blank=True, null=True)
	error = models.TextField(blank=True, null=True)

	def __str__(self):
		return '%s - %s' % (self.job.username, self.metadata_type)

class DeployJobComponent(models.Model):
	deploy_job = models.ForeignKey(DeployJob)
	validation_rule = models.ForeignKey(ValidationRule, blank=True, null=True)
	workflow_rule = models.ForeignKey(WorkflowRule, blank=True, null=True)
	flow = models.ForeignKey(Flow, blank=True, null=True)
	trigger = models.ForeignKey(ApexTrigger, blank=True, null=True)
	enable = models.BooleanField()
	status = models.CharField(max_length=255, blank=True, null=True)
	error = models.TextField(blank=True, null=True)

