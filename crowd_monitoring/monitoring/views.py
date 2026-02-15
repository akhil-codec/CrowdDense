import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.gis.geos import GEOSGeometry
from .models import Event, Zone, Attendee, Manager, AttendeeLocationLog, ManagerLocationLog

def event_list(request):
    events = Event.objects.all()
    
    if request.method == "POST":
        # Check which form was submitted
        if 'create_event' in request.POST:
            name = request.POST.get('name')
            date = request.POST.get('date')
            time = request.POST.get('time')
            boundary_wkt = request.POST.get('boundary')
            boundary_wkt = "POLYGON ((" + boundary_wkt + "))"
            # Validation to prevent IntegrityError (null values)
            if name and date and time and boundary_wkt:
                try:
                    Event.objects.create(
                        event_name=name,
                        event_date=date,
                        event_time=time,
                        location_boundary=GEOSGeometry(boundary_wkt)
                    )
                except Exception as e:
                    print(f"Error creating event: {e}")
            
        elif 'create_zone' in request.POST:
            event_id = request.POST.get('event_id')
            zone_name = request.POST.get('zone_name')
            zone_boundary_wkt = request.POST.get('zone_boundary')
            zone_boundary_wkt = "POLYGON ((" + zone_boundary_wkt + "))"
            if event_id and zone_name and zone_boundary_wkt:
                try:
                    event = get_object_or_404(Event, id=event_id)
                    Zone.objects.create(
                        event=event,
                        zone_name=zone_name,
                        location_boundary=GEOSGeometry(zone_boundary_wkt)
                    )
                except Exception as e:
                    print(f"Error creating zone: {e}")
            
        return redirect('event_list')

    return render(request, 'event_list.html', {'events': events})

def dashboard(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    zones = event.zones.all()
    for zone in zones:
        # Check how many attendee points are inside this zone's polygon
        # 'location__within' is the GeoDjango spatial filter
        count = AttendeeLocationLog.objects.filter(
            location__within=zone.location_boundary
        ).count()
        
        # Save the new count to the database
        zone.current_count = count
        zone.save()
         
    # Fetching logs for the heatmap dots
    attendee_logs = AttendeeLocationLog.objects.filter(attendee__event=event)
    manager_logs = ManagerLocationLog.objects.filter(manager__event=event)
    
    map_data = []
    for log in attendee_logs:
        map_data.append({'lat': log.location.y, 'lng': log.location.x, 'role': 'attendee'})
    for log in manager_logs:
        map_data.append({'lat': log.location.y, 'lng': log.location.x, 'role': 'manager'})

    context = {
        'event': event,
        'total_attendees': event.attendees.count(),
        'total_managers': event.managers.count(),
        'zones': event.zones.all(),
        'map_data_json': json.dumps(map_data),
    }
    return render(request, 'dashboard.html', context)