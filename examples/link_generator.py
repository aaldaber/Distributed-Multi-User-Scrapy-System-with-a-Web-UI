# This script is written under the username admin, with project name Retrofm
# Change the class name AdminRetrofmSpider accordingly
import datetime

_start_date = datetime.date(2012, 12, 25)
_initial_date = datetime.date(2012, 12, 25)
_priority = 0
start_urls = ['http://retrofm.ru']


def parse(self, response):
    while AdminRetrofmSpider._start_date < self.datetime.date.today():
        AdminRetrofmSpider._priority -= 1
        AdminRetrofmSpider._start_date += self.datetime.timedelta(days=1)
        theurlstart = 'http://retrofm.ru/index.php?go=Playlist&date=%s' % (
        AdminRetrofmSpider._start_date.strftime("%d.%m.%Y"))
        theurls = []
        theurls.append(theurlstart + '&time_start=17%3A00&time_stop=23%3A59')
        theurls.append(theurlstart + '&time_start=11%3A00&time_stop=17%3A01')
        theurls.append(theurlstart + '&time_start=05%3A00&time_stop=11%3A01')
        theurls.append(theurlstart + '&time_start=00%3A00&time_stop=05%3A01')

        for theurl in theurls:
            request = Request(theurl, method="GET",
                              dont_filter=True, priority=(AdminRetrofmSpider._priority), callback=self.parse)
            self.insert_link(request)