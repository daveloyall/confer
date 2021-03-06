import json, sys, re, hashlib, smtplib, base64, urllib, os, difflib, random

from auth import *
from django.http import *
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.core.context_processors import csrf
from django.db.utils import IntegrityError
from collections import defaultdict

from utils import *
from models import *

p = os.path.abspath(os.path.dirname(__file__))
if(os.path.abspath(p+"/..") not in sys.path):
  sys.path.append(os.path.abspath(p+"/.."))


'''
@author: Anant Bhardwaj
@date: Feb 12, 2012
'''

def home (request):
  conferences = Conference.objects.all().values()
  login_id, user = get_login(request)
  login_name = '' if not user else user.f_name
  return render_to_response('home.html', {
        'conferences':conferences,
        'login_id': login_id,
        'login_name': login_name
      }
  )


def team (request):
  current_team = json.loads(
      open(p+'/fixtures/' + 'team.json').read())
  past_collaborators = json.loads(
      open(p+'/fixtures/' + 'collaborators.json').read())
  login_id, user = get_login(request)
  login_name = '' if not user else user.f_name
  return render_to_response(
      'team.html', {'current_team': current_team,
      'past_collaborators': past_collaborators,
      'login_id': login_id,
      'login_name': login_name
    }
  )


def conf (request, conf):
  conf = conf.lower()
  try:
    request.session[kConf] = conf
    Conference.objects.get(unique_name=conf)
    return HttpResponseRedirect('/%s/papers' %(conf))
  except Conference.DoesNotExist:
    raise Http404


def papers (request, conf):
  conf = conf.lower()
  try:
    Conference.objects.get(unique_name=conf)
    request.session[kConf] = conf
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    meetups = None if not user else user.meetups_enabled
    return render_to_response('papers.html', {
        'conf':conf,
        'login_id': login_id,
        'login_name': login_name,
        'meetups_enabled': meetups
      }
    )
  except Conference.DoesNotExist:
    raise Http404
  
  

def schedule (request, conf):
  conf = conf.lower()
  try:
    Conference.objects.get(unique_name=conf)
    request.session[kConf] = conf
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    meetups = None if not user else user.meetups_enabled
    return render_to_response('schedule.html', {
        'conf':conf,
        'login_id': login_id,
        'login_name': login_name,
        'meetups_enabled': meetups
      }
    )
  except Conference.DoesNotExist:
    raise Http404


def paper (request, conf):
  conf = conf.lower()
  try:
    Conference.objects.get(unique_name=conf)
    request.session[kConf] = conf
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    meetups = None if not user else user.meetups_enabled
    return render_to_response('paper.html', {
        'conf':conf,
        'login_id': login_id,
        'login_name': login_name,
        'meetups_enabled': meetups
      }
    )
  except Conference.DoesNotExist:
    raise Http404


@login_required
def meetups (request, conf):
  conf = conf.lower()
  try:
    Conference.objects.get(unique_name=conf)
    similar_people = []
    request.session[kConf] = conf
    login_id, user = get_login(request)
    meetups_enabled = user.meetups_enabled
    if meetups_enabled:
      similar_people = get_similar_people(user.email, conf, meetups=True)
    return render_to_response('meetups.html', {
        'conf':conf,
        'similar_people': similar_people[:20],
        'meetups_enabled': meetups_enabled,
        'login_id': user.email,
        'login_name': user.f_name
      }
    )
  except Conference.DoesNotExist:
    raise Http404


@login_required
def settings (request):
  errors = []
  error = False
  redirect_url = '/'

  if('redirect_url' in request.GET.keys()):
    redirect_url = request.GET['redirect_url']

  if request.method == "POST":
    try:
      if('redirect_url' in request.POST.keys()):
        redirect_url = request.POST['redirect_url']

      user_email = request.POST["user_email"].lower()
      meetups = request.POST["meetups_enabled"] 
      user = User.objects.get(email=user_email)
      if meetups == 'enabled':
        user.meetups_enabled = True
      else:
        user.meetups_enabled = False

      user.save()
      return HttpResponseRedirect(redirect_url)
    except Exception, e:
      errors.append(
          'Some unknown error happened. '
          'Please try again or send an email to '
          '<a href="mailto:confer@csail.mit.edu">confer@csail.mit.edu</a>')
      c = {'errors': errors} 
      c.update(csrf(request))
      return render_to_response('settings.html', c)
  else:
    login = get_login(request)
    user = login[1]
    c = {
        'user_email': user.email,
        'login_id': user.email,
        'login_name': user.f_name,
        'meetups_enabled': user.meetups_enabled,
        'redirect_url': redirect_url}
    c.update(csrf(request))
    return render_to_response('settings.html', c)


@login_required
def anonymized_data_dump (request, conf):
  conf = conf.lower()
  likes = []
  msg = 'OK'
  try:
    login_id, user = get_login(request)
    conference = Conference.objects.get(unique_name=conf)
    admins = json.loads(conference.admins)
    if user.email in admins:
      registrations = Registration.objects.filter(conference=conference)
      for r in registrations:
        res = {
            'id': encrypt_text(r.user.email),
            'meetups_enabled': r.user.meetups_enabled
        }
        try:
          r_likes = Likes.objects.get(registration=r)
          res['likes'] = json.loads(r_likes.likes)
        except:
          res['likes'] = []

        likes.append(res)
        random.shuffle(likes)
    else:
      msg = 'ACCESS DENIED: You are not an admin for this conference.'
    
  except Exception, e:
    msg = 'Error: %s.' %(e)

  return HttpResponse(json.dumps({'msg': msg, 'data': likes}), mimetype="application/json")

def visualizations (request, conf):
  conf = conf.lower()
  try:
    request.session[kConf] = conf
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    strength = 10
    try:
      strength = int(request.REQUEST["strength"])
    except:
      pass
    return render_to_response('visualizations.html', {
        'strength' : strength,
        'conf':conf,
        'login_id': login_id,
        'login_name': login_name
      }
    )
  except:
    return HttpResponseRedirect('/')

def paper_paper_graph (request, conf):
  conf = conf.lower()
  edges = defaultdict(dict)
  nodes = set()
  likes = defaultdict(set)
  nodesArray = []
  linksArray = []
  errors = []
  try:
    strength = 10
    try:
      strength = int(request.REQUEST["strength"])
    except:
      pass

    conference = Conference.objects.get(unique_name=conf)    
    registrations = Registration.objects.filter(conference=conference)
    for r in registrations:
      try:      
        r_likes = Likes.objects.get(registration=r)
        r_papers = json.loads(r_likes.likes)
        for p in r_papers:
          likes[p].add(r)
          nodes.add(p)
      except:
        pass
    
    nodes = list(nodes)

    for p1 in nodes:
      for p2 in nodes:
        edges[p1][p2] = -1
        if(p1 != p2): 
          common_likes = likes[p1].intersection(likes[p2])        
          edges[p1][p2] = len(common_likes)

    k = 0
    for node in nodes:
      nodesArray.append({'id': k, 'paper_id': node, 'weight': len(likes[node])})
      k += 1

    for edge in edges:
      links = edges[edge]
      for l in links:
        weight = edges[edge][l]
        if(weight >= strength):
          linksArray.append({'source' : nodes.index(edge), 'target' : nodes.index(l), 'weight': weight})

  except Exception, e:
    errors.append(str(e))
  
  return HttpResponse(json.dumps({'nodes': nodesArray, 'links': linksArray, 'errors': errors}), mimetype="application/json")


def feed (request, conf):
  conf = conf.lower()
  try:
    request.session[kConf] = conf
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    return render_to_response('feed.html', {
        'conf':conf,
        'login_id': login_id,
        'login_name': login_name
      }
    )
  except:
    return HttpResponseRedirect('/')

@csrf_exempt
def data (request):
  recs = []
  likes = []
  error = False
  msg = 'OK'
  login = None
  login_name = None
  try:
    login = request.session[kLogIn]
    login_name = request.session[kName]
    conf = request.session[kConf]
    registration = get_registration(login, conf)
    data = None

    try:
      data = Likes.objects.get(registration = registration)
    except:
      pass

    if not data or not data.likes:
      default_likes = []
      try:
        prefs = json.loads(
            open(p+'/../data/%s/prefs.json' %(conf)).read())
        name = request.session[kFName] + ' ' + request.session[kLName]
        name = name.lower()
        if name in prefs:
          default_likes = prefs[name]
        else:
          matches = difflib.get_close_matches(name, prefs.keys())
          if len(matches) > 0:
            default_likes = prefs[matches[0]]

      except Exception, e:
        pass

      data = Likes(registration = registration, likes=json.dumps(default_likes))
      data.save()

    likes.extend(json.loads(data.likes))

  except Exception, e:
    error = True
    msg = str(e)

  return HttpResponse(json.dumps({
      'login_id': login,
      'login_name': login_name,
      'recs':recs, 
      'likes':likes,
      'error': error,
      'msg':msg}), mimetype="application/json")


@csrf_exempt
@login_required
def log (request, action):
  try:
    login = request.session[kLogIn]
    conf = request.session[kConf]
    registration = get_registration(login, conf)
    insert_log(registration, action)
    return HttpResponse(
        json.dumps({'error':False}), mimetype="application/json")

  except:
    return HttpResponse(
        json.dumps({'error':True}), mimetype="application/json")


@csrf_exempt
@login_required
def like (request, like_str):
  login = request.session[kLogIn]
  likes = []
  recs = []
  error = False
  msg = "OK"
  try:
    papers = json.loads(request.POST["papers"])
    conf = request.session[kConf]
    registration = get_registration(login, conf)
    data = None
    insert_log(registration, like_str, papers)
    try:
      data = Likes.objects.get(registration = registration)
      likes.extend(json.loads(data.likes))
    except:
      data = Likes(registration = registration, likes = json.dumps([]))
      data.save()   
    
    for paper_id in papers:
      if(like_str=='star' and (paper_id not in likes) and paper_id != ''):
        likes.append(paper_id)
      if(like_str=='unstar' and (paper_id in likes) and paper_id != ''):
        likes.remove(paper_id)

    likes = list(set(likes))    
    data.likes = json.dumps(likes)
    data.save()
    recs = []

  except Exception, e:
    error = True
    msg = str(e)

  return HttpResponse(
    json.dumps({
        'recs':recs,
        'likes':likes,
        'error':error,
        'msg':msg
      }
    ),
    mimetype="application/json"
  )



'''
Confer APIs
'''


@csrf_exempt
def likes (request):
  likes = []
  error = False
  msg = 'OK'
  login = None
  conf = None
  try:
    login = request.POST["login_id"]
    conf = request.POST["conf_id"]
    registration = get_registration(login, conf)
    user = User.objects.get(email=login)
    app_id = request.POST["app_id"]
    app_token = request.POST["app_token"]
    app = App.objects.get(app_id=app_id, app_token=app_token)
    perm = None
    try:
      perm = Permission.objects.get(app=app, user=user)
    except:
      pass

    if perm and perm.access:
      data = None

      try:
        data = Likes.objects.get(registration = registration)
        likes.extend(json.loads(data.likes))
      except:
        pass

    else:
      msg = 'ACCESS_DENIED'

  except Exception, e:
    error = True
    msg = str(e)

  return HttpResponse(json.dumps({
      'login_id': login,
      'conf':conf,
      'likes':likes,
      'error': error,
      'msg':msg}), mimetype="application/json")



@csrf_exempt
def similar_people (request):
  login = None
  similar_people = []
  conf = None
  error = False
  msg = "OK"
  try:
    login = request.POST["login_id"]
    conf = request.POST["conf_id"]
    user = User.objects.get(email=login)
    app_id = request.POST["app_id"]
    app_token = request.POST["app_token"]
    app = App.objects.get(app_id=app_id, app_token=app_token)

    perm = None
    try:
      perm = Permission.objects.get(app=app, user=user)
    except:
      pass

    if perm and perm.access:
      similar_people = get_similar_people(login, conf, app=app)
    else:
      msg = 'ACCESS_DENIED'
  
  except Exception, e:
    error = True
    msg = str(e)

  return HttpResponse(json.dumps({
        'login_id': login,
        'conf':conf,
        'similar_people': similar_people,
        'error': error,
        'msg':msg
      }), mimetype="application/json")


@login_required
def register_app (request):
  errors = []
  error = False

  if request.method == "POST":
    try:
      user_email = request.POST["user_email"].lower()
      app_id = request.POST["app_id"].lower()
      app_name = request.POST["app_name"]
      user = User.objects.get(email=user_email)
      app_token = hashlib.sha1(app_id + '_token').hexdigest()
      app = App(app_id=app_id, app_name=app_name, user=user, app_token=app_token)
      app.save()
      return HttpResponseRedirect('/developer/apps')
    except Exception, e:
      errors.append(e)
      c = {'errors': errors} 
      c.update(csrf(request))
      return render_to_response('register_app.html', c)
  else:
    login = get_login(request)
    user = login[1]
    c = {
        'user_email': user.email,
        'login_id': user.email,
        'login_name': user.f_name}
    c.update(csrf(request))
    return render_to_response('register_app.html', c)

@login_required
def apps (request):
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    meetups = None if not user else user.meetups_enabled
    apps = App.objects.filter(user=user)
    res = []
    for app in apps:
      res.append({'app_id': app.app_id, 'app_name': app.app_name, 'app_token': app.app_token})
    
    c = {
        'user_email': login_id,
        'login_id': login_id,
        'login_name': login_name,
        'apps': res}
    return render_to_response('apps.html', c)

@login_required
def allow_access (request):
  errors = []
  try:
    login_id, user = get_login(request)
    login_name = '' if not user else user.f_name
    
    if 'app_id' not in request.REQUEST.keys():
      errors.append("Couldn't find a required parameter 'app_id' in the request")
    else:
      app_id = request.REQUEST["app_id"].lower()
      app = App.objects.get(app_id=app_id)
      access_allowed = True
      if request.method == "POST":
        access_val = request.REQUEST["access_val"]
        if access_val == "allow":
          access_allowed = True
        else:
          access_allowed = False

        perm = None

        try:
          perm = Permission.objects.get(app=app, user=user)
        except Permission.DoesNotExist:
          perm = Permission(app=app, user=user)

        perm.access = access_allowed
        perm.save()

        c = {
          'msg_title': 'Thank you',
          'msg_body': 'Your preference has been saved.'
        } 
        c.update(csrf(request))

        return render_to_response('confirmation.html', c)
      else:
        c = {
          'user_email': login_id,
          'login_id': login_id,
          'login_name': login_name,
          'app_id': app_id,
          'app_name': app.app_name,
          'access_allowed': access_allowed}
        c.update(csrf(request))
        return render_to_response('app_access.html', c)

  except Exception, e:
    errors.append('Error: ' + str(e))
    
  c = {'msg_title': 'Data Access Permission', 'errors': errors} 
  c.update(csrf(request))
  return render_to_response('confirmation.html', c)







