from scrapy.utils.reqser import request_to_dict, request_from_dict

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Base(object):

    def __init__(self, server, spider, key, exchange=None):

        self.server = server
        self.spider = spider
        self.key = key

    def _encode_request(self, request):
        return pickle.dumps(request_to_dict(request, self.spider), protocol=-1)

    def _decode_request(self, encoded_request):
        return request_from_dict(pickle.loads(encoded_request), self.spider)

    def __len__(self):
        raise NotImplementedError

    def push(self, request):
        raise NotImplementedError

    def pop(self, timeout=0):
        raise NotImplementedError

    def clear(self):
        self.server.queue_purge(self.key)


class SpiderQueue(Base):

    def __len__(self):
        response = self.server.queue_declare(self.key, passive=True)
        return response.method.message_count

    def push(self, request):
        self.server.basic_publish(
            exchange='',
            routing_key=self.key,
            body=self._encode_request(request)
        )

    def pop(self):
        method_frame, header, body = self.server.basic_get(queue=self.key)

        if body:
            ack_signal = method_frame.delivery_tag
            request = self._decode_request(body)
            request.meta['ack_signal'] = ack_signal
            return request

    def acknowledge(self, ack_signal):
        self.server.basic_ack(delivery_tag=ack_signal)


__all__ = ['SpiderQueue']
