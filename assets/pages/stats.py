"""Script that generates the browsing history Visual."""

import pandas as pd
import tldextract
import sqlite3
from os.path import expanduser
import shutil
import webbrowser
import glob
import json

# option = 0
# while not int(option) in range(1, 3):
#     option = int(input("Select your broswer:\n1.Chrome\n2.Firefox\n"))

# Chrome
# On Mac: ~/Library/Application\ Support/Google/Chrome/Default/History
# On Windows: C:\Users\YOUR USER NAME\AppData\Local\Google\Chrome\User Data\Default\History
# On Linux: ~/.config/google-chrome/Default/History
home = expanduser("~")
# path = {1: home + "/.config/google-chrome/Default/History",
#         2: glob.glob(home + '/.mozilla/firefox/*/places.sqlite')[0]}
path = glob.glob(home + '/.mozilla/firefox/*/places.sqlite')[0]
shutil.copy2(path, "assets/pages/history.sqlite3")

# query = {
#     1:
#     "select datetime(last_visit_time/1000000-11644473600,'unixepoch') as 'date',url from  urls order by last_visit_time desc",
#     2:
#     "select datetime(last_visit_date/1000000-11644473600,'unixepoch') as 'date',url from  moz_places order by last_visit_date desc"
# }

query = "select datetime(last_visit_date/1000000-11644473600,'unixepoch') as 'date',url from  moz_places order by last_visit_date desc"

# Read sqlite query results into a pandas DataFrame
con = sqlite3.connect("assets/pages/history.sqlite3", timeout=5)
df = pd.read_sql_query(query, con)
con.close()

########################################################################################################
#Below snippet is taken from https://github.com/Dineshkarthik/browsing_history_viz

########################################################################################################
def _tld(dns):
    ext = tldextract.extract(dns)
    return ext.domain


def _suffix(dns):
    ext = tldextract.extract(dns)
    return ext.suffix


df["domain"] = df["url"].apply(_tld)
df["suffix"] = df["url"].apply(_suffix)

s = df.domain.value_counts()
s = s.nlargest(15)
r = df["suffix"].value_counts()
r = r.nlargest(15)

_dict = {}
_dict["domain"] = s.to_dict()
_dict["suffix"] = r.to_dict()

json_ = json.dumps(_dict)
with open('assets/pages/data.json', 'w') as savetxt:
    savetxt.write(json_)
f = open('assets/pages/stats.html', 'w')
message = """<!DOCTYPE html>

<html>
<head>
    <meta charset="utf-8">

    <title>Browsing History</title>
    <style>
    body{font-size: 15px; font-family: Myriad Pro; font-style: none;}.axis path, .axis line{fill: none; stroke: #A0A0A0; shape-rendering: crispEdges;}.line{fill: none; stroke-width: 1px;}.line{stroke: #4682B8;}.grid{stroke: #E6E6E6;}.y.axis path{display: none;}.axis text{font-size: 6px;}.label text, .chart-text{font-size: 8px;}.legend text, .axis{font-size: 14px;}.front-bar{fill: #00CDF2;}.back-bar{fill: #EBEBEB;}
    </style>
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" rel="stylesheet">
</head>

<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-sm-6" id="domain">
                <h1> Top 15 most visited domains</h1>
            </div>
            <div class="col-sm-6" id="suffix">
                <h1>Top 15 most visited suffixes</h1>
            </div>
         </div>

    </div>
    <script src="http://d3js.org/d3.v3.js">
    </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3-tip/0.6.7/d3-tip.js">
    </script>
    <script>
    d3.json("data.json",function(t,e){function n(t,e,n){var s=d3.select("#"+e).append("svg").attr("preserveAspectRatio","xMinYMin meet").attr("viewBox","0 0 "+a+" "+r).classed("svg-content",!0).append("g").attr("class","container-g"),f=s.append("g").attr("class","chartContainer").attr("transform","translate("+a/3+","+r/2+")").call(l),v=f.selectAll(".arc").data(c(t)).enter().append("g").attr("class","arc");v.append("path").attr("d",d).style("fill",function(t){return i(t.data.key)}).on("mouseover",function(t){l.show(t.data),d3.select(this).transition().duration(100).attr("d",u)}).on("mousemove",function(){return l.style("top",d3.event.pageY+16+"px").style("left",d3.event.pageX+16+"px")}).on("mouseout",function(t){l.hide(t),d3.select(this).transition().ease("elastic").duration(1e3).attr("d",d)}),v.append("text").attr("class","chart-text").transition().duration(500).attr("transform",function(t){return"translate("+o.centroid(t)+")"}).text(function(t){return p(t.value/n)}).style("font-size","14px");var g=s.append("g").attr("class","legendContainer").selectAll(".legend").data(t.slice(0,20));g.enter().append("g").attr("class","legend").attr("transform",function(t,e){return"translate("+.7*a+","+(25*e-1e-4*r)+")"}),g.append("rect").attr("x",0).attr("width",10).attr("height",10).style("fill",function(t,e){return i(e)}),g.append("text").attr("x",20).attr("y",5).attr("dy",".35em").text(function(t){return t.key}).style("font-size","18px")}var a=960,r=600,s=Math.min(a,r)/2,s=.2*a,i=d3.scale.category20(),d=(d3.scale.category20(),d3.svg.arc().outerRadius(s).innerRadius(0)),o=d3.svg.arc().outerRadius(1.2*s).innerRadius(1.2*s),u=d3.svg.arc().outerRadius(1.05*s).innerRadius(0),l=d3.tip().attr("class","d3-tip").offset([-10,0]).style("font-size","12px").html(function(t){return t.key+" - "+t.value}),c=d3.layout.pie().sort(null).value(function(t){return+t.value}),p=d3.format("1%"),f=d3.entries(e.domain),v=d3.sum(f,function(t){return parseInt(t.value)});f.sort(function(t,e){return d3.descending(t.value,e.value)});var g=d3.entries(e.suffix),m=d3.sum(g,function(t){return parseInt(t.value)});g.sort(function(t,e){return d3.descending(t.value,e.value)}),n(f,"domain",v),n(g,"suffix",m)});
    </script>
</body>
</html>"""
f.write(message)
f.close()

###################################################################################################################
