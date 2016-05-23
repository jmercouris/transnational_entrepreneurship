import networkx as nx
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.properties import DictProperty, StringProperty, ObjectProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.core.window import Window
from graph.graph import get_statuses_for_screen_name, load_graph_from_database
from kivy.uix.stencilview import StencilView
from kivy.metrics import dp
from math import pow


class NetworktUI(Widget):
    def __init__(self, **kwargs):
        super(NetworktUI, self).__init__()
        self.network = self.ids.network
    
    def update(self, dt):
        self.network.update_logic()
        self.network.update()


class ScrollableLabel(ScrollView):
    text = StringProperty('')


class Inspector(ScrollableLabel):
    selected_node = ObjectProperty(None)
    
    def on_selected_node(self, *args):
        pass


class Statuses(ScrollableLabel):
    selected_node = ObjectProperty(None)
    
    def on_selected_node(self, *args):
        pass


class Camera(object):
    """Documentation for Camera
    
    """
    def __init__(self, **kwargs):
        super(Camera, self).__init__()
        self.position = (0, 0)
        self.zoom = 250
        self.move_speed = 10
        self.zoom_factor = 10
    
    def camera_up(self):
        self.position = (self.position[0], self.position[1] + self.move_speed)
    
    def camera_down(self):
        self.position = (self.position[0], self.position[1] - self.move_speed)
    
    def camera_left(self):
        self.position = (self.position[0] - self.move_speed, self.position[1])
    
    def camera_right(self):
        self.position = (self.position[0] + self.move_speed, self.position[1])
    
    def camera_zoom_in(self):
        self.zoom = self.zoom + self.zoom_factor
    
    def camera_zoom_out(self):
        self.zoom = self.zoom - self.zoom_factor


class Network(StencilView):
    """Extends Stencilview to clip drawing to bounding box
    
    
    """
    nodes = DictProperty({})
    selected_node = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(Network, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self, 'text')
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.camera = Camera()
    
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None
        
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if (text == 'w'):
            self.camera.camera_down()
            self.update_node_positions()
            return True
        elif (text == 'a'):
            self.camera.camera_right()
            self.update_node_positions()
            return True
        elif (text == 's'):
            self.camera.camera_up()
            self.update_node_positions()
            return True
        elif (text == 'd'):
            self.camera.camera_left()
            self.update_node_positions()
            return True
        elif (text == 'e'):
            self.camera.camera_zoom_in()
            self.update_node_positions()
            return True
        elif (text == 'q'):
            self.camera.camera_zoom_out()
            self.update_node_positions()
            return True
        
        return False
    
    def on_touch_up(self, touch):
        for node in self.nodes:
            nodei = self.nodes[node]
            # (R0-R1)^2 <= (x0-x1)^2+(y0-y1)^2 <= (R0+R1)^2
            squared_x = pow((touch.x - nodei.render_position[0]), 2)
            squared_y = pow((touch.y - nodei.render_position[1]), 2)
            squared_radius = pow(nodei.radius, 2)
            if (squared_radius > squared_x + squared_y):
                self.selected_node = nodei
    
    def update_node_positions(self):
        for node in self.nodes:
            nodei = self.nodes[node]
            nodei.render_position = self.translate_render(nodei.position)
        self.update()
    
    def translate_render(self, position):
        position = (int(position[0] * self.camera.zoom) + 50, int(position[1] * self.camera.zoom) + 200)
        position = (position[0] + self.camera.position[0], position[1] + self.camera.position[1])
        position = (dp(position[0]), dp(position[1]))
        return position
    
    def update(self):
        self.canvas.clear()
        with self.canvas:
            Color(0, 1, 0)
            for node in self.nodes:
                nodei = self.nodes[node]
                # Draw All Nodes
                Line(circle=(nodei.render_position[0], nodei.render_position[1], dp(nodei.radius)))
                # Draw All Edges
                for edge in nodei.edges:
                    Line(points=(nodei.render_position[0], nodei.render_position[1],
                                 edge.render_position[0], edge.render_position[1]))
                # Draw All Statuses
                for status in nodei.active_statuses:
                    Line(circle=(status.render_position[0], status.render_position[1], dp(status.radius)))
    
    def update_logic(self):
        for node in self.nodes:
            nodei = self.nodes[node]
            for status in nodei.active_statuses:
                status.act()
    
    def on_selected_node(self, *args):
        for edge in self.selected_node.edges:
            tmp_message = Status(self.selected_node, edge, 'message')
            self.selected_node.active_statuses.append(tmp_message)
    
    def on_nodes(self, *args):
        self.update()


class NetworktApp(App):
    nodes = DictProperty({})
    
    def build(self):
        self.networktUI = NetworktUI()
        self.load_graph()
        Clock.schedule_interval(self.networktUI.update, 1.0 / 30.0)
        network = self.networktUI.ids.network
        network.update_node_positions()
        return self.networktUI
    
    def load_graph(self):
        # Generate a simple graph
        self.nodes = {}
        root_user = 'FactoryBerlin'
        graph = load_graph_from_database(root_user)
        layout = nx.spring_layout(graph)
        # Generate the list of nodes with positions
        for node in layout:
            nodei = Node(graph.node[node])
            nodei.position = layout[node]
            nodei.statuses = get_statuses_for_screen_name(nodei.screen_name)
            self.nodes[nodei.screen_name] = nodei
        # Add edges to every node in graph
        for edge in graph.edges():
            self.nodes[edge[0]].edges.append(self.nodes[edge[1]])
        # Invoke Update
        self.nodes['0'] = Node(graph.node[root_user])
        self.nodes.pop('0', 0)


class Node(object):
    """Documentation for Node
    
    """
    def __init__(self, dictionary):
        self.position = (0, 0)
        self.radius = 10.0
        self.render_position = (0, 0)
        self.edges = []
        self.created_at = dictionary.get('createdat', None)
        self.description = dictionary.get('description', None)
        self.favorites_count = int(dictionary.get('favouritescount') or -1)
        self.followers_count = int(dictionary.get('followerscount') or -1)
        self.friends_count = int(dictionary.get('friendscount') or -1)
        self.id_str = dictionary.get('idstr', None)
        self.lang = dictionary.get('lang', None)
        self.listed_count = int(dictionary.get('listedcount') or -1)
        self.location = dictionary.get('location', None)
        self.name = dictionary.get('name', None)
        self.screen_name = dictionary.get('screenname', 'default')
        self.statuses_count = int(dictionary.get('statusescount') or -1)
        self.statuses = []
        self.active_statuses = []
        self.time_zone = dictionary.get('timezone', None)
        self.utc_offset = int(dictionary.get('utcoffset') or -1)
        self.verified = bool(dictionary.get('verified', False) or False)
        self.id = int(self.id_str or -1)


class Status(object):
    """Documentation for Status
    
    """
    def __init__(self, sender, receiver, text):
        super(Status, self).__init__()
        self.sender = sender
        self.receiver = receiver
        self.text = text
        self.position = sender.render_position
        self.steps = 10
        self.radius = 5.0
        self.calculate_delta()
    
    def calculate_delta(self):
        self.delta_x = (self.receiver.render_position[0] - self.sender.render_position[0]) / self.steps
        self.delta_y = (self.receiver.render_position[1] - self.sender.render_position[1]) / self.steps
    
    def act(self):
        self.position = (self.position[0] + self.delta_x, self.position[1] + self.delta_y)
        self.render_position = (int(self.position[0]), int(self.position[1]))
        self.steps = self.steps - 1


if __name__ == '__main__':
    NetworktApp().run()
