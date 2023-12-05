import itertools

import networkx as nx
from PySide2 import QtGui, QtCore, QtWidgets


class TopImage:

    def __init__(self, image: QtGui.QImage):
        self._density_dict: dict[tuple[int, int, int, int], tuple[str, int]] = {}
        self._graph = nx.Graph()
        self._image = image
        self._step_size = None

    @property
    def colors(self) -> tuple[tuple[int, int, int, int]]:
        return tuple(self._density_dict.keys())

    @property
    def image(self) -> QtGui.QImage:
        return self._image

    def read_edges(self, density_dict: dict[tuple[int, int, int, int], tuple[str, int]]):
        self._graph.clear_edges()
        self._density_dict = density_dict.copy()

        def get_density(s: tuple[int, int], t: tuple[int, int]) -> tuple[str, int]:
            return min(density_dict[self._graph.nodes[s]['color']], density_dict[self._graph.nodes[t]['color']],
                       key=lambda d: d[1])

        def get_star(s: tuple[int, int]) -> iter:
            return ((s, target, {'factor': factor, 'terrain': (d := get_density(s, target))[0],
                                 'weight': int(d[1] * factor)})
                    for (target, factor) in (
                ((s[0] + self._step_size, s[1]), 1),
                ((s[0], s[1] + self._step_size), 1),
                ((s[0] + self._step_size, s[1] + self._step_size), 1.5),
                ((s[0] + self._step_size, s[1] - self._step_size), 1.5),
            ))

        self._graph.add_edges_from(
            itertools.chain(*(get_star((i, j))
                              for i in range(self._step_size, self._image.width() - self._step_size - 1,
                                             self._step_size)
                              for j in range(self._step_size, self._image.height() - self._step_size - 1,
                                             self._step_size)))
        )

    def read_nodes(self, step_size: int = 1):
        self._graph.clear()
        self._step_size = step_size
        for i in range(0, self._image.width() - 1, step_size):
            for j in range(0, self._image.height() - 1, step_size):
                color = self._image.pixelColor(i, j).toTuple()
                if color not in self._density_dict:
                    self._density_dict[color] = ('', 0)
                self._graph.add_node((i, j), color=color)

    def read_path(self, source: tuple[int, int], target: tuple[int, int], pixel_length: float = 1.0,
                  rest: float = 0.0) -> dict[str, list[tuple[tuple[int, int], float, float, str]] | list[tuple[int, int]]]:
        node_list = nx.single_source_dijkstra(self._graph, source, target)[1]
        last_node = node_list[0]
        rests = []
        stages = []
        rest_distance = 0.0
        rest_cost = 0.0
        stage_distance = 0.0
        stage_cost = 0.0
        stage_terrain = self._density_dict[self._graph.nodes[last_node]['color']][0]
        for node in node_list[1:]:
            edge = self._graph.edges[(last_node, node)]
            distance = pixel_length * edge['factor'] * self._step_size
            cost = distance * edge['weight'] / edge['factor']
            terrain = edge['terrain']
            rest_distance += distance
            rest_cost += cost
            stage_distance += distance
            stage_cost += cost
            if rest and rest_cost >= rest:
                rests.append((node, rest_distance, rest_cost, terrain))
                rest_distance = 0.0
                rest_cost = 0.0
            if terrain != stage_terrain or node == node_list[-1]:
                stages.append((last_node, stage_distance, stage_cost, stage_terrain))
                stage_terrain = terrain
                stage_distance = 0.0
            last_node = node
        return {'rests': rests, 'stages': stages, 'nodes': node_list}

    @property
    def step_size(self) -> int:
        return self._step_size


class Cormyr(QtWidgets.QLabel):

    LOCATIONS = (('Arabel', (365, 270)),
                 ('Suzail', (250, 580)))

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        density_dict = {
            (129, 255, 0, 153): ('Untraveled plains, grassland, heath', 4),
            (150, 156, 24, 153): ('Desert sand', 12),
            (33, 178, 94, 153): ('Moor', 16),
            (99, 175, 89, 153): ('Marsh Swamp', 32),
            (137, 133, 126, 153): ('Mountains high', 32),
            (140, 83, 0, 153): ('Mountains medium', 24),
            (227, 156, 50, 153): ('Mountains low', 16),
            (255, 255, 255, 153): ('Clear Road or Trail', 2),
            (11, 119, 0, 153): ('Forest medium', 12),
            (255, 0, 0, 153): ('Forest Trail', 6),
            (22, 64, 223, 153): ('Water', 1000),
            (185, 166, 70, 153): ('Desert Rocky', 8),
            (234, 49, 255, 153): ('Mountain Trail', 12)
        }
        self.image = TopImage(QtGui.QImage('cormyr_main_top.bmp'))
        self.original_pixmap = QtGui.QPixmap('cormyr_main.png')
        self.setPixmap(self.original_pixmap)
        self.image.read_nodes(step_size=1)
        self.image.read_edges(density_dict=density_dict)


class Main(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('signal_flag_filled.png'))
        self.setWindowTitle('Pixelmap Cormyr')
        self.current_pixmap = QtGui.QPixmap(self.size())
        self.setStyleSheet('*{font-family: Roboto Slab; font-size: 10pt}')
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, False)
        self.setWindowFlag(QtCore.Qt.MSWindowsFixedSizeDialogHint, True)
        self.frame = QtWidgets.QFrame()
        self.setCentralWidget(self.frame)
        self.cormyr = Cormyr(self)

        input_layout = QtWidgets.QGridLayout()
        self.start_position_box = QtWidgets.QComboBox()
        self.end_position_box = QtWidgets.QComboBox()
        self.terrain_budget = QtWidgets.QComboBox()
        self.calculate_button = QtWidgets.QPushButton('Calculate')
        self.result_edit = QtWidgets.QTextEdit()
        self.result_edit.setReadOnly(True)
        self.start_position_label = QtWidgets.QLabel()
        self.end_position_label = QtWidgets.QLabel()
        self.start_position_label.setFixedWidth(70)
        self.start_position_box.setFixedWidth(200)
        for index, (text, widget) in enumerate((('Start:', self.start_position_box),
                                                ('Destination:', self.end_position_box),
                                                ('Daily Terrain Budget:', self.terrain_budget))):
            input_layout.addWidget(QtWidgets.QLabel(text), index, 0)
            input_layout.addWidget(widget, index, 1)
        for box in (self.start_position_box, self.end_position_box):
            for (name, pos) in Cormyr.LOCATIONS:
                box.addItem(name, pos)
            box.addItem('custom', None)
        for budget in range(1, 50):
            self.terrain_budget.addItem(str(budget), budget)
        input_layout.addWidget(self.calculate_button, 3, 0, 1, 3)
        input_layout.addWidget(self.result_edit, 4, 0, 1, 3)
        input_layout.addWidget(self.start_position_label, 0, 2)
        input_layout.addWidget(self.end_position_label, 1, 2)
        input_layout.setColumnStretch(0, 0)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 0)
        input_layout.setAlignment(QtCore.Qt.AlignTop)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(input_layout, stretch=0)
        layout.addWidget(self.cormyr, stretch=0)
        self.frame.setLayout(layout)
        self.start_position_box.setCurrentText('custom')
        self.end_position_box.setCurrentText('custom')
        self.terrain_budget.setCurrentText('24')

        self.start_position_box.currentIndexChanged.connect(
            lambda _: self.start_position_label.setText(str(p)) if
            (p := self.start_position_box.currentData(QtCore.Qt.UserRole)) else self.start_position_label.setText(''))
        self.end_position_box.currentIndexChanged.connect(
            lambda _: self.end_position_label.setText(str(p)) if
            (p := self.end_position_box.currentData(QtCore.Qt.UserRole)) else self.end_position_label.setText(''))
        self.start_position_box.currentIndexChanged.connect(lambda _: self.recalculate_states())
        self.end_position_box.currentIndexChanged.connect(lambda _: self.recalculate_states())
        self.recalculate_states()
        self.calculate_button.clicked.connect(self.calculate)
        self.cormyr.installEventFilter(self)

    def calculate(self):
        try:
            start_pos = eval(self.start_position_label.text())
            end_pos = eval(self.end_position_label.text())
        except SyntaxError:
            return

        budget = self.terrain_budget.currentData(QtCore.Qt.UserRole)
        data = self.cormyr.image.read_path(start_pos, end_pos, pixel_length=1/2.7,
                                           rest=budget * 4)

        rest_text = '<br >'.join(f'Day {index+1}: {terrain} for {distance:.2f} miles'
                                 for index, (position, distance, _, terrain) in enumerate(data['rests']))
        stages_text = '<br >'.join(f'{terrain} for {distance:.2f} miles' for _, distance, _, terrain in data['stages'])
        text = f'''<b>Start:</b>\t\t {start_pos}<br >
        <b>End:</b>\t\t {end_pos}<br >
        <b>Terrain Budget per Day:</b>\t\t {budget}<br >
        <b>Total Distance:</b> {sum(stage[1] for stage in data['stages']):.2f} miles <br >
        <b>Arrival:</b> on Day {len(data["rests"]) + 1}
        <br ><br >
        <b>Stages:</b><br >
        {stages_text}
        <br ><br >
        <b>Travel Days:</b><br >
        {rest_text}
        '''
        self.result_edit.setHtml(text)
        self.current_pixmap = self.cormyr.original_pixmap.copy()
        painter = QtGui.QPainter(self.current_pixmap)
        pen = QtGui.QPen(QtGui.Qt.red, 3, QtGui.Qt.SolidLine, QtGui.Qt.RoundCap, QtGui.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setRenderHint(painter.Antialiasing, True)
        for last_node, node in itertools.pairwise(data['nodes']):
            painter.drawLine(*last_node, *node)
        tent = QtGui.QImage('tent_filled.png').scaled(20, 20, QtGui.Qt.KeepAspectRatio)
        for (x, y), *_ in data['rests']:
            painter.drawImage(x - 10, y - 10, tent)
        self.cormyr.setPixmap(self.current_pixmap)

    def eventFilter(self, watched: QtWidgets.QWidget, event: QtCore.QEvent) -> bool:
        if watched == self.cormyr:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.map_menu(event)
                return True
        return super().eventFilter(watched, event)

    def map_menu(self, event: QtCore.QEvent.ContextMenu):
        menu = QtWidgets.QMenu(self)
        position = str(tuple(map(lambda c: c - c % self.cormyr.image.step_size, event.pos().toTuple())))
        start_action = QtWidgets.QAction(QtGui.QIcon('signal_flag.png'), 'Start Here', self)
        start_action.triggered.connect(lambda:
                                       (self.start_position_box.setCurrentText('custom'),
                                        self.start_position_label.setText(position),
                                        self.recalculate_states()))
        end_action = QtWidgets.QAction(QtGui.QIcon('signal_flag_checkered.png'), 'Destination Here', self)
        end_action.triggered.connect(lambda:
                                     (self.end_position_box.setCurrentText('custom'),
                                      self.end_position_label.setText(position),
                                      self.recalculate_states()))
        menu.addActions([start_action, end_action])
        menu.popup(event.globalPos())

    def recalculate_states(self):
        try:
            start_pos = eval(self.start_position_label.text())
        except SyntaxError:
            start_pos = None
        try:
            end_pos = eval(self.end_position_label.text())
        except SyntaxError:
            end_pos = None
        enabled = bool(start_pos and end_pos and start_pos != end_pos)
        self.current_pixmap = self.cormyr.original_pixmap.copy()
        painter = QtGui.QPainter(self.current_pixmap)
        if start_pos:
            flag = QtGui.QImage('signal_flag_filled.png').scaled(20, 20, QtGui.Qt.KeepAspectRatio)
            painter.drawImage(start_pos[0] - 10, start_pos[1] - 10, flag)
        if end_pos:
            flag = QtGui.QImage('signal_flag_checkered_filled.png').scaled(20, 20, QtGui.Qt.KeepAspectRatio)
            painter.drawImage(end_pos[0] - 10, end_pos[1] - 10, flag)

        self.calculate_button.setEnabled(enabled)
        self.cormyr.setPixmap(self.current_pixmap)


app = QtWidgets.QApplication()
main = Main()
main.show()
app.exec_()
