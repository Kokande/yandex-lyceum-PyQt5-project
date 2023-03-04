import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTableWidgetItem
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5 import uic
import sqlite3
import random
import csv
import datetime


class Entity:
    def __init__(self, coords):
        self.coords = coords

    def get_coords(self):
        return self.coords

    def move(self, x, y):
        self.coords = (self.coords[0] + x, self.coords[1] + y)


class App(QMainWindow):
    def __init__(self, victory, GO):
        super().__init__()
        uic.loadUi("Game.ui", self)
        self.victory = victory
        self.name = 'name'
        self.GO = GO
        self.initUI()

    def initUI(self):
        self.map_path = sqlite3.connect('map.db')
        self.mapDialog = SaveDialog(self)

    def load_tile(self, coords):
        if coords == (47, 40):
            return "pngs/verysuspicioustile.png"
        entity = self.map_path.cursor().execute("""SELECT entity FROM tiles
                                                   WHERE column = ? AND row = ?""",
                                                coords).fetchone()
        name = self.map_path.cursor().execute("""SELECT type FROM tiles 
                                                 WHERE column = ? AND row = ?""",
                                              coords).fetchone()
        if name is None:
            name = (None,)
        if entity is None:
            entity = (None,)
        return NAMES_OF_PNGs[name[0]] if entity[0] is None else NAMES_OF_PNGs[entity[0]]

    def victory_screen(self):
        self.records = {'place': [], 'date': [], 'score': [], 'name': []}
        for i in csv.DictReader(open("records.rec"), delimiter=';'):
            for k in dict(i):
                self.records[k].append(dict(i)[k])
        self.records['place'].append(0)
        self.records['date'].append(datetime.datetime.now().date())
        self.records['score'].append(self.tile_96.text())
        self.records['name'].append(self.name)
        order = [i for i in range(len(self.records['score']))]
        order = list(sorted(order, key=lambda x: int(self.records['score'][x])))
        for i in self.records:
            old = [i for i in self.records[i]]
            self.records[i] = [old[k] for k in order]
        writer = csv.writer(open("records.rec", 'w', newline=''), delimiter=';')
        writer.writerow(['place', 'date', 'score', 'name'])
        for i in range(15):
            if len(self.records['score']) < i + 1:
                break
            writer.writerow([i + 1, self.records['date'][i],
                             self.records['score'][i], self.records['name'][i]])
        self.victory.show()
        self.map_path.cursor().execute("""UPDATE tiles SET entity = 'ended' 
                                          WHERE type = 'status'""")
        self.map_path.commit()
        self.close()

    def get_coords_from_db(self, obj):
        return tuple(self.map_path.cursor().execute("""SELECT column, row FROM tiles 
                                                       WHERE entity = ?""",
                                                    (obj,)).fetchall()[0])

    def delete_entity(self, entity):
        self.map_path.cursor().execute("""UPDATE tiles SET entity = NULL 
                                          WHERE column = ? AND row = ?""",
                                       entity.get_coords())

    def place_entity(self, entity):
        if entity == self.hero:
            for i in self.enemies:
                if entity.get_coords() == i.get_coords():
                    self.GO_screen()
            for i in self.obstacles:
                if entity.get_coords() == i.get_coords():
                    self.obstacle_touched(self.map_path.cursor(
                    ).execute("""SELECT entity FROM tiles WHERE column = ? AND row = ?""",
                              i.get_coords()).fetchone()[0])
            self.map_path.cursor().execute("""UPDATE tiles SET entity = 'hero'
                                              WHERE column = ? AND row = ?""",
                                           entity.get_coords())
        else:
            self.map_path.cursor().execute("""UPDATE tiles SET entity = ?
                                              WHERE column = ? AND row = ?""",
                                           ('enemy' + str(self.enemies.index(entity) + 1),
                                            entity.get_coords()[0],
                                            entity.get_coords()[1]))

    def GO_screen(self):
        self.GO.show()
        self.map_path.cursor().execute("""UPDATE tiles SET entity = 'ended' 
                                          WHERE type = 'status'""")
        self.map_path.commit()
        self.close()

    def tile_available(self, coords):
        if 0 <= coords[0] < 64 and 0 <= coords[1] < 64:
            tile_check = self.map_path.cursor().execute("""SELECT entity FROM tiles 
                                                           WHERE column = ? AND row = ?""",
                                                        coords).fetchone()
            if tile_check is None or tile_check == (None,):
                return True
        return False

    def enemy_move(self):
        for i in self.enemies:
            starting_coords = i.get_coords()
            move_priorities = random.sample([(0, -1), (0, 1),
                                             (-1, 0), (1, 0)], 4)  # вверх, вниз, влево, вправо
            for k in move_priorities:
                new_coords = (starting_coords[0] + k[0], starting_coords[1] + k[1])
                if self.tile_available(new_coords):
                    self.delete_entity(i)
                    i.move(k[0], k[1])
                    self.place_entity(i)
                    self.map_path.commit()
                    break
                elif self.hero.get_coords() == new_coords:
                    self.GO_screen()

    def save_result(self, res):
        self.map_path.cursor().execute("""UPDATE tiles SET column = ?
                                          WHERE type = 'status'""", (res,))

    def map_load(self, direction='starting'):
        if direction == 'starting':
            self.hero = Entity(self.get_coords_from_db('hero'))
            self.screen = [[], [], [], [], [], [], [], []]
            self.obstacles = [Entity(self.get_coords_from_db('obstacle1')),
                              Entity(self.get_coords_from_db('obstacle2')),
                              Entity(self.get_coords_from_db('obstacle3'))]
            self.enemies = [Entity(self.get_coords_from_db('enemy1')),
                            Entity(self.get_coords_from_db('enemy2')),
                            Entity(self.get_coords_from_db('enemy3')),
                            Entity(self.get_coords_from_db('enemy4')),
                            Entity(self.get_coords_from_db('enemy5'))]
            for k in range(-3, 5):
                for i in range(-5, 7):
                    self.screen[k + 3].append(eval('self.tile_%s' %
                                                   str(i + 6 + 12 * (k + 4 - 1))))
                    if 0 <= self.hero.get_coords()[0] + i < 64 and \
                            0 <= self.hero.get_coords()[1] + k < 64\
                            or (k == 4 and i == 6):
                        if k == 4 and i == 6:
                            self.screen[7][11].setText(str(self.map_path.cursor(
                            ).execute("""SELECT column FROM tiles 
                                         WHERE type = 'status'""").fetchone()[0]))
                            break
                        if i == 0 and k == 0:
                            self.screen[k + 3][i + 5].setPixmap(QPixmap(
                                NAMES_OF_PNGs['hero']))
                        elif (self.hero.get_coords()[0] + i,
                              self.hero.get_coords()[1] + k) in [j.get_coords()
                                                                 for j in self.obstacles]:
                            self.screen[k + 3][i + 5].setPixmap(QPixmap(self.load_tile((
                                self.hero.get_coords()[0] + i,
                                self.hero.get_coords()[1] + k))))
                        else:
                            self.screen[k + 3][i + 5].setPixmap(QPixmap(
                                self.load_tile((self.hero.get_coords()[0] + i,
                                                self.hero.get_coords()[1] + k))))
                    else:
                        self.screen[k + 3][i + 5].setPixmap(QPixmap(NAMES_OF_PNGs['void']))
        else:
            if direction == 'Down' and self.hero.get_coords()[1] + 1 < 64:
                self.delete_entity(self.hero)
                self.hero.move(0, 1)
                self.place_entity(self.hero)
            elif direction == 'Up' and self.hero.get_coords()[1] - 1 >= 0:
                self.delete_entity(self.hero)
                self.hero.move(0, -1)
                self.place_entity(self.hero)
            elif direction == 'Right' and self.hero.get_coords()[0] + 1 < 64:
                self.delete_entity(self.hero)
                self.hero.move(1, 0)
                self.place_entity(self.hero)
            elif direction == 'Left' and self.hero.get_coords()[0] - 1 >= 0:
                self.delete_entity(self.hero)
                self.hero.move(-1, 0)
                self.place_entity(self.hero)
            self.screen[7][11].setText(str(int(self.screen[7][11].text()) + 1))
            self.save_result(self.screen[7][11].text())
            self.enemy_move()
            self.map_path.commit()
            self.check_for_events()
            for k in range(-3, 5):
                for i in range(-5, 7):
                    if 0 <= self.hero.get_coords()[0] + i < 64 and \
                            0 <= self.hero.get_coords()[1] + k < 64 or (k == 4 and i == 6):
                        if k == 4 and i == 6:
                            break
                        if not k == i == 0:
                            self.screen[k + 3][i + 5].setPixmap(QPixmap(self.load_tile(
                                (self.hero.get_coords()[0] + i,
                                 self.hero.get_coords()[1] + k))))
                    else:
                        self.screen[k + 3][i + 5].setPixmap(QPixmap(NAMES_OF_PNGs['void']))

    def keyPressEvent(self, event):
        if not self.map_path.cursor().execute("""SELECT entity FROM tiles
                                                 WHERE type = 'status'""").fetchone()[0] == \
               'ended':
            if event.key() == Qt.Key_Up:
                self.map_load('Up')
            elif event.key() == Qt.Key_Left:
                self.map_load('Left')
            elif event.key() == Qt.Key_Right:
                self.map_load('Right')
            elif event.key() == Qt.Key_Down:
                self.map_load('Down')

    def closeEvent(self, event):
        self.mapDialog.close()

    def check_for_events(self):
        goal_coords = self.map_path.cursor().execute("""SELECT column, row FROM tiles
                                                        WHERE type = 'goal'""").fetchall()[0]
        if self.hero.get_coords() == goal_coords:
            self.victory_screen()

    def obstacle_touched(self, obstacle):
        self.map_path.cursor().execute("""UPDATE tiles SET entity = 'ended' 
                                          WHERE type = 'status'""")
        self.map_path.commit()
        if obstacle == 'obstacle1':
            raise SyntaxError("don't mess with syntax")
        elif obstacle == 'obstacle2':
            raise RuntimeError("WCGW?")
        else:
            raise MemoryError("That's not a real error")


class SaveDialog(QWidget):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.manually_closed = False
        uic.loadUi("Save.ui", self)
        self.records = None
        self.initUI()

    def initUI(self):
        if self.game.map_path.cursor().execute(
                """SELECT entity FROM tiles
                WHERE type = 'status'""").fetchone()[0] == \
                'ended':
            self.btn_yes.setEnabled(False)
        self.btn_yes.clicked.connect(self.load_old_map)
        self.btn_no.clicked.connect(self.make_new_map)
        self.rec.clicked.connect(self.show_records)

    def load_old_map(self):
        self.game.map_load()
        self.manually_closed = True
        self.game.name = self.name.text()
        self.close()

    def closeEvent(self, event):
        if not self.manually_closed:
            if self.records is not None:
                self.records.close()
            self.game.close()

    def update_bd_entity(self, entity, coords):
        self.game.map_path.cursor().execute("""UPDATE tiles SET entity = ? 
                                               WHERE column = ? AND row = ?""",
                                            (entity, coords[0], coords[1]))

    def show_records(self):
        self.records = RecordsTable()
        self.records.show()

    def make_new_map(self):
        self.manually_closed = True
        x_s = random.sample(range(0, 64), 10)
        y_s = random.sample(range(0, 64), 10)
        hero, princess, o1, o2, o3, e1, e2, e3, e4, e5 = [(x_s[i], y_s[i])
                                                          for i in range(10)]
        self.game.map_path.cursor().execute("""UPDATE tiles SET entity = 'in_progress' 
                                               WHERE type = 'status'""")
        for i in range(64):
            for k in range(64):
                if self.game.map_path.cursor().execute("""SELECT type FROM tiles 
                                                          WHERE column = ? AND row = ?""",
                                                       (i, k)).fetchone() is None:
                    self.game.map_path.cursor().execute("""INSERT INTO tiles(column,row)
                                                           VALUES(?,?)""", (i, k))
                    self.game.map_path.commit()
                self.game.map_path.cursor().execute("""UPDATE tiles SET type = ?
                                                       WHERE column = ? AND row = ?""",
                                                    (random.choice(['type1', 'type2',
                                                                    'type1', 'type1',
                                                                    None, None,
                                                                    None, None,
                                                                    None, None,
                                                                    None, None]),
                                                     i, k))
                self.game.map_path.cursor().execute("""UPDATE tiles SET entity = ?
                                                       WHERE column = ? AND row = ?""",
                                                    (None, i, k))
        self.game.map_path.cursor().execute("""UPDATE tiles SET type = ? 
                                               WHERE column = ? AND row = ?""",
                                            ('goal', princess[0], princess[1]))
        self.update_bd_entity('hero', hero)
        self.update_bd_entity('obstacle1', o1)
        self.update_bd_entity('obstacle2', o2)
        self.update_bd_entity('obstacle3', o3)
        self.update_bd_entity('enemy1', e1)
        self.update_bd_entity('enemy2', e2)
        self.update_bd_entity('enemy3', e3)
        self.update_bd_entity('enemy4', e4)
        self.update_bd_entity('enemy5', e5)
        self.game.map_path.cursor().execute("""UPDATE tiles SET column = 0 
                                               WHERE type = 'status'""")
        self.game.map_path.commit()
        self.game.map_load()
        self.game.name = self.name.text()
        self.close()


class VictoryScreen(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("Victory.ui", self)
        self.img.setPixmap(QPixmap("pngs/victory.png"))


class GOScreen(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("go.ui", self)
        self.img.setPixmap(QPixmap("pngs/go.png"))
        self.setWindowTitle('Поражение')


NAMES_OF_PNGs = {None: "pngs/defaulttile.png", 'type1': "pngs/type1.png",
                 'type2': "pngs/type2.png", 'goal': "pngs/princess.png",
                 'void': "pngs/sea.png", 'hero': "pngs/hero.png",
                 'obstacle1': "pngs/obstacle1.png", 'obstacle2': "pngs/obstacle2.png",
                 'obstacle3': "pngs/obstacle3.png", 'enemy1': "pngs/enemy.png",
                 'enemy2': "pngs/enemy.png", 'enemy3': "pngs/enemy.png",
                 'enemy4': "pngs/enemy.png", 'enemy5': "pngs/enemy.png"}


class RecordsTable(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("records.ui", self)
        self.initUI()

    def initUI(self):
        for i in csv.DictReader(open("records.rec"), delimiter=';'):
            self.tableWidget.setItem(int(dict(i)['place']) - 1,
                                     0, QTableWidgetItem(dict(i)['date']))
            self.tableWidget.setItem(int(dict(i)['place']) - 1,
                                     1, QTableWidgetItem(dict(i)['score']))
            self.tableWidget.setItem(int(dict(i)['place']) - 1,
                                     2, QTableWidgetItem(dict(i)['name']))


if __name__ == '__main__':
    app = QApplication([])
    victory = VictoryScreen()
    go = GOScreen()
    ex = App(victory, go)
    ex.show()
    ex.mapDialog.show()
    sys.exit(app.exec())