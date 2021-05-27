import streamlit as st
import requests
import json
import pandas as pd
from matplotlib import pyplot as plt
import plotly.express as px
import plotly.graph_objs as go
from plotly.offline import init_notebook_mode, plot, iplot
import base64
from IPython.display import HTML
import datetime
# from datetime import date, datetime, timedelta
import time
from requests_futures.sessions import FuturesSession
from apps.keys import header, api_version, fleet_ip, SBD_missions_200, SBD_missions_500, SBD_mission_test
from fpdf import FPDF
from tempfile import NamedTemporaryFile

from pandas.core.common import SettingWithCopyWarning
import warnings
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
config = {'staticPlot': True}

shift_hour = 10
num_shift = 2

def today_format(s):
    today_date = datetime.today().strftime(f"%Y{s}%m{s}%d")
    return today_date

category = { 'MiR_200' : ['MiR_S1166 (MiR_200)','MiR_S1167 (MiR_200)','MiR_S1168 (MiR_200)','MiR_S1169 (MiR_200)','MiR_S1170 (MiR_200)','MiR_S1073 (MiR_200)'],
                'MiR_500' : ['MiR_U0221 (MiR_500)','MiR_U0197 (MiR_500)','MiR_U0224 (MiR_500)','MiR_U0207 (MiR_500)']}

today = (datetime.date.today() + datetime.timedelta(days=1))
three_days_ago = (today - datetime.timedelta(days=5))
# today = today.strftime("%Y-%m-%d")


def convert(seconds): 
    seconds = seconds % (24 * 3600) 
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds) 

def get_robots():
    url = f"http://{fleet_ip}/api/{api_version}/robots/scan"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    robots = r.result().json()
    robot_dict = {}
    for i in range(len(robots)):
        robot_dict[robots[i]['name']] = robots[i]['ip']
    return robot_dict

def get_missions():

    url = f"http://{fleet_ip}/api/{api_version}/missions"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()    
    df = pd.json_normalize(result)
    df = df.set_index('guid')
    return df
gm = get_missions()

def pull_distance(robot_name):
    robot_dict = get_robots()
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/{api_version}/statistics/distance"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
        result = r.result().json()   
    df = pd.json_normalize(result)
    df = df.drop(columns=["allowed_methods"])
    df['robot_name'] = robot_name
    df['distance'] = df['distance']/1000
    df['date'] = pd.to_datetime(df['date'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index("date")
    df = df.resample('D').max()
    df['distance'] = df['distance'].diff()
    df = df.dropna()
    df = df.reset_index()
    if "U" in robot_name:
        df["robot_name"] = robot_name+" (MiR_500)"
    elif "S" in robot_name:
        df["robot_name"] = robot_name+" (MiR_200)"
    return df

def error_log_id(robot_name):
    error_id_all = []
    robot_dict = get_robots()
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/v2.0.0/log/error_reports"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()
    for i in range(len(result)):
        error_id_all.append(result[i]["id"])
    return error_id_all

def error_log(robot_name):    
    robot_dict = get_robots()
    error_ids = error_log_id(robot_name)
    ip = robot_dict[robot_name]
    df = pd.DataFrame()
    with FuturesSession() as session:
        for i in range(len(error_ids)):
            url = f"http://{ip}/api/v2.0.0/log/error_reports/{error_ids[i]}"
            r = session.get(url=url, headers=header)
            result = r.result().json()
            df_temp = pd.json_normalize(result)
            df = df.append(df_temp, ignore_index=True)
    if "U" in robot_name:
        df["robot_name"] = robot_name+" (MiR_500)"
    elif "S" in robot_name:
        df["robot_name"] = robot_name+" (MiR_200)"
    return df

def get_mission_queue_id(robot_name):
    mission_ids = []
    robot_dict = get_robots()
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/v2.0.0/mission_queue"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()
    for i in range(len(result)):
        mission_ids.append(result[i]["id"])
    return mission_ids

def get_mission_log(robot_name):    
    robot_dict = get_robots()
    mission_ids = get_mission_queue_id(robot_name)
    ip = robot_dict[robot_name]
    df = pd.DataFrame()
    with FuturesSession() as session:
        for i in range(len(mission_ids)):
            url = f"http://{ip}/api/{api_version}/mission_queue/{mission_ids[i]}"
            r = session.get(url=url, headers=header)
            result = r.result().json()
            df_temp = pd.json_normalize(result)
            df = df.append(df_temp, ignore_index=True)
    if "U" in robot_name:
        df["robot_name"] = robot_name+" (MiR_500)"
    elif "S" in robot_name:
        df["robot_name"] = robot_name+" (MiR_200)"
    return df

def mission_count(robot_name):
    df = get_mission_log(robot_name)
    df = df.drop(columns=['priority','description','actions','created_by','allowed_methods','control_state','control_posid',
                         'parameters','state','started','created_by_name','mission','fleet_schedule_guid','mission_id',
                          'created_by_id','message','id','robot_name','ordered'])
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index('date')
    df = df.resample('D').count()
    df = df.reset_index()
    return df

def number_mission(robot_name):
    return len(get_mission_queue_id(robot_name))

def number_error(robot_name):
    return len(error_log_id(robot_name))

def error_per_mission(robot_name):
    return round((number_error(robot_name) / number_mission(robot_name)),2)

def error_pie(robot_name):
    a = error_log(robot_name)
    a = a.groupby(['module']).count()
    a = a.reset_index()
    fig = px.pie(a, values='robot_name', names='module',hole=0.5)
    return fig

def get_total_distance(robot_name):
    robot_dict = get_robots()
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/{api_version}/statistics/distance"
    session = requests.Session()
    r = session.get(url, headers=header)
    # r = requests.request("GET", url=url, headers=header)
    distance = r.json()
    d = (distance[-1]['distance'])/1000
    return d

def get_robots_distance():
    robot_dict = get_robots()
    robot_travel = {}
    for robot_name in robot_dict.keys():
        try:
            robot_travel[robot_name] = get_total_distance(robot_name)
        except:
            pass
    return robot_travel

def create_download_link(df,robot_name=None,title=None, filename=None, streamlit=False):
    if title is None:
        title = 'Export Table as CSV'
    if filename is None:
        filename = f'{datetime.date.today()}_{robot_name}_error_log.csv'
    csv = df.to_csv()
    b64 = base64.b64encode(csv.encode())
    payload = b64.decode()
    html = '<a download="{filename}" href="data:text/csv;base64,{payload}" target="_blank">{title}</a>'
    html = html.format(payload=payload,title=title, filename=filename)
    if streamlit:
        return html
    else:
        return HTML(html)

@st.cache(allow_output_mutation=True)
def get_all_robots_distance():
    robot_dict = get_robots()
    df_all = pd.DataFrame()
    for robot_name in robot_dict.keys():
        try:
            df = pull_distance(robot_name)
            df_all = df_all.append(df, ignore_index=True)
        except:
            pass
    df_all["robot_type"] = 'x'
    for row in range(len(df_all)):
        for key in category:
            if (df_all['robot_name'][row] in category[key]):
                df_all['robot_type'][row] = key
    return df_all

def get_all_robots_distance_type():
    df = get_all_robots_distance()
    df = df.set_index('date')
    df = df.groupby(['robot_type']).resample('D').sum()
    df = df.reset_index()
    return df

@st.cache(allow_output_mutation=True)
def get_robots_mission_log():
    robot_dict = get_robots()
    df_all = pd.DataFrame()
    for robot_name in robot_dict.keys():
        try:
            df = get_mission_log(robot_name)
            df_all = df_all.append(df, ignore_index=True)
        except:
            pass
    df_all = df_all.set_index('mission_id')
    df_all['mission_name'] = gm['name']
    df_all = df_all.reset_index()
    df_all['started'] = pd.to_datetime(df_all['started'],format='%Y-%m-%dT%H:%M:%S')
    df_all['finished'] = pd.to_datetime(df_all['finished'],format='%Y-%m-%dT%H:%M:%S')
    df_all['robot_type'] = 'x'
    for row in range(len(df_all)):
        for key in category:
            if (df_all['robot_name'][row] in category[key]):
                df_all['robot_type'][row] = key
    return df_all

def get_robots_mission():
    df = get_robots_mission_log()
    df = df.copy().loc[~df['mission_id'].astype(str).str.contains('mirconst')]
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index("date")
    return df

def get_robots_mission_count():
    df = get_robots_mission()
    df = df.groupby(['robot_type']).resample('D').count()
    df = df.drop(columns=['priority','description','actions','created_by','allowed_methods','control_state','control_posid',
                     'parameters','state','started','created_by_name','mission','fleet_schedule_guid','mission_id',
                      'created_by_id','message','id','ordered','robot_name','robot_type'])
    df = df.reset_index()
    df = df.sort_values(by='date')
    return df

@st.cache(allow_output_mutation=True)
def get_robots_error_log():
    robot_dict = get_robots()
    df_all = pd.DataFrame()
    for robot_name in robot_dict.keys():
        try:
            df = error_log(robot_name)
            df_all = df_all.append(df, ignore_index=True)
        except:
            pass
    df_all['robot_type'] = 'x'
    for row in range(len(df_all)):
        for key in category:
            if (df_all['robot_name'][row] in category[key]):
                df_all['robot_type'][row] = key
    return df_all

def num_mission_all():
    robot_dict = get_robots()
    num = 0
    for robot_name in robot_dict.keys():
        try:
            num += number_mission(robot_name)
        except:
            pass
    return num

def num_error_all():
    robot_dict = get_robots()
    num = 0
    for robot_name in robot_dict.keys():
        try:
            num += number_error(robot_name)
        except:
            pass
    return num

def unstacking(df_in):
    df = df_in
    df = df.set_index("date")
    df = df.groupby('state').resample('D').count()
    df = df.drop(columns=['robot_name','mission_name','state'])
    df = df.unstack(1)
    df = df.transpose()
    df = df.reset_index()
    df = df.drop(columns=['level_0'])
    df["Done"] = df["Done"].fillna(0)
    df = df.rename(index={'state': 'Index'})
    df['Total'] = df.Aborted + df.Done
    df['SuccessRate%'] = round((df.Done / df.Total)*100, 2)
    df["SuccessRate%"] = df["SuccessRate%"].fillna(0)
    return df

# MiR 500
def pallet_move():
    df = get_robots_mission_log()
    df = df[df.robot_type == 'MiR_500']
    df = df.copy().loc[df.mission_id.isin(SBD_missions_500)]
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.drop(columns=['priority','description','actions','created_by','allowed_methods','control_state','control_posid',
                     'parameters','started','created_by_name','mission','fleet_schedule_guid',
                      'created_by_id','message','id','ordered','finished','robot_type'])
    df = df.reset_index(drop=True)
    df = df.sort_values(by='date')
    df = df.dropna()
    return df

def pallet_move_count():
    df = pallet_move()
    df = df.set_index("date")
    df = df.groupby('state').resample('D').count()
    df = df.drop(columns=['robot_name','mission_name','state'])
    df = df.reset_index()
    df = df.sort_values(by=['date'])
    df = df.rename(columns={'mission_id' : 'count'})
    return df

# MiR 200
def cart_move():
    df = get_robots_mission_log()
    df = df[df.robot_type == 'MiR_200']
    df = df.copy().loc[df.mission_id.isin(SBD_missions_200)]
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.drop(columns=['priority','description','actions','created_by','allowed_methods','control_state','control_posid',
                     'parameters','started','created_by_name','mission','fleet_schedule_guid',
                      'created_by_id','message','id','ordered','finished','robot_type'])
    df = df.reset_index(drop=True)
    df = df.sort_values(by='date')
    df = df.dropna()
    return df

def cart_move_count():
    df = cart_move()
    df = df.set_index("date")
    df = df.groupby('state').resample('D').count()
    df = df.drop(columns=['robot_name','mission_name','state'])
    df = df.reset_index()
    df = df.sort_values(by=['date'])
    df = df.rename(columns={'mission_id' : 'count'})
    return df


def get_robots_utilization():
    s_in_day = int(num_shift) * int(shift_hour) * 3600
    df = get_robots_mission_log()
    df = df.drop(columns=['priority','description','parameters','created_by_name','mission','actions','created_by',
                         'allowed_methods','control_state','control_posid','fleet_schedule_guid','id'])
    df_200 = df.copy().loc[df.mission_id.isin(SBD_missions_200)]
    df_500 = df.copy().loc[df.mission_id.isin(SBD_missions_500)]
    df = pd.concat([df_200, df_500])
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index('date')
    df['ran_for_s'] = (df.finished - df.started).dt.total_seconds()
    df = df.groupby(['robot_name']).resample('D').sum()
    df['utilization_per'] = round((df.ran_for_s / s_in_day) * 100,2)
    df = df.reset_index()
    df = df.loc[(df.utilization_per < 100)]
    return df

def get_robots_real_mission_count():
    df = get_robots_mission_log()
    df = df.drop(columns=['priority','description','parameters','created_by_name','mission','actions','created_by',
                         'allowed_methods','control_state','control_posid','fleet_schedule_guid','id'])
    df_200 = df.copy().loc[df.mission_id.isin(SBD_missions_200)]
    df_500 = df.copy().loc[df.mission_id.isin(SBD_missions_500)]
    df = pd.concat([df_200, df_500])
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.sort_values(by=['date'])
    df = df.reset_index(drop=True)
    return df 

def groupby_mission_count(groupby):
    df = get_robots_real_mission_count()
    df = df.set_index("date")
    df = df.groupby([f"{groupby}"]).resample('D').count()
    df = df[["mission_id"]]
    df = df.rename(columns={"mission_id":"count"})
    df = df.reset_index()
    return df

def get_robot_mission_count(robot_name):
    df = get_mission_log(robot_name)
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index("date")
    if "S" in robot_name:
        df = df.copy().loc[df.mission_id.isin(SBD_missions_200)]
    if "U" in robot_name:
        df = df.copy().loc[df.mission_id.isin(SBD_missions_500)]
    df = df.groupby(['state']).resample('D').count()
    df = df[['ordered']]
    df = df.rename(columns={'ordered' : "count"})
    df = df.reset_index()
    return df


def get_robot_type_utilization():
    s_in_day = int(num_shift) * int(shift_hour) * 3600
    df = get_robots_mission_log()
    df = df.drop(columns=['priority','description','parameters','created_by_name','mission','actions','created_by',
                         'allowed_methods','control_state','control_posid','fleet_schedule_guid','id'])
    df_200 = df.copy().loc[df.mission_id.isin(SBD_missions_200)]
    df_500 = df.copy().loc[df.mission_id.isin(SBD_missions_500)]
    df = pd.concat([df_200, df_500])
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index('date')
    df['ran_for_s'] = (df.finished - df.started).dt.total_seconds()

    df = df.groupby(['robot_type']).resample('D').sum()
    df['utilization_per'] = round((df.ran_for_s / s_in_day) * 100,2)
    df = df.reset_index()
    df = df.loc[(df.utilization_per < 100)]
    return df

def last_error(day,robot_type):
    df = get_robots_error_log()
    df = df[df.robot_type == robot_type]
    df['time'] = pd.to_datetime(df['time'],format='%Y-%m-%dT%H:%M:%S')
    df = df.sort_values(by=['time'])
    df = df.set_index("time")  
    df = df.last(f"{day}D")
    df = df.groupby("module").count()
    df = df.reset_index()
    df = df[["module", "description"]]
    df = df.rename(columns={"description":"count"})
    return df

def last_error_time(day,robot_type):
    df = get_robots_error_log()
    df = df[df.robot_type == robot_type]
    df['time'] = pd.to_datetime(df['time'],format='%Y-%m-%dT%H:%M:%S')
    df = df.sort_values(by=['time'])
    df = df.set_index("time")  
    df = df.last(f"{day}D")
    df = df.groupby("module").resample("D").count()
    df = df[["description"]]
    df = df.rename(columns={"description":"count"})
    df = df.reset_index()
    return df

def robot_last_error(robot_name,day):
    df = error_log(robot_name)
    df['time'] = pd.to_datetime(df['time'],format='%Y-%m-%dT%H:%M:%S')
    df = df.sort_values(by=['time'])
    df = df.set_index("time")  
    df = df.last(f"{day}D")
    df = df.groupby("module").count()
    df = df.reset_index()
    df = df[["module", "description"]]
    df = df.rename(columns={"description":"count"})
    return df

def robot_last_error_time(robot_name, day):
    df = error_log(robot_name)
    df['time'] = pd.to_datetime(df['time'],format='%Y-%m-%dT%H:%M:%S')
    df = df.sort_values(by=['time'])
    df = df.set_index("time")  
    df = df.last(f"{day}D")
    df = df.groupby("module").resample("D").count()
    df = df[["description"]]
    df = df.rename(columns={"description":"count"})
    df = df.reset_index()
    return df


def MiR200_test():
    df = get_robots_mission_log()
    df = df.copy().loc[df.mission_id.isin(SBD_mission_test)]
    df['date'] = pd.to_datetime(df['finished'],format='%Y-%m-%dT%H:%M:%S')
    df = df.set_index("date")
    df = df.drop(columns=['priority','description','actions','created_by','allowed_methods','control_state','control_posid',
                     'parameters','state','started','created_by_name','mission','fleet_schedule_guid','mission_id',
                      'created_by_id','message','id','ordered','finished','robot_type'])
    return df

def MiR200_test_count():
    df = MiR200_test()

    df = df.groupby(['robot_name']).resample('D').count()
    df = df.drop(columns=['robot_name'])
    df = df.rename(columns={'mission_name' : 'count'})
    df = df.reset_index()
    return df


def create_download_link_pdf(val, filename):
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'

def available_robot():
    robot_dict = get_robots()
    df = pd.DataFrame.from_dict(robot_dict,orient='index')
    df = df.reset_index()
    for i in range(len(df)):
        if "U" in df.loc[i,'index']:
            df.at[i,"index"] += " (MiR_500)"
        elif "S" in df.loc[i,'index']:
            df.at[i,"index"] += " (MiR_200)"
    df = df.rename(columns={'index':'Robot Name', 0 : 'IP Address'})

    df.index += 1
    return df

def robot_page(robot_name):
# try:
    start_date = st.sidebar.date_input('Start Date', three_days_ago)
    end_date = st.sidebar.date_input('End Date', today)
    delta_date = (end_date - start_date).days


    st.subheader(f'{robot_name} Mission Count Over Last {delta_date} Days')
    fig_robot_mission_count = px.bar(get_robot_mission_count(robot_name), x='date', y='count', 
                                        title=f'{robot_name} Mission Count over the {delta_date} days', 
                                        color='state',
                                        color_discrete_map={
                                                "Aborted":"#EF553B",
                                                "Done" : "#00CC96"
                                                    }, 
                                        barmode='group')

    fig_robot_mission_count.update_layout(xaxis_range=[start_date, end_date])      
    st.plotly_chart(fig_robot_mission_count, use_container_width=True)


    st.subheader(f'{robot_name} Has Traveled Over Last {delta_date} Days')                    
    df_dt = pull_distance(robot_name)
    fig_dt = px.bar(df_dt, x='date', y='distance', 
                    labels={
                    "distance": "distance (km)"}, title=f'{robot_name} Milage over the {delta_date} days')
    fig_dt.update_layout(xaxis_range=[start_date, end_date])
    st.plotly_chart(fig_dt,use_container_width=True)


    st.subheader(f'{robot_name} Errors Over Last {delta_date} Days')
    fig_error_bar = px.bar(robot_last_error_time(robot_name,delta_date), x='time', y='count', color="module",
                                            barmode='group',
                                            color_discrete_map={
                                                "AMCL":"rgb(27,158,119)",
                                                "Planner":"rgb(217,95,2)",
                                                "Mapping":"rgb(117,112,179)",
                                                "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                                "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                                "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                                "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                                "MissionController": "rgb(0,204,102)",
                                                "/Power System/Battery": "rgb(0,204,204)",
                                                "/Power System/Charger": "rgb(0,128,255)",
                                                "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                                        })
    fig_error_bar.update_layout(xaxis_range=[start_date, end_date])
    st.plotly_chart(fig_error_bar,use_container_width=True)  

    st.subheader(f'{robot_name} Errors Over Last {delta_date} Days')
    fig_error_pie = px.pie(robot_last_error(robot_name,delta_date), values='count', names='module',
                                            hole=0.3,
                                            color_discrete_map={
                                                "AMCL":"rgb(27,158,119)",
                                                "Planner":"rgb(217,95,2)",
                                                "Mapping":"rgb(117,112,179)",
                                                "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                                "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                                "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                                "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                                "MissionController": "rgb(0,204,102)",
                                                "/Power System/Battery": "rgb(0,204,204)",
                                                "/Power System/Charger": "rgb(0,128,255)",
                                                "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                                        })
    fig_error_pie.update_traces(textinfo='percent+value')
    fig_error_pie.update_layout(xaxis_range=[start_date, end_date])
    st.plotly_chart(fig_error_pie,use_container_width=True)        

    # ml = get_mission_log(robot_name)
    # st.subheader(f"{robot_name}'s mission log")
    # st.write(ml)
    # st.markdown(create_download_link(ml, robot_name=robot_name, title=f"Download {robot_name}'s mission log as CSV", streamlit='True'), unsafe_allow_html=True)
    
    # st.subheader(f"{robot_name}'s error log")
    # st.write(error_log(robot_name))
    # st.markdown(create_download_link(error_log(robot_name), robot_name=robot_name, title=f"Download {robot_name}'s error log as CSV", streamlit='True'), unsafe_allow_html=True)
    st.write(get_robot_mission_count(robot_name))
        # except:
        #     st.warning(f"Oops, `{robot_name}` is not available at the moment.")
    

def fleet_page():
    # try:        
    start_time = time.time()
    
    st.title('MiR Fleet')

    st.subheader('Available Robots:')
    st.table(available_robot())
    start_date = st.sidebar.date_input('Start Date', three_days_ago)
    end_date = st.sidebar.date_input('End Date', today)
    delta_date = (end_date - start_date).days
    if delta_date >= 0:
        ###################### MISSION COUNT (NAME) ######################
        st.subheader(f'Mission Count (Per Robot) Over Last {delta_date} Days')
        robots_mission_type = groupby_mission_count("robot_name")
        fig_mission_count = px.bar(robots_mission_type, x='date', y='count',color='robot_name', 
                title="Mission Count Per Robot Name (Cart+Pallet)",
                labels={'count':'Mission Completed'
                    }, 
                    barmode='group',
                    color_discrete_map={
                                "MiR_S1073 (MiR_200)":"rgb(255,51,51)",
                                "MiR_S1166 (MiR_200)":"rgb(255,153,51)",
                                "MiR_S1167 (MiR_200)":"rgb(255,255,0)",
                                "MiR_S1168 (MiR_200)":"rgb(0,204,0)",
                                "MiR_S1169 (MiR_200)": "rgb(0,204,102)",
                                "MiR_S1170 (MiR_200)": "rgb(0,204,204)",
                                "MiR_U0221 (MiR_500)": "rgb(0,128,255)",
                                "MiR_U0197 (MiR_500)": "rgb(51,51,255)",
                                "MiR_U0207 (MiR_500)": "rgb(217,0,255)",
                                "MiR_U0224 (MiR_500)": "rgb(255,102,178)"}
                            )

        # fig_mission_count.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])))
        fig_mission_count.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_mission_count,use_container_width=True,config=config)

        checkbox_mission_count = st.checkbox("Show Data", key='checkbox_mission_count_name')
        if checkbox_mission_count:
            st.write(get_robots_real_mission_count())

        ###################### MISSION COUNT (TYPE) ######################
        st.subheader(f'Mission Count (Per Robot Type) Over Last {delta_date} Days')
        robots_mission_type = groupby_mission_count("robot_type")
        fig_mission_count_type = px.bar(robots_mission_type, x='date', y='count',color='robot_type', 
                title="Mission Count Per Robot Type (Cart+Pallet)",
                labels={'count':'Mission Completed'
                    }, barmode='group',
                    color_discrete_map={
                        "MiR_200":"#636EFA",
                        "MiR_500":"#EF553B"}
                                    )

        # fig_mission_count_type.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])))
        fig_mission_count_type.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_mission_count_type,use_container_width=True,config=config)

        checkbox_mission_count = st.checkbox("Show Data", key='checkbox_mission_count_type')
        if checkbox_mission_count:
            st.write(get_robots_real_mission_count())

        ###################### MiR200s ######################
        st.subheader(f'MiR 200 Cart Count Over Last {delta_date} Days')
        fig_200 = px.bar(cart_move_count(), x='date', y='count',title='Mission Count (Cart)',
                            color_discrete_map={
                                                "Aborted":"#EF553B",
                                                "Done" : "#00CC96"
                                                    },
                            color='state', barmode='group')

        # fig_200.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])
        #     )
        # )
        # fig_200.update_traces(textposition='outside')
        fig_200.update_layout(xaxis_range=[start_date, end_date])
        fig_200.update_xaxes(showgrid=True)
        fig_200.update_yaxes(showgrid=True)
        st.plotly_chart(fig_200,use_container_width=True,config=config)
        checkbox_200 = st.checkbox("Show Data", key='checkbox_200')
        if checkbox_200:
            st.table(unstacking(cart_move()))
            st.write(cart_move())
            
        ###################### MiR500s ######################
        st.subheader(f'MiR 500 Pallet Count Over Last {delta_date} Days')
        fig_500 = px.bar(pallet_move_count(), x='date', y='count',title='Mission Count (Pallet)',
                            color_discrete_map={
                                                "Aborted":"#EF553B",
                                                "Done" : "#00CC96"
                                                    },
                            color='state', barmode='group')

        # fig_500.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])
        #     )
        # )
        # fig_500.update_traces(textposition='outside')
        fig_500.update_layout(xaxis_range=[start_date, end_date])
        fig_500.update_xaxes(showgrid=True)
        fig_500.update_yaxes(showgrid=True)
        st.plotly_chart(fig_500,use_container_width=True,config=config)
        
        checkbox_500 = st.checkbox("Show Data", key='checkbox_500')
        if checkbox_500:
            st.table(unstacking(pallet_move()))
            st.write(pallet_move())

        ###################### Utilization_robots ######################
        st.subheader(f'Utilization Per Robot Over Last {delta_date} Days')
        st.markdown(f"*Definition* of **Utilization**:\
                    Sum of time-spent to do value-added missions over {num_shift * shift_hour} hours")
        # st.latex(r'''$$Utilization = \frac{\sum T_{value\_added\; missions}}{20\; hours} * 100\% $$''')
        
        
        fig_uti_robots = px.bar(get_robots_utilization(), x='date', y='utilization_per',
                            labels={"utilization_per": "Utilization Percentage"},
                            color='robot_name',barmode='group',
                            title='Utilization of Robots (Cart+Pallet)'
                            ,color_discrete_map={
                                "MiR_S1073 (MiR_200)":"rgb(255,51,51)",
                                "MiR_S1166 (MiR_200)":"rgb(255,153,51)",
                                "MiR_S1167 (MiR_200)":"rgb(255,255,0)",
                                "MiR_S1168 (MiR_200)":"rgb(0,204,0)",
                                "MiR_S1169 (MiR_200)": "rgb(0,204,102)",
                                "MiR_S1170 (MiR_200)": "rgb(0,204,204)",
                                "MiR_U0221 (MiR_500)": "rgb(0,128,255)",
                                "MiR_U0197 (MiR_500)": "rgb(51,51,255)",
                                "MiR_U0207 (MiR_500)": "rgb(217,0,255)",
                                "MiR_U0224 (MiR_500)": "rgb(255,102,178)"}
                            )

        # fig_uti_robots.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])
        #     )
        # )
        fig_uti_robots.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_uti_robots,use_container_width=True,config=config)

        
        checkbox_utilization = st.checkbox("Show Data", key='checkbox_utilization')
        if checkbox_utilization:
            # st.write(get_robots_utilization())
            st.write(get_robots_utilization())
        ###################### Utilization_robots_type ######################
        st.subheader(f'Utilization Per Robot Type Over Last {delta_date} Days')
        st.markdown(f"*Definition* of **Utilization**:\
                    Sum of time-spent to do value-added missions over {num_shift * shift_hour} hours")
        # st.latex(r'''$$Utilization = \frac{\sum T_{value\_added\; missions}}{20\; hours} * 100\% $$''')
        fig_uti_type = px.bar(get_robot_type_utilization(), x='date', y='utilization_per',
                                labels={"utilization_per": "Utilization Percentage"},
                                color='robot_type',barmode='group',
                                title='Utilization of Robots Type (Cart+Pallet)',
                                color_discrete_map={
                                    "MiR_200":"#636EFA",
                                    "MiR_500":"#EF553B"}
                                                )

        # fig_uti_type.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])
        #     )
        # )
        fig_uti_type.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_uti_type,use_container_width=True,config=config)
        checkbox_utilization_robot_type = st.checkbox("Show Data", key='checkbox_utilization_robot_type')
        if checkbox_utilization_robot_type:
            st.write(get_robot_type_utilization())

        ###################### Distance Per Robot ######################
        st.subheader(f'Robots Traveled Distance Per Robot over {delta_date} Days')
        fig_distance_robot = px.bar(get_all_robots_distance(), x='date', y='distance',
                color='robot_name', labels={'distance':'Distance (km)'},
                barmode='group', title='Distance Traveled Per Robots')
        fig_distance_robot.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_distance_robot,use_container_width=True)
        checkbox_dist_robot = st.checkbox("Show Data", key='checkbox_dist_robot')
        if checkbox_dist_robot:
            st.write(get_all_robots_distance())

        ###################### Distance Per Robot Type ######################
        st.subheader(f'Robots Traveled Distance Per Robot Type over {delta_date} Days')
        fig_distance_type = px.bar(get_all_robots_distance_type(), x='date', y='distance',
                color='robot_type', labels={'distance':'Distance (km)'},
                barmode='group', title='Distance Traveled Per Robots Type')
        fig_distance_type.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_distance_type,use_container_width=True)
        checkbox_dist_robot_type = st.checkbox("Show Data", key='checkbox_dist_robot_type')
        if checkbox_dist_robot_type:
            st.write(get_all_robots_distance_type())

        ###################### MiR Testing ######################
        # st.subheader(f'MiR Testing Over Last {delta_date} Days')
        # fig_test_count = px.bar(MiR200_test_count(), x='date', y='count',
        #         labels={'robot_name':'Test Mission Count'}, color='robot_name', 
        #         barmode='group', title='Mission Count (ROEQ Test 1,2,3,4)')

        # fig_test_count.update_xaxes(
        #     rangeslider_visible=True,
        #     rangeselector=dict(
        #         buttons=list([
        #             dict(count=7, label="7d", step="day", stepmode="backward"),
        #             dict(count=3, label="3m", step="month", stepmode="backward"),
        #             dict(count=6, label="6m", step="month", stepmode="backward"),
        #             dict(count=1, label="YTD", step="year", stepmode="todate"),
        #             dict(count=1, label="1y", step="year", stepmode="backward"),
        #             dict(step="all")
        #         ])
        #     )
        # )
        # fig_test_count.update_layout(xaxis_range=[start_date, end_date])
        # st.plotly_chart(fig_test_count,use_container_width=True)
        # checkbox_test = st.checkbox("Show Data", key='checkbox_test')
        # if checkbox_test:
        #     st.write(MiR200_test())
        ###################### DOWNLOADABLE DATA ######################
        # fleet_expander = st.beta_expander("Download Data", expanded=False)
        # with fleet_expander:
        #     st.success(f"The MiR Fleet ran **{num_mission_all()}** missions in total and had **{num_error_all()}** errors since the beginning.")
        #     st.subheader("CMO MiR Robots' Mission Log")
        #     st.write(get_robots_mission_log())
        #     st.markdown(create_download_link(get_robots_mission_log(), title=f"Download all mission log as CSV", streamlit='True',filename=f"{date.today()}all_mission_log.csv"), unsafe_allow_html=True)
            
        #     st.subheader("CMO MiR Robots' Error Log")
        #     st.write(get_robots_error_log())
        #     st.markdown(create_download_link(get_robots_error_log(), title=f"Download all error log as CSV", streamlit='True',filename=f"{date.today()}_all_error_log.csv"), unsafe_allow_html=True)

        ##################### ERROR OVER TIME 200 ######################
        st.subheader(f'MiR 200 Errors Over Last {delta_date} Days')
        fig_error_time_200 = px.bar(last_error_time(delta_date,"MiR_200"), 
                                x='time', y='count', color="module",
                                barmode='group',
                                color_discrete_map={
                                    "AMCL":"rgb(27,158,119)",
                                    "Planner":"rgb(217,95,2)",
                                    "Mapping":"rgb(117,112,179)",
                                    "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                    "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                    "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                    "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                    "MissionController": "rgb(0,204,102)",
                                    "/Power System/Battery": "rgb(0,204,204)",
                                    "/Power System/Charger": "rgb(0,128,255)",
                                    "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                    })
        fig_error_time_200.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_error_time_200,use_container_width=True,config=config)

        ##################### ERRORS MiR_200 ######################
        st.subheader(f'MiR 200 Errors Over Last {delta_date} Days')
        fig_error_pie_200 = px.pie(last_error(delta_date,"MiR_200"), values='count',names="module",
                                                hole=0.3,
                                                color_discrete_map={
                                                "AMCL":"rgb(27,158,119)",
                                                "Planner":"rgb(217,95,2)",
                                                "Mapping":"rgb(117,112,179)",
                                                "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                                "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                                "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                                "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                                "MissionController": "rgb(0,204,102)",
                                                "/Power System/Battery": "rgb(0,204,204)",
                                                "/Power System/Charger": "rgb(0,128,255)",
                                                "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                                            })
        fig_error_pie_200.update_traces(textinfo='percent+value')
        st.plotly_chart(fig_error_pie_200,use_container_width=True)

        ##################### ERROR OVER TIME 500 ######################
        st.subheader(f'MiR 500 Errors Over Last {delta_date} Days')
        fig_error_time_500 = px.bar(last_error_time(delta_date,"MiR_500"), 
                                x='time', y='count', color="module",
                                barmode='group',
                                color_discrete_map={
                                    "AMCL":"rgb(27,158,119)",
                                    "Planner":"rgb(217,95,2)",
                                    "Mapping":"rgb(117,112,179)",
                                    "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                    "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                    "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                    "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                    "MissionController": "rgb(0,204,102)",
                                    "/Power System/Battery": "rgb(0,204,204)",
                                    "/Power System/Charger": "rgb(0,128,255)",
                                    "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                    })
        fig_error_time_500.update_layout(xaxis_range=[start_date, end_date])
        st.plotly_chart(fig_error_time_500,use_container_width=True,config=config)

        ##################### ERRORS MiR_500 ######################
        st.subheader(f'MiR 500 Errors Over Last {delta_date} Days')
        fig_error_pie_500 = px.pie(last_error(delta_date,"MiR_500"), values='count',names="module",
                                                hole=0.3,
                                                color_discrete_map={
                                                    "AMCL":"rgb(27,158,119)",
                                                    "Planner":"rgb(217,95,2)",
                                                    "Mapping":"rgb(117,112,179)",
                                                    "/Sensors/3D camera (Left)/Connection":"rgb(255,51,51)",
                                                    "/Sensors/3D camera (Right)/Connection":"rgb(255,153,51)",
                                                    "/Sensors/3D camera (Left)/Metrics":"rgb(255,255,0)",
                                                    "/Sensors/3D camera (Right)/Metrics":"rgb(0,204,0)",
                                                    "MissionController": "rgb(0,204,102)",
                                                    "/Power System/Battery": "rgb(0,204,204)",
                                                    "/Power System/Charger": "rgb(0,128,255)",
                                                    "/Safety System/Emergency Stop": "rgb(51,51,255)"
                                                            })
        fig_error_pie_500.update_traces(textinfo='percent+value')
        st.plotly_chart(fig_error_pie_500,use_container_width=True)


        ###################### EXPORT CHARTS ######################
        # export_as_pdf = st.button("Export Report")
        # if export_as_pdf:
        #     figs = [fig_mission_count,
        #             fig_mission_count_type,
        #             fig_200,
        #             fig_500,
        #             fig_uti_robots,
        #             fig_uti_type,
        #             fig_error_time_200,
        #             fig_error_time_500]
        #     pdf = FPDF()
        #     for fig in figs:
        #         pdf.add_page()
        #         with NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        #                 fig.write_image(tmpfile.name)
        #                 pdf.image(tmpfile.name, 10, 10, 190, 110)
        #     html = create_download_link_pdf(pdf.output(dest="S").encode("latin-1"), f"{today_format('_')}_daily_report")
        #     st.markdown(html, unsafe_allow_html=True)

        st.info(f"It took {convert(time.time() - start_time)}")

        # except:
        #     st.warning("Oops, the MiR Fleet is not available at the moment.")
    else:
        st.error("Error! The input **Start Date** is later than the **End Date**")
    
