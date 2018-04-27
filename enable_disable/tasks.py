from __future__ import absolute_import
from celery import Celery
from django.conf import settings
from zipfile import ZipFile
from suds.client import Client
from base64 import b64encode, b64decode
import requests
import json
import xml.etree.ElementTree as ET
import os
import glob
import datetime
import time
import sys
import traceback

reload(sys)
sys.setdefaultencoding("utf-8")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sfswitch.settings')

app = Celery('tasks', broker=os.environ.get('REDISTOGO_URL', 'redis://localhost'))

from enable_disable.models import Job, ValidationRule, WorkflowRule, ApexTrigger, Flow, DeployJob, DeployJobComponent

@app.task
def get_metadata(job): 
	
	job.status = 'Downloading Metadata'
	job.save()

	try:

		# instantiate the metadata WSDL
		metadata_client = Client('http://sfswitch.herokuapp.com/static/metadata-' + str(settings.SALESFORCE_API_VERSION) + '.xml')

		# URL for metadata API
		metadata_url = job.instance_url + '/services/Soap/m/' + str(settings.SALESFORCE_API_VERSION) + '.0/' + job.org_id

		# set the metadata url based on the login result
		metadata_client.set_options(location = metadata_url)

		# set the session id from the login result
		session_header = metadata_client.factory.create("SessionHeader")
		session_header.sessionId = job.access_token
		metadata_client.set_options(soapheaders = session_header)

		component_list = []

		component = metadata_client.factory.create("ListMetadataQuery")
		component.type = 'ValidationRule'
		component_list.append(component)

		component = metadata_client.factory.create("ListMetadataQuery")
		component.type = 'WorkflowRule'
		component_list.append(component)

		component = metadata_client.factory.create("ListMetadataQuery")
		component.type = 'ApexTrigger'
		component_list.append(component)

		validation_rules = []
		workflows = []
		triggers = []

		# Note: Only 3 metadata types supported
		for component in metadata_client.service.listMetadata(component_list, settings.SALESFORCE_API_VERSION):

			if component and component.fullName:

				if component.type == 'ValidationRule':
					validation_rules.append(component.fullName)

				if component.type == 'WorkflowRule':
					workflows.append(component.fullName)

				if component.type == 'ApexTrigger':
					triggers.append(component.fullName)

		# Logic to query for details for each type of metadata.
		# Note: Only 10 components are supported per query, so the list and counter are used to ensure that is met.

		query_list = []
		loop_counter = 0

		for validation_rule in validation_rules:

			query_list.append(validation_rule)

			if len(query_list) >= 10 or (len(validation_rules) - loop_counter) <= 10:

				for component in metadata_client.service.readMetadata('ValidationRule', query_list)[0]:

					if component:

						val_rule = ValidationRule()
						val_rule.job = job
						val_rule.object_name = component.fullName.split('.')[0]
						val_rule.name = component.fullName.split('.')[1]
						val_rule.fullName = component.fullName
						val_rule.active = component.active

						if 'description' in component:
							val_rule.description = component.description.encode('ascii', 'replace')

						if 'errorConditionFormula' in component:
							val_rule.errorConditionFormula = component.errorConditionFormula.encode('ascii', 'replace')

						if 'errorDisplayField' in component:
							val_rule.errorDisplayField = component.errorDisplayField.encode('ascii', 'replace')

						if 'errorMessage' in component:
							val_rule.errorMessage = component.errorMessage.encode('ascii', 'replace')

						val_rule.save()

				query_list = []

			loop_counter = loop_counter + 1

		query_list = []
		loop_counter = 0

		for workflow in workflows:

			query_list.append(workflow)

			if len(query_list) >= 10 or (len(workflows) - loop_counter) <= 10:

				for component in metadata_client.service.readMetadata('WorkflowRule', query_list)[0]:

					if component:

						wflow_rule = WorkflowRule()
						wflow_rule.job = job
						wflow_rule.object_name = component.fullName.split('.')[0]
						wflow_rule.name = component.fullName.split('.')[1]
						wflow_rule.fullName = component.fullName
						wflow_rule.active = component.active

						if 'actions' in component:
							actions = ''
							for action in component.actions:
								actions += '- ' + action.type + ': ' + action.name + '\n'
							wflow_rule.actions = actions.rstrip()

						if 'booleanFilter' in component:
							wflow_rule.booleanFilter = component.booleanFilter.encode('ascii', 'replace')

						if 'criteriaItems' in component:
							criteria_items = ''
							for criteriaItem in component.criteriaItems:
								criteria_items += '- ' + criteriaItem.field.split('.')[1] + ' ' + criteriaItem.operation + ' '
								if 'value' in criteriaItem:
									if criteriaItem.value:
										criteria_items += criteriaItem.value
								elif 'valueField' in criteriaItem:
									if criteriaItem.valueField:
										criteria_items += criteriaItem.valueField
								criteria_items += '\n'

							wflow_rule.criteriaItems = criteria_items.rstrip()

						if 'description' in component:
							wflow_rule.description = component.description.encode('ascii', 'replace')

						if 'formula' in component:
							wflow_rule.formula = component.formula.encode('ascii', 'replace')

						if 'triggerType' in component:
							wflow_rule.triggerType = component.triggerType.encode('ascii', 'replace')

						if 'workflowTimeTriggers' in component:
							time_triggers = ''
							for time_trigger in component.workflowTimeTriggers:
								time_triggers += '- ' + time_trigger.timeLength + ' ' + time_trigger.workflowTimeTriggerUnit + ':\n'
								if 'actions' in time_trigger:
									for action in time_trigger.actions:
										time_triggers += '---- ' + action.type + ': ' + action.name + '\n'
								time_triggers += '\n'
							wflow_rule.workflowTimeTriggers = time_triggers.rstrip()

						wflow_rule.save()

				query_list = []

			loop_counter = loop_counter + 1

		# Query for flows
		# Note: Using the Tooling REST API, as the Metadata API didn't return the stuff I needed
		# And the Tooling SOAP API I couldn't get working
		request_url = job.instance_url + '/services/data/v' + str(settings.SALESFORCE_API_VERSION) + '.0/tooling/'
		request_url += 'query/?q=Select+Id,ActiveVersion.VersionNumber,LatestVersion.VersionNumber,DeveloperName+From+FlowDefinition'
		headers = { 
			'Accept': 'application/json',
			'X-PrettyPrint': 1,
			'Authorization': 'Bearer ' + job.access_token
		}

		flows_query = requests.get(request_url, headers = headers)

		if flows_query.status_code == 200 and 'records' in flows_query.json():

			for component in flows_query.json()['records']:

				if component:

					flow = Flow()
					flow.job = job
					flow.name = component['DeveloperName']
					flow.flow_id = component['Id']
					flow.active = False

					if 'LatestVersion' in component and component['LatestVersion']:
						flow.latest_version = component['LatestVersion']['VersionNumber']
					else:
						flow.latest_version = 1

					if 'ActiveVersion' in component and component['ActiveVersion']:
						flow.active_version = component['ActiveVersion']['VersionNumber']
						flow.active = True

					flow.save()

		if triggers:

			# Get triggers
			retrieve_request = metadata_client.factory.create('RetrieveRequest')
			retrieve_request.apiVersion = settings.SALESFORCE_API_VERSION
			retrieve_request.singlePackage = True
			retrieve_request.packageNames = None
			retrieve_request.specificFiles = None

			trigger_retrieve_list = []

			for trigger in triggers:

				trigger_to_retrieve = metadata_client.factory.create('PackageTypeMembers')
				trigger_to_retrieve.members = trigger
				trigger_to_retrieve.name = 'ApexTrigger'
				trigger_retrieve_list.append(trigger_to_retrieve)
			
			package_to_retrieve = metadata_client.factory.create('Package')
			package_to_retrieve.apiAccessLevel = None
			package_to_retrieve.types = trigger_retrieve_list
			package_to_retrieve.packageType = None # This stupid line of code took me ages to work out!

			# Add retrieve package to the retrieve request
			retrieve_request.unpackaged = package_to_retrieve

			# Start the async retrieve job
			retrieve_job = metadata_client.service.retrieve(retrieve_request)

			# Set the retrieve result - should be unfinished initially
			retrieve_result = metadata_client.service.checkRetrieveStatus(retrieve_job.id, True)

			# Continue to query retrieve result until it's done
			while not retrieve_result.done:

				# check job status
				retrieve_result = metadata_client.service.checkRetrieveStatus(retrieve_job.id, True)

				# sleep job for 3 seconds
				time.sleep(3)

			if not retrieve_result.success:

				job.status = 'Error'
				job.json_message = retrieve_result

				if 'errorMessage' in retrieve_result:
					job.error = retrieve_result.errorMessage

				if 'messages' in retrieve_result:
					job.error = retrieve_result.messages[0].problem

			else:

				job.json_message = retrieve_result

				# Save the zip file result to server
				zip_file = open('metadata.zip', 'w+')
				zip_file.write(b64decode(retrieve_result.zipFile))
				zip_file.close()

				# Open zip file
				metadata = ZipFile('metadata.zip', 'r')

				# Loop through files in the zip file
				for filename in metadata.namelist():

					try:

						if '-meta.xml' not in filename.split('/')[1]:
							
							trigger = ApexTrigger()
							trigger.job = job
							trigger.name = filename.split('/')[1][:-8]
							trigger.content = metadata.read(filename)
							trigger.save()

						else:

							# Take the previous trigger to assign meta content to
							trigger = ApexTrigger.objects.all().order_by('-id')[0]
							trigger.meta_content = metadata.read(filename)

							# Find status of trigger from meta xml
							for node in ET.fromstring(metadata.read(filename)):
								if 'status' in node.tag:
									trigger.active = node.text == 'Active'
									break

							trigger.save()

					# not in a folder (could be package.xml). Skip record
					except Exception as error:
						continue

				# Delete zip file, no need to store
				os.remove('metadata.zip')

				job.status = 'Finished'
		else:

			job.status = 'Finished'

	except Exception as error:
		
		job.status = 'Error'
		job.error = traceback.format_exc()

	job.finished_date = datetime.datetime.now()
	job.save()


@app.task
def deploy_metadata(deploy_job): 

	deploy_job.status = 'Deploying'
	deploy_job.save()

	# Set up metadata API connection
	metadata_client = Client('http://sfswitch.herokuapp.com/static/metadata-' + str(settings.SALESFORCE_API_VERSION) + '.xml')
	metadata_url = deploy_job.job.instance_url + '/services/Soap/m/' + str(settings.SALESFORCE_API_VERSION) + '.0/' + deploy_job.job.org_id
	metadata_client.set_options(location = metadata_url)
	session_header = metadata_client.factory.create("SessionHeader")
	session_header.sessionId = deploy_job.job.access_token
	metadata_client.set_options(soapheaders = session_header)

	deploy_components = DeployJobComponent.objects.filter(deploy_job = deploy_job.id)

	try:

		if deploy_job.metadata_type == 'validation_rule':

			update_list = []
			loop_counter = 0

			for deploy_component in deploy_components:

				update_list.append(deploy_component.validation_rule.fullName)

				if len(update_list) >= 10 or (len(deploy_components) - loop_counter) <= 10:

					update_components = metadata_client.service.readMetadata('ValidationRule', update_list)[0]
					for update_component in update_components:
						update_component.active = deploy_component.enable

					result = metadata_client.service.updateMetadata(update_components)

					if not result[0].success:

						deploy_job.status = 'Error'
						deploy_job.error = result[0].errors[0].message

					update_list = []

				loop_counter = loop_counter + 1

			if deploy_job.status != 'Error':
				deploy_job.status = 'Finished'

		elif deploy_job.metadata_type == 'workflow_rule':

			update_list = []
			loop_counter = 0

			for deploy_component in deploy_components:

				update_list.append(deploy_component.workflow_rule.fullName)

				if len(update_list) >= 10 or (len(deploy_components) - loop_counter) <= 10:

					update_components = metadata_client.service.readMetadata('WorkflowRule', update_list)[0]
					for update_component in update_components:
						update_component.active = deploy_component.enable

					result = metadata_client.service.updateMetadata(update_components)

					if not result[0].success:

						deploy_job.status = 'Error'
						deploy_job.error = result[0].errors[0].message

					update_list = []

				loop_counter = loop_counter + 1

			if deploy_job.status != 'Error':
				deploy_job.status = 'Finished'

		elif deploy_job.metadata_type == 'flow':

			# Deploy flows using REST API
			# SOAP API doesn't support an easy update
			request_url = deploy_job.job.instance_url + '/services/data/v' + str(settings.SALESFORCE_API_VERSION) + '.0/tooling/sobjects/FlowDefinition/'
			headers = { 
				'Accept': 'application/json',
				'X-PrettyPrint': 1,
				'Authorization': 'Bearer ' + deploy_job.job.access_token,
				'Content-Type': 'application/json'
			}

			for deploy_component in deploy_components:

				# Set the JSON body to patch
				if deploy_component.enable:

					flow_update = {
						'Metadata': {
							'activeVersionNumber': deploy_component.flow.latest_version
						}
					}

				else:

					flow_update = {
						'Metadata': {
							'activeVersionNumber': None
						}
					}

				# Execute patch request to update the flow
				result = requests.patch(request_url + deploy_component.flow.flow_id + '/', headers = headers, data = json.dumps(flow_update))

				if result.status_code != 200 and result.status_code != 204:
					deploy_job.status = 'Error'
					deploy_job.error = result.json()[0]['errorCode'] + ': ' + result.json()[0]['message']


			if deploy_job.status != 'Error':
				deploy_job.status = 'Finished'


		elif deploy_job.metadata_type == 'trigger':

			# Remove path if exists
			remove_triggers()

			# Create triggers directory
			os.mkdir('triggers')

			zip_file = ZipFile('deploy.zip', 'w')
		
			for deploy_component in deploy_components:

				trigger_file = open('triggers/' + deploy_component.trigger.name + '.trigger','w+')
				trigger_file.write(deploy_component.trigger.content)
				trigger_file.close()

				zip_file.write('triggers/' + deploy_component.trigger.name + '.trigger')

				trigger_meta_file = open('triggers/' + deploy_component.trigger.name + '.trigger-meta.xml','w+')
				meta_content = deploy_component.trigger.meta_content
				if deploy_component.enable:
					meta_content = meta_content.replace('<status>Inactive</status>', '<status>Active</status>')
				else:
					meta_content = meta_content.replace('<status>Active</status>', '<status>Inactive</status>')
				trigger_meta_file.write(meta_content)
				trigger_meta_file.close()

				zip_file.write('triggers/' + deploy_component.trigger.name + '.trigger-meta.xml')

			# Create package.xml
			package_xml = open('package.xml','w+')
			package_xml.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			package_xml.write('<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n')
			package_xml.write('    <types>\n        <members>*</members>\n        <name>ApexTrigger</name>\n    </types>\n')
			package_xml.write('    <version>' + str(settings.SALESFORCE_API_VERSION) + '.0</version>\n')
			package_xml.write('</Package>')
			package_xml.close()

			zip_file.write('package.xml')
			zip_file.close()

			# Open and encode zip file
			zip_file = open('deploy.zip', 'rb')
			zip_file_encoded = b64encode(zip_file.read())

			# set deploy options
			deploy_options = metadata_client.factory.create('DeployOptions')
			deploy_options.allowMissingFiles = True
			deploy_options.autoUpdatePackage = True
			deploy_options.checkOnly = False 
			deploy_options.ignoreWarnings = True
			deploy_options.performRetrieve = False
			deploy_options.purgeOnDelete = False
			deploy_options.rollbackOnError = True
			#deploy_options.runAllTests = False
			# Set the tests to run if production or sandbox
			deploy_options.testLevel = 'NoTestRun' if deploy_job.job.is_sandbox else 'RunLocalTests'
			deploy_options.runTests = None
			deploy_options.singlePackage = True

			# Start the async retrieve job
			deployment_job = metadata_client.service.deploy(zip_file_encoded, deploy_options)

			# Set the retrieve result - should be unfinished initially
			deployment_job_result = metadata_client.service.checkDeployStatus(deployment_job.id, True)

			# Continue to query retrieve result until it's done
			while not deployment_job_result.done:

				# check job status
				deployment_job_result = metadata_client.service.checkDeployStatus(deployment_job.id, True)

				# sleep job for 3 seconds
				time.sleep(1)

			deploy_job.deploy_result = deployment_job_result

			if not deployment_job_result.success:

				deploy_job.status = 'Error'

				all_errors = ''

				if deployment_job_result.numberComponentErrors > 0:

					# Component errors
					all_errors = 'Component Errors:\n'

					for error in deployment_job_result.details.componentFailures:

						all_errors += ' - ' + error.problem + '\n'

				# Any test errors
				if deployment_job_result.numberTestErrors > 0:

					all_errors += '\nTest Errors:\n'

					for error in deployment_job_result.details.runTestResult.failures:

						all_errors += ' - ' + error.name + '.' + error.methodName + ': ' + error.message + '\n'

				deploy_job.error = all_errors

			else:

				deploy_job.status = 'Finished'

			# Remove files
			remove_triggers()
			os.remove('package.xml')
			os.remove('deploy.zip')

	except Exception as error:

		deploy_job.status = 'Error'
		deploy_job.error = error

	deploy_job.save()
	

def remove_triggers():
    """
    Remove the trigger files and folders if exists
    """ 
    # Remove files
    for f in glob.glob('triggers/*'):
        os.remove(f)
    if os.path.exists('triggers'):
        os.rmdir('triggers')
        