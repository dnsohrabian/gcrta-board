import displayio
import time
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text.scrolling_label import ScrollingLabel
from adafruit_matrixportal.matrix import Matrix

from config import config


class TrainBoard:
    """
        get_new_data is a function that is expected to return an array of dictionaries like this:
        [
            {
                'line_color': 0xFFFFFF,
                'destination': 'Dest Str',
                'arrival': '5'
            }
        ]
    """
    def __init__(self, get_new_data):
        self.get_new_data = get_new_data
        self.matrix = Matrix(bit_depth=3)
        self.display = self.matrix.display
        # self.display.auto_refresh = False

        # create parent group for entire display relative positioning
        self.parent_group = displayio.Group()

        # loading indicator
        self.loading_dot = Rect(width=2, height=2, x=0,y=0, fill=0x000055)
        self.loading_dot_grp = displayio.Group(x=61,y=29)
        self.loading_dot_grp.append(self.loading_dot)
        self.parent_group.append(self.loading_dot_grp)
        # setup header row showing LINE DESTINATION MINUTES
        self.heading_label = Label(x=0, y=0, font=config['time_font'], anchor_point=(0,0), anchored_position= (0,0))
        self.heading_label.color = config['heading_color']
        self.heading_label.text=config['heading_text']
        self.parent_group.append(self.heading_label)

        # add small clock at bottom
        self.time_update = Label(anchored_position=(32, 27),
                                 font=config['time_font'],
                                 anchor_point=(0.5, 0),
                                 color= 0x000055,
                                 )

        self.time_update.text = config['loading_time_msg']
        self.parent_group.append(self.time_update)

        # instantiate configured number of rows (trains) on board and add to parent group
        self.trains = []

        for i in range(config['num_routes_display']):
            self.trains.append(Train(self.parent_group, index= i))

        # display parent displayio group on board
        self.display.show(self.parent_group)
        self.display.refresh()

    def refresh(self) -> bool:
        # prep time stamp for clock update
        cur_hour = time.localtime().tm_hour
        cur_min = time.localtime().tm_min
        tstamp = f'{cur_hour}:{cur_min:0>2}'
        print(f'{tstamp} Refreshing train information...')

        # call function fetch_predictions from main api.py, get parsed list
        train_data = self.get_new_data()

        if train_data is not None:
            for i in range(config['num_routes_display']):
                if i < len(train_data):
                    train = train_data[i]
                    if not train['arrival']:
                        self._hide_train(i)
                    else:
                        self._update_train(i,
                        train['line_color'],
                        train['route_name'],
                        train['destination'],
                        train['arrival']
                        )
                else:
                    self._hide_train(i)
            self.time_update.text = tstamp # update clock
        else:
            print('No data received. Clearing display.')
            for i in range(config['num_routes']):
                self._hide_train(i)

    def _hide_train(self, index: int):
        self.trains[index].hide()

    def _update_train(self, index: int, line_color: int, route: str, destination: str, minutes: str):
        self.trains[index].update(line_color, route, destination, minutes)


class Train:
    def __init__(self, parent_group, index):
        y = (index+1) * 7 - 1
        self.line_rect = Rect(x=0, y=0, width=config['train_line_width'], height=config['train_line_height'], fill=config['loading_line_color'])

        self.route_label = Label(x=config['text_padding'], y=3, font=config['font'])
        self.route_label.color = config['text_color']
        self.route_label.text = config['loading_route_text']

        # self.destination_label = Label(x=18, y=3, font=config['font'])
        # self.destination_label.color = config['text_color']
        # self.destination_label.text = config['loading_destination_text']

        self.destination_label = Label(x=14,
          y=3, text=config['loading_destination_text'],
          # max_characters = config['destination_max_characters'],
          # animate_time = 0.3,
          font=config['font'])
        self.destination_label.color = config['dest_color']

        self.min_label = Label(
            anchor_point = (1.0,0.0),
            anchored_position = (config['matrix_width'],0),
            font=config['font'],
            text=config['loading_min_text'])
        self.min_label.color = config['text_color']

        self.group = displayio.Group(x=0, y=y)
        self.group.append(self.line_rect)
        self.group.append(self.route_label)
        self.group.append(self.destination_label)
        self.group.append(self.min_label)

        parent_group.append(self.group)

    # show and hide a row on board
    def show(self):
        self.group.hidden = False

    def hide(self):
        self.group.hidden = True

    # lower level update functions
    def set_line_color(self, line_color: int):
        self.line_rect.fill = line_color

    def set_route(self, route: str):
        self.route_label.text = route[:3]

    def set_destination(self, destination: str):
        self.destination_label.text = ''  # setting destination to empty because the full destination makes the board
        # too busy. Considering adding an Inbound (I) Outbound (O) letter after route name instead
        # may add an option to add scrolling text later

    def set_arrival_time(self, minutes: str):
        minutes_len = len(minutes)

        # Left-padding the minutes label
        minutes = ' ' * (config['min_label_characters'] - minutes_len) + minutes

        self.min_label.text = minutes

    # high level update using above
    def update(self, line_color: int, route: str, destination: str, minutes: str):
        self.show()
        self.set_line_color(line_color)
        self.set_route(route)
        self.set_destination(destination)
        self.set_arrival_time(minutes)
