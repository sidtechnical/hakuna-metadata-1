import shutil, sqlite3, glob, re, json, unicodedata, string, dateutil, webbrowser, requests

from os.path import expanduser

import pandas as pd
from pandas.tseries.resample import TimeGrouper 

from urlparse import urlparse, parse_qs
from collections import defaultdict

import nltk
from nltk.tokenize import word_tokenize  
from nltk import FreqDist
from nltk.corpus import stopwords
from nltk.tag.stanford import StanfordNERTagger
from nltk.internals import find_jars_within_path

from bs4 import BeautifulSoup

from plotly.offline.offline import *
from plotly.graph_objs import *

from wordcloud import WordCloud

from nltk.internals import find_jars_within_path
# parser = StanfordParser(model_path="path/to/englishPCFG.ser.gz")
##################### ENV setting #################################################################


os.environ['CLASSPATH'] = "assets/stanford-ner-2016-10-31"
st = StanfordNERTagger('assets/stanford-ner-2016-10-31/classifiers/english.all.3class.distsim.crf.ser.gz')
# st._classpath = tuple(find_jars_within_path('assets/stanford-ner-2015-04-20'))
###################################################################################################


########################### Generic functions begins ##############################################
#Copying the place.sqlite file to local folder to the current local direcotry
def copy_browser_history_database():
	shutil.copy2(glob.glob(expanduser("~") + '/Library/Application Support/Firefox/Profiles/*/places.sqlite')[0] , "browser_history_database.sqlite3")



# Create a dataframe from local copy of browser history database i.e. from the place.sqalite
def create_browser_history_dataframe(browser_history_database):
	query = "select datetime(moz_historyvisits.visit_date/1000000, 'unixepoch', 'localtime') as recent_visit, moz_places.url as url_location, moz_places.title as name, moz_places.visit_count as visit_count, moz_places.frecency as frecency from moz_places, moz_historyvisits where moz_historyvisits.place_id = moz_places.id order by moz_historyvisits.visit_date desc;"
	con = sqlite3.connect(browser_history_database, timeout=5)
	browser_history_dataframe = pd.read_sql_query(query, con)
	con.close()
	return browser_history_dataframe

# Seperate the URLs for further analysis
def seperate_the_dataframes(dataframe,url_string):
	return dataframe[dataframe['url_location'].str.contains(url_string)]

########################### Generic functions ends ################################################


########################### Facebook functions begins ##############################################
#Classifying the (Facebook) urls into photo, event, profile, group, search and messages
def Facebook_URL_Categorizre(URL):
	# print "categorizing Facebook URLs"
	category_tag = ''
	if urlparse(URL).netloc=="www.facebook.com":
		if "photo" in urlparse(URL).path:
			category_tag = "photo"
		elif "search" in urlparse(URL).path and "message" not in urlparse(URL).path and "photo" not in urlparse(URL).path and "group" not in urlparse(URL).path:
				category_tag = "search"
		elif "group" in urlparse(URL).path:
			category_tag = "group"
		elif "message" in urlparse(URL).path:
			category_tag = "message"
		elif "events" in urlparse(URL).path:
			category_tag = "event"
		elif "posts" in urlparse(URL).path:
			category_tag = "posts"
		else:
			category_tag = "profile"
	return category_tag



def cleanup_facebook_dataframe(dataframe):
	#Remove the repeated profile urls
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/"]
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/#"]
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/?_rdr=p"]
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/?_rdr=p#"]
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/?q="]
	dataframe = dataframe[dataframe.url_location != "https://www.facebook.com/?ref=tn_tnmn"]

	repeated_facebook_pages_words = ["people","settings", "dyi?", "react", "help", "support", "utm_source", "preview_cover" , "/?q=#/", "video.php" , "recover" ,"react", "login", "password", "l.php?", "viewas", "insights", "story_id", "sharer.php" ,"about" ,"pages", "?stype=lo", "homepage", "app_data", "ft[qid]" , "safetycheck","l.php?u=https", "location=profile_browser", "?next=", "friends" ,"videos", "?entry_point=", "deactivate", "careers", "saved", "timeline", "page_user_activity", "notif_t=page_fan", "manager", "notifications", "media", "notif", "oauth"]
	facebook_pattern = '|'.join(map(re.escape, repeated_facebook_pages_words))
	dataframe = dataframe[~dataframe.url_location.str.contains(facebook_pattern)]

	return dataframe

def url_cleanup(url):
	parsed_url = urlparse(url)
	qry =  parsed_url.query
	path = parsed_url.path
	if 'profile.php' in path:
		result = re.search('id=(\d+)',qry)
		return 'https://www.facebook.com/'+result.group(1)
	else:
		return "https://www.facebook.com"+parsed_url.path

def name_extractor(URL, Name):
	try:
		if not Name or 'Facebook' in Name:
			return urlparse(URL).path.split("/",1)[1] #Prints 
		else:
			return(''.join(c for c in Name.split(' - ')[0] if c.isalpha() or c in ' .').strip())
	except IndexError:
		print URL, Name 

def create_json_for_circle_packing(Domain, dataframe):
	gp = dataframe.groupby(['visit_count'])
	dict_json = {"name": Domain}
	children = []
	for name, group in gp:
		temp = {"name": name, "children": []}
		rgp = group.groupby(['frecency'])
		for n, g in rgp:
			temp["children"].append({
				"name": n,
				"children": [
					{"name": row["real_name"],
                	"size": row["visit_count"] * 1000 / len(g)}
                	for _, row in g.iterrows()
            	]
        })
		children.append(temp)

	dict_json["children"] = children
	return dict_json


########################### Facebook functions ends ##############################################

########################### Twitter fucntions begin ##############################################

def twitter_url_cleanup(url):
	parsed_url = urlparse(url)
	if not parsed_url.path or parsed_url.path!="/":
		return 'https://www.twitter.com/'+ parsed_url.path.split("/",1)[1].split("/",1)[0]

def twitter_name_extractor(URL, Name):
	try:
		if 'on Twitter' in Name or 'Twitter / Notifications' in Name:
			return URL.split("https://www.twitter.com/",1)[1]
		elif not Name or Name!='Twitter / ?':
			real_name = Name.split("|",1)[0].split("(",1)[0]
			if not real_name or Name =='Twitter / ?':
				# print "It was empty"
				return URL.split("https://www.twitter.com/",1)[1] #real_name
			else:
				return real_name #URL.split("https://www.twitter.com/",1)[1]
	except:
		return URL.split("https://www.twitter.com/",1)[1]

########################### Twitter functions ends ##############################################

########################### Google functions begins ##############################################

def Google_search_query_keywords(URL, Name):
	if not Name:
		parsed_url = urlparse(URL)
		if "google" in parsed_url.netloc  and parsed_url.path=='/search':

			query_dict = parse_qs(parsed_url.query, keep_blank_values=True)

			for k, v in query_dict.iteritems():
				if k=="q":
					return v[0]
			
		else:
			return ""

	else:
		return Name.split("- Google Search",1)[0]

########################### Google functions ends ##############################################





########################### Browsing pattern functions starts ##############################################

def Count_Unique_URLs(URL_List):
	return len(URL_List)

def strip_time(DateValue):
	return DateValue.time()

def strip_date(DateValue):
	return DateValue.date()


########################### Browsing pattern functions ends ##############################################

########################### NER functions starts #########################################################

def netloc_extractor(URL):
	return urlparse(URL).netloc

def remove_SE_SM(dataframe):
	SocMedia_SearchEngines = ["mail", "gmail.com", "drive", "dropbox" ,"soundcloud.com", "spotify.com", "youtube.com","github.com", "stackoverflow.com", "facebook.com","twitter.com","google","amazon", "duckduckgo", "disconnect", "airbnb", "booking", "linkedin"]
	dataframe = dataframe[~dataframe.netloc.str.contains('|'.join(SocMedia_SearchEngines))]
	return dataframe

def grab_website_text(url_list):
	cert = "assets/certs.pem"
	text_blob = ""
	text_list_dummy =[]
	
	for url in url_list:
		
		try:
			result = requests.get(url, verify= cert)
			result.raise_for_status()
			

			html = result.content

			soup = BeautifulSoup(html)

			# remove all script and style elements
			for script in soup(["script", "style"]):
				script.extract()   

			# get text
			try:
				text = soup.body.get_text()
				# break into lines and remove leading and trailing space on each

				lines = (line.strip() for line in text.splitlines())

				# break multi-headlines into a line each
				chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

				# drop blank lines
				text = ' '.join(chunk for chunk in chunks if chunk)
			except AttributeError:
				text = ""
			

			text_list_dummy.append(text)

		except requests.exceptions.RequestException:
			text_list_dummy.append("")

	text_blob = '\n'.join(text_list_dummy)
	return text_blob


def NER_string(NER_list):
    NER_str = ""
    for item in NER_list:
        NER_str +=str(item)
        NER_str += " | "
    return NER_str

def create_stopword_free_text(text_to_process):
	stoplist = stopwords.words('english')
	
	more_sw = "a about above across after again against all almost alone along already also although always am among an and another any anybody anyone anything anywhere are area areas aren't around as ask asked asking asks at away b back backed backing backs be became because become becomes been before began behind being beings below best better between big both but by c came can cannot can't case cases certain certainly clear clearly come could couldn't d did didn't differ different differently do does doesn't doing done don't down downed downing downs during e each early either end ended ending ends enough even evenly ever every everybody everyone everything everywhere f face faces fact facts far felt few find finds first for four from full fully further furthered furthering furthers g gave general generally get gets give given gives go going good goods got great greater greatest group grouped grouping groups h had hadn't has hasn't have haven't having he he'd he'll her here here's hers herself he's high higher highest him himself his how however how's i i'd if i'll i'm important in interest interested interesting interests into is isn't it its it's itself i've j just k keep keeps kind knew know known knows l large largely last later latest least less let lets let's like likely long longer longest m made make making man many may me member members men might more most mostly mr mrs much must mustn't my myself n necessary need needed needing needs never new newer newest next no nobody non noone nor not nothing now nowhere number numbers o of off often old older oldest on once one only open opened opening opens or order ordered ordering orders other others ought our ours ourselves out over own p part parted parting parts per perhaps place places point pointed pointing points possible present presented presenting presents problem problems put puts q quite r rather really right room rooms s said same saw say says second seconds see seem seemed seeming seems sees several shall shan't she she'd she'll she's should shouldn't show showed showing shows side sides since small smaller smallest so some somebody someone something somewhere state states still such sure t take taken than that that's the their theirs them themselves then there therefore there's these they they'd they'll they're they've thing things think thinks this those though thought thoughts three through thus to today together too took toward turn turned turning turns two u under until up upon us use used uses v very w want wanted wanting wants was wasn't way ways we we'd well we'll wells went were we're weren't we've what what's when when's where where's whether which while who whole whom who's whose why why's will with within without won't work worked working works would wouldn't x y year years yes yet you you'd you'll young younger youngest your you're yours yourself yourselves you've z"

	stoplist += more_sw.split()

	# Tokenize the text into words using NLTK library
	scrapped_words = nltk.tokenize.word_tokenize(text_to_process)

	# Remove single-character tokens (mostly punctuation)
	scrapped_words = [word for word in scrapped_words if len(word) > 1]

	# Remove numbers
	scrapped_words = [word for word in scrapped_words if not word.isdigit()]

	# Lowercase all words (default_stopwords are lowercase too)
	scrapped_words = [word.lower() for word in scrapped_words]

	# Remove stopwords
	scrapped_words = [word for word in scrapped_words if word not in stoplist]

	punctuations = list(string.punctuation)
	punctuations.extend(("''", "//", "--","..."))

	#Remove punctuations
	scrapped_words = [word for word in scrapped_words if word not in punctuations]

	return NER_string(scrapped_words)

def create_NER_strings(textblob_text):
	ne_tagged_sent = st.tag(textblob_text.split())
	Organization = []
	Location = []
	Person = []
	for x,y in ne_tagged_sent:
	        if y == 'ORGANIZATION':
	            Organization.append(x)
	        elif y== 'LOCATION':
	          Location.append(x)
	        elif y == 'PERSON':
	          Person.append(x)

	Org_values = NER_string(Organization)
	Per_values = NER_string(Person)
	Loc_values = NER_string(Location)
	return Org_values, Per_values, Loc_values
	

########################### NER functions ends #########################################################



if __name__ == "__main__":
	print "################################################################################################"
	print "Please be patient. This might take a while. \nWhen the tool completes running, it automatically opens a browser tab and displays the visuals."
	print "\nUnless the program stops with errors, ignore the warnings/messages if any."
	print "\nIf you want to interrupt the program execution, please press CTRL+C."
	print "################################################################################################"
	
	#Copy Firefox Browser History database i.e place.sqlite to current folder
	copy_browser_history_database()

	# create the dataframe from local copy of brwoser history database
	browser_history_dataframe = create_browser_history_dataframe("browser_history_database.sqlite3")

	os.system("python assets/pages/stats.py")


	#Seperate Facebook URLs from the browser_history_dataframe 
	facebook_df = seperate_the_dataframes(browser_history_dataframe,"facebook.com")

	#Clean up the facebook dataframe to remove unwanted urls
	facebook_df = cleanup_facebook_dataframe(facebook_df)

	#classify the urls into photo, event, profile, group, search, post and messages; 
	# add a new column "category_tags to the facebook_df  
	facebook_df['category_tags']= facebook_df.apply(lambda row: Facebook_URL_Categorizre(row['url_location']), axis=1)

	#Copy only the "profile" URLs to a new dataframe
	facebook_profile_df = facebook_df.loc[facebook_df['category_tags']=='profile']

	if len(facebook_profile_df) == 0:
		print "\nno facebook profile data found"
	else:
		#Remove duplicates and copy to a new dataframe
		facebook_profile_clean =facebook_profile_df.drop_duplicates(['url_location'])
	
		sorted_facebook_profile_clean = facebook_profile_clean.sort_values(['visit_count', 'frecency'], ascending=[False, False])

		current_user = sorted_facebook_profile_clean ['name'].iloc[0]
		current_user_url =  sorted_facebook_profile_clean ['url_location'].iloc[0]

		facebook_profile_clean_without_current_user = sorted_facebook_profile_clean[~sorted_facebook_profile_clean.url_location.str.contains(current_user_url)]

		pd.options.mode.chained_assignment = None
		facebook_profile_clean_without_current_user['url_location']= facebook_profile_clean_without_current_user.apply(lambda row: url_cleanup(row['url_location']), axis=1)

		pd.options.mode.chained_assignment = None
		facebook_profile_clean_without_current_user['real_name']= facebook_profile_clean_without_current_user.apply(lambda row: name_extractor(row['url_location'], row['name']), axis=1)

		Facebook_Profile_list = facebook_profile_clean_without_current_user.drop_duplicates(['url_location'])

		Facebook_Profile_list_Final = Facebook_Profile_list[['real_name','url_location', 'visit_count','frecency']]

		facebook_json = create_json_for_circle_packing("Facebook", Facebook_Profile_list_Final.nlargest(100, 'visit_count'))
	
		with open('assets/pages/facebook_profiles.json', 'w') as outfile:
			json.dump(facebook_json, outfile)

	######################## End of Facebook related script ###################################################

	######################## Start of Twitter related script ##################################################

	twitter_df= browser_history_dataframe[browser_history_dataframe['url_location'].str.contains("https://twitter.com")]

	twitter_stop_words = ["notifications","following","careers","url", "jobs", "support","status","likes", "settings","moments","help","search","account","widgets","hashtag","intent", "about"]
	twitter_pattern = '|'.join(map(re.escape, twitter_stop_words))
	twitter_df = twitter_df[~twitter_df.url_location.str.contains(twitter_pattern)]

	if len(twitter_df) == 0:
		print "\nno twitter profile data found"
	else:
		twitter_df['url_location']= twitter_df.apply(lambda row: twitter_url_cleanup(row['url_location']), axis=1)
		twitter_df= twitter_df[twitter_df.url_location.notnull()]
		twitter_df2 = twitter_df.drop_duplicates(['url_location'])

		sorted_twitter_df = twitter_df2.sort_values(['visit_count', 'frecency'], ascending=[False, False])

		current_user_twitter = sorted_twitter_df['name'].iloc[0]
		current_user_url_twitter =  sorted_twitter_df['url_location'].iloc[0]
	
		twitter_df_without_current_user = sorted_twitter_df[~sorted_twitter_df.url_location.str.contains(current_user_url_twitter)]

		pd.options.mode.chained_assignment = None
		twitter_df_without_current_user['real_name']= twitter_df_without_current_user.apply(lambda row: twitter_name_extractor(row['url_location'], row['name']), axis=1)
		Twitter_Profile_Final = twitter_df_without_current_user[['real_name','url_location', 'visit_count','frecency']]

		twitter_json = create_json_for_circle_packing("Twitter", Twitter_Profile_Final.nlargest(100, 'visit_count'))

		with open('assets/pages/twitter_profiles.json', 'w') as outfile:
			json.dump(twitter_json, outfile)

	#################### End of Twitter related script ###################################################


	#################### Start of Google related script ##################################################
	google_df= browser_history_dataframe[browser_history_dataframe['url_location'].str.contains("www.google.")]

	google_df = google_df[google_df.url_location != "https://www.google.com/"]

	google_stop_words = ["url","gmail","maps", "intl", "inputtools", "gfe_rd", "landing", "accounts" "textise"]
	google_pattern = '|'.join(map(re.escape, google_stop_words))
	google_df = google_df[~google_df.url_location.str.contains(google_pattern)]


	google_df['search_query']= google_df.apply(lambda row: Google_search_query_keywords(row['url_location'], row['name']), axis=1)

	google_df = google_df[google_df.search_query.notnull()]
	google_df = google_df.drop_duplicates(['search_query'])

	#Preparing the data for graph
	# Convert the column of search queries to a list
	query_list = google_df['search_query'].tolist()

	# Combine all the list elements to a text blob and then encode it
	query_list_text_dump = ' '.join(query_list)

	query_list_text = unicodedata.normalize('NFKD', query_list_text_dump).encode('ascii','ignore')

	# Tokenize the text into words using NLTK library
	stopwords2 = set(nltk.corpus.stopwords.words('english'))

	words = nltk.tokenize.word_tokenize(query_list_text)

	# Remove single-character tokens (mostly punctuation)
	words = [word for word in words if len(word) > 1]

	# Remove numbers
	words = [word for word in words if not word.isdigit()]

	# Lowercase all words (default_stopwords are lowercase too)
	words = [word.lower() for word in words]

	# Remove stopwords
	words = [word for word in words if word not in stopwords2]

	punctuations = list(string.punctuation)
	punctuations.extend(("''", "//", "--","..."))

	#Remove punctuations
	words = [word for word in words if word not in punctuations]

	#Word frequency count using NLTk module
	query_frequency_dist = nltk.FreqDist(words)

	# Create a dictionary to plot a graph 
	query_freq_df_unsorted = pd.DataFrame.from_dict(query_frequency_dist, orient='index').reset_index()
	query_freq_df_unsorted = query_freq_df_unsorted.rename(columns={'index':'query_word', 0:'count'})

	# Sort the dictionary of query word frequency counts
	query_freq_df = query_freq_df_unsorted.sort_values(['count'], ascending=[False])

	query_freq_df_top = query_freq_df.nlargest(50, 'count')

	data = [Bar(x= query_freq_df_top['query_word'].tolist(), y= query_freq_df_top['count'].tolist())]
	# plotly.offline.plot(data, output_type='div', filename='/word_plot.html')
	plotly.offline.plot(data, auto_open=False, filename='assets/pages/word_plot.html') 

	#################### End of Google related script ###################################################


	#################### Start of Browsing pattern related script #######################################


	# Seperating only required columns from the original df
	pd.options.mode.chained_assignment = None
	browshistory_required_cols_df = browser_history_dataframe[['recent_visit','url_location', 'visit_count']]  

	browshistory_required_cols_df['recent_visit'] = pd.to_datetime(browshistory_required_cols_df['recent_visit'])

	Unique_URLs_df = browshistory_required_cols_df.set_index('recent_visit').url_location.resample('H').agg({'Unique_URLs': 'unique'})

	pd.options.mode.chained_assignment = None
	Unique_URLs_df['Unique_URL_Count'] = Unique_URLs_df.apply(lambda row: Count_Unique_URLs(row['Unique_URLs']), axis=1)

	Unique_URLs_df['datetimevalues'] = Unique_URLs_df.index

	Unique_URLs_df['TimeOnly'] = Unique_URLs_df.apply(lambda row: strip_time(row['datetimevalues']), axis=1)
	Unique_URLs_df['DateOnly'] = Unique_URLs_df.apply(lambda row: strip_date(row['datetimevalues']), axis=1)

	heatmap_data = [
    Heatmap(
        x= Unique_URLs_df["DateOnly"].tolist(),
        y= Unique_URLs_df["TimeOnly"].tolist(),
        z= Unique_URLs_df["Unique_URL_Count"].tolist(),
        colorscale='Viridis'
        # colorscale=[[0, 'rgb(166,206,227)'], [0.25, 'rgb(31,120,180)'], [0.45, 'rgb(178,223,138)'], [0.65, 'rgb(51,160,44)'], [0.85, 'rgb(251,154,153)'], [1, 'rgb(227,26,28)']]
    )
	]
	plotly.offline.plot(heatmap_data, auto_open=False, filename='assets/pages/browspattern_heatmap.html')


	browspat_bar_data = [Bar(x= Unique_URLs_df.index.tolist(), y= Unique_URLs_df['Unique_URL_Count'].tolist())]

	plotly.offline.plot(browspat_bar_data, auto_open=False, filename='assets/pages/wordcount_plot.html') 


	#################### End of Browsing pattern related script #########################################

	#################### Start of NER related script ####################################################

	# Extract netloc to seperate column
	browser_history_dataframe['netloc']= browser_history_dataframe.apply(lambda row: netloc_extractor(row['url_location']), axis=1)

	Without_SE_SM_df =  remove_SE_SM(browser_history_dataframe)

	clean_URL_duplicates = Without_SE_SM_df.drop_duplicates(['url_location'])
	clean_null_URLS = clean_URL_duplicates[clean_URL_duplicates.url_location.notnull()]
	clean_null_netloc = clean_null_URLS [clean_null_URLS .netloc.notnull()]

	sorted_Without_SE_SM_df = clean_null_netloc.sort_values(['visit_count', 'frecency'], ascending=[False, False])

	#Select URLs which are most visited
	top_URLS_df = sorted_Without_SE_SM_df.nlargest(100, 'visit_count')
	
	URLs_to_scrape = top_URLS_df.url_location.unique()

	#Fetch text from the top visited URLS by crawling
	text_from_website = grab_website_text(URLs_to_scrape)

	#normalize by converting the unicode text to string		
	text_to_analyze = unicodedata.normalize('NFKD', text_from_website).encode('ascii','ignore')

	stopword_free_text = create_stopword_free_text(text_to_analyze)

	# Create a world cloud of the overall text
	wc_org = WordCloud(max_words =1000, width=600, height=400).generate(stopword_free_text)
	wc_org.to_file("assets/img/wc_all.png")

	(Org_values, Per_values, Loc_values) = create_NER_strings(text_to_analyze)


	wc_org = WordCloud(max_words =1000,width=600 , height=400).generate(Org_values)
	wc_org.to_file("assets/img/wc_org.png")

	wc_per = WordCloud(max_words =1000, width=600 , height=400).generate(Per_values)
	wc_per.to_file("assets/img/wc_per.png")

	wc_loc = WordCloud(max_words =1000, width=600 ,height=400).generate(Loc_values)
	wc_loc.to_file("assets/img/wc_loc.png")


	#################### END of NER related script ####################################################

	cwd = os.getcwd()
	file_to_open =  "file:"+cwd+"/index.html"
	webbrowser.open_new_tab(file_to_open)
	
	


