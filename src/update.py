from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import IOLoop
import tornado.gen
import tornado.options
import json
import sys
try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse


STORIES_ONLY = True

http_client = AsyncHTTPClient()

@tornado.gen.coroutine
def download_and_index_item(item_id):
    
    url = "https://hacker-news.firebaseio.com/v0/item/%s.json?print=pretty" % item_id
    h = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36"}
    response = yield http_client.fetch(url, headers=h)
    item = json.loads(response.body.decode('utf_8'))

    # not needed
    if 'kids' in item:
        item.pop('kids')

    if STORIES_ONLY and item['type'] != 'story':
        print("\nskiped item %s" % item['id'])
        return

    if not 'url' in item or not item['url']:
        item['url'] = "http://news.ycombinator.com/item?id=%s" % item['id']
        item['domain'] = "news.ycombinator.com"
    else:
        u = urlparse(item['url'])
        item['domain'] = u.hostname.replace("www.", "") if u.hostname else ""

    # ES uses milliseconds        
    item['time'] = int(item['time']) * 1000

    es_url = "http://localhost:9200/hn/%s/%s" % (item['type'], item['id'])
    request = HTTPRequest(es_url, method="PUT", body=json.dumps(item), request_timeout=10)
    response = yield http_client.fetch(request)
    if not response.code in [200, 201]:
        print("\nfailed to add item %s" % item['id'])
    else:
        sys.stdout.write('.')
        sys.stdout.flush()

@tornado.gen.coroutine
def download_topstories():
    response = yield http_client.fetch('https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty')
    top100_ids = json.loads(response.body.decode('utf_8'))
    print("Got Top 100")

    for item_id in top100_ids:
        yield download_and_index_item(item_id)

    print("Done")


if __name__ == '__main__':
    print("Starting")
    IOLoop.instance().run_sync(download_topstories)