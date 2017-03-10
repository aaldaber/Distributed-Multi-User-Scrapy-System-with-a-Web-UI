# -*- coding: utf-8 -*-

try:
    import pika
except ImportError:
    raise ImportError("Please install pika before running scrapy-rabbitmq.")


RABBITMQ_CONNECTION_TYPE = 'blocking'
RABBITMQ_CONNECTION_PARAMETERS = {'host': 'localhost'}


def from_settings(settings, spider_name):

    connection_type = settings.get('RABBITMQ_CONNECTION_TYPE',
                                   RABBITMQ_CONNECTION_TYPE)
    queue_name = "%s:requests" % spider_name
    connection_host = settings.get('RABBITMQ_HOST')
    connection_port = settings.get('RABBITMQ_PORT')
    connection_username = settings.get('RABBITMQ_USERNAME')
    connection_pass = settings.get('RABBITMQ_PASSWORD')

    connection_attempts = 5
    retry_delay = 3

    credentials = pika.PlainCredentials(connection_username, connection_pass)

    connection = {
        'blocking': pika.BlockingConnection,
        'libev': pika.LibevConnection,
        'select': pika.SelectConnection,
        'tornado': pika.TornadoConnection,
        'twisted': pika.TwistedConnection
    }[connection_type](pika.ConnectionParameters(host=connection_host,
                       port=connection_port, virtual_host='/',
                       credentials=credentials,
                       connection_attempts=connection_attempts,
                       retry_delay=retry_delay))

    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    return channel


def close(channel):
    channel.close()
