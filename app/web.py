from flask import render_template
from app.config import MODULES,TITLE,SHORT
from app.pipeline import execute,load_sample
from app import store
def register_pages(app):
    def page(index):
        run=store.latest() or execute(load_sample("dirty.csv"))
        stage=run["stages"][index]
        rows=stage["rows"]
        choices=[['event_id','card','route','event_time','result','reported'],['event_id','card','route','line_group'],['event_id','card','fare_version','base_fare','reported','at'],['journey','card','route','business_day','at'],['event_id','card','route','base_fare','transfer_anchor','transfer_discount','cap_discount','expected','day_paid'],['event_id','card','expected','reported','difference','status'],['event_id','card','expected','reported','status']]
        columns=choices[index]
        labels={'event_id':'事件','card':'卡号','route':'线路','event_time':'刷卡时间','result':'刷卡状态','reported':'实扣 / 元','line_group':'线路组','fare_version':'票价版','base_fare':'基础票价','at':'事件时间 UTC','journey':'行程编号','business_day':'业务日','transfer_anchor':'锚点','transfer_discount':'换乘优惠','cap_discount':'封顶减免','expected':'应扣 / 元','day_paid':'日累计','difference':'差额 / 元','status':'结论','accepted':'采纳行','versions':'版本','expected_total':'应扣总额','daily_caps':'卡日数量','transfer_hits':'换乘次数','input':'输入行','quarantine':'隔离行','duplicate':'重复行','blank':'空白行','repeated_headers':'重复表头','encoding':'编码','routes':'线路数','cards':'卡数','journeys':'行程数','records':'记录数','source_lines':'来源行数','sha256':'摘要','ready':'可归档','differences':'差异项'}
        for key,label in {'accepted_inputs': '采纳来源行', 'quarantine_inputs': '隔离来源行', 'output_records': '结果记录', 'input': '输入行', 'excluded': '排除行', 'balanced': '行数平衡', 'expected_total': '预期合计', 'reported_total': '申报合计', 'differences': '差异项', 'blank': '空行', 'repeated_headers': '分段表头', 'encoding': '编码', 'duplicate': '重复行', 'quarantine': '隔离行', 'accepted': '采纳行', 'sha256': '校验摘要', 'ready': '可归档'}.items(): labels.setdefault(key,label)
        return render_template(f"m{index+1}.html",title=TITLE,short=SHORT,modules=MODULES,index=index,run=run,stage=stage,rows=rows,columns=columns[:12],history=store.history(),labels=labels)
    app.add_url_rule("/",view_func=lambda:page(4))
    for index,(slug,name) in enumerate(MODULES):
        app.add_url_rule("/"+slug,endpoint="page_"+slug,view_func=lambda index=index:page(index))
