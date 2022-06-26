import adafruit_requests as requests
from config import config
import time
# Get wifi details and more from a secrets.py file


# set up
url_nextconnect = config['api_url']
seconds_1day = 24 * 60 * 60 # 24 hours x 60 minutes x 60 seconds
network_reset = 1 # minutes before starting network

routes = config['routes']

# TODO remove when confirm dict passing color works
# manual edit of route colors for now; conditionals must match your route names in config
# def fetch_line_color(route_name: str) -> int:
#     if route_name == '22':
#         return 0x0011aa  # hex color format, begins with 0x
#     elif route_name == '45':
#         return 0xa81995
#     elif route_name == '71':
#         return 0x22cf19
#     elif route_name == '26':
#         return 0xde4e00
#     else:
#         return 0xFF0000


class RealTimeAPI:
    def __init__(self, esp_control):
        self.esp = esp_control
    def fetch_predictions(self, routes: list = routes) -> list:
        results = []
        for route in routes:
            update = self.fetch_route(route['route_name'], route['route_color'], route['params'])
            time.sleep(1)
            if not update:
                continue
            results.append(update)
            print('Fetched 1 trip update.')
        results = [result for result in results if result.get('arrival',None)] # filter out unnecessary updates
        print("Finished round of fetch predictions.")
        return sorted(results, key= lambda x: int(x['arrival'].split(',')[0])) # sort by the next arrival for each

    def fetch_route(self, route_name: str, route_color: int, route_params: dict) -> dict:
        payload = route_params
        hdrs = {'Content-Type': 'application/json',
         'Accept': 'application/json',
         'Accept-Encoding': 'gzip, deflate',
         'Host': 'nextconnect.riderta.com',
         'Referer': 'http://nextconnect.riderta.com/LiveDepartureTimes',
         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
         }
        while True:
            try:
                r = requests.post(url_nextconnect,json=payload,headers=hdrs)
                if r.status_code == 200:
                    update = r.json()['d']
                    r.close()

                    # current time to measure offset from
                    nowtime = time.localtime()
                    now_hour = nowtime.tm_hour
                    now_min = nowtime.tm_min
                    now_sec = nowtime.tm_sec
                    now_ampm = 'am' if now_hour < 12 else 'pm'

                    # calculate output time
                    crossings = update['routeStops'][0]['stops'][0]['crossings'] # next two upcoming trips, can link to config variable
                    if not crossings: # Make sure cross
                        return None
                    predictions = []
                    for trip in crossings:
                        if trip['cancelled'] == 'true':
                            continue
                        time_key = 'pred' if trip['predTime'] else 'sched'
                        pred_hour, pred_min = map(int, trip[time_key+'Time'].split(':'))
                        pred_ampm = trip[time_key+'Period']
                        pred_hour = self.convert24(pred_ampm, pred_hour) # convert to 24

                        # convert times to seconds
                        pred_secs = (pred_hour * 60 * 60) + (pred_min * 60)
                        now_secs = (now_hour * 60 * 60) + (now_min * 60) + now_sec

                        # final time difference calculation
                        if pred_ampm == 'am' and now_ampm == 'pm': # if bus comes next day after midnight
                            arrival_in = ((seconds_1day - now_secs) + pred_secs )// 60 # add remaining time to prediction time as minutes
                        else:
                            arrival_in = (pred_secs - now_secs) // 60 # otherwise subtract prediction from current time as minutes
                        predictions.append(arrival_in-1)

                    # filter out all before our cutoff time of choice
                    predictions = list(filter(lambda x: x >= config['cutoff_min'], predictions))
                    # grab next 2 departs
                    last_2 = list(map(str,predictions[:2]))
                    prediction = ','.join(last_2) if predictions else None # output 2

                    # final output of dict
                    destination = crossings[0]['destination']
                    tokens = destination.split(' ')
                    if tokens[0] in ["Red", "Green", "Blue"]:
                        rail_color = tokens[0]
                        destination = destination.split(f'{rail_color} Line')[1].strip()
                    else:
                        destination = ' '.join(tokens[1:]).strip('- ')

                    return {
                        'line_color': route_color, # output 1
                        'route_name': str(route_name), # output 2
                        'destination': '',  # output 3, coded to be off by preference, too busy on board
                        'arrival': prediction, # output 4

                    }
                else:
                    print('Request status code not successful')
                    r = None
                    return None
            except Exception as e:
                print(f"Failed to get data due to {e}. Resetting ESP")
                self.esp.reset()
                self.esp.connect_AP(config["wifi_ssid"], config["wifi_password"])

    # helper, converts API's 12 hour time to 24 hour so calculations can be made
    @staticmethod
    def convert24(period,hour):
        if period == 'pm' and hour != 12:
            return hour + 12
        if period == 'am' and hour == 12:
            return 0
        else:
            return hour
