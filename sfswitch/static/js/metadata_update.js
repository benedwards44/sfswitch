$.SyntaxHighlighter.init();

$(document).ready(function() 
{
	// init on/off switch
	$('input[type=checkbox]').bootstrapSwitch();

	// Show metadata properties on click
	$('td.component').click(function() 
	{
		if ( $(this).hasClass('trigger_click') )
		{
			$('#viewMetadataLabel').text($(this).find('textarea').attr('id'));
			var $content = $('<pre class="highlight">' + $(this).find('textarea.content').val() + '</pre><br/>' + 
							'<pre class="highlight">' + $(this).find('textarea.meta_content').val()
										.replace(/</g, '&lt;')
										.replace(/>/g,'&gt;')
										.replace(/\n/g, '<br/>') + '</pre>');
			$content.syntaxHighlight();
			$('#viewMetadataBody').html($content);
			$.SyntaxHighlighter.init();
			$('#viewMetadataModal .modal-dialog').width('90%');
		}
		else
		{
			$('#viewMetadataLabel').text($(this).find('div').attr('id'));
			$('#viewMetadataBody').html($(this).find('div').html());
			$('#viewMetadataModal .modal-dialog').width('800px');
		}
		
		$('#viewMetadataModal').modal();
	});

	// Enable all button
	$('.enable').click(function ()
	{
		$(this).closest('table').find('input[type=checkbox]').bootstrapSwitch('state', true);
	});

	// Disable all button
	$('.disable').click(function ()
	{
		$(this).closest('table').find('input[type=checkbox]').bootstrapSwitch('state', false);
	});

	// Deploy changes
	$('.submit').click(function ()
	{
		var metadata_type = $(this).attr('id').split('__')[1];
		var componentIds = [];

		$(this).parent().parent().find('td.' + metadata_type).each(function ()
		{
			var new_value = $(this).find('.new_value').bootstrapSwitch('state');
			var old_value = $(this).find('.old_value').val() == 'True' || $(this).find('.old_value').val() == 'true';

			if (new_value != old_value)
			{
				// Push to component update array
				var component = {
					component_id: $(this).attr('id'),
					enable: new_value
				};
				componentIds.push(component);

				// Set new old_value
				$(this).find('.old_value').val($(this).find('.new_value').bootstrapSwitch('state'));
			}

		});

		update_metadata(componentIds, metadata_type);

	});

	// Rollback changes
	$('.rollback').click(function ()
	{

		var rollbackAll = confirm('This will rollback all metadata for this metadata type to it\'s original state from when the metadata was first queried.');

		if (rollbackAll)
		{

			var metadata_type = $(this).attr('id').split('__')[1];
			var componentIds = [];

			$(this).parent().parent().find('td.' + metadata_type).each(function ()
			{
				var new_value = $(this).find('.new_value').bootstrapSwitch('state');
				var orig_value = $(this).find('.orig_value').val() == 'True' || $(this).find('.orig_value').val() == 'true';

				if (new_value != orig_value)
				{
					// Push to component update array
					var component = {
						component_id: $(this).attr('id'),
						enable: orig_value
					};
					componentIds.push(component);

					// Set old and new value back to original state
					$(this).find('.old_value').val(orig_value);
					$(this).find('.new_value').val(orig_value);
					$(this).find('.new_value').bootstrapSwitch('state', orig_value);
				}

			});

			update_metadata(componentIds, metadata_type);
		}

	});

});

function updateModal(header, body, allow_close)
{
	if (allow_close)
	{
		$('#progressModal .modal-header').html('<button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button><h4 class="modal-title">' + header + '</h4>');
		$('#progressModal .modal-footer').html('<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>');
	}
	else
	{
		$('#progressModal .modal-header').html('<h4 class="modal-title">' + header + '</h4>');
		$('#progressModal .modal-footer').html('');
	}

	$('#progressModal .modal-body').html(body);
}

function check_status(job_id)
{
	var refreshIntervalId = window.setInterval(function () 
	{
   		$.ajax({
		    url: '/check_deploy_status/' + job_id + '/',
		    type: 'get',
		    dataType: 'json',
		    success: function(resp) 
		    {
		        if (resp.status == 'Finished')
		        {
					updateModal('Complete',
								'<div class="alert alert-success" role="alert">All changes have been successfully deployed.</div>',
								true);
					clearInterval(refreshIntervalId);
		        } 
		        else if (resp.status == 'Error')
		        {
					updateModal('Error',
								'<div class="alert alert-danger" role="alert">There was an error deploying your components: ' + resp.error + '</div>',
								true);
					clearInterval(refreshIntervalId);
		        }
		        // Else job is still running, this will re-run shortly.
		    },
		    failure: function(resp) 
		    { 
				updateModal('Error',
					'<div class="alert alert-danger" role="alert">There was an error deploying your components: ' + resp + '</div>',
					true);
				clearInterval(refreshIntervalId);
		    }
		});
	}, 1000);
}