web: gunicorn sfswitch.wsgi --workers $WEB_CONCURRENCY
worker: celery -A enable_disable.tasks worker -B --loglevel=info