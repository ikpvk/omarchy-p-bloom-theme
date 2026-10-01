"""Reviewable quality-pass drawings; deterministic paths, type and data labels."""
from century.render import draw_view,callouts


def main_hardware(s,slug,mx,my):
    entry={'slug':slug,'number':0}
    anchors=draw_view(s,entry,'A',mx,my-20,652,675)
    callouts(s,entry,anchors,mx,my)


def component(s,slug,key,cx,cy,w,h):
    return draw_view(s,{'slug':slug,'number':0},key,cx,cy,w,h)


def aroma_detail(s,rx):
    component(s,'aroma-command','A',rx,313,350,270)
    s.view_label(rx,495,'C','ODOUR COMMAND PATH','METERING HARDWARE / SIX OF 96 CHANNELS SHOWN')
