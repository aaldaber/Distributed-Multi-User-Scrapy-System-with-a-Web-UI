import connection
import queue
from scrapy.utils.misc import load_object
from scrapy.utils.job import job_dir

SCHEDULER_PERSIST = False
QUEUE_CLASS = 'queue.SpiderQueue'
IDLE_BEFORE_CLOSE = 0


class Scheduler(object):

    def __init__(self, server, persist,
                 queue_key, queue_cls, idle_before_close,
                 stats, *args, **kwargs):
        self.server = server
        self.persist = persist
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.idle_before_close = idle_before_close
        self.stats = stats

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.spider.islinkgenerator:
            settings = crawler.settings
            persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
            queue_key = "%s:requests" % crawler.spider.name
            queue_cls = queue.SpiderQueue
            idle_before_close = settings.get('SCHEDULER_IDLE_BEFORE_CLOSE', IDLE_BEFORE_CLOSE)
            server = connection.from_settings(settings, crawler.spider.name)
            stats = crawler.stats
            return cls(server, persist, queue_key, queue_cls, idle_before_close, stats)
        else:
            settings = crawler.settings
            dupefilter_cls = load_object(settings['DUPEFILTER_CLASS'])
            dupefilter = dupefilter_cls.from_settings(settings)
            pqclass = load_object(settings['SCHEDULER_PRIORITY_QUEUE'])
            dqclass = load_object(settings['SCHEDULER_DISK_QUEUE'])
            mqclass = load_object(settings['SCHEDULER_MEMORY_QUEUE'])
            logunser = settings.getbool('LOG_UNSERIALIZABLE_REQUESTS', settings.getbool('SCHEDULER_DEBUG'))
            core_scheduler = load_object('scrapy.core.scheduler.Scheduler')
            return core_scheduler(dupefilter, jobdir=job_dir(settings), logunser=logunser,
                   stats=crawler.stats, pqclass=pqclass, dqclass=dqclass, mqclass=mqclass)

    def open(self, spider):
        self.spider = spider
        self.queue = self.queue_cls(self.server, spider, self.queue_key)

        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.queue.clear()
        connection.close(self.server)

    def enqueue_request(self, request):
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/rabbitmq', spider=self.spider)
        self.queue.push(request)

    def next_request(self):
        request = self.queue.pop()
        if request and self.stats:
            self.stats.inc_value('scheduler/dequeued/rabbitmq', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0
