# coding:utf-8

import datetime

from pymongo import errors
from pymongo.mongo_client import MongoClient
from pymongo.mongo_replica_set_client import MongoReplicaSetClient
from pymongo.read_preferences import ReadPreference
from scrapy.exporters import BaseItemExporter
try:
    from urllib.parse import quote
except:
    from urllib import quote

def not_set(string):
    """ Check if a string is None or ''

    :returns: bool - True if the string is empty
    """
    if string is None:
        return True
    elif string == '':
        return True
    return False


class MongoDBPipeline(BaseItemExporter):
    """ MongoDB pipeline class """
    # Default options
    config = {
        'uri': 'mongodb://localhost:27017',
        'fsync': False,
        'write_concern': 0,
        'database': 'scrapy-mongodb',
        'collection': 'items',
        'replica_set': None,
        'buffer': None,
        'append_timestamp': False,
        'sharded': False
    }

    # Needed for sending acknowledgement signals to RabbitMQ for all persisted items
    queue = None
    acked_signals = []

    # Item buffer
    item_buffer = dict()

    def load_spider(self, spider):
        self.crawler = spider.crawler
        self.settings = spider.settings
        self.queue = self.crawler.engine.slot.scheduler.queue

    def open_spider(self, spider):
        self.load_spider(spider)

        # Configure the connection
        self.configure()

        self.spidername = spider.name
        self.config['uri'] = 'mongodb://' + self.config['username'] + ':' + quote(self.config['password']) + '@' + self.config['uri'] + '/admin'
        self.shardedcolls = []

        if self.config['replica_set'] is not None:
            self.connection = MongoReplicaSetClient(
                self.config['uri'],
                replicaSet=self.config['replica_set'],
                w=self.config['write_concern'],
                fsync=self.config['fsync'],
                read_preference=ReadPreference.PRIMARY_PREFERRED)
        else:
            # Connecting to a stand alone MongoDB
            self.connection = MongoClient(
                self.config['uri'],
                fsync=self.config['fsync'],
                read_preference=ReadPreference.PRIMARY)

        # Set up the collection
        self.database = self.connection[spider.name]

        # Autoshard the DB
        if self.config['sharded']:
            db_statuses = self.connection['config']['databases'].find({})
            partitioned = []
            notpartitioned = []
            for status in db_statuses:
                if status['partitioned']:
                    partitioned.append(status['_id'])
                else:
                    notpartitioned.append(status['_id'])
            if spider.name in notpartitioned or spider.name not in partitioned:
                try:
                    self.connection.admin.command('enableSharding', spider.name)
                except errors.OperationFailure:
                    pass
            else:
                collections = self.connection['config']['collections'].find({})
                for coll in collections:
                    if (spider.name + '.') in coll['_id']:
                        if coll['dropped'] is not True:
                            if coll['_id'].index(spider.name + '.') == 0:
                                self.shardedcolls.append(coll['_id'][coll['_id'].index('.') + 1:])

    def configure(self):
        """ Configure the MongoDB connection """

        # Set all regular options
        options = [
            ('uri', 'MONGODB_URI'),
            ('fsync', 'MONGODB_FSYNC'),
            ('write_concern', 'MONGODB_REPLICA_SET_W'),
            ('database', 'MONGODB_DATABASE'),
            ('collection', 'MONGODB_COLLECTION'),
            ('replica_set', 'MONGODB_REPLICA_SET'),
            ('buffer', 'MONGODB_BUFFER_DATA'),
            ('append_timestamp', 'MONGODB_ADD_TIMESTAMP'),
            ('sharded', 'MONGODB_SHARDED'),
            ('username', 'MONGODB_USER'),
            ('password', 'MONGODB_PASSWORD')
        ]

        for key, setting in options:
            if not not_set(self.settings[setting]):
                self.config[key] = self.settings[setting]

    def process_item(self, item, spider):
        """ Process the item and add it to MongoDB

        :type item: Item object
        :param item: The item to put into MongoDB
        :type spider: BaseSpider object
        :param spider: The spider running the queries
        :returns: Item object
        """
        item_name = item.__class__.__name__

        # If we are working with a sharded DB, the collection will also be sharded
        if self.config['sharded']:
            if item_name not in self.shardedcolls:
                try:
                    self.connection.admin.command('shardCollection', '%s.%s' % (self.spidername, item_name), key={'_id': "hashed"})
                    self.shardedcolls.append(item_name)
                except errors.OperationFailure:
                    self.shardedcolls.append(item_name)

        itemtoinsert = dict(self._get_serialized_fields(item))

        if self.config['buffer']:
            if item_name not in self.item_buffer:
                self.item_buffer[item_name] = []
                self.item_buffer[item_name].append([])
                self.item_buffer[item_name].append(0)

            self.item_buffer[item_name][1] += 1

            if self.config['append_timestamp']:
                itemtoinsert['scrapy-mongodb'] = {'ts': datetime.datetime.utcnow()}

            self.item_buffer[item_name][0].append(itemtoinsert)

            if self.item_buffer[item_name][1] == self.config['buffer']:
                self.item_buffer[item_name][1] = 0
                self.insert_item(self.item_buffer[item_name][0], spider, item_name)

            return item

        self.insert_item(itemtoinsert, spider, item_name)
        return item

    def close_spider(self, spider):
        """ Method called when the spider is closed

        :type spider: BaseSpider object
        :param spider: The spider running the queries
        :returns: None
        """
        for key in self.item_buffer:
            if self.item_buffer[key][0]:
                self.insert_item(self.item_buffer[key][0], spider, key)

    def insert_item(self, item, spider, item_name):
        """ Process the item and add it to MongoDB

        :type item: (Item object) or [(Item object)]
        :param item: The item(s) to put into MongoDB
        :type spider: BaseSpider object
        :param spider: The spider running the queries
        :returns: Item object
        """
        self.collection = self.database[item_name]

        if not isinstance(item, list):

            if self.config['append_timestamp']:
                item['scrapy-mongodb'] = {'ts': datetime.datetime.utcnow()}

            ack_signal = item['ack_signal']
            item.pop('ack_signal', None)
            self.collection.insert(item, continue_on_error=True)
            if ack_signal not in self.acked_signals:
                self.queue.acknowledge(ack_signal)
                self.acked_signals.append(ack_signal)
        else:
            signals = []
            for eachitem in item:
                signals.append(eachitem['ack_signal'])
                eachitem.pop('ack_signal', None)
            self.collection.insert(item, continue_on_error=True)
            del item[:]
            for ack_signal in signals:
                if ack_signal not in self.acked_signals:
                    self.queue.acknowledge(ack_signal)
                    self.acked_signals.append(ack_signal)
