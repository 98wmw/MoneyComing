
import math
import random
import sys
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPointF, QRectF,
    QSequentialAnimationGroup, QPropertyAnimation,
    QTimer, Qt, Property
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget


def resource_path(relative):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / relative)


class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.base_pixmap = QPixmap(resource_path("assets/shiba.png"))
        if self.base_pixmap.isNull():
            raise RuntimeError("无法加载柴犬图片")

        self.scale_factor = 0.36
        self.min_scale = 0.18
        self.max_scale = 0.75
        self.topmost = True

        self.dragging = False
        self.drag_offset = QPoint()
        self.press_pos = QPoint()
        self.has_moved = False

        self.anim_dx = 0.0
        self.anim_dy = 0.0
        self.anim_sy = 1.0
        self.anim_rotation = 0.0
        self.breath_phase = 0.0
        self.blink_amount = 0.0
        self.expression = "normal"
        self.interaction_index = 0

        self.bubble_text = ""
        self.bubble_visible = False

        self.setWindowTitle("柴犬桌宠")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint
        )
        self.setMouseTracking(True)
        self.update_window_size()

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 25,
                  screen.bottom() - self.height() - 25)

        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.on_frame)
        self.frame_timer.start(16)

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.start_blink)
        self.blink_timer.start(random.randint(2500, 5000))

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.idle_action)
        self.idle_timer.start(6500)

        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.hide_bubble)

        self.setup_tray()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon(resource_path("assets/shiba_icon.png")), self)
        menu = QMenu()
        menu.addAction("显示桌宠").triggered.connect(self.showNormal)
        top_action = menu.addAction("始终置顶")
        top_action.setCheckable(True)
        top_action.setChecked(True)
        top_action.triggered.connect(self.toggle_topmost)
        menu.addSeparator()
        menu.addAction("退出").triggered.connect(QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("柴犬桌宠")
        self.tray.show()

    def update_window_size(self):
        self.dog_w = max(150, int(self.base_pixmap.width() * self.scale_factor))
        self.dog_h = max(170, int(self.base_pixmap.height() * self.scale_factor))
        self.resize(self.dog_w + 60, self.dog_h + 122)
        self.update()

    def on_frame(self):
        self.breath_phase += 0.035
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing
        )

        cx = self.width() / 2 + self.anim_dx
        dog_top = 92 + self.anim_dy
        breath = 1.0 + 0.009 * math.sin(self.breath_phase)
        sx = breath
        sy = self.anim_sy / max(0.98, breath)

        p.save()
        p.translate(cx, dog_top + self.dog_h / 2)
        p.rotate(self.anim_rotation)
        p.scale(sx, sy)
        target = QRectF(-self.dog_w / 2, -self.dog_h / 2,
                        self.dog_w, self.dog_h)
        p.drawPixmap(target, self.base_pixmap, QRectF(self.base_pixmap.rect()))
        self.draw_blink(p)
        self.draw_happy_cheeks(p)
        p.restore()

        if self.bubble_visible:
            self.draw_bubble(p)

    def draw_blink(self, p):
        if self.blink_amount <= 0.01:
            return

        # 针对用户提供的柴犬照片绘制眼睑。
        # 这是覆盖动画，不会修改原图，也不会抠掉眼睛。
        eyes = [
            (0.668, 0.270, 0.078),
            (0.840, 0.262, 0.074),
        ]
        lid_color = QColor(104, 76, 55, 248)
        line_color = QColor(42, 31, 25, 220)

        for nx, ny, nw in eyes:
            x = -self.dog_w / 2 + nx * self.dog_w
            y = -self.dog_h / 2 + ny * self.dog_h
            ww = nw * self.dog_w
            hh = max(2.0, 0.026 * self.dog_h * self.blink_amount)

            path = QPainterPath()
            path.moveTo(x - ww / 2, y)
            path.quadTo(x, y + hh * 1.35, x + ww / 2, y)
            path.quadTo(x, y - hh * 0.20, x - ww / 2, y)
            p.fillPath(path, lid_color)

            p.setPen(line_color)
            p.drawArc(QRectF(x - ww / 2, y - hh * 0.15, ww, hh * 1.15),
                      190 * 16, 160 * 16)

    def draw_happy_cheeks(self, p):
        if self.expression != "happy":
            return
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 165, 175, 150))
        for nx in (0.68, 0.895):
            x = -self.dog_w / 2 + nx * self.dog_w
            y = -self.dog_h / 2 + 0.405 * self.dog_h
            p.drawEllipse(QPointF(x, y),
                          0.018 * self.dog_w,
                          0.010 * self.dog_h)

    def draw_bubble(self, p):
        font = QFont("Microsoft YaHei UI", 12)
        font.setBold(True)
        p.setFont(font)
        fm = p.fontMetrics()
        bw = min(self.width() - 20,
                 max(140, fm.horizontalAdvance(self.bubble_text) + 36))
        bh = 56
        bx = (self.width() - bw) / 2
        by = 8

        path = QPainterPath()
        path.addRoundedRect(QRectF(bx, by, bw, bh), 18, 18)
        tail_x = min(bx + bw - 34, self.width() / 2 + 28)
        path.moveTo(tail_x - 11, by + bh - 2)
        path.lineTo(tail_x + 8, by + bh + 18)
        path.lineTo(tail_x + 12, by + bh - 2)
        path.closeSubpath()

        p.setPen(QColor(70, 70, 70, 230))
        p.setBrush(QColor(255, 255, 255, 248))
        p.drawPath(path)
        p.setPen(QColor(30, 30, 30))
        p.drawText(QRectF(bx + 12, by, bw - 24, bh),
                   Qt.AlignCenter, self.bubble_text)

    def start_blink(self):
        self.blink_timer.start(random.randint(2600, 5200))
        close_anim = QPropertyAnimation(self, b"blinkValue")
        close_anim.setDuration(90)
        close_anim.setStartValue(0.0)
        close_anim.setEndValue(1.0)
        close_anim.setEasingCurve(QEasingCurve.InQuad)

        open_anim = QPropertyAnimation(self, b"blinkValue")
        open_anim.setDuration(120)
        open_anim.setStartValue(1.0)
        open_anim.setEndValue(0.0)
        open_anim.setEasingCurve(QEasingCurve.OutQuad)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(close_anim)
        group.addAnimation(open_anim)
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def idle_action(self):
        if self.dragging:
            return
        random.choice([self.head_tilt, self.soft_bounce, self.start_blink])()
        if random.random() < 0.35:
            self.show_bubble(random.choice([
                "偷偷看你一眼～",
                "今天也要开心呀！",
                "汪！",
                "摸摸我嘛～",
                "休息一下吧！",
                "我一直在这里。"
            ]))
        self.idle_timer.start(random.randint(5500, 9500))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = True
            self.press_pos = e.globalPosition().toPoint()
            self.drag_offset = self.press_pos - self.frameGeometry().topLeft()
            self.has_moved = False
            e.accept()
        elif e.button() == Qt.RightButton:
            self.show_context_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self.dragging and (e.buttons() & Qt.LeftButton):
            gp = e.globalPosition().toPoint()
            if (gp - self.press_pos).manhattanLength() > 4:
                self.has_moved = True
            self.move(gp - self.drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            was_click = self.dragging and not self.has_moved
            self.dragging = False
            if was_click:
                self.play_next_interaction()
            e.accept()

    def wheelEvent(self, e):
        old_center = self.geometry().center()
        delta = 0.035 if e.angleDelta().y() > 0 else -0.035
        self.scale_factor = max(
            self.min_scale,
            min(self.max_scale, self.scale_factor + delta)
        )
        self.update_window_size()
        self.move(old_center - self.rect().center())

    def show_context_menu(self, pos):
        menu = QMenu(self)
        size_menu = menu.addMenu("调整大小")
        for label, value in [
            ("小", 0.24),
            ("中", 0.36),
            ("大", 0.50),
            ("特大", 0.65)
        ]:
            action = size_menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, v=value: self.set_scale(v)
            )

        top_action = menu.addAction("始终置顶")
        top_action.setCheckable(True)
        top_action.setChecked(self.topmost)
        top_action.triggered.connect(self.toggle_topmost)

        menu.addAction("眨眨眼").triggered.connect(self.start_blink)
        menu.addAction("开心一下").triggered.connect(self.happy_bounce)
        menu.addSeparator()
        menu.addAction("退出程序").triggered.connect(QApplication.quit)
        menu.exec(pos)

    def set_scale(self, value):
        old_center = self.geometry().center()
        self.scale_factor = value
        self.update_window_size()
        self.move(old_center - self.rect().center())

    def toggle_topmost(self, checked):
        self.topmost = checked
        flags = Qt.FramelessWindowHint | Qt.Tool
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def play_next_interaction(self):
        actions = [
            self.jump,
            self.squash,
            self.shake,
            self.happy_bounce,
            self.head_tilt
        ]
        actions[self.interaction_index % len(actions)]()
        self.interaction_index += 1
        self.show_bubble(random.choice([
            "嘿嘿，被你发现啦！",
            "主人好呀～",
            "再摸一下！",
            "今天也超喜欢你！",
            "汪汪！",
            "一起偷个懒吧～",
            "我是不是很可爱？",
            "别忘了喝水哦！"
        ]))

    def show_bubble(self, text):
        self.bubble_text = text
        self.bubble_visible = True
        self.bubble_timer.start(2200)
        self.update()

    def hide_bubble(self):
        self.bubble_visible = False
        self.update()

    def animation(self, prop, start, end, duration, easing=QEasingCurve.OutCubic):
        anim = QPropertyAnimation(self, prop)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing)
        return anim

    def jump(self):
        group = QSequentialAnimationGroup(self)
        group.addAnimation(self.animation(
            b"offsetY", 0.0, -48.0, 180, QEasingCurve.OutQuad
        ))
        group.addAnimation(self.animation(
            b"offsetY", -48.0, 0.0, 260, QEasingCurve.OutBounce
        ))
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def squash(self):
        group = QSequentialAnimationGroup(self)
        group.addAnimation(self.animation(
            b"scaleY", 1.0, 0.72, 110, QEasingCurve.InQuad
        ))
        group.addAnimation(self.animation(
            b"scaleY", 0.72, 1.14, 150, QEasingCurve.OutBack
        ))
        group.addAnimation(self.animation(
            b"scaleY", 1.14, 1.0, 160
        ))
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def shake(self):
        group = QSequentialAnimationGroup(self)
        current = 0.0
        for target in [-14, 14, -11, 11, -7, 7, 0]:
            group.addAnimation(self.animation(
                b"offsetX", current, float(target), 55, QEasingCurve.Linear
            ))
            current = float(target)
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def head_tilt(self):
        group = QSequentialAnimationGroup(self)
        group.addAnimation(self.animation(b"rotation", 0.0, -7.0, 220))
        group.addAnimation(self.animation(b"rotation", -7.0, 6.0, 320))
        group.addAnimation(self.animation(b"rotation", 6.0, 0.0, 240))
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def soft_bounce(self):
        group = QSequentialAnimationGroup(self)
        group.addAnimation(self.animation(b"offsetY", 0.0, -12.0, 220))
        group.addAnimation(self.animation(b"offsetY", -12.0, 0.0, 260))
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def happy_bounce(self):
        self.expression = "happy"
        self.update()
        group = QSequentialAnimationGroup(self)
        group.addAnimation(self.animation(b"offsetY", 0.0, -28.0, 150))
        group.addAnimation(self.animation(
            b"offsetY", -28.0, 0.0, 220, QEasingCurve.OutBounce
        ))
        group.addAnimation(self.animation(b"rotation", 0.0, -5.0, 100))
        group.addAnimation(self.animation(b"rotation", -5.0, 5.0, 160))
        group.addAnimation(self.animation(b"rotation", 5.0, 0.0, 120))
        group.finished.connect(self.clear_expression)
        group.start(QSequentialAnimationGroup.DeleteWhenStopped)

    def clear_expression(self):
        self.expression = "normal"
        self.update()

    def get_offset_x(self):
        return self.anim_dx

    def set_offset_x(self, value):
        self.anim_dx = float(value)
        self.update()

    offsetX = Property(float, get_offset_x, set_offset_x)

    def get_offset_y(self):
        return self.anim_dy

    def set_offset_y(self, value):
        self.anim_dy = float(value)
        self.update()

    offsetY = Property(float, get_offset_y, set_offset_y)

    def get_scale_y(self):
        return self.anim_sy

    def set_scale_y(self, value):
        self.anim_sy = float(value)
        self.update()

    scaleY = Property(float, get_scale_y, set_scale_y)

    def get_rotation(self):
        return self.anim_rotation

    def set_rotation(self, value):
        self.anim_rotation = float(value)
        self.update()

    rotation = Property(float, get_rotation, set_rotation)

    def get_blink(self):
        return self.blink_amount

    def set_blink(self, value):
        self.blink_amount = float(value)
        self.update()

    blinkValue = Property(float, get_blink, set_blink)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("柴犬桌宠")
    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())
