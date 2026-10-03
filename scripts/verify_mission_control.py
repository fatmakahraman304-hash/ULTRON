"""Native mission control interaction checks and exact UHD render export."""
import os,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['MARK_SMOKE_SECONDS']='30'
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage,QPainter
from PyQt6.QtWidgets import QPushButton
import integration.panel
original=integration.panel.attach

def attach(ui):
    original(ui)
    def verify():
        mission=ui._mission
        assert ui._mission_stack.currentWidget() is mission
        assert not mission.plate.isNull()
        assert len(mission.findChildren(QPushButton))>=20
        mission.findChild(QPushButton,'mission-nav-browser').click()
        assert mission.entry.text()=='Web araştırması: '
        mission.findChild(QPushButton,'mission-nav-ai core').click()
        assert ui._merged_dock.isVisible()
        ui._merged_dock.hide()
        mission.findChild(QPushButton,'mission-nav-settings').click()
        assert ui._mission_stack.currentIndex()==0
        ui._mission_home()
        assert ui._mission_stack.currentWidget() is mission
        mission.entry.clear()
        folder=root/'logs/mission';folder.mkdir(parents=True,exist_ok=True)
        ui._win.grab().save(str(folder/'desktop.png'))
        from integration.mission_control import MissionControl
        render=MissionControl(ui,lambda:None)
        render.resize(3840,2160);render.ensurePolished()
        output=QImage(3840,2160,QImage.Format.Format_ARGB32)
        output.fill(0xff000000)
        painter=QPainter(output);render.render(painter);painter.end()
        assert output.save(str(folder/'ultron-mission-control-4k.png'))
        assert (output.width(),output.height())==(3840,2160)
        render.timer.stop();render.telemetry.stop();render.deleteLater()
        (folder/'checks.json').write_text(json.dumps({'status':'PASS','output':[3840,2160],'background_source':[mission.plate.width(),mission.plate.height()],'checks':['default mission screen','buttons bound','browser compose','local AI panel','settings tools and return','UHD native render']},indent=2),encoding='utf-8')
        print('MISSION_CONTROL_NATIVE_UHD_PASS',flush=True)
        ui._app.quit()
    QTimer.singleShot(5000,verify)
integration.panel.attach=attach
import runpy
runpy.run_path(str(root/'mark_app.py'),run_name='__main__')
