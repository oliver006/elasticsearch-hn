#!/bin/sh

curl -XDELETE "http://localhost:9200/*"

curl -XPUT "http://localhost:9200/hn/" -d '{
    "settings" : {
        "index" : {
            "number_of_shards" :   2,
            "number_of_replicas" : 0
        }
    },
    "mappings" : {
        "story" : {
            "_source" : { "enabled" : true },
            "properties" : {
                "time" :   { "type" : "date" },
                "domain":  { "type" : "string", "index" : "not_analyzed" },
                "by":      { "type" : "string", "index" : "not_analyzed" }
            }
        },
        "job" : {
            "_source" : { "enabled" : true },
            "properties" : {
                "time" :   { "type" : "date" },
                "domain":  { "type" : "string", "index" : "not_analyzed" },
                "by":      { "type" : "string", "index" : "not_analyzed" }
            }
        },
        "poll" : {
            "_source" : { "enabled" : true },
            "properties" : {
                "time" :   { "type" : "date" },
                "domain":  { "type" : "string", "index" : "not_analyzed" },
                "by":      { "type" : "string", "index" : "not_analyzed" }
            }
        }
    }
}'
echo ""

