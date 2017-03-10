# You need to create an Item name 'played' for running this script
# item['ack_signal'] = int(response.meta['ack_signal']) - this line is used for sending ack signal to RabbitMQ
def parse(self, response):
    item = played()
    songs = response.xpath('//li[@class="player-in-playlist-holder"]')
    indexr = response.url.find('date=')
    indexr = indexr + 5
    date = response.url[indexr:indexr + 10]

    for song in songs:
        item['timeplayed'] = song.xpath('.//span[@class="time"]/text()').extract()[0]
        item['artist'] = song.xpath('.//div[@class="jp-title"]/strong//span//text()').extract()[0]
        item['song'] = song.xpath('.//div[@class="jp-title"]/strong//em//text()').extract()[0]
        item['dateplayed'] = date
        item['ack_signal'] = int(response.meta['ack_signal'])
        yield item