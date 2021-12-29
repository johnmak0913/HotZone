from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from cases.models import Case, Location, Patient,Visit
from django.http import HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import urllib.request
import json
import logging
from urllib.error import HTTPError
from django.shortcuts import redirect
from django.db.models import Q
import numpy as np
from sklearn.cluster import DBSCAN
import math
from datetime import datetime, date, timedelta
# Create your views here.

def LoginView(request):
    if request.method=='POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect('/')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def LogoutView(request):
    logout(request)
    return render(request, 'login.html', {'form': AuthenticationForm()})

@login_required(login_url="/login")
def saveGeoData(request):
    name = request.GET.get("name")
    address = request.GET.get("address")
    x = float(request.GET.get("x"))
    y = float(request.GET.get("y"))
    query = Location.objects.all().filter(name__iexact=name).filter(address__iexact=address).filter(x_coord=x).filter(y_coord=y)
    if not query.exists():
        record = Location(name=name, address=address, x_coord = x, y_coord = y);
        record.save()
    return HttpResponse("success")

@login_required(login_url="/login")
def queryLocationDB(request):
    name = request.GET.get("name")
    address = request.GET.get("address")
    x = float(request.GET.get("x"))
    y = float(request.GET.get("y"))
    query = Location.objects.all().filter(name__iexact=name).filter(address__iexact=address).filter(x_coord=x).filter(y_coord=y)
    if query.exists():
        return HttpResponse(str(query.first().pk))
    else:
        return 0

@login_required(login_url="/login")
def saveVisit(request):
    caseNo = request.GET.get("caseNo")
    dateFrom = request.GET.get("dateFrom")
    dateTo = request.GET.get("dateTo")
    category = request.GET.get("category")
    locationId = request.GET.get("locationId")

    case_obj = Case.objects.filter(num=caseNo).first()
    location_obj = Location.objects.filter(id=locationId).first()
    visit_obj = Visit(date_from=dateFrom, date_to=dateTo, category=category, case=case_obj, location=location_obj)
    visit_obj.save()
    return HttpResponse("success")

def findLocation(l, x):
    for loc in l:
        if loc['name'] == x['nameEN'] and loc['address'] == x['addressEN'] and float(loc['x']) == float(x['x']) and float(loc['y']) == float(x['y']):
            return loc
    return None

@method_decorator(login_required, name='dispatch')
class addVisitRecordView(TemplateView):
    template_name = "add_visit_record.html"

    def get_context_data(self, **kwargs):
        caseNo = self.request.GET.get("caseNo")
        datefrom = self.request.GET.get("datefrom")
        dateto = self.request.GET.get("dateto")
        category_choice = self.request.GET.get("category-choice")
        location = self.request.GET.get("location")

        context = super().get_context_data(**kwargs)

        if caseNo:
            context['caseNo'] = caseNo
        if datefrom:
            context['datefrom'] = datefrom
        if dateto:
            context['dateto'] = dateto
        if category_choice:
            context['category'] = category_choice
        if location:
            context['location'] = location
            try:
                response = urllib.request.urlopen('https://geodata.gov.hk/gs/api/v1.0.0/locationSearch?q=' + urllib.parse.quote(location))
            except HTTPError as e:
                return {'status': e.code}
            if (response.getcode() != 200):
                return {'status': response.getcode()}
            locations_from_geodata = json.load(response)
            locations_from_db = []
            all_from_db = []
            locations_from_geodata_escaped = []
            query_from_db = Location.objects.all()
            for loc in query_from_db:
                all_from_db.append({"name": loc.name, "address": loc.address, "x": loc.x_coord, "y": loc.y_coord})
            for loc in locations_from_geodata:
                loc_from_db = findLocation(all_from_db, loc)
                locations_from_geodata_escaped.append({"name": loc["nameEN"], "address": loc["addressEN"], "nameEN": loc["nameEN"].replace("'", r"\'"), "addressEN": loc["addressEN"].replace("'", r"\'"), "x": loc["x"], "y": loc["y"]})
                if loc_from_db:
                    locations_from_db.append({"name": loc_from_db["name"], "address": loc_from_db["address"], "name": loc_from_db["name"].replace("'", r"\'"), "address": loc_from_db["address"].replace("'", r"\'"), "x": loc_from_db["x"], "y": loc_from_db["y"]})

            if locations_from_db:
                context['query_from_app_db_empty'] = False
                context['results_from_app_db'] = locations_from_db
            else:
                context['query_from_app_db_empty'] = True
            
            if locations_from_geodata_escaped:
                after_dedup = [x for x in locations_from_geodata_escaped if not findLocation(locations_from_db, x)]
                if after_dedup:
                    context['query_from_geodata_empty'] = False
                    context['results_from_geodata'] = after_dedup
                else:
                    context['query_from_geodata_empty'] = True
            else:
                context['query_from_geodata_empty'] = True
        else:
            context['query_from_app_db_empty'] = True
            context['query_from_geodata_empty'] = True
            
        return context

@method_decorator(login_required, name='dispatch')
class casesView(ListView):
    model = Case
    allow_empty = True
    template_name = "view_cases.html"

    def get_queryset(self):
        query = self.request.GET.get("search_query")
        if (query): 
            case_list = Case.objects.filter(Q(patient__identity_number=query) | Q(num=query))
            if (not case_list):
                case_list.empty_query_result = 1
        else:
            case_list = Case.objects.all()
        return case_list

def custom_metric(q, p, space_eps, time_eps):
    dist = 0
    for i in range(2):
        dist += (q[i] - p[i])**2
    spatial_dist = math.sqrt(dist)
    time_dist = math.sqrt((q[2]-p[2])**2)
    if time_dist/time_eps <= 1 and spatial_dist/space_eps <= 1 and p[3] != q[3]:
        return 1
    else:
        return 2

def visit_date_key(visit):
    return visit["day"]

@method_decorator(login_required, name='dispatch')
class clustersView(TemplateView):
    template_name = "view_clusters.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        D = self.request.GET.get('D')
        T = self.request.GET.get('T')
        C = self.request.GET.get('C')
        if D is None or T is None or C is None:
            if D is None:
                context["D"] = "200"
            else:
                context["D"] = D
            if T is None:
                context["T"] = "3"
            else:
                context["T"] = T
            if C is None:
                context["C"] = "2"
            else:
                context["C"] = C
            context["result"] = False
            return context
        context["result"] = True
        context["D"] = D
        context["T"] = T
        context["C"] = C
        distance = int(self.request.GET.get('D'))
        time = int(self.request.GET.get('T'))
        minimum_cluster = int(self.request.GET.get('C'))
        
        epoch = date(2019, 12, 1)
        vector_4d = []
        for visit in Visit.objects.all():
            x = visit.location.x_coord
            y = visit.location.y_coord
            day = (visit.date_from - epoch).days
            caseno = visit.case.num
            vector_4d.append([x, y, day, caseno])
        vector_4d = np.array(vector_4d).astype(np.float64)
        
        params = {"space_eps": distance, "time_eps": time}
        db = DBSCAN(eps=1, min_samples=minimum_cluster-1, metric=custom_metric, metric_params=params).fit_predict(vector_4d)
        unique_labels = set(db)
        total_clusters = len(unique_labels) if -1 not in unique_labels else len(unique_labels) -1
        clusters = []
        total_noise = list(db).count(-1)
        context["unclustered"] = total_noise
        for k in unique_labels:
            if k != -1:
                labels_k = db == k
                cluster_k = vector_4d[labels_k]
                cluster = { "no" : k, "size" : len(cluster_k), "visits" : [] }
                for pt in cluster_k:
                    x = pt[0]
                    y = pt[1]
                    day = int(pt[2])
                    visit_date = epoch + timedelta(days=day)
                    location = Location.objects.all().filter(x_coord=x).filter(y_coord=y).first().name
                    cluster["visits"].append({"location" : location, "x" : x, "y" : y, "day" : day, "date" : visit_date, "caseno" : int(pt[3])})
                cluster["visits"].sort(key=visit_date_key)
                clusters.append(cluster)
        context["clusters"] = clusters
        return context


@method_decorator(login_required, name='dispatch')
class caseDetails(TemplateView):
    template_name = "case_details.html"

    def get_context_data (self, **kwargs): 

        case = self.kwargs['case']

        context = super().get_context_data(**kwargs)
        context['visits'] = Visit.objects.filter(case__num=case)
        context['case'] = Case.objects.get(num=case)
        
        #confused about this two visit__pk & pk
        return context
