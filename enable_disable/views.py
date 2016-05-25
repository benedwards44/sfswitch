from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from enable_disable.models import Job, ValidationRule, WorkflowRule, ApexTrigger, Flow, DeployJob, DeployJobComponent
from enable_disable.forms import LoginForm
from django.conf import settings
from enable_disable.tasks import get_metadata, deploy_metadata
from suds.client import Client
import uuid
import json	
import requests
import datetime
from time import sleep
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

def index(request):
	
	if request.method == 'POST':

		login_form = LoginForm(request.POST)

		if login_form.is_valid():

			environment = login_form.cleaned_data['environment']

			oauth_url = 'https://login.salesforce.com/services/oauth2/authorize'
			if environment == 'Sandbox':
				oauth_url = 'https://test.salesforce.com/services/oauth2/authorize'

			oauth_url = oauth_url + '?response_type=code&client_id=' + settings.SALESFORCE_CONSUMER_KEY + '&redirect_uri=' + settings.SALESFORCE_REDIRECT_URI + '&state='+ environment
			
			return HttpResponseRedirect(oauth_url)
	else:
		login_form = LoginForm()

	return render_to_response('index.html', RequestContext(request,{'login_form': login_form}))

def oauth_response(request):

	error_exists = False
	error_message = ''
	username = ''
	org_name = ''
	org_id = ''

	# On page load
	if request.GET:

		oauth_code = request.GET.get('code')
		environment = request.GET.get('state')
		access_token = ''
		instance_url = ''

		if 'Production' in environment:
			login_url = 'https://login.salesforce.com'
		else:
			login_url = 'https://test.salesforce.com'
		
		r = requests.post(login_url + '/services/oauth2/token', headers={ 'content-type':'application/x-www-form-urlencoded'}, data={'grant_type':'authorization_code','client_id': settings.SALESFORCE_CONSUMER_KEY,'client_secret':settings.SALESFORCE_CONSUMER_SECRET,'redirect_uri': settings.SALESFORCE_REDIRECT_URI,'code': oauth_code})
		auth_response = json.loads(r.text)

		if 'error_description' in auth_response:
			error_exists = True
			error_message = auth_response['error_description']
		else:
			access_token = auth_response['access_token']
			instance_url = auth_response['instance_url']
			user_id = auth_response['id'][-18:]
			org_id = auth_response['id'][:-19]
			org_id = org_id[-18:]

			# get username of the authenticated user
			r = requests.get(instance_url + '/services/data/v' + str(settings.SALESFORCE_API_VERSION) + '.0/sobjects/User/' + user_id + '?fields=Username', headers={'Authorization': 'OAuth ' + access_token})
			query_response = json.loads(r.text)
			username = query_response['Username']

			# get the org name of the authenticated user
			r = requests.get(instance_url + '/services/data/v' + str(settings.SALESFORCE_API_VERSION) + '.0/sobjects/Organization/' + org_id + '?fields=Name', headers={'Authorization': 'OAuth ' + access_token})
			org_name = json.loads(r.text)['Name']

		login_form = LoginForm(initial={'environment': environment, 'access_token': access_token, 'instance_url': instance_url, 'org_id': org_id, 'username': username, 'org_name':org_name})	

	# Run after user selects logout or get schema
	if request.POST:

		login_form = LoginForm(request.POST)

		if login_form.is_valid():

			environment = login_form.cleaned_data['environment']
			access_token = login_form.cleaned_data['access_token']
			instance_url = login_form.cleaned_data['instance_url']
			org_id = login_form.cleaned_data['org_id']
			username = login_form.cleaned_data['username']
			org_name = login_form.cleaned_data['org_name']

			if 'logout' in request.POST:

				r = requests.post(instance_url + '/services/oauth2/revoke', headers={'content-type':'application/x-www-form-urlencoded'}, data={'token': access_token})
				return HttpResponseRedirect('/logout?instance_prefix=' + instance_url.replace('https://','').replace('.salesforce.com',''))

			if 'get_metadata' in request.POST:

				job = Job()
				job.random_id = uuid.uuid4()
				job.created_date = datetime.datetime.now()
				job.status = 'Not Started'
				job.username = username
				job.org_id = org_id
				job.org_name = org_name
				job.instance_url = instance_url
				job.access_token = access_token
				job.is_sandbox = 'Production' not in environment
				job.save()

				# Start downloading metadata using async task
				get_metadata.delay(job)

				return HttpResponseRedirect('/loading/' + str(job.random_id))

	return render_to_response('oauth_response.html', RequestContext(request,{'error': error_exists, 'error_message': error_message, 'username': username, 'org_name': org_name, 'login_form': login_form}))

def logout(request):

	# Determine logout url based on environment
	instance_prefix = request.GET.get('instance_prefix')
		
	return render_to_response('logout.html', RequestContext(request, {'instance_prefix': instance_prefix}))

# AJAX endpoint for page to constantly check if job is finished
def job_status(request, job_id):

	job = get_object_or_404(Job, random_id = job_id)

	response_data = {
		'status': job.status,
		'error': job.error
	}

	return HttpResponse(json.dumps(response_data), content_type = 'application/json')

# Page for user to wait for job to run
def loading(request, job_id):

	job = get_object_or_404(Job, random_id = job_id)

	if job.status == 'Finished':

		# Return URL when job is finished
		return_url = '/job/' + str(job.random_id) + '/'

		# If no header is in URL, keep it there
		if request.GET.noheader == '1':
			return_url += '?noheader=1'

		return HttpResponseRedirect(return_url)

	else:
		
		return render_to_response('loading.html', RequestContext(request, {'job': job}))	

def job(request, job_id):
	"""
	Controller to page that displays metadata components
	
	"""

	job = get_object_or_404(Job, random_id = job_id)

	# Map of objects to their validation rules
	val_object_names = []
	for val_rule in job.validation_rules():
		val_object_names.append(val_rule.object_name)
		
	# Make a unique list
	val_object_names = list(set(val_object_names))
	val_object_names.sort()

	# Map of objects to their workflow rules
	wf_object_names = []
	for workflow_rule in job.workflow_rules():
		wf_object_names.append(workflow_rule.object_name)
		
	# make a unique list
	wf_object_names = list(set(wf_object_names))
	wf_object_names.sort()


	return render_to_response('job.html', RequestContext(request, {
		'job': job, 
		'val_object_names': val_object_names, 
		'val_rules': job.validation_rules(),
		'wf_object_names': wf_object_names, 
		'wf_rules': job.workflow_rules(),
		'triggers': job.triggers(),
		'flows': job.flows()
	}))

def update_metadata(request, job_id, metadata_type):

	job = get_object_or_404(Job, random_id = job_id)

	deploy_job = DeployJob()
	deploy_job.job = job
	deploy_job.status = 'Not Started'
	deploy_job.metadata_type = metadata_type
	deploy_job.save()

	try:

		components_for_update = json.loads(request.POST.get('components'))

		for component in components_for_update:

			deploy_job_component = DeployJobComponent()
			deploy_job_component.deploy_job = deploy_job

			if metadata_type == 'validation_rule':

				deploy_job_component.validation_rule = ValidationRule.objects.get(id = int(component['component_id']))

			elif metadata_type == 'workflow_rule':

				deploy_job_component.workflow_rule = WorkflowRule.objects.get(id = int(component['component_id']))

			elif metadata_type == 'trigger':

				deploy_job_component.trigger = ApexTrigger.objects.get(id = int(component['component_id']))

			elif metadata_type == 'flow':

				deploy_job_component.flow = Flow.objects.get(id = int(component['component_id']))

			deploy_job_component.enable = component['enable']
			deploy_job_component.save()

		deploy_metadata.delay(deploy_job)

	except Exception as error:

		deploy_job.status = 'Error'
		deploy_job.error = error
		deploy_job.save()

	return HttpResponse(deploy_job.id)


def check_deploy_status(request, deploy_job_id):

	deploy_job = get_object_or_404(DeployJob, id = deploy_job_id)

	response_data = {
		'status': deploy_job.status,
		'error': deploy_job.error
	}

	return HttpResponse(json.dumps(response_data), content_type = 'application/json')


@csrf_exempt
def auth_details(request):
	"""
		RESTful endpoint to pass authentication details
	"""

	try:

		request_data = json.loads(request.body)

		# Check for all required fields
		if 'org_id' not in request_data or 'access_token' not in request_data or 'instance_url' not in request_data:

			response_data = {
				'status': 'Error',
				'success':  False,
				'error_text': 'Not all required fields were found in the message. Please ensure org_id, access_token and instance_url are all passed in the payload'
			}

		# All fields exist. Start job and send response
		else:

			# create the package record to store results
			job = Job()
			job.random_id = uuid.uuid4()
			job.created_date = datetime.datetime.now()
			job.status = 'Not Started'
			job.org_id = request_data['org_id']
			job.instance_url = request_data['instance_url']
			job.access_token = request_data['access_token']
			job.save()

			# Attempt to get username and org name. 
			try:

				# get the org name of the authenticated user
				r = requests.get(job.instance_url + '/services/data/v' + str(settings.SALESFORCE_API_VERSION) + '.0/sobjects/Organization/' + job.org_id + '?fields=Name', headers={'Authorization': 'OAuth ' + job.access_token})
				job.org_name = json.loads(r.text)['Name']
				job.save()

			# If there is an error, we can live with that.
			except:
				pass

			# Run job
			get_metadata.delay(job)

			# Build response 
			response_data = {
				'job_url': 'https://sfswitch.herokuapp.com/loading/' + str(job.random_id) + '/?noheader=1',
				'status': 'Success',
				'success': True
			}

	except Exception as error:

		# If there is an error, raise exception and return
		response_data = {
			'status': 'Error',
			'success':  False,
			'error_text': str(error)
		}
	
	return HttpResponse(json.dumps(response_data), content_type = 'application/json')
