import requests
import json
import pandas as pd
from matplotlib import pyplot as plt
import plotly.express as px
from datetime import date,datetime
import time
from requests_futures.sessions import FuturesSession
import numpy as np
import os
from openpyxl import load_workbook

category = { 'MiR_200' : ['MiR_S1166','MiR_S1167','MiR_S1168','MiR_S1169','MiR_S1170','MiR_S1073'],
                'MiR_500' : ['MiR_U0221','MiR_U0197','MiR_U0224','MiR_U0207']}

fleet_ip = "10.46.175.228"
header = {
    "Content-Type" : "application/json",
    "Authorization" : "Basic ZXRsX3JlYWRlcjplNjgwMmQ0OTU4MDdjZTRmOGZlYWFhYzRiODM5YjUyNDUzYWVmZWQzMzA4NTdmNTQyZDRlYjY0ZTE4ZDUyYjdj"
}
api_version = "v2.0.0"

def get_robots():
    '''
    Getting all available robots
    Input: None
    Ouput: robot_name and its IP address
    '''
    url = f"http://{fleet_ip}/api/{api_version}/robots/scan"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    robots = r.result().json()
    robot_dict = {}
    for i in range(len(robots)):
        robot_dict[robots[i]['name']] = robots[i]['ip']
    return robot_dict

def get_missions():
    '''
    Pulling all programs
    Input: None
    Ouput: missions (df)
    '''
    url = f"http://{fleet_ip}/api/{api_version}/missions"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()    
    df = pd.json_normalize(result)
    df = df.set_index('guid')
    return df

gm = get_missions()

def get_mission_queue_id(robot_name):
    '''
    Pulling mission log id from one robot
    Input: robot's name (str)
    Ouput: robot's mission id  (list)
    '''
    mission_ids = []
    robot_dict = get_robots()
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/{api_version}/mission_queue"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()
    for i in range(len(result)):
        mission_ids.append(result[i]["id"])
    return mission_ids

def get_mission_log(robot_name): 
    '''
    Pulling mission log from one robot
    Input: robot's name (str)
    Ouput: robot's error log (df)
    '''
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
        df["robot_name"] = robot_name
    return df

def get_robots_mission_log():
    '''
    loop thur all available robots and collect mission logs
    Input: None
    Ouput: all available robots' mission logs (df)
    '''
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
                df_all.copy()['robot_type'][row] = key
    return df_all

def error_log_id(robot_name):
    '''
    Pulling error log id from one robot
    Input: robot's name (str)
    Ouput: robot's error id  (list)
    '''
    robot_dict = get_robots()
    id_all = []
    ip = robot_dict[robot_name]
    url = f"http://{ip}/api/{api_version}/log/error_reports"
    with FuturesSession() as session:
        r = session.get(url=url, headers=header)
    result = r.result().json()
    for i in range(len(result)):
        id_all.append(result[i]["id"])
    return id_all

def error_log(robot_name):
    '''
    Pulling error log from one robot
    Input: robot's name (str)
    Ouput: robot's error log (df)
    '''
    robot_dict = get_robots()
    error_id_all = error_log_id(robot_name)
    ip = robot_dict[robot_name]
    df = pd.DataFrame()
    for i in range(len(error_id_all)):
        url = f"http://{ip}/api/{api_version}/log/error_reports/{error_id_all[i]}"
        with FuturesSession() as session:
            r = session.get(url=url, headers=header)
        result = r.result().json()
        df_temp = pd.json_normalize(result)
        df = df.append(df_temp, ignore_index=True)
    df["robot_name"] = robot_name
    return df

def get_robots_error_log():
    '''
    loop thur all available robots and collect error logs
    Input: None
    Ouput: all available robots' error logs (df)
    '''
    robot_dict = get_robots()
    df_all = pd.DataFrame()
    for robot_name in robot_dict.keys():
        try:
            df = error_log(robot_name)
            df_all = df_all.append(df, ignore_index=True)
        except:
            pass
    return df_all



# get_robots_mission_log()
# get_robots_error_log()