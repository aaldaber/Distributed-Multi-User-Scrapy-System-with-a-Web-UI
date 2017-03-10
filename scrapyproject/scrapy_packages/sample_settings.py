#rabbitmq and mongodb settings
SCHEDULER = ".rabbitmq.scheduler.Scheduler"
SCHEDULER_PERSIST = True
RABBITMQ_HOST = 'ip address'
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = 'guest'
RABBITMQ_PASSWORD = 'guest'

MONGODB_PUBLIC_ADDRESS = 'ip:port'  # This will be shown on the web interface, but won't be used for connecting to DB
MONGODB_URI = 'ip:port'  # Actual uri to connect to DB
MONGODB_USER = ''
MONGODB_PASSWORD = ''
MONGODB_SHARDED = False
MONGODB_BUFFER_DATA = 100

LINK_GENERATOR = 'http://192.168.0.209:6800'  # Set your link generator worker address here
SCRAPERS = ['http://192.168.0.210:6800',
            'http://192.168.0.211:6800', 'http://192.168.0.212:6800']  # Set your scraper worker addresses here
