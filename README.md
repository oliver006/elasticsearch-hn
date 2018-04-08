Elasticsearch For Beginners: Index and Search Hacker News 
================


#### Big picture plz? 

Hacker News officially released their [API](http://blog.ycombinator.com/hacker-news-api) this October, giving access to a vast amount of news articles, comments, polls, job postings, etc and via JSON, perfect to put it into Elasticsearch.

[Elasticsearch](http://elasticsearch.org) is currently the most popular Open-Source search engine, used for a wide variety of use cases. It natively works with JSON documents so this sounds like a perfect fit.

It runs on a [DigitalOcean 512MB droplet](https://m.do.co/c/c9b25dec9715) droplet and hosts the Elasticsearch node and a simple Tornado app for the frontend. Crontab runs the update every 5 minutes.


#### Prerequisites

Set up Elasticsearch and make sure it's running at [http://localhost:9200](http://localhost:9200)

See [here](https://www.elastic.co/guide/en/elasticsearch/guide/current/running-elasticsearch.html) if you need more information on how to install Elasticsearch.

I use Python and [Tornado](https://github.com/tornadoweb/tornado/) for the scripts to import and query the data.



#### Aight, so what are we doing? 

We'll start with loading the Top 100 HN stories IDs, retrieve detailed information about each item and then index them in Elasticsearch.


Top 100 Stories:

`curl https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty`

the result looking something like this:

```
[ 8605204, 8604814, 8602936, 8604489, 8604533, 8604626, 8605207, 8605186, 
...
8603147, 8602037 ]
```

We can now loop through the IDs and retrieve more detailed information:

`curl https://hacker-news.firebaseio.com/v0/item/8605204.json?print=pretty`

yields this:

```
{
  "by" : "davecheney",
  "id" : 8605204,
  "kids" : [ 8605567, 8605461, 8605280, 8605824, 8605404, 8605601, 8605246, 8605323, 8605712, 8605346, 8605743, 8605242, 8605321, 8605268 ],
  "score" : 260,
  "text" : "",
  "time" : 1415926359,
  "title" : "Go is moving to GitHub",
  "type" : "story",
  "url" : "https://groups.google.com/forum/#!topic/golang-dev/sckirqOWepg"
}
```

And store the JSON document in Elasticsearch:

`curl -XPUT http://localhost:9200/hn/story/***item['id']*** -d @doc.json`

where `***item['id']***` is the ID of the document we just retrieved and `@doc.json` is the body of the document we just downloaded.


#### Got it, show me some real code!

Check out the full Python code here: [src/update.py](src/update.py)

This is the loop over the top 100 IDs:

```
    response = yield http_client.fetch('https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty')
    top100_ids = json.loads(response.body)
    
    for item_id in top100_ids:
        yield download_and_index_item(item_id)

    print "Done"

```

and this (shortened) piece downloads the individual items:

```
def download_and_index_item(item_id):
    
    url = "https://hacker-news.firebaseio.com/v0/item/%s.json?print=pretty" % item_id
    response = yield http_client.fetch(url)
    item = json.loads(response.body)

	# all sorts of clean-up of "item"

    es_url = "http://localhost:9200/hn/%s/%s" % (item['type'], item['id'])
    request = HTTPRequest(es_url, method="PUT", body=json.dumps(item), request_timeout=10)
    response = yield http_client.fetch(request)
    if not response.code in [200, 201]:
        print "\nfailed to add item %s" % item['id']
    else:
        sys.stdout.write('.')
```


#### Ok, but where's the data?

Once we have a batch of HN articles in ES we can run queries

`curl "http://localhost:9200/hn/story/_search?pretty"`

gives us all the stories (the first 10 really as ES defaults to 10 results by default).

All stories for a given user:

`curl "http://localhost:9200/hn/story/_search?q=by:davecheney&pretty"`

We can also run aggregations and for see who posted the most stories and what the most popular domains are:

```
curl -XGET 'http://localhost:9200/hn/story/_search?search_type=count' -d '
{ "aggs" : { "domains" : { "terms" : { "field" : "domain", "size": 11 } }, "by" : {  "terms" : { "field" : "by", "size": 5 } } } }'
```

returning something like this:

```
{ "aggregations": {
    "by": {
      "buckets": [
        { "doc_count": 5,
          "key": "luu" "},
        { "doc_count": 3,
          "key": "benbreen" },
        { "doc_count": 3,
          "key": "dnetesn" "},
        ...
      ]
    },
    "domains": {
      "buckets": [
        { "doc_count": 6,
          "key": "github.com" },
        { "doc_count": 4,
          "key": "medium.com" },
        ...
      ]
    }
  }
}
```



#### What can we do better? 

##### Field Mappings

Elasticsearch is doing a pretty good job at figuring out what type a field is but sometimes it can use a little help.
Run this query to see how ES maps each field of the `story` type:

`curl -XGET 'http://localhost:9200/hn/_mapping/story'`

Looks all pretty straight forward but one mapping sticks out:

```
    "time": {
        "type": "long"
    },
```

The type `long` is ok but what we really want is the type `date` so we can take advantage of the built-in date operators and aggregations. <br>
Let's set up a index mapping for `time`:

```
curl -XPUT "http://localhost:9200/hn/" -d '{
    "mappings" : {
        "story" : {
            "properties" : {
                "time" :   { "type" : "date" }
            }
        }
    }
}'
```
That should do the trick so now we can run a query to see how many stories are being posted to the HN Top 100 per week:

```
curl -XGET 'http://localhost:9200/hn/story/_search?search_type=count' -d '
{
    "aggs" : {
        "articles_over_time" : {
            "date_histogram" : {
                "field" : "time",
                "interval" : "1w"
            }
        }
    }
}
'
```
Result:

```
{ "aggregations": {
    "articles_over_time": {
      "buckets": [
        { "doc_count": 1609,
          "key": 1413158400000,
          "key_as_string": "2014-10-13T00:00:00.000Z"
        },
        { "doc_count": 1195,
          "key": 1413763200000,
          "key_as_string": "2014-10-20T00:00:00.000Z"
        },
        { "doc_count": 1236,
          "key": 1414368000000,
          "key_as_string": "2014-10-27T00:00:00.000Z"
        },
        { "doc_count": 1304,
          "key": 1414972800000,
          "key_as_string": "2014-11-03T00:00:00.000Z"
        }
  ] } },
}
```

 

##### Other possible future improvements

- use bulk API
- more interesting queries
- simple web interface to query ES


#### feedback

Open pull requests, issues or email me at o@21zoo.com








