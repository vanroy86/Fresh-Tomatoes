#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import division
from google.appengine.ext import db
from apiclient.discovery import build
from apiclient.errors import HttpError

import os, re, string, urllib2, json, logging, webapp2, jinja2, cookielib

SECRET = "imsosecret"
DEVELOPER_KEY = "AIzaSyAgf7k0mQmxF12ywMq1_pxOxFi_OfOuuUs"
API_KEY = '49101d62654e71a2931722642ac07e5e'
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

def youtube_search(query, max_results=20):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
 
    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=max_results,
        type="video"
    ).execute()
 
    #extract only a few 'interesting' fields from the data
    result_transform = lambda search_result: {
                    'id': search_result['id']['videoId'],
                    'title': search_result['snippet']['title'], 
                    'thumbnail': search_result['snippet']['thumbnails']['default']['url'],
                    'date': search_result['snippet']['publishedAt']
                }
    # Filter results to retaun only matching videos, and filter out channels and playlists.
    
    return map(result_transform, search_response.get("items", []))


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class Movie(db.Model):
    name = db.StringProperty(required = True)
    trailer_url = db.StringProperty(required = True)
    poster_url = db.StringProperty(required = True)
    plot = db.TextProperty(required = True)
    total_ratings = db.IntegerProperty(required = True)
    rating = db.IntegerProperty(required = True)
    star_5 = db.IntegerProperty(required = True)
    star_4 = db.IntegerProperty(required = True)
    star_3 = db.IntegerProperty(required = True)
    star_2 = db.IntegerProperty(required = True)
    star_1 = db.IntegerProperty(required = True)

class MainPage(Handler):
    def get(self):
        movies = db.GqlQuery("SELECT * from Movie ORDER BY rating DESC ")
        my_movie_names = self.request.cookies.get("my_movie_names")
        my_movies = None
        submitted_movies = []
        if my_movie_names:
            my_movies = []
            for movie in movies:
                if movie.name in my_movie_names:
                    my_movies += [movie] 
                else: 
                    submitted_movies += [movie]
        else:
            submitted_movies = movies
        
        #self.write("hello")
        self.render('jumbotron.html', submitted_movies=submitted_movies, my_movies=my_movies)
    def post(self):
        user_rating = self.request.get("rating")
        movie_id = self.request.get("movie")
        key = db.Key.from_path('Movie', int(movie_id))
        movie = db.get(key)
        total_ratings = movie.total_ratings
        total_ratings += 1
        star_5 = movie.star_5
        star_4 = movie.star_4
        star_3 = movie.star_3
        star_2 = movie.star_2
        star_1 = movie.star_1
        if int(user_rating) == 1: 
            star_1 += 1
            movie.star_1 = star_1
        elif int(user_rating) == 2: 
            star_2 += 1
            movie.star_2 = star_2
        elif int(user_rating) == 3: 
            star_3 += 1
            movie.star_3 = star_3
        elif int(user_rating) == 4: 
            star_4 += 1
            movie.star_4 = star_4
        elif int(user_rating) == 5: 
            star_5 += 1
            movie.star_5 = star_5
        movie.rating = int(round((5*star_5 + 4*star_4 + 3*star_3 + 2*star_2 + 1*star_1)/total_ratings)) 
        movie.total_ratings = total_ratings
        movie.put()
        logging.error(movie.rating)
        logging.error(movie.name)
        logging.error(user_rating)

        self.redirect("/")
class SubmitHandler(Handler):
    def get(self):
        self.render("signin.html" , movie_error = None)
    def post(self):
        movie = self.request.get("movie")
        search_results = youtube_search(movie+" Trailer")
        if len(search_results) != 0:
            trailer_url = "http://www.youtube.com/embed/"+search_results[0]['id']
        else: 
            trailer_url = None

        movie_split = movie.split(" ")
        encoded_movie_name = "%20".join(movie_split)
        #logging.error("url is http://www.omdbapi.com/?t=" + encoded_movie_name)
        connection = urllib2.urlopen(r"http://api.themoviedb.org/3/search/movie?query="+encoded_movie_name+"&api_key="+API_KEY)
        j = connection.read()
        search_results = json.loads(j)
        #logging.error(movie_attributes)
        if search_results["total_results"] == 0:
            #logging.error("Error route")
            self.render("signin.html",movie_error="Movie cannot be found/does not exist. Please check spelling.")
        else:
            #logging.error("Correct route")
            result_number = -1
            poster_url = None
            while not poster_url:
                result_number += 1
                poster_url = search_results["results"][result_number]["poster_path"]
                connection = urllib2.urlopen("http://api.themoviedb.org/3/movie/"+str(search_results["results"][result_number]["id"])+"?api_key="+API_KEY)
                j = connection.read()
                movie_attributes = json.loads(j)
                plot = movie_attributes["overview"]
                logging.error(plot)
                if not plot:
                    poster_url = None
                name = movie_attributes["title"]
            poster_url = r"http://image.tmdb.org/t/p/w500" +  poster_url
            
            # poster_result = movie_attributes["poster_path"]
            # logging.error(poster_result)
            # if poster_result:
            #     poster_url = r"http://image.tmdb.org/t/p/w500" + movie_attributes["poster_path"]
            # else: 
                
            #     self.render("signin.html",movie_error="Movie cannot be found/does not exist. Please check spelling.")
            logging.error(poster_url)
           
            check = db.GqlQuery('SELECT * FROM Movie WHERE name = :1', name).get()
            if not check:
                # youtube_id_match = re.search(r'(?<=v=)[^&#]+', youtube)
                # youtube_id_match = youtube_id_match or re.search(r'(?<=be/)[^&#]+', youtube)
                # youtube = youtube_id_match.group(0) if youtube_id_match else None
                u = Movie(name=name,trailer_url=trailer_url,poster_url=poster_url,plot=plot,rating=0,total_ratings=0,
                           star_5=0,star_4=0,star_3=0,star_2=0,star_1=0)
                u.put()
                self.redirect('/')
                
                # Adding this movie to the users movie list
                my_movie_names = self.request.cookies.get("my_movie_names")
                if my_movie_names:
                    my_movie_names = json.loads(my_movie_names)
                    if name not in my_movie_names:
                        my_movie_names += [name]
                else:
                    my_movie_names = [name]
                self.response.set_cookie("my_movie_names", json.dumps(my_movie_names), max_age=315360000)
                logging.error(my_movie_names)
            else:
                self.render("signin.html",movie_error="Movie already exists")


class DetailsHandler(Handler):
    def get(self, movie_id):
        key = db.Key.from_path('Movie', int(movie_id))
        movie = db.get(key)
        if not movie:
            self.write("404 Error")
        else:
            self.render("details.html", movie = movie)




class TestHandler(Handler):
    def get(self):
        self.render("test_ajax.html")
        
class AjaxHandler(Handler):
    def post(self):
        numberOfRecords =int(self.request.get('numberOfRecords'))
        logging.error(numberOfRecords)
        movies = db.GqlQuery("SELECT * from Movie").count()
        logging.error(movies)
        if movies != numberOfRecords:
            logging.error("Yes")
            response  = {'isUpdateAvail': "Yes","count": movies}
            self.response.out.write(json.dumps(response))
        else:
            logging.error("No")
            response =  {'isUpdateAvail': "No"}
            self.response.out.write(json.dumps(response))
        


app = webapp2.WSGIApplication([('/', MainPage),
                                ('/ajax', AjaxHandler),
                               ('/submit' , SubmitHandler),
                               ('/([0-9]+)',DetailsHandler)], debug=True)
